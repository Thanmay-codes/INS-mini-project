"""HTTP-level KDC exchange tests using real tickets and SQLite replay state."""

from dataclasses import replace

import pytest

from kerberos_lab.common.clock import FrozenClock
from kerberos_lab.common.crypto import (
    encode_b64,
    new_identifier,
    open_ticket,
    seal_ticket,
    sign_authenticator,
)
from kerberos_lab.common.errors import InvalidAuthentication
from kerberos_lab.common.material import initialize_run, load_material
from kerberos_lab.common.models import ClientSession, Ticket
from kerberos_lab.common.settings import Settings
from kerberos_lab.kdc.app import create_app


PASSWORD = "a synthetic test password"
NOW = 1_700_000_000


@pytest.fixture
def kdc(tmp_path):
    run_dir = tmp_path / "run"
    initialize_run(run_dir, password=PASSWORD, run_id="a" * 32)
    clock = FrozenClock(NOW)
    settings = Settings(
        run_dir=run_dir,
        role="kdc",
        port=5000,
        frozen_time_seconds=NOW,
    )
    app = create_app(settings, clock=clock)
    app.testing = True
    return app.test_client(), run_dir, clock


def login(client, username="alice", password=PASSWORD):
    return client.post("/login", json={"username": username, "password": password})


def service_exchange(client, login_response, *, body=None, timestamp=NOW, nonce=None,
                     mutate_auth=None, tgt_override=None):
    data = login_response.get_json()
    tgt = data["tgt"] if tgt_override is None else tgt_override
    body = {"service_id": "files"} if body is None else body
    session = ClientSession.from_dict(data["client_session"])
    authenticator = sign_authenticator(
        session,
        data["tgt"],
        {"service_id": "files"},
        purpose="tgs",
        timestamp=timestamp,
        request_nonce=nonce,
    )
    if mutate_auth is not None:
        mutate_auth(authenticator)
    return client.post("/service-ticket", json={
        "version": 1,
        "tgt": tgt,
        "authenticator": authenticator,
        "body": body,
    })


def test_health_and_valid_as_tgs_exchange(kdc):
    client, run_dir, _clock = kdc
    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok", "role": "kdc", "stage": "implemented"}

    login_response = login(client)
    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert set(login_data) == {"version", "tgt", "client_session"}
    assert login_data["version"] == 1

    material = load_material(run_dir, role="kdc")
    tgt = open_ticket(login_data["tgt"], material.tgs_key, expected_kind="tgt")
    tgt_session = ClientSession.from_dict(login_data["client_session"])
    assert tgt.client_id == tgt_session.client_id == "alice"
    assert tgt.ticket_id == tgt_session.ticket_id
    assert tgt.session_key == tgt_session.session_key
    assert tgt.service_id == tgt_session.service_id == "tgs"

    service_response = service_exchange(client, login_response)
    assert service_response.status_code == 200
    service_data = service_response.get_json()
    assert set(service_data) == {"version", "service_ticket", "client_session"}
    assert service_data["version"] == 1
    service = open_ticket(
        service_data["service_ticket"], material.service_key, expected_kind="service"
    )
    service_session = ClientSession.from_dict(service_data["client_session"])
    assert service.client_id == service_session.client_id == "alice"
    assert service.service_id == service_session.service_id == "files"
    assert service.ticket_id == service_session.ticket_id
    assert service.session_key == service_session.session_key
    assert service.session_key != tgt.session_key
    with pytest.raises(InvalidAuthentication):
        open_ticket(service_data["service_ticket"], material.tgs_key, expected_kind="service")


@pytest.mark.parametrize(
    ("username", "password"),
    [("unknown-user", PASSWORD), ("alice", "incorrect password")],
)
def test_unknown_user_and_wrong_password_have_same_public_error(kdc, username, password):
    response = login(kdc[0], username=username, password=password)
    assert response.status_code == 401
    assert response.get_json() == {"version": 1, "error": "invalid_credentials"}


@pytest.mark.parametrize("tamper", ["ciphertext", "kind"])
def test_modified_or_wrong_kind_tgt_is_rejected(kdc, tamper):
    client, _run_dir, _clock = kdc
    login_response = login(client)
    tgt = login_response.get_json()["tgt"]
    if tamper == "kind":
        tgt["kind"] = "service"
    else:
        from base64 import b64decode

        ciphertext = bytearray(b64decode(tgt["ciphertext"]))
        ciphertext[0] ^= 1
        tgt["ciphertext"] = encode_b64(bytes(ciphertext))

    response = service_exchange(client, login_response, tgt_override=tgt)
    assert response.status_code == 401
    assert response.get_json() == {"version": 1, "error": "invalid_authentication"}


