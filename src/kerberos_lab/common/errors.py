"""Stable public errors, separated from controlled private diagnostics."""


class LabError(Exception):
    code = "lab_error"
    http_status = 500

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__(reason)


class MalformedRequest(LabError):
    code = "malformed_request"
    http_status = 400


class InvalidAuthentication(LabError):
    code = "invalid_authentication"
    http_status = 401


class InvalidCredentials(LabError):
    code = "invalid_credentials"
    http_status = 401


class WrongService(LabError):
    code = "wrong_service"
    http_status = 403


class ReplayDetected(LabError):
    code = "replay_detected"
    http_status = 409


class ReplayStateUnavailable(LabError):
    code = "replay_state_unavailable"
    http_status = 503


def to_error_response(error: LabError) -> tuple[dict[str, object], int]:
    return {"version": 1, "error": error.code}, error.http_status
