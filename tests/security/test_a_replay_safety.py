"""Adversarial retained-state checks at public crypto/HTTP/store seams."""

from dataclasses import replace
import hashlib
import hmac

import pytest

from kerberos_lab.common.clock import FrozenClock
from kerberos_lab.common.crypto import encode_b64, new_identifier, new_key, seal_ticket, sign_authenticator
from kerberos_lab.common.material import initialize_run, load_material
from kerberos_lab.common.models import ClientSession, Ticket, canonical_bytes
from kerberos_lab.common.replay_cache import ReplayStore
from kerberos_lab.common.settings import Settings
from kerberos_lab.resource_server.app import create_app


NOW = 1_700_000_000


@pytest.fixture
def lab(tmp_path):
    run = tmp_path / 'run'
    initialize_run(run, password='disposable replay safety test password')
    settings = Settings(run_dir=run, role='resource', port=5001)
    material = load_material(run, role='resource')
    ticket = Ticket(version=1, kind='service', ticket_id=new_identifier(), client_id='alice',
                    service_id='files', issued_at=NOW, not_before=NOW, expires_at=NOW + 300,
                    session_key=encode_b64(new_key()))
    session = ClientSession(ticket.client_id, ticket.service_id, ticket.ticket_id,
                            ticket.session_key, ticket.expires_at)
    envelope = seal_ticket(ticket, material.service_key)
    store = ReplayStore.open_existing(material.resource_store_path, expected_run_id=material.run_id, namespace='resource')
    return settings, session, envelope, store


def message(session, envelope, *, timestamp=NOW, nonce=None):
    body = {'operation': 'increment'}
    return dict(version=1, service_ticket=envelope, body=body,
                authenticator=sign_authenticator(session, envelope, body, purpose='resource',
                                                 timestamp=timestamp, request_nonce=nonce))


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
def test_forward_and_backward_clock_changes_never_forget_consumed_identity(lab, mode):
    settings, session, envelope, store = lab
    clock = FrozenClock(NOW)
    client = create_app(replace(settings, defense_mode=mode), clock=clock).test_client()
    captured = message(session, envelope)
    assert client.post('/access-resource', json=captured).get_json()['counter'] == 1
    count = 1
    # Outside tolerance, exact inclusive boundaries, and return to original time.
    for time, expected in [(NOW + 400, 401), (NOW - 31, 401),
                           (NOW - 30, 409), (NOW + 30, 409), (NOW, 409)]:
        clock.set(time)
        if expected == 409 and mode == 'authenticator_no_cache':
            expected = 200
            count += 1
        response = client.post('/access-resource', json=captured)
        assert response.status_code == expected
        if expected != 200:
            assert response.get_json() == {'version': 1, 'error': 'replay_detected' if expected == 409 else 'invalid_authentication'}
        assert store.counter(service_id='files') == count
    fresh = message(session, envelope)
    assert client.post('/access-resource', json=fresh).get_json()['counter'] == count + 1


def test_retention_and_capacity_do_not_reset_after_large_clock_excursion(lab):
    settings, session, envelope, store = lab
    clock = FrozenClock(NOW)
    client = create_app(replace(settings, replay_capacity=1), clock=clock).test_client()
    consumed = message(session, envelope)
    assert client.post('/access-resource', json=consumed).status_code == 200
    clock.set(NOW + 100_000)
    assert client.post('/access-resource', json=consumed).status_code == 401
    clock.set(NOW)
    assert client.post('/access-resource', json=consumed).status_code == 409
    response = client.post('/access-resource', json=message(session, envelope))
    assert response.status_code == 503
    assert response.get_json() == {'version': 1, 'error': 'replay_state_unavailable'}
    assert store.counter(service_id='files') == 1


def test_resigning_same_nonce_at_a_fresh_time_does_not_refresh_its_identity(lab):
    settings, session, envelope, store = lab
    clock = FrozenClock(NOW)
    client = create_app(settings, clock=clock).test_client()
    first = message(session, envelope, nonce='a' * 32)
    assert client.post('/access-resource', json=first).status_code == 200
    clock.advance(60)
    assert client.post('/access-resource', json=first).status_code == 401
    resigned = message(session, envelope, timestamp=NOW + 60, nonce='a' * 32)
    assert resigned['authenticator']['mac'] != first['authenticator']['mac']
    assert client.post('/access-resource', json=resigned).status_code == 409
    assert store.counter(service_id='files') == 1
    assert client.post('/access-resource', json=message(session, envelope, timestamp=NOW + 60)).get_json()['counter'] == 2


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('fault', ['domain', 'method', 'path', 'service', 'identity', 'ticket_id', 'body_digest', 'ticket_digest'])
def test_valid_mac_cannot_authorize_a_different_role_or_context(lab, mode, fault):
    from base64 import b64decode
    settings, session, envelope, store = lab
    client = create_app(replace(settings, defense_mode=mode), clock=FrozenClock(NOW)).test_client()
    attack = message(session, envelope)
    auth = attack['authenticator']
    modifications = {
        'method': ('method', 'GET'), 'path': ('path', '/service-ticket'),
        'service': ('service_id', 'other'), 'identity': ('client_id', 'bob'),
        'ticket_id': ('ticket_id', 'f' * 32), 'body_digest': ('body_sha256', '0' * 64),
        'ticket_digest': ('ticket_sha256', '0' * 64),
    }
    if fault != 'domain':
        key, value = modifications[fault]
        auth[key] = value
    # Attacker has the synthetic session key and recomputes a valid tag. This
    # checks authorization/context and domain separation, not just broken MACs.
    unsigned = {key: value for key, value in auth.items() if key != 'mac'}
    domain = b'ins-kerberos-lab:auth:v1:tgs\0' if fault == 'domain' else b'ins-kerberos-lab:auth:v1:resource\0'
    auth['mac'] = encode_b64(hmac.digest(b64decode(session.session_key), domain + canonical_bytes(unsigned), hashlib.sha256))
    response = client.post('/access-resource', json=attack)
    assert response.status_code == 401
    assert response.get_json() == {'version': 1, 'error': 'invalid_authentication'}
    assert store.counter(service_id='files') == 0
    valid = message(session, envelope, nonce=auth['request_nonce'])
    assert client.post('/access-resource', json=valid).get_json()['counter'] == 1


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('fault', ['deep_json', 'surrogate', 'escaped_duplicate'])
def test_adversarial_json_cannot_reach_protected_execution(lab, mode, fault):
    settings, session, envelope, store = lab
    client = create_app(replace(settings, defense_mode=mode), clock=FrozenClock(NOW)).test_client()
    valid = message(session, envelope)
    raw = canonical_bytes(valid)
    if fault == 'deep_json':
        raw = b'{"body":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}'
    elif fault == 'surrogate':
        raw = raw.replace(b'"increment"', b'"\\ud800"')
    else:
        raw = raw.replace(b'"version":1', b'"version":1,"ver\\u0073ion":1', 1)
    response = client.post('/access-resource', data=raw, content_type='application/json')
    assert response.status_code == 400
    assert response.get_json() == {'version': 1, 'error': 'malformed_request'}
    assert store.counter(service_id='files') == 0
    assert client.post('/access-resource', json=valid).get_json()['counter'] == 1
