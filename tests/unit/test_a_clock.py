"""Public logical clocks and inclusive protocol validity boundaries."""

import pytest


def test_injected_clocks_allow_reproducible_forward_and_backward_time():
    from kerberos_lab.common.clock import FrozenClock, OffsetClock
    from kerberos_lab.common.errors import MalformedRequest

    base = FrozenClock(1000)
    service = OffsetClock(base, -15)
    assert service.now() == 985
    base.advance(60)
    assert service.now() == 1045
    base.set(1010)
    assert service.now() == 995
    for invalid in (True, -1, 1.5, 2**53):
        with pytest.raises(MalformedRequest):
            base.set(invalid)
    assert base.now() == 1010
    with pytest.raises(MalformedRequest):
        OffsetClock(base, True)
    with pytest.raises(MalformedRequest):
        OffsetClock(FrozenClock(0), -1).now()


def test_system_clock_floors_seconds_at_the_time_boundary(monkeypatch):
    from kerberos_lab.common.clock import SystemClock

    monkeypatch.setattr("time.time", lambda: 1000.9)
    assert SystemClock().now() == 1000


@pytest.mark.parametrize("now, reason", [
    (970, None), (1330, None), (969, "ticket_not_yet_valid"), (1331, "ticket_expired"),
])
def test_ticket_leeway_is_inclusive(now, reason):
    from kerberos_lab.common.errors import InvalidAuthentication
    from kerberos_lab.common.models import Ticket, validate_ticket_time

    ticket = Ticket(1, "service", "1" * 32, "alice", "files", 1000, 1000, 1300,
                    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    if reason is None:
        assert validate_ticket_time(ticket, now=now, skew=30) is None
    else:
        with pytest.raises(InvalidAuthentication) as caught:
            validate_ticket_time(ticket, now=now, skew=30)
        assert caught.value.reason == reason


@pytest.mark.parametrize("now, accepted", [(970, True), (1030, True), (969, False), (1031, False)])
def test_authenticator_tolerance_is_inclusive(now, accepted):
    from kerberos_lab.common.errors import InvalidAuthentication, MalformedRequest
    from kerberos_lab.common.models import validate_authenticator_time

    if accepted:
        assert validate_authenticator_time(1000, now=now, skew=30) is None
    else:
        with pytest.raises(InvalidAuthentication, match="authenticator_skew"):
            validate_authenticator_time(1000, now=now, skew=30)
    with pytest.raises(MalformedRequest):
        validate_authenticator_time(True, now=now, skew=30)
