"""Reusable loopback client APIs for login, ticket requests and captures."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from kerberos_lab.common.clock import Clock, SystemClock
from kerberos_lab.common.crypto import decode_b64, sign_authenticator
from kerberos_lab.common.errors import LabError
from kerberos_lab.common.models import ClientSession, canonical_bytes, parse_json_object


_BODY_LIMIT = 65_536
_CAPTURE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,123}\.json\Z")
_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_NONCE = re.compile(r"[0-9a-f]{32}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_AUTHENTICATOR_FIELDS = {
    "version", "client_id", "service_id", "ticket_id", "timestamp",
    "request_nonce", "method", "path", "body_sha256", "ticket_sha256", "mac",
}


class ClientError(Exception):
    """Base class for client-side failures that are safe to display."""


class ClientTransportError(ClientError):
    """The loopback endpoint could not be reached or timed out."""


class ClientProtocolError(ClientError):
    """A server response did not match the v1 message contract."""


class CaptureError(ClientError):
    """A private request capture could not be validated or accessed."""


class RemoteError(ClientError):
    """A server returned a stable v1 public error response."""

    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code
        super().__init__(f"server returned HTTP {status}: {code}")


@dataclass(frozen=True)
class LoginGrant:
    tgt: dict[str, object] = field(repr=False)
    session: ClientSession = field(repr=False)


@dataclass(frozen=True)
class ServiceGrant:
    service_ticket: dict[str, object] = field(repr=False)
    session: ClientSession = field(repr=False)


@dataclass(frozen=True, repr=False)
class CapturedRequest:
    """A validated canonical resource request; raw bytes are preserved exactly."""

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.raw_bytes, bytes):
            raise CaptureError("capture must be bytes")
        try:
            message = parse_json_object(self.raw_bytes, max_bytes=_BODY_LIMIT)
            if canonical_bytes(message) != self.raw_bytes:
                raise CaptureError("capture is not canonical v1 JSON")
            _validate_resource_request(message)
        except CaptureError:
            raise
        except (LabError, ClientProtocolError, TypeError, ValueError):
            raise CaptureError("capture does not match the v1 resource request") from None

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> "CapturedRequest":
        return cls(raw_bytes)

    @property
    def message(self) -> dict[str, object]:
        # Return a fresh parse so callers cannot mutate validation state.
        return parse_json_object(self.raw_bytes, max_bytes=_BODY_LIMIT)

    @property
    def request_nonce(self) -> str:
        auth = self.message["authenticator"]
        assert isinstance(auth, dict)
        nonce = auth["request_nonce"]
        assert isinstance(nonce, str)
        return nonce

    @property
    def operation(self) -> str:
        body = self.message["body"]
        assert isinstance(body, dict)
        operation = body["operation"]
        assert isinstance(operation, str)
        return operation

    def __repr__(self) -> str:
        return f"CapturedRequest(request_nonce={self.request_nonce!r}, bytes={len(self.raw_bytes)})"


def _exact_fields(value: object, expected: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ClientProtocolError("response fields do not match the v1 contract")
    return value


def _version_one(value: object) -> None:
    if type(value) is not int or value != 1:
        raise ClientProtocolError("unsupported response version")


def _base_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise ClientProtocolError("invalid loopback endpoint") from None
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ClientProtocolError("endpoints must use the 127.0.0.1 HTTP interface")
    if port is not None and not 1 <= port <= 65535:
        raise ClientProtocolError("invalid loopback endpoint port")
    return f"http://127.0.0.1{':' + str(port) if port is not None else ''}"


def _validate_envelope(value: object, *, kind: str) -> dict[str, object]:
    envelope = _exact_fields(value, {"version", "kind", "nonce", "ciphertext"})
    _version_one(envelope["version"])
    if envelope["kind"] != kind:
        raise ClientProtocolError("ticket envelope has the wrong kind")
    try:
        decode_b64(envelope["nonce"], expected_length=12)
        ciphertext = decode_b64(envelope["ciphertext"])
    except LabError:
        raise ClientProtocolError("ticket envelope is malformed") from None
    if not 16 <= len(ciphertext) <= 8208:
        raise ClientProtocolError("ticket envelope is malformed")
    return envelope


def _validate_resource_request(message: object) -> dict[str, object]:
    request = _exact_fields(
        message, {"version", "service_ticket", "authenticator", "body"}
    )
    _version_one(request["version"])
    envelope = _validate_envelope(request["service_ticket"], kind="service")
    body = _exact_fields(request["body"], {"operation"})
    if body["operation"] != "increment":
        raise ClientProtocolError("unsupported captured operation")

    auth = _exact_fields(request["authenticator"], _AUTHENTICATOR_FIELDS)
    _version_one(auth["version"])
    if (not isinstance(auth["client_id"], str) or not _ID.fullmatch(auth["client_id"])
            or auth["service_id"] != "files"
            or not isinstance(auth["ticket_id"], str) or not _NONCE.fullmatch(auth["ticket_id"])
            or not isinstance(auth["request_nonce"], str) or not _NONCE.fullmatch(auth["request_nonce"])
            or type(auth["timestamp"]) is not int
            or not 0 <= auth["timestamp"] <= 9_007_199_254_740_991
            or auth["method"] != "POST" or auth["path"] != "/access-resource"
            or not isinstance(auth["body_sha256"], str) or not _DIGEST.fullmatch(auth["body_sha256"])
            or not isinstance(auth["ticket_sha256"], str) or not _DIGEST.fullmatch(auth["ticket_sha256"])):
        raise ClientProtocolError("captured authenticator is malformed")
    try:
        decode_b64(auth["mac"], expected_length=32)
    except LabError:
        raise ClientProtocolError("captured authenticator is malformed") from None
    if (auth["body_sha256"] != hashlib.sha256(canonical_bytes(body)).hexdigest()
            or auth["ticket_sha256"] != hashlib.sha256(canonical_bytes(envelope)).hexdigest()):
        raise ClientProtocolError("captured request digest does not match its contents")
    return request


def _parse_object(raw: bytes, *, description: str) -> dict[str, object]:
    try:
        return parse_json_object(raw, max_bytes=_BODY_LIMIT)
    except LabError:
        raise ClientProtocolError(f"{description} was not a v1 JSON object") from None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AuthenticationClient:
    """Reusable AS/TGS/resource client with injectable logical time."""

    def __init__(self, kdc_url: str = "http://127.0.0.1:5000",
                 resource_url: str = "http://127.0.0.1:5001", *,
                 clock: Clock | None = None, timeout: float = 5.0) -> None:
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or timeout <= 0):
            raise ClientProtocolError("timeout must be positive")
        self.kdc_url = _base_url(kdc_url)
        self.resource_url = _base_url(resource_url)
        self.clock = SystemClock() if clock is None else clock
        self.timeout = float(timeout)
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _exchange(self, url: str, *, method: str, data: bytes | None = None
                  ) -> tuple[int, dict[str, object]]:
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                status = response.status
                raw = response.read(_BODY_LIMIT + 1)
        except HTTPError as error:
            status = error.code
            raw = error.read(_BODY_LIMIT + 1)
        except (URLError, TimeoutError, OSError):
            raise ClientTransportError("loopback service could not be reached") from None
        if len(raw) > _BODY_LIMIT:
            raise ClientProtocolError("server response exceeded the v1 size limit")
        if not 200 <= status < 300:
            try:
                error = _parse_object(raw, description="error response")
            except ClientProtocolError:
                raise RemoteError(status, f"http_{status}") from None
            if set(error) != {"version", "error"} or type(error["version"]) is not int or error["version"] != 1 or not isinstance(error["error"], str):
                raise ClientProtocolError("server returned a non-contract error response")
            raise RemoteError(status, error["error"])
        return status, _parse_object(raw, description="success response")

    def _post_object(self, base_url: str, path: str, payload: dict[str, object]
                     ) -> dict[str, object]:
        _status, response = self._exchange(
            base_url + path, method="POST", data=canonical_bytes(payload)
        )
        return response

    def login(self, username: str, password: str) -> LoginGrant:
        if not isinstance(username, str) or not isinstance(password, str):
            raise ClientProtocolError("username and password must be text")
        response = self._post_object(
            self.kdc_url,
            "/login",
            {"username": username, "password": password},
        )
        _exact_fields(response, {"version", "tgt", "client_session"})
        _version_one(response["version"])
        tgt = _validate_envelope(response["tgt"], kind="tgt")
        try:
            session = ClientSession.from_dict(response["client_session"])
        except LabError:
            raise ClientProtocolError("KDC returned an invalid client/TGS session") from None
        if session.client_id != username or session.service_id != "tgs":
            raise ClientProtocolError("KDC returned a session for the wrong client or role")
        return LoginGrant(tgt=tgt, session=session)

    def request_service_ticket(self, login: LoginGrant, *, service_id: str = "files"
                               ) -> ServiceGrant:
        if not isinstance(login, LoginGrant):
            raise ClientProtocolError("login result is required")
        body: dict[str, object] = {"service_id": service_id}
        authenticator = sign_authenticator(
            login.session,
            login.tgt,
            body,
            purpose="tgs",
            timestamp=self.clock.now(),
        )
        response = self._post_object(self.kdc_url, "/service-ticket", {
            "version": 1,
            "tgt": login.tgt,
            "authenticator": authenticator,
            "body": body,
        })
        _exact_fields(response, {"version", "service_ticket", "client_session"})
        _version_one(response["version"])
        envelope = _validate_envelope(response["service_ticket"], kind="service")
        try:
            session = ClientSession.from_dict(response["client_session"])
        except LabError:
            raise ClientProtocolError("KDC returned an invalid client/service session") from None
        if (session.client_id != login.session.client_id
                or session.service_id != service_id):
            raise ClientProtocolError("KDC returned a session for the wrong client or service")
        return ServiceGrant(service_ticket=envelope, session=session)

    def authenticate(self, username: str, password: str, *, service_id: str = "files"
                     ) -> ServiceGrant:
        """Perform AS login and TGS issuance once; reuse the result for fresh requests."""
        return self.request_service_ticket(
            self.login(username, password), service_id=service_id
        )

    def build_resource_request(self, grant: ServiceGrant, *, operation: str = "increment"
                               ) -> CapturedRequest:
        if not isinstance(grant, ServiceGrant):
            raise ClientProtocolError("service ticket grant is required")
        body: dict[str, object] = {"operation": operation}
        authenticator = sign_authenticator(
            grant.session,
            grant.service_ticket,
            body,
            purpose="resource",
            timestamp=self.clock.now(),
        )
        return CapturedRequest.from_bytes(canonical_bytes({
            "version": 1,
            "service_ticket": grant.service_ticket,
            "authenticator": authenticator,
            "body": body,
        }))

    def send_resource_request(self, captured: CapturedRequest) -> dict[str, object]:
        if not isinstance(captured, CapturedRequest):
            raise ClientProtocolError("a validated captured request is required")
        _status, response = self._exchange(
            self.resource_url + "/access-resource",
            method="POST",
            data=captured.raw_bytes,
        )
        _exact_fields(response, {
            "version", "status", "client_id", "service_id", "request_nonce",
            "operation", "counter",
        })
        _version_one(response["version"])
        message = captured.message
        auth = message["authenticator"]
        assert isinstance(auth, dict)
        if (response["status"] != "granted"
                or response["client_id"] != auth["client_id"]
                or response["service_id"] != "files"
                or response["request_nonce"] != captured.request_nonce
                or response["operation"] != captured.operation
                or type(response["counter"]) is not int
                or response["counter"] < 1):
            raise ClientProtocolError("resource response does not match the v1 grant")
        return response


def _capture_directory(run_dir: Path) -> Path:
    try:
        root = Path(run_dir).resolve(strict=True)
        if not root.is_dir():
            raise OSError("not a run directory")
        directory = root / "captures"
        if directory.is_symlink():
            raise OSError("capture directory cannot be a symlink")
        directory.mkdir(mode=0o700, exist_ok=True)
        resolved = directory.resolve(strict=True)
        if resolved.parent != root:
            raise OSError("capture directory escaped run directory")
        return resolved
    except (OSError, TypeError, ValueError):
        raise CaptureError("private capture directory is unavailable") from None


def _capture_path(run_dir: Path, name: str) -> Path:
    if not isinstance(name, str) or not _CAPTURE_NAME.fullmatch(name):
        raise CaptureError("capture name must be a simple .json filename")
    return _capture_directory(run_dir) / name


def save_capture(run_dir: Path, captured: CapturedRequest, *, name: str | None = None) -> str:
    """Create a non-overwriting capture under `<run-dir>/captures/`."""
    if not isinstance(captured, CapturedRequest):
        raise CaptureError("a validated captured request is required")
    filename = name or f"resource-{captured.request_nonce}.json"
    target = _capture_path(run_dir, filename)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(target, flags, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(captured.raw_bytes)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        raise CaptureError("capture already exists") from None
    except OSError:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise CaptureError("capture could not be written") from None
    return f"captures/{filename}"


def load_capture(run_dir: Path, name: str) -> CapturedRequest:
    """Read and validate a capture without changing its transmitted bytes."""
    target = _capture_path(run_dir, name)
    if target.is_symlink():
        raise CaptureError("capture cannot be a symlink")
    try:
        raw = target.read_bytes()
    except OSError:
        raise CaptureError("capture could not be read") from None
    return CapturedRequest.from_bytes(raw)


def _get_json(url: str, *, timeout: float) -> dict[str, object]:
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with opener.open(req, timeout=timeout) as response:
            if response.status != 200:
                raise ClientProtocolError("health endpoint did not return HTTP 200")
            raw = response.read(_BODY_LIMIT + 1)
    except HTTPError as error:
        raise ClientProtocolError(f"health endpoint returned HTTP {error.code}") from None
    except (URLError, TimeoutError, OSError):
        raise ClientTransportError("loopback health endpoint could not be reached") from None
    if len(raw) > _BODY_LIMIT:
        raise ClientProtocolError("health response exceeded the v1 size limit")
    return _parse_object(raw, description="health response")


def check_health(kdc_url: str = "http://127.0.0.1:5000",
                 resource_url: str = "http://127.0.0.1:5001", *,
                 timeout: float = 3.0) -> list[dict[str, object]]:
    """Check both local roles, preserving the original no-argument CLI behavior."""
    endpoints = (("kdc", _base_url(kdc_url) + "/health"),
                 ("resource_server", _base_url(resource_url) + "/health"))
    results: list[dict[str, object]] = []
    for role, url in endpoints:
        payload = _get_json(url, timeout=timeout)
        if payload.get("status") != "ok" or payload.get("role") != role:
            raise ClientProtocolError(f"{role} health response did not match the expected role")
        results.append({"url": url, **payload})
    return results
