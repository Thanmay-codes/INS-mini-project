"""Reproducible E01-E10 local replay, clock and concurrency experiments.

Only the released loopback KDC/resource APIs are used. Runtime keys and SQLite
stores live briefly under an ignored private directory; evidence excludes
credentials, tickets, authenticators and request bodies.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

from kerberos_lab.client import AuthenticationClient, RemoteError
from kerberos_lab.client.api import CapturedRequest, ServiceGrant
from kerberos_lab.common.clock import FrozenClock
from kerberos_lab.common.crypto import open_ticket
from kerberos_lab.common.material import initialize_run, load_material
from kerberos_lab.common.models import canonical_bytes


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = tuple(f"E{i:02d}" for i in range(1, 11))
MODES = ("authenticator_no_cache", "authenticator_cache")
BASE_TIME = 1_800_000_000
SKEW_SECONDS = 30
WORKERS = (2, 4, 8)
OFFSETS = (-60, -15, 0, 15, 60)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http(url: str, *, raw: bytes | None = None, method: str = "GET",
          timeout: float = 5.0) -> tuple[int, str | None, dict[str, object] | None, float]:
    request = urllib.request.Request(
        url, data=raw, method=method,
        headers={"Accept": "application/json", **({"Content-Type": "application/json"} if raw is not None else {})},
    )
    started = time.perf_counter_ns()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status, data = response.status, response.read(65537)
    except urllib.error.HTTPError as error:
        status, data = error.code, error.read(65537)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, "transport_failure", None, (time.perf_counter_ns() - started) / 1_000_000
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return status, "non_json_response", None, elapsed
    code = payload.get("error") if isinstance(payload, dict) else None
    return status, code if isinstance(code, str) else None, payload if isinstance(payload, dict) else None, elapsed


class ChildServer(AbstractContextManager):
    """One released app process, with bounded readiness and deterministic cleanup."""

    def __init__(self, role: str, run_dir: Path, *, port: int | None = None,
                 mode: str | None = None, offset: int = 0, frozen: int = BASE_TIME,
                 logs: Path) -> None:
        if role not in ("kdc", "resource_server"):
            raise ValueError("unknown role")
        self.role = role
        self.run_dir = run_dir
        self.port = _free_port() if port is None else port
        self.mode = mode
        self.offset = offset
        self.frozen = frozen
        self.url = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen | None = None
        self.log_path = logs / f"{role}-{self.port}.log"
        self.log_file = None
        self.startup_ms: float | None = None

    def start(self) -> "ChildServer":
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("server is already running")
        module = "kerberos_lab.kdc.app" if self.role == "kdc" else "kerberos_lab.resource_server.app"
        command = [sys.executable, "-m", module, "--run-dir", str(self.run_dir),
                   "--port", str(self.port), "--clock-offset-seconds", str(self.offset),
                   "--frozen-time-seconds", str(self.frozen)]
        if self.mode is not None:
            command.extend(("--defense-mode", self.mode))
        environment = os.environ.copy()
        source = str(ROOT / "src")
        environment["PYTHONPATH"] = source + os.pathsep + environment.get("PYTHONPATH", "")
        self.log_file = self.log_path.open("wb")
        self.process = subprocess.Popen(command, cwd=ROOT, env=environment,
                                        stdout=self.log_file, stderr=subprocess.STDOUT)
        # Startup timing intentionally excludes the Popen call itself; it covers
        # readiness polling through the first healthy endpoint response.
        started = time.perf_counter_ns()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.log_file.flush()
                raise RuntimeError(f"{self.role} exited during startup with {self.process.returncode}; see {self.log_path}")
            status, _code, payload, _latency = _http(self.url + "/health", timeout=0.3)
            if status == 200 and payload == {"role": "kdc" if self.role == "kdc" else "resource_server",
                                            "stage": "implemented", "status": "ok"}:
                self.startup_ms = (time.perf_counter_ns() - started) / 1_000_000
                return self
            time.sleep(0.05)
        self.stop()
        raise TimeoutError(f"{self.role} did not become healthy")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None

    def __enter__(self) -> "ChildServer":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()


@dataclass
class Attempt:
    scenario: str
    trial: int
    phase: str
    mode: str | None
    offset_seconds: int
    worker_count: int
    request_index: int
    status: int
    error_code: str | None
    accepted: bool
    counter: int | None
    latency_ms: float
    startup_ms: float | None
    ticket_time_valid: bool | None = None
    authenticator_time_valid: bool | None = None
    expected_time_reason: str | None = None
    expected_outcome: bool = True


class TrialLab(AbstractContextManager):
    """A fresh run/ticket; same-key database clones provide paired conditions."""

    def __init__(self, private_root: Path, logs: Path, trial_id: str) -> None:
        self.private_root = private_root
        self.logs = logs
        self.trial_id = trial_id
        self.temp: tempfile.TemporaryDirectory | None = None
        self.source: Path | None = None
        self.client: AuthenticationClient | None = None
        self.grant: ServiceGrant | None = None
        self.kdc: ChildServer | None = None
        self.run_id: str | None = None

    def __enter__(self) -> "TrialLab":
        self.private_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="b03-", dir=self.private_root)
        self.source = Path(self.temp.name) / "source"
        self._password = uuid.uuid4().hex + "-B03"
        try:
            initialize_run(self.source, password=self._password)
        except Exception:
            try:
                self.temp.cleanup()
            except OSError:
                pass
            raise
        material = load_material(self.source, role="resource")
        self.run_id = material.run_id
        self.kdc = ChildServer("kdc", self.source, logs=self.logs).start()
        self.client = AuthenticationClient(self.kdc.url, clock=FrozenClock(BASE_TIME), timeout=5)
        self.grant = self.client.authenticate("alice", self._password)
        return self

    def clone(self, name: str) -> Path:
        assert self.source is not None and self.temp is not None
        target = Path(self.temp.name) / name
        shutil.copytree(self.source, target)
        return target

    def request(self, timestamp: int = BASE_TIME) -> CapturedRequest:
        assert self.client is not None and self.grant is not None
        return AuthenticationClient(self.client.kdc_url, clock=FrozenClock(timestamp)).build_resource_request(self.grant)

    def __exit__(self, *_exc) -> None:
        if self.kdc is not None:
            self.kdc.stop()
        if self.temp is not None:
            self.temp.cleanup()

def _trial(private_root: Path, logs: Path, trial_id: str) -> TrialLab:
    return TrialLab(private_root, logs, trial_id)


def _record(attempts: list[Attempt], *, scenario: str, trial: int, phase: str,
            mode: str | None, offset: int, worker_count: int, index: int,
            url: str, raw: bytes, startup_ms: float | None = None,
            expected_status: int | None = None, time_checks: tuple[bool, bool, str | None] | None = None) -> Attempt:
    status, error, payload, latency = _http(url + "/access-resource", raw=raw, method="POST")
    accepted = status == 200
    expected = expected_status is None or status == expected_status
    record = Attempt(scenario, trial, phase, mode, offset, worker_count, index,
                     status, error, accepted,
                     payload.get("counter") if payload and type(payload.get("counter")) is int else None,
                     latency, startup_ms,
                     *(time_checks if time_checks is not None else (None, None, None)), expected)
    attempts.append(record)
    return record


def _alter_request(raw: bytes, mutation: str) -> bytes:
    message = json.loads(raw)
    if mutation == "ticket":
        value = message["service_ticket"]["ciphertext"]
        message["service_ticket"]["ciphertext"] = ("A" if value[0] != "A" else "B") + value[1:]
    elif mutation == "authenticator":
        value = message["authenticator"]["mac"]
        message["authenticator"]["mac"] = ("A" if value[0] != "A" else "B") + value[1:]
    elif mutation == "body":
        message["body"]["operation"] = "delete"
    elif mutation == "service":
        message["authenticator"]["service_id"] = "other"
    else:
        raise ValueError("unknown mutation")
    return canonical_bytes(message)


def _time_conditions(ticket_not_before: int, ticket_expires_at: int,
                     authenticator_timestamp: int, now: int,
                     skew: int = SKEW_SECONDS) -> tuple[bool, bool, str | None]:
    """Mirror the released verifier order for explainable public time outcomes."""
    ticket_ok = ticket_not_before - skew <= now <= ticket_expires_at + skew
    authenticator_ok = abs(now - authenticator_timestamp) <= skew
    reason = None if ticket_ok and authenticator_ok else "ticket_validity" if not ticket_ok else "authenticator_freshness"
    return ticket_ok, authenticator_ok, reason


def _do_scenario(scenario: str, trial: int, private_root: Path, logs: Path,
                 attempts: list[Attempt], startup: list[float]) -> None:
    lab = _trial(private_root, logs, f"{scenario}-{trial}")
    with lab:
        assert lab.grant is not None and lab.source is not None
        base_request = lab.request()
        if lab.kdc and lab.kdc.startup_ms is not None:
            startup.append(lab.kdc.startup_ms)

        if scenario == "E01":
            for mode in MODES:
                run = lab.clone(mode)
                with ChildServer("resource_server", run, mode=mode, logs=logs) as server:
                    startup.append(server.startup_ms or 0)
                    _record(attempts, scenario=scenario, trial=trial, phase="valid_request", mode=mode,
                            offset=0, worker_count=1, index=1, url=server.url,
                            raw=base_request.raw_bytes, startup_ms=server.startup_ms, expected_status=200)

        elif scenario == "E02":
            for mode in MODES:
                run = lab.clone(mode)
                with ChildServer("resource_server", run, mode=mode, logs=logs) as server:
                    startup.append(server.startup_ms or 0)
                    for index in (1, 2):
                        expected = 200 if mode == MODES[0] or index == 1 else 409
                        _record(attempts, scenario=scenario, trial=trial, phase="exact_duplicate", mode=mode,
                                offset=0, worker_count=1, index=index, url=server.url,
                                raw=base_request.raw_bytes, startup_ms=server.startup_ms,
                                expected_status=expected)

        elif scenario == "E03":
            requests = (base_request, lab.request())
            for mode in MODES:
                run = lab.clone(mode)
                with ChildServer("resource_server", run, mode=mode, logs=logs) as server:
                    startup.append(server.startup_ms or 0)
                    for index, captured in enumerate(requests, 1):
                        _record(attempts, scenario=scenario, trial=trial, phase="fresh_authenticator", mode=mode,
                                offset=0, worker_count=1, index=index, url=server.url,
                                raw=captured.raw_bytes, startup_ms=server.startup_ms, expected_status=200)

        elif scenario == "E04":
            run = lab.clone("tamper")
            with ChildServer("resource_server", run, mode="authenticator_cache", logs=logs) as server:
                startup.append(server.startup_ms or 0)
                for index, mutation in enumerate(("ticket", "authenticator", "body", "service"), 1):
                    _record(attempts, scenario=scenario, trial=trial, phase=f"mutated_{mutation}",
                            mode="authenticator_cache", offset=0, worker_count=1, index=index,
                            url=server.url, raw=_alter_request(base_request.raw_bytes, mutation),
                            startup_ms=server.startup_ms, expected_status=400 if mutation == "body" else 401)

        elif scenario == "E05":
            for count in WORKERS:
                # Each worker-count condition starts from an untouched replay store.
                run = lab.clone(f"shared-workers-{count}")
                ports = [_free_port() for _ in range(count)]
                servers: list[ChildServer] = []
                try:
                    for port in ports:
                        server = ChildServer("resource_server", run, port=port,
                                             mode="authenticator_cache", logs=logs).start()
                        servers.append(server)
                        startup.append(server.startup_ms or 0)
                    barrier = threading.Barrier(count)
                    def send(index: int) -> tuple[int, str | None, dict[str, object] | None, float]:
                        barrier.wait(timeout=10)
                        return _http(servers[index].url + "/access-resource", raw=base_request.raw_bytes, method="POST")
                    with ThreadPoolExecutor(max_workers=count) as pool:
                        results = list(pool.map(send, range(count)))
                    expected_one = sum(1 for status, _code, _body, _ms in results if status == 200) == 1
                    for index, (status, error, payload, latency) in enumerate(results, 1):
                        record = Attempt(scenario, trial, f"concurrent_{count}", "authenticator_cache", 0,
                                         count, index, status, error, status == 200,
                                         payload.get("counter") if payload and type(payload.get("counter")) is int else None,
                                         latency, servers[index - 1].startup_ms, expected_outcome=expected_one and status in (200, 409))
                        attempts.append(record)
                finally:
                    for server in reversed(servers):
                        server.stop()

        elif scenario == "E06":
            run = lab.clone("restart")
            server = ChildServer("resource_server", run, mode="authenticator_cache", logs=logs).start()
            startup.append(server.startup_ms or 0)
            try:
                _record(attempts, scenario=scenario, trial=trial, phase="before_restart",
                        mode="authenticator_cache", offset=0, worker_count=1, index=1,
                        url=server.url, raw=base_request.raw_bytes, startup_ms=server.startup_ms,
                        expected_status=200)
            finally:
                server.stop()
            server.start()
            startup.append(server.startup_ms or 0)
            try:
                _record(attempts, scenario=scenario, trial=trial, phase="after_restart_exact_replay",
                        mode="authenticator_cache", offset=0, worker_count=1, index=2,
                        url=server.url, raw=base_request.raw_bytes, startup_ms=server.startup_ms,
                        expected_status=409)
            finally:
                server.stop()

        elif scenario == "E07":
            for offset in OFFSETS:
                run = lab.clone(f"offset-{offset}")
                with ChildServer("resource_server", run, mode="authenticator_cache", offset=offset,
                                 frozen=BASE_TIME, logs=logs) as server:
                    startup.append(server.startup_ms or 0)
                    ticket = open_ticket(lab.grant.service_ticket,
                                         load_material(run, role="resource").service_key,
                                         expected_kind="service")
                    now = BASE_TIME + offset
                    ticket_ok, auth_ok, reason = _time_conditions(
                        ticket.not_before, ticket.expires_at,
                        int(base_request.message["authenticator"]["timestamp"]), now)
                    expect = 200 if ticket_ok and auth_ok else 401
                    _record(attempts, scenario=scenario, trial=trial, phase="clock_offset", mode="authenticator_cache",
                            offset=offset, worker_count=1, index=offset, url=server.url,
                            raw=base_request.raw_bytes, startup_ms=server.startup_ms,
                            expected_status=expect, time_checks=(ticket_ok, auth_ok, reason))

        elif scenario == "E08":
            service_ticket = open_ticket(lab.grant.service_ticket,
                                         load_material(lab.source, role="resource").service_key,
                                         expected_kind="service")
            points = (("before_not_before", service_ticket.not_before - SKEW_SECONDS - 1),
                      ("at_not_before_leeway", service_ticket.not_before - SKEW_SECONDS),
                      ("inside_not_before", service_ticket.not_before - SKEW_SECONDS + 1),
                      ("inside_expiry", service_ticket.expires_at + SKEW_SECONDS - 1),
                      ("at_expiry_leeway", service_ticket.expires_at + SKEW_SECONDS),
                      ("after_expiry", service_ticket.expires_at + SKEW_SECONDS + 1))
            for index, (name, now) in enumerate(points, 1):
                run = lab.clone(f"boundary-{name}")
                request_at_point = lab.request(now)
                with ChildServer("resource_server", run, mode="authenticator_cache",
                                 frozen=now, logs=logs) as server:
                    startup.append(server.startup_ms or 0)
                    ticket_ok, auth_ok, reason = _time_conditions(
                        service_ticket.not_before, service_ticket.expires_at,
                        int(request_at_point.message["authenticator"]["timestamp"]), now)
                    _record(attempts, scenario=scenario, trial=trial, phase=name, mode="authenticator_cache",
                            offset=now - BASE_TIME, worker_count=1, index=index, url=server.url,
                            raw=request_at_point.raw_bytes, startup_ms=server.startup_ms,
                            expected_status=200 if ticket_ok and auth_ok else 401,
                            time_checks=(ticket_ok, auth_ok, reason))

        elif scenario == "E09":
            for index, failure in enumerate(("missing", "corrupt"), 1):
                run = lab.clone(f"store-{failure}")
                with ChildServer("resource_server", run, mode="authenticator_cache", logs=logs) as server:
                    startup.append(server.startup_ms or 0)
                    database = run / "resource.sqlite"
                    if failure == "missing":
                        database.unlink()
                    else:
                        database.write_bytes(b"B03 intentionally corrupted disposable SQLite store")
                    _record(attempts, scenario=scenario, trial=trial, phase=f"store_{failure}",
                            mode="authenticator_cache", offset=0, worker_count=1, index=index,
                            url=server.url, raw=base_request.raw_bytes,
                            startup_ms=server.startup_ms, expected_status=503)

        elif scenario == "E10":
            run = lab.clone("time-retained-restart")
            server = ChildServer("resource_server", run, mode="authenticator_cache", frozen=BASE_TIME,
                                 logs=logs).start()
            startup.append(server.startup_ms or 0)
            try:
                _record(attempts, scenario=scenario, trial=trial, phase="consume_at_base",
                        mode="authenticator_cache", offset=0, worker_count=1, index=1,
                        url=server.url, raw=base_request.raw_bytes, startup_ms=server.startup_ms,
                        expected_status=200)
            finally:
                server.stop()
            for index, (label, offset) in enumerate((("forward_15", 15), ("backward_15", -15)), 2):
                server.frozen = BASE_TIME + offset
                server.start()
                startup.append(server.startup_ms or 0)
                try:
                    _record(attempts, scenario=scenario, trial=trial, phase=label,
                            mode="authenticator_cache", offset=offset, worker_count=1, index=index,
                            url=server.url, raw=base_request.raw_bytes, startup_ms=server.startup_ms,
                            expected_status=409)
                finally:
                    server.stop()


def _summary(attempts: list[Attempt], trials: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        selected = [item for item in attempts if item.scenario == scenario]
        for mode in sorted({item.mode or "not_applicable" for item in selected}):
            group = [item for item in selected if (item.mode or "not_applicable") == mode]
            rows.append({
                "scenario": scenario,
                "defense_mode": mode,
                "requested_trials": trials,
                "observed_trials": len({item.trial for item in group}),
                "trial_denominator": trials,
                "observed_attempts": len(group),
                "accepted": sum(item.accepted for item in group),
                "rejected": sum(item.status not in (0, 200) for item in group),
                "failed_trials": len({item.trial for item in group if not item.expected_outcome}),
                "protected_operations": sum(item.accepted for item in group),
                "latency_p50_ms": _percentile([item.latency_ms for item in group], 0.50),
                "latency_p95_ms": _percentile([item.latency_ms for item in group], 0.95),
                "startup_p50_ms": _percentile([item.startup_ms for item in group if item.startup_ms is not None], 0.50),
            })
    return rows


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.5)))
    return round(ordered[index], 4)


def run(*, scenarios: tuple[str, ...] = SCENARIOS, trials: int = 1,
        output_dir: Path | None = None, private_root: Path | None = None) -> tuple[Path, list[Attempt]]:
    if not scenarios or any(item not in SCENARIOS for item in scenarios):
        raise ValueError("scenario selection must contain only E01-E10")
    if isinstance(trials, bool) or not isinstance(trials, int) or not 1 <= trials <= 1000:
        raise ValueError("trials must be between 1 and 1000")
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    destination = (ROOT / "results" / "raw" / ("b03-" + tag)) if output_dir is None else output_dir.resolve()
    if destination.exists():
        raise FileExistsError("output directory already exists; choose a new ignored run directory")
    destination.mkdir(parents=True)
    private = (ROOT / "data" / "private") if private_root is None else private_root.resolve()
    logs = destination / "process-logs"
    logs.mkdir()
    attempts: list[Attempt] = []
    startup: list[float] = []
    try:
        for trial in range(1, trials + 1):
            for scenario in scenarios:
                before = len(attempts)
                try:
                    _do_scenario(scenario, trial, private, logs, attempts, startup)
                except Exception as error:
                    attempts.append(Attempt(scenario, trial, "runner_failure", None, 0, 0,
                                            len(attempts) - before + 1, 0,
                                            type(error).__name__, False, None, 0.0, None,
                                            expected_outcome=False))
                    if not (destination / "runner-error.txt").exists():
                        (destination / "runner-error.txt").write_text(
                            f"{scenario} trial {trial}: {type(error).__name__}: {error}\n", encoding="utf-8")
    except Exception as error:
        attempts.append(Attempt(scenarios[len({item.scenario for item in attempts}) % len(scenarios)],
                                trials, "runner_failure", None, 0, 0, len(attempts) + 1,
                                0, type(error).__name__, False, None, 0.0, None,
                                expected_outcome=False))
        (destination / "runner-error.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
    with (destination / "requests.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for attempt in attempts:
            stream.write(json.dumps(attempt.__dict__, sort_keys=True, separators=(",", ":")) + "\n")
    summary = _summary(attempts, trials)
    if summary:
        with (destination / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
            writer.writeheader()
            writer.writerows(summary)
    metadata = {
        "schema_version": 1,
        "run_tag": tag,
        "started_utc": tag.split("-", 1)[0],
        "git_head": _git_head(),
        "python": sys.version,
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "scenarios": list(scenarios),
        "scenario_order": list(scenarios),
        "trial_order": "trial-major: for each trial 1..N, scenarios run in scenario_order",
        "trials_per_scenario": trials,
        "expected_trial_denominator": trials,
        "scenario_seed": None,
        "randomness": "No seeded PRNG; runtime keys and request nonces use cryptographic randomness.",
        "attempt_count": len(attempts),
        "failed_trial_attempts": sum(not item.expected_outcome for item in attempts),
        "clock": {"base_seconds": BASE_TIME, "allowed_skew_seconds": SKEW_SECONDS,
                  "E07_offsets_seconds": list(OFFSETS), "E08_ticket_boundary_leeway_seconds": SKEW_SECONDS,
                  "E10_offsets_seconds": [15, -15]},
        "worker_counts": list(WORKERS),
        "modes": list(MODES),
        "timing": {"request": "time.perf_counter_ns around loopback HTTP request",
                   "startup": "time.perf_counter_ns from Popen return until healthy endpoint response",
                   "separation": "deterministic validation and timed intervals recorded separately"},
        "time_reasons": "Expected categories are computed from released ticket/authenticator checks; server exposes only stable invalid_authentication publicly.",
        "raw_records": "requests.jsonl; request bodies and bearer artifacts are excluded",
        "private_run_data": "temporary data/private subtree, deleted after each trial",
    }
    (destination / "environment.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Keep per-process diagnostics out of the public evidence bundle after cleanup.
    shutil.rmtree(logs, ignore_errors=True)
    return destination, attempts


def _git_head() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, timeout=3, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", default=",".join(SCENARIOS), help="comma-separated E01-E10")
    parser.add_argument("--trials", type=int, default=1,
                        help="smoke default is one; use 30 for selected performance conditions")
    parser.add_argument("--output-dir", type=Path,
                        help="new output directory; default is results/raw/b03-<UTC-id>")
    parser.add_argument("--private-root", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        scenarios = tuple(item.strip().upper() for item in args.scenarios.split(",") if item.strip())
        if args.output_dir is not None:
            raw_root = (ROOT / "results" / "raw").resolve()
            selected_output = args.output_dir.resolve()
            if not selected_output.is_relative_to(raw_root):
                raise ValueError("--output-dir must be inside the ignored results/raw directory")
        destination, attempts = run(scenarios=scenarios, trials=args.trials,
                                    output_dir=args.output_dir, private_root=args.private_root)
    except (ValueError, FileExistsError, OSError) as error:
        parser.error(str(error))
    failed = sum(not item.expected_outcome for item in attempts)
    print(json.dumps({"output_dir": str(destination), "attempts": len(attempts),
                      "failed_attempts": failed}, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
