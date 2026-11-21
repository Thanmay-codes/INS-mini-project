"""Immutable wire models for the educational v1 protocol."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from typing import Literal

from ._validation import MAX_INTEGER, decode_base64, exact_fields, identifier, integer, nonce_id
from .errors import InvalidAuthentication, MalformedRequest


TicketKind = Literal["tgt", "service"]
Role = Literal["kdc", "resource"]
Purpose = Literal["tgs", "resource"]
DefenseMode = Literal["authenticator_no_cache", "authenticator_cache"]


def _check_json(value: object) -> None:
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        integer(value, minimum=-MAX_INTEGER)
    elif isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, list):
        for item in value:
            _check_json(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise MalformedRequest("non_string_json_key")
            key.encode("utf-8", errors="strict")
            _check_json(item)
    else:
        raise MalformedRequest("invalid_json_value")


def canonical_bytes(value: object) -> bytes:
    try:
        _check_json(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, UnicodeError, RecursionError):
        raise MalformedRequest("invalid_json_value") from None


def parse_json_object(raw: bytes, *, max_bytes: int = 65536) -> dict[str, object]:
    integer(max_bytes, minimum=1)
    if not isinstance(raw, bytes) or len(raw) > max_bytes:
        raise MalformedRequest("invalid_json_size")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise MalformedRequest("duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs)
    except (ValueError, UnicodeError, RecursionError):
        raise MalformedRequest("invalid_json") from None
    if not isinstance(value, dict):
        raise MalformedRequest("json_object_required")
    canonical_bytes(value)
    return value


@dataclass(frozen=True)
class Ticket:
    version: int
    kind: TicketKind
    ticket_id: str
    client_id: str
    service_id: str
    issued_at: int
    not_before: int
    expires_at: int
    session_key: str

    def __post_init__(self) -> None:
        if integer(self.version) != 1 or self.kind not in ("tgt", "service"):
            raise MalformedRequest("invalid_ticket_version_or_kind")
        nonce_id(self.ticket_id)
        identifier(self.client_id)
        identifier(self.service_id)
        if self.service_id != ("tgs" if self.kind == "tgt" else "files"):
            raise MalformedRequest("invalid_ticket_audience")
        for value in (self.issued_at, self.not_before, self.expires_at):
            integer(value)
        if not self.issued_at <= self.not_before < self.expires_at:
            raise MalformedRequest("invalid_ticket_interval")
        decode_base64(self.session_key, expected_length=32)

    @classmethod
    def from_dict(cls, value: object) -> Ticket:
        return cls(**exact_fields(value, {field.name for field in fields(cls)}))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ClientSession:
    client_id: str
    service_id: str
    ticket_id: str
    session_key: str
    expires_at: int

    def __post_init__(self) -> None:
        identifier(self.client_id)
        identifier(self.service_id)
        if self.service_id not in ("tgs", "files"):
            raise MalformedRequest("invalid_session_audience")
        nonce_id(self.ticket_id)
        decode_base64(self.session_key, expected_length=32)
        integer(self.expires_at)

    @classmethod
    def from_dict(cls, value: object) -> ClientSession:
        return cls(**exact_fields(value, {field.name for field in fields(cls)}))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_ticket_time(ticket: Ticket, *, now: int, skew: int) -> None:
    integer(now)
    integer(skew)
    if not isinstance(ticket, Ticket):
        raise MalformedRequest("invalid_ticket")
    if now < ticket.not_before - skew:
        raise InvalidAuthentication("ticket_not_yet_valid")
    if now > ticket.expires_at + skew:
        raise InvalidAuthentication("ticket_expired")


def validate_authenticator_time(timestamp: int, *, now: int, skew: int) -> None:
    integer(timestamp)
    integer(now)
    integer(skew)
    if abs(now - timestamp) > skew:
        raise InvalidAuthentication("authenticator_skew")
