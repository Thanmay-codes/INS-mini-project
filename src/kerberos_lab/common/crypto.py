"""Library-backed crypto for the bounded, custom educational protocol."""

import base64
import hashlib
import secrets

from cryptography.exceptions import InvalidKey, InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ._validation import decode_base64, exact_fields, identifier, integer, nonce_id, text_pattern
from .errors import InvalidAuthentication, MalformedRequest
from .models import (ClientSession, Purpose, Ticket, TicketKind, canonical_bytes,
                     parse_json_object, validate_authenticator_time, validate_ticket_time)


def encode_b64(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise MalformedRequest("invalid_bytes")
    return base64.b64encode(value).decode("ascii")


def decode_b64(value: str, *, expected_length: int | None = None) -> bytes:
    return decode_base64(value, expected_length=expected_length)


def new_key() -> bytes:
    return secrets.token_bytes(32)


def new_identifier() -> str:
    return secrets.token_hex(16)


def _key(value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise MalformedRequest("invalid_key_length")
    return value


def _envelope(value: object) -> dict[str, object]:
    envelope = exact_fields(value, {"version", "kind", "nonce", "ciphertext"})
    if integer(envelope["version"]) != 1 or envelope["kind"] not in ("tgt", "service"):
        raise MalformedRequest("invalid_envelope_version_or_kind")
    decode_b64(envelope["nonce"], expected_length=12)
    if not isinstance(envelope["ciphertext"], str) or len(envelope["ciphertext"]) > 10944:
        raise MalformedRequest("invalid_ciphertext_size")
    if not 16 <= len(decode_b64(envelope["ciphertext"])) <= 8208:
        raise MalformedRequest("invalid_ciphertext_size")
    return envelope


def seal_ticket(ticket: Ticket, key: bytes) -> dict[str, object]:
    if not isinstance(ticket, Ticket):
        raise MalformedRequest("invalid_ticket")
    plaintext = canonical_bytes(ticket.to_dict())
    if len(plaintext) > 8192:
        raise MalformedRequest("invalid_ticket_size")
    nonce = secrets.token_bytes(12)
    aad = f"ins-kerberos-lab:ticket:v1:{ticket.kind}".encode("ascii")
    ciphertext = AESGCM(_key(key)).encrypt(nonce, plaintext, aad)
    return {"version": 1, "kind": ticket.kind, "nonce": encode_b64(nonce),
            "ciphertext": encode_b64(ciphertext)}


def open_ticket(envelope: object, key: bytes, *, expected_kind: TicketKind) -> Ticket:
    if expected_kind not in ("tgt", "service"):
        raise MalformedRequest("invalid_expected_kind")
    envelope = _envelope(envelope)
    if envelope["kind"] != expected_kind:
        raise InvalidAuthentication("bad_context")
    aad = f"ins-kerberos-lab:ticket:v1:{expected_kind}".encode("ascii")
    try:
        plaintext = AESGCM(_key(key)).decrypt(decode_b64(envelope["nonce"]),
                                            decode_b64(envelope["ciphertext"]), aad)
    except InvalidTag:
        raise InvalidAuthentication("bad_integrity") from None
    ticket = Ticket.from_dict(parse_json_object(plaintext, max_bytes=8192))
    if ticket.kind != expected_kind:
        raise InvalidAuthentication("bad_context")
    return ticket


def _context(purpose: Purpose) -> tuple[str, str, str, bytes]:
    if purpose == "tgs":
        return "tgt", "tgs", "/service-ticket", b"ins-kerberos-lab:auth:v1:tgs\0"
    if purpose == "resource":
        return "service", "files", "/access-resource", b"ins-kerberos-lab:auth:v1:resource\0"
    raise MalformedRequest("invalid_purpose")


def _body(body: object, purpose: Purpose) -> dict:
    if purpose == "tgs":
        body = exact_fields(body, {"service_id"})
        identifier(body["service_id"])
    else:
        body = exact_fields(body, {"operation"})
        if body["operation"] != "increment":
            raise MalformedRequest("invalid_operation")
    return body


def _authenticator(value: object) -> dict:
    auth = exact_fields(value, {"version", "client_id", "service_id", "ticket_id",
                               "timestamp", "request_nonce", "method", "path",
                               "body_sha256", "ticket_sha256", "mac"})
    if integer(auth["version"]) != 1:
        raise MalformedRequest("invalid_authenticator_version")
    identifier(auth["client_id"])
    identifier(auth["service_id"])
    nonce_id(auth["ticket_id"])
    nonce_id(auth["request_nonce"])
    integer(auth["timestamp"])
    for name in ("body_sha256", "ticket_sha256"):
        text_pattern(auth[name], r"[0-9a-f]{64}")
    for name in ("method", "path"):
        if not isinstance(auth[name], str):
            raise MalformedRequest("invalid_authenticator_context")
    decode_b64(auth["mac"], expected_length=32)
    canonical_bytes(auth)
    return auth


def sign_authenticator(session: ClientSession, envelope: dict[str, object],
                       body: dict[str, object], *, purpose: Purpose,
                       timestamp: int, request_nonce: str | None = None
                       ) -> dict[str, object]:
    kind, audience, path, domain = _context(purpose)
    if not isinstance(session, ClientSession):
        raise MalformedRequest("invalid_session")
    envelope = _envelope(envelope)
    body = _body(body, purpose)
    if envelope["kind"] != kind or session.service_id != audience:
        raise InvalidAuthentication("bad_context")
    timestamp = integer(timestamp)
    nonce = new_identifier() if request_nonce is None else nonce_id(request_nonce)
    auth = {"version": 1, "client_id": session.client_id, "service_id": audience,
            "ticket_id": session.ticket_id, "timestamp": timestamp, "request_nonce": nonce,
            "method": "POST", "path": path,
            "body_sha256": hashlib.sha256(canonical_bytes(body)).hexdigest(),
            "ticket_sha256": hashlib.sha256(canonical_bytes(envelope)).hexdigest()}
    signer = hmac.HMAC(decode_b64(session.session_key, expected_length=32), hashes.SHA256())
    signer.update(domain + canonical_bytes(auth))
    return {**auth, "mac": encode_b64(signer.finalize())}


def verify_authenticator(authenticator: object, ticket: Ticket,
                         envelope: dict[str, object], body: dict[str, object], *,
                         purpose: Purpose, now: int, skew: int) -> dict[str, object]:
    kind, audience, path, domain = _context(purpose)
    if not isinstance(ticket, Ticket):
        raise MalformedRequest("invalid_ticket")
    envelope = _envelope(envelope)
    body = _body(body, purpose)
    auth = _authenticator(authenticator)
    if (ticket.kind != kind or ticket.service_id != audience or envelope["kind"] != kind
            or auth["client_id"] != ticket.client_id or auth["service_id"] != audience
            or auth["ticket_id"] != ticket.ticket_id or auth["method"] != "POST"
            or auth["path"] != path
            or auth["body_sha256"] != hashlib.sha256(canonical_bytes(body)).hexdigest()
            or auth["ticket_sha256"] != hashlib.sha256(canonical_bytes(envelope)).hexdigest()):
        raise InvalidAuthentication("bad_context")
    unsigned = {key: value for key, value in auth.items() if key != "mac"}
    verifier = hmac.HMAC(decode_b64(ticket.session_key, expected_length=32), hashes.SHA256())
    verifier.update(domain + canonical_bytes(unsigned))
    try:
        verifier.verify(decode_b64(auth["mac"]))
    except InvalidSignature:
        raise InvalidAuthentication("bad_integrity") from None
    validate_ticket_time(ticket, now=now, skew=skew)
    validate_authenticator_time(auth["timestamp"], now=now, skew=skew)
    return dict(auth)


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str):
        raise MalformedRequest("invalid_password")
    try:
        encoded = password.encode("utf-8", errors="strict")
    except UnicodeError:
        raise MalformedRequest("invalid_password") from None
    if not 1 <= len(encoded) <= 1024:
        raise MalformedRequest("invalid_password_length")
    return encoded


def make_password_verifier(password: str) -> dict[str, object]:
    encoded = _password_bytes(password)
    salt = secrets.token_bytes(16)
    digest = Scrypt(salt=salt, length=32, n=16384, r=8, p=1).derive(encoded)
    return {"version": 1, "algorithm": "scrypt", "n": 16384, "r": 8, "p": 1,
            "salt": encode_b64(salt), "digest": encode_b64(digest)}


def verify_password(password: str, verifier: object) -> bool:
    encoded = _password_bytes(password)
    verifier = exact_fields(verifier, {"version", "algorithm", "n", "r", "p", "salt", "digest"})
    if verifier["algorithm"] != "scrypt":
        raise MalformedRequest("invalid_password_verifier")
    for field, expected in (("version", 1), ("n", 16384), ("r", 8), ("p", 1)):
        if integer(verifier[field]) != expected:
            raise MalformedRequest("invalid_password_verifier")
    salt = decode_b64(verifier["salt"], expected_length=16)
    digest = decode_b64(verifier["digest"], expected_length=32)
    try:
        Scrypt(salt=salt, length=32, n=16384, r=8, p=1).verify(encoded, digest)
    except InvalidKey:
        return False
    return True


def derive_service_key(password: str, *, salt: bytes, iterations: int = 100000) -> bytes:
    encoded = _password_bytes(password)
    if not isinstance(salt, bytes) or len(salt) != 16:
        raise MalformedRequest("invalid_service_salt")
    integer(iterations, minimum=1, maximum=1000000)
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=iterations).derive(encoded)