def test_tgs_authenticator_replay_is_rejected(kdc):
    client, _run_dir, _clock = kdc
    login_response = login(client)
    nonce = "b" * 32
    first = service_exchange(client, login_response, nonce=nonce)
    replay = service_exchange(client, login_response, nonce=nonce)
    assert first.status_code == 200
    assert replay.status_code == 409
    assert replay.get_json() == {"version": 1, "error": "replay_detected"}


def test_tgs_replay_is_always_checked_in_resource_no_cache_mode(tmp_path):
    run_dir = tmp_path / "run"
    initialize_run(run_dir, password=PASSWORD, run_id="d" * 32)
    settings = Settings(
        run_dir=run_dir,
        role="kdc",
        port=5000,
        frozen_time_seconds=NOW,
        defense_mode="authenticator_no_cache",
    )
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    login_response = login(client)
    assert login_response.status_code == 200
    nonce = "c" * 32
    assert service_exchange(client, login_response, nonce=nonce).status_code == 200
    replay = service_exchange(client, login_response, nonce=nonce)
    assert replay.status_code == 409
    assert replay.get_json() == {"version": 1, "error": "replay_detected"}


def test_unsupported_service_is_authenticated_then_rejected(kdc):
    client, _run_dir, _clock = kdc
    login_response = login(client)
    data = login_response.get_json()
    session = ClientSession.from_dict(data["client_session"])
    body = {"service_id": "admin"}
    authenticator = sign_authenticator(
        session, data["tgt"], body, purpose="tgs", timestamp=NOW
    )
    response = client.post("/service-ticket", json={
        "version": 1,
        "tgt": data["tgt"],
        "authenticator": authenticator,
        "body": body,
    })
    assert response.status_code == 403
    assert response.get_json() == {"version": 1, "error": "wrong_service"}


def test_modified_body_and_authenticator_context_are_rejected(kdc):
    client, _run_dir, _clock = kdc
    login_response = login(client)

    body_mismatch = service_exchange(client, login_response, body={"service_id": "other"})
    assert body_mismatch.status_code == 401
    assert body_mismatch.get_json() == {"version": 1, "error": "invalid_authentication"}

    context_mismatch = service_exchange(
        client, login_response, mutate_auth=lambda auth: auth.update(path="/login")
    )
    assert context_mismatch.status_code == 401
    assert context_mismatch.get_json() == {"version": 1, "error": "invalid_authentication"}


def test_authenticator_skew_and_expired_tgt_are_rejected(kdc):
    client, run_dir, _clock = kdc
    login_response = login(client)

    skewed = service_exchange(client, login_response, timestamp=NOW - 31)
    assert skewed.status_code == 401
    assert skewed.get_json() == {"version": 1, "error": "invalid_authentication"}

    data = login_response.get_json()
    session = ClientSession.from_dict(data["client_session"])
    material = load_material(run_dir, role="kdc")
    expired = Ticket(
        version=1,
        kind="tgt",
        ticket_id=new_identifier(),
        client_id="alice",
        service_id="tgs",
        issued_at=NOW - 600,
        not_before=NOW - 600,
        expires_at=NOW - 31,
        session_key=session.session_key,
    )
    expired_session = replace(session, ticket_id=expired.ticket_id, expires_at=expired.expires_at)
    envelope = seal_ticket(expired, material.tgs_key)
    body = {"service_id": "files"}
    authenticator = sign_authenticator(
        expired_session, envelope, body, purpose="tgs", timestamp=NOW
    )
    expired_response = client.post("/service-ticket", json={
        "version": 1,
        "tgt": envelope,
        "authenticator": authenticator,
        "body": body,
    })
    assert expired_response.status_code == 401
    assert expired_response.get_json() == {"version": 1, "error": "invalid_authentication"}


def test_malformed_http_and_duplicate_json_keys_are_normalized(kdc):
    client, _run_dir, _clock = kdc
    no_json = client.post("/login", data="{}", content_type="text/plain")
    duplicate = client.post(
        "/login",
        data='{"username":"alice","username":"alice","password":"x"}',
        content_type="application/json",
    )
    query = client.post("/login?debug=1", json={"username": "alice", "password": PASSWORD})
    for response in (no_json, duplicate, query):
        assert response.status_code == 400
        assert response.get_json() == {"version": 1, "error": "malformed_request"}
