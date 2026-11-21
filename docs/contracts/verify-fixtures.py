"""Check A01 public vectors independently; not a production protocol validator."""

import base64
import hashlib
import hmac
import json
from pathlib import Path
import re
import tomllib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data/fixtures/contract"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def decode(value):
    raw = base64.b64decode(value, validate=True)
    assert base64.b64encode(raw).decode("ascii") == value
    return raw


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def main():
    vectors = json.loads((FIXTURES / "vectors-v1.json").read_text(),
                         object_pairs_hook=no_duplicates)
    cases = json.loads((FIXTURES / "cases-v1.json").read_text(),
                       object_pairs_hook=no_duplicates)["cases"]
    for kind, envelope, key_name in (
        ("tgt", vectors["login_response"]["tgt"], "tgs"),
        ("service", vectors["service_response"]["service_ticket"], "service"),
    ):
        plaintext = AESGCM(decode(vectors["keys"][key_name])).decrypt(
            decode(envelope["nonce"]), decode(envelope["ciphertext"]),
            f"ins-kerberos-lab:ticket:v1:{kind}".encode("ascii"),
        )
        assert plaintext == canonical(vectors["ticket_plaintexts"][kind])
        assert vectors["ticket_plaintexts"][kind]["session_key"] == (
            vectors["login_response" if kind == "tgt" else "service_response"]
            ["client_session"]["session_key"]
        )
    for purpose, name in (("tgs", "service_request"), ("resource", "resource_request")):
        request = vectors[name]
        auth = dict(request["authenticator"])
        mac = decode(auth.pop("mac"))
        plain = vectors["ticket_plaintexts"]["tgt" if purpose == "tgs" else "service"]
        envelope = request["tgt" if purpose == "tgs" else "service_ticket"]
        assert auth["body_sha256"] == hashlib.sha256(canonical(request["body"])).hexdigest()
        assert auth["ticket_sha256"] == hashlib.sha256(canonical(envelope)).hexdigest()
        expected = hmac.new(decode(plain["session_key"]),
                            f"ins-kerberos-lab:auth:v1:{purpose}\0".encode("ascii")
                            + canonical(auth), hashlib.sha256).digest()
        assert hmac.compare_digest(mac, expected)

    verifier = vectors["password_verifier"]
    Scrypt(salt=decode(verifier["salt"]), length=32, n=16384, r=8, p=1).verify(
        vectors["login_request"]["password"].encode(), decode(verifier["digest"]))
    kdf = vectors["service_kdf"]
    PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=decode(kdf["salt"]),
              iterations=kdf["iterations"]).verify(kdf["password"].encode(),
                                                   decode(kdf["derived_key"]))

    # This intentionally checks only the declared fixture cases, not all schemas.
    def reference_outcome(case):
        request = case["request"]
        auth = request["authenticator"]
        if (set(request) != {"version", "service_ticket", "authenticator", "body"}
                or type(request["version"]) is not int or request["version"] != 1
                or type(auth["timestamp"]) is not int
                or not re.fullmatch("[0-9a-f]{32}", auth["request_nonce"])):
            return 400, None
        envelope = request["service_ticket"]
        try:
            plain = json.loads(AESGCM(decode(vectors["keys"]["service"])).decrypt(
                decode(envelope["nonce"]), decode(envelope["ciphertext"]),
                b"ins-kerberos-lab:ticket:v1:service"))
        except InvalidTag:
            return 401, "bad_integrity"
        if auth["path"] != "/access-resource":
            return 401, "bad_context"
        unsigned = {key: value for key, value in auth.items() if key != "mac"}
        expected = hmac.new(decode(plain["session_key"]),
                            b"ins-kerberos-lab:auth:v1:resource\0" + canonical(unsigned),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(decode(auth["mac"]), expected):
            return 401, "bad_integrity"
        now, skew = case["now"], vectors["skew"]
        if now < plain["not_before"] - skew:
            return 401, "ticket_not_yet_valid"
        if now > plain["expires_at"] + skew:
            return 401, "ticket_expired"
        if abs(now - auth["timestamp"]) > skew:
            return 401, "authenticator_skew"
        return 200, None

    for case in cases:
        status, reason = reference_outcome(case)
        assert status == case["expected_http"], case["name"]
        if "expected_reason" in case:
            assert reason == case["expected_reason"], case["name"]
    try:
        json.loads((FIXTURES / "invalid-json-v1.txt").read_text(),
                   object_pairs_hook=no_duplicates)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate-key fixture was accepted")
    for path in (ROOT / "configs/replay.example.toml", ROOT / "pyproject.toml"):
        with path.open("rb") as handle:
            tomllib.load(handle)
    print(f"A01 vectors checked: AES-GCM, both request MACs, both KDFs, {len(cases)} cases, duplicate JSON and TOML syntax.")
    print("Reference-fixture checks only; runtime shared helpers/apps are not implemented by A01.")


if __name__ == "__main__":
    main()
