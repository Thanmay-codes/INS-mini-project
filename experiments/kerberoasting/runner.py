"""Bounded synthetic service-password guessing runner (B05, Kerberoasting-inspired)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kerberos_lab.common._validation import exact_fields, identifier, integer  # noqa: E402
from kerberos_lab.common.crypto import (  # noqa: E402
    decode_b64,
    derive_service_key,
    encode_b64,
    new_identifier,
    open_ticket,
    seal_ticket,
)
from kerberos_lab.common.errors import InvalidAuthentication, MalformedRequest  # noqa: E402
from kerberos_lab.common.models import Ticket  # noqa: E402

DEFAULT_WORDLIST = ROOT / "data" / "wordlists" / "demo.txt"
DEFAULT_ITERATIONS = 100_000
DEFAULT_SALT_BYTES = 16
DEFAULT_TICKET_LIFETIME_SECONDS = 300
DEFAULT_BASE_TIME = 1_700_000_000


def load_candidate_wordlist(path: Path) -> list[str]:
    """Load non-empty candidate lines from a local wordlist file."""
    if not path.is_file():
        raise MalformedRequest("missing_wordlist")
    candidates = [
        line.rstrip("\r\n")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.rstrip("\r\n")
    ]
    if not candidates:
        raise MalformedRequest("empty_wordlist")
    return candidates


def acquire_synthetic_service_ticket(
    *,
    service_password: str,
    service_id: str = "files",
    client_id: str = "alice",
    salt: bytes | None = None,
    iterations: int = DEFAULT_ITERATIONS,
    issued_at: int = DEFAULT_BASE_TIME,
    output_path: Path | None = None,
) -> dict[str, object]:
    """Simulate service-ticket acquisition under a password-derived service key.

    Does not store the plaintext password or derived key in the returned artifact.
    """
    identifier(service_id)
    identifier(client_id)
    actual_salt = secrets.token_bytes(DEFAULT_SALT_BYTES) if salt is None else salt
    key = derive_service_key(service_password, salt=actual_salt, iterations=iterations)
    ticket = Ticket(
        version=1,
        kind="service",
        ticket_id=new_identifier(),
        client_id=client_id,
        service_id=service_id,
        issued_at=issued_at,
        not_before=issued_at,
        expires_at=issued_at + DEFAULT_TICKET_LIFETIME_SECONDS,
        session_key=encode_b64(secrets.token_bytes(32)),
    )
    envelope = seal_ticket(ticket, key)
    artifact: dict[str, object] = {
        "version": 1,
        "service_id": service_id,
        "kdf": {
            "algorithm": "pbkdf2_hmac_sha256",
            "salt": encode_b64(actual_salt),
            "iterations": iterations,
        },
        "service_ticket": envelope,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(output_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(artifact, handle, indent=2)
            handle.write("\n")
    return artifact


def _validate_artifact(artifact: object) -> tuple[dict[str, object], bytes, int]:
    """Validate artifact structure and KDF/envelope metadata before guessing."""
    top = exact_fields(artifact, {"version", "service_id", "kdf", "service_ticket"})
    if integer(top["version"]) != 1:
        raise MalformedRequest("unsupported_artifact_version")
    identifier(top["service_id"])

    kdf = exact_fields(top["kdf"], {"algorithm", "salt", "iterations"})
    if kdf["algorithm"] != "pbkdf2_hmac_sha256":
        raise MalformedRequest("unsupported_kdf_algorithm")
    salt = decode_b64(kdf["salt"], expected_length=DEFAULT_SALT_BYTES)
    iterations = integer(kdf["iterations"], minimum=1, maximum=1_000_000)

    envelope = exact_fields(top["service_ticket"], {"version", "kind", "nonce", "ciphertext"})
    if integer(envelope["version"]) != 1 or envelope["kind"] != "service":
        raise MalformedRequest("invalid_service_ticket_envelope")
    decode_b64(envelope["nonce"], expected_length=12)
    ciphertext_raw = decode_b64(envelope["ciphertext"])
    if not 16 <= len(ciphertext_raw) <= 8208:
        raise MalformedRequest("invalid_ciphertext_size")
    return envelope, salt, iterations


def verify_ticket_offline(
    artifact: object,
    candidates: Sequence[str],
    *,
    max_attempts: int | None = None,
    max_seconds: float | None = None,
) -> dict[str, object]:
    """Attempt offline candidate verification via authenticated decryption.

    Makes zero network calls. Distinguishes malformed input (raises
    MalformedRequest) from candidate mismatches (InvalidAuthentication).
    """
    envelope, salt, iterations = _validate_artifact(artifact)
    if max_attempts is not None:
        integer(max_attempts, minimum=1)
    if max_seconds is not None and (not isinstance(max_seconds, (int, float)) or isinstance(max_seconds, bool) or max_seconds <= 0):
        raise MalformedRequest("invalid_max_seconds")

    attempts = 0
    budget_hit = False
    start_ns = time.perf_counter_ns()
    deadline_ns = None if max_seconds is None else start_ns + int(max_seconds * 1_000_000_000)

    for index, candidate in enumerate(candidates, start=1):
        if max_attempts is not None and attempts >= max_attempts:
            budget_hit = True
            break
        if deadline_ns is not None and time.perf_counter_ns() >= deadline_ns:
            budget_hit = True
            break

        attempts += 1
        candidate_key = derive_service_key(candidate, salt=salt, iterations=iterations)
        try:
            open_ticket(envelope, candidate_key, expected_kind="service")
            elapsed_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000, 4)
            return {
                "recovered": True,
                "outcome": "recovered",
                "attempts": attempts,
                "matched_candidate_index": index,
                "elapsed_ms": elapsed_ms,
            }
        except InvalidAuthentication:
            continue

    elapsed_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000, 4)
    outcome = "not_recovered_within_budget" if budget_hit else "not_recovered_within_list_budget"
    return {
        "recovered": False,
        "outcome": outcome,
        "attempts": attempts,
        "matched_candidate_index": None,
        "elapsed_ms": elapsed_ms,
    }


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _generate_absent_random_password(candidates: Sequence[str]) -> str:
    candidate_set = set(candidates)
    while True:
        secret = secrets.token_urlsafe(24)
        if secret not in candidate_set:
            return secret


def run_kerberoasting_experiment(
    *,
    output_dir: Path,
    wordlist_path: Path = DEFAULT_WORDLIST,
    weak_password: str = "labservice",
    iterations: int = DEFAULT_ITERATIONS,
    max_attempts: int | None = None,
    max_seconds: float | None = None,
) -> dict[str, object]:
    """Run E11 (weak in list) and E12 (random absent) with identical parameters."""
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    candidates = load_candidate_wordlist(wordlist_path)
    if weak_password not in candidates:
        raise MalformedRequest("weak_password_must_be_in_wordlist")
    random_password = _generate_absent_random_password(candidates)

    cases = [
        ("E11", "weak_in_list", weak_password),
        ("E12", "random_absent", random_password),
    ]
    records: list[dict[str, object]] = []
    for case_id, password_class, password in cases:
        artifact = acquire_synthetic_service_ticket(
            service_password=password,
            iterations=iterations,
        )
        result = verify_ticket_offline(
            artifact,
            candidates,
            max_attempts=max_attempts,
            max_seconds=max_seconds,
        )
        records.append(
            {
                "case_id": case_id,
                "password_class": password_class,
                "cipher": "AES-256-GCM",
                "kdf_algorithm": "pbkdf2_hmac_sha256",
                "salt_bytes": DEFAULT_SALT_BYTES,
                "iterations": iterations,
                "wordlist_size": len(candidates),
                "budget_attempts": max_attempts if max_attempts is not None else len(candidates),
                "budget_seconds": max_seconds,
                "attempts": result["attempts"],
                "matched_candidate_index": result["matched_candidate_index"],
                "elapsed_ms": result["elapsed_ms"],
                "recovered": result["recovered"],
                "outcome": result["outcome"],
            }
        )

    output_dir.mkdir(parents=True, exist_ok=False)
    results_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.csv"
    env_path = output_dir / "environment.json"

    with results_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    fieldnames = [
        "case_id",
        "password_class",
        "cipher",
        "kdf_algorithm",
        "salt_bytes",
        "iterations",
        "wordlist_size",
        "budget_attempts",
        "budget_seconds",
        "attempts",
        "matched_candidate_index",
        "elapsed_ms",
        "recovered",
        "outcome",
    ]
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["recovered"] = "true" if record["recovered"] else "false"
            writer.writerow(row)

    environment = {
        "schema_version": 1,
        "git_head": _git_head(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cipher": "AES-256-GCM",
        "kdf_algorithm": "pbkdf2_hmac_sha256",
        "salt_bytes": DEFAULT_SALT_BYTES,
        "iterations": iterations,
        "wordlist_path": str(wordlist_path.relative_to(ROOT)) if wordlist_path.is_relative_to(ROOT) else str(wordlist_path),
        "wordlist_size": len(candidates),
        "max_attempts": max_attempts,
        "max_seconds": max_seconds,
        "network_calls_during_verification": 0,
        "limitations": [
            "Kerberoasting-inspired synthetic mechanism demo using AES-GCM and PBKDF2-SHA256, not AD RC4/RFC 3962.",
            "E11/E12 illustrate bounded wordlist inclusion vs. exclusion, not population password entropy or uncrackability.",
        ],
    }
    env_path.write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    return {"output_dir": str(output_dir), "records": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="New ignored output directory (defaults to results/raw/b05-<UTC-timestamp>)",
    )
    parser.add_argument("--wordlist", type=Path, default=DEFAULT_WORDLIST)
    parser.add_argument("--weak-password", default="labservice")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--max-attempts", type=int, default=None)
    parser.add_argument("--max-seconds", type=float, default=None)
    args = parser.parse_args(argv)

    if args.output_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = ROOT / "results" / "raw" / f"b05-{stamp}"
    else:
        output_dir = args.output_dir

    result = run_kerberoasting_experiment(
        output_dir=output_dir,
        wordlist_path=args.wordlist,
        weak_password=args.weak_password,
        iterations=args.iterations,
        max_attempts=args.max_attempts,
        max_seconds=args.max_seconds,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
