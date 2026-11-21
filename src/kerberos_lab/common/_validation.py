"""Internal, shared v1 shape/encoding checks. No credential values in errors."""

import base64
import binascii
import re

from .errors import MalformedRequest


MAX_INTEGER = 9007199254740991


def integer(value: object, *, minimum: int = 0, maximum: int = MAX_INTEGER) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise MalformedRequest("invalid_integer")
    return value


def text_pattern(value: object, pattern: str) -> str:
    if not isinstance(value, str) or re.fullmatch(pattern, value, flags=re.ASCII) is None:
        raise MalformedRequest("invalid_string")
    return value


def identifier(value: object) -> str:
    return text_pattern(value, r"[a-z][a-z0-9_-]{0,63}")


def nonce_id(value: object) -> str:
    return text_pattern(value, r"[0-9a-f]{32}")


def exact_fields(value: object, fields: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise MalformedRequest("invalid_fields")
    return value


def decode_base64(value: object, *, expected_length: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise MalformedRequest("invalid_base64")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise MalformedRequest("invalid_base64") from None
    if base64.b64encode(raw).decode("ascii") != value:
        raise MalformedRequest("noncanonical_base64")
    if expected_length is not None and len(raw) != expected_length:
        raise MalformedRequest("invalid_encoded_length")
    return raw
