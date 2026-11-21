"""Public responses must not expose private diagnostic strings."""

import pytest


@pytest.mark.parametrize("name, status, code", [
    ("MalformedRequest", 400, "malformed_request"),
    ("InvalidCredentials", 401, "invalid_credentials"),
    ("InvalidAuthentication", 401, "invalid_authentication"),
    ("WrongService", 403, "wrong_service"),
    ("ReplayDetected", 409, "replay_detected"),
    ("ReplayStateUnavailable", 503, "replay_state_unavailable"),
])
def test_private_error_diagnostics_never_enter_the_public_error_envelope(name, status, code):
    from kerberos_lab.common import errors

    error = getattr(errors, name)("private-diagnostic")
    assert errors.to_error_response(error) == ({"version": 1, "error": code}, status)
    assert error.reason == "private-diagnostic"
