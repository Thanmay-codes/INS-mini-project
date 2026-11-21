"""Resource v1 behavior through the public factory and HTTP interface."""

from dataclasses import replace

import pytest

from kerberos_lab.common.clock import FrozenClock
from kerberos_lab.common.crypto import (
    encode_b64, new_identifier, new_key, seal_ticket, sign_authenticator,
)
from kerberos_lab.common.material import initialize_run, load_material
from kerberos_lab.common.models import ClientSession, Ticket
from kerberos_lab.common.replay_cache import ReplayStore
from kerberos_lab.common.settings import Settings
from kerberos_lab.resource_server.app import create_app


NOW = 1_700_000_000


@pytest.fixture
def lab(tmp_path):
    run = tmp_path / 'run'
    initialize_run(run, password='disposable resource test password')
    return Settings(run_dir=run, role='resource', port=5001)


def resource_request(settings, *, timestamp=NOW, ticket=None, envelope=None, nonce=None):
    material = load_material(settings.run_dir, role='resource')
    if ticket is None:
        ticket = Ticket(version=1, kind='service', ticket_id=new_identifier(),
                        client_id='alice', service_id='files', issued_at=NOW,
                        not_before=NOW, expires_at=NOW + 300,
                        session_key=encode_b64(new_key()))
    if envelope is None:
        envelope = seal_ticket(ticket, material.service_key)
    session = ClientSession(ticket.client_id, ticket.service_id, ticket.ticket_id,
                            ticket.session_key, ticket.expires_at)
    body = {'operation': 'increment'}
    authenticator = sign_authenticator(session, envelope, body, purpose='resource',
                                      timestamp=timestamp, request_nonce=nonce)
    return {'version': 1, 'service_ticket': envelope, 'authenticator': authenticator, 'body': body}


def counter(settings):
    material = load_material(settings.run_dir, role='resource')
    return ReplayStore.open_existing(material.resource_store_path, expected_run_id=material.run_id,
                                     namespace='resource').counter(service_id='files')


def test_valid_request_commits_operation_and_returns_only_public_fields(lab):
    message = resource_request(lab)
    client = create_app(lab, clock=FrozenClock(NOW)).test_client()
    response = client.post('/access-resource', json=message)
    assert response.status_code == 200
    assert response.get_json() == {
        'version': 1, 'status': 'granted', 'client_id': 'alice', 'service_id': 'files',
        'request_nonce': message['authenticator']['request_nonce'], 'operation': 'increment', 'counter': 1,
    }
    assert counter(lab) == 1
    assert client.get('/health').get_json() == {
        'status': 'ok', 'role': 'resource_server', 'stage': 'implemented',
    }


@pytest.mark.parametrize('mode,second_status,expected_counter', [
    ('authenticator_cache', 409, 1), ('authenticator_no_cache', 200, 2),
])
def test_replay_differs_only_by_duplicate_tracking(lab, mode, second_status, expected_counter):
    import json
    settings = replace(lab, defense_mode=mode)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    message = resource_request(settings)
    assert client.post('/access-resource', json=message).status_code == 200
    # Formatting the same logical request differently must not refresh its identity.
    response = client.post('/access-resource', data=json.dumps(message, indent=2), content_type='application/json')
    assert response.status_code == second_status
    if second_status == 409:
        assert response.get_json() == {'version': 1, 'error': 'replay_detected'}
    else:
        assert response.get_json()['counter'] == 2
    assert counter(settings) == expected_counter


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
def test_fresh_nonce_on_same_ticket_is_legitimate(lab, mode):
    settings = replace(lab, defense_mode=mode)
    message = resource_request(settings)
    ticket = Ticket(version=1, kind='service', ticket_id=message['authenticator']['ticket_id'],
                    client_id='alice', service_id='files', issued_at=NOW, not_before=NOW,
                    expires_at=NOW + 300, session_key=encode_b64(new_key()))
    first = resource_request(settings, ticket=ticket)
    second = resource_request(settings, ticket=ticket, envelope=first['service_ticket'])
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    assert first['authenticator']['request_nonce'] != second['authenticator']['request_nonce']
    assert client.post('/access-resource', json=first).get_json()['counter'] == 1
    assert client.post('/access-resource', json=second).get_json()['counter'] == 2
    assert counter(settings) == 2


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('field,value', [
    ('client_id', 'bob'), ('service_id', 'other'), ('ticket_id', 'f' * 32),
    ('method', 'GET'), ('path', '/service-ticket'), ('body_sha256', '0' * 64),
    ('ticket_sha256', '0' * 64), ('mac', encode_b64(bytes(32))),
])
def test_invalid_authentication_cannot_mutate_counter_or_reserve_nonce(lab, mode, field, value):
    from copy import deepcopy
    settings = replace(lab, defense_mode=mode)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    valid = resource_request(settings)
    invalid = deepcopy(valid)
    invalid['authenticator'][field] = value
    response = client.post('/access-resource', json=invalid)
    assert response.status_code == 401
    assert response.get_json() == {'version': 1, 'error': 'invalid_authentication'}
    assert counter(settings) == 0
    assert client.post('/access-resource', json=valid).get_json()['counter'] == 1


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('fault', ['ciphertext', 'wrong_key', 'tgt', 'unknown_user'])
def test_invalid_ticket_rejected_in_both_modes(lab, mode, fault):
    from base64 import b64decode
    settings = replace(lab, defense_mode=mode)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    message = resource_request(settings)
    if fault == 'ciphertext':
        ciphertext = bytearray(b64decode(message['service_ticket']['ciphertext']))
        ciphertext[0] ^= 1
        message['service_ticket']['ciphertext'] = encode_b64(bytes(ciphertext))
    elif fault == 'tgt':
        tgt = Ticket(version=1, kind='tgt', ticket_id=new_identifier(), client_id='alice',
                     service_id='tgs', issued_at=NOW, not_before=NOW, expires_at=NOW + 300,
                     session_key=encode_b64(new_key()))
        # Even a TGT encrypted under the resource key cannot cross the role boundary.
        message['service_ticket'] = seal_ticket(tgt, load_material(settings.run_dir, role='resource').service_key)
    else:
        ticket = Ticket(version=1, kind='service', ticket_id=new_identifier(),
                        client_id='bob' if fault == 'unknown_user' else 'alice', service_id='files',
                        issued_at=NOW, not_before=NOW, expires_at=NOW + 300, session_key=encode_b64(new_key()))
        envelope = seal_ticket(ticket, new_key()) if fault == 'wrong_key' else None
        message = resource_request(settings, ticket=ticket, envelope=envelope)
    response = client.post('/access-resource', json=message)
    assert response.status_code == 401
    assert response.get_json() == {'version': 1, 'error': 'invalid_authentication'}
    assert counter(settings) == 0


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('field,value', [
    ('version', True), ('version', 2), ('extra', 1), ('body', {'operation': 'delete'}),
    ('body', {'operation': 'increment', 'extra': 1}), ('body', None),
    ('authenticator', {}), ('service_ticket', {}),
])
def test_invalid_schema_rejected_in_both_modes(lab, mode, field, value):
    settings = replace(lab, defense_mode=mode)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    message = resource_request(settings)
    message[field] = value
    response = client.post('/access-resource', json=message)
    assert response.status_code == 400
    assert response.get_json() == {'version': 1, 'error': 'malformed_request'}
    assert counter(settings) == 0


@pytest.mark.parametrize('raw,content_type,path', [
    (b'{}', 'text/plain', '/access-resource'),
    (b'{}', 'application/json', '/access-resource?debug=1'),
    (b'{"version":1,"version":1}', 'application/json', '/access-resource'),
    (b'{"a":{"key":1,"key":2}}', 'application/json', '/access-resource'),
    (b'{"version":1.0}', 'application/json', '/access-resource'),
    (b'{"version":NaN}', 'application/json', '/access-resource'),
    (b'\xff', 'application/json', '/access-resource'),
    (b'[]', 'application/json', '/access-resource'),
    (b'{' + b' ' * 65536, 'application/json', '/access-resource'),
])
def test_http_boundary_normalizes_bad_requests(lab, raw, content_type, path):
    client = create_app(lab, clock=FrozenClock(NOW)).test_client()
    response = client.post(path, data=raw, content_type=content_type)
    assert response.status_code == 400
    assert response.get_json() == {'version': 1, 'error': 'malformed_request'}
    assert counter(lab) == 0


def test_other_routes_and_methods_keep_framework_status(lab):
    client = create_app(lab, clock=FrozenClock(NOW)).test_client()
    assert client.get('/access-resource').status_code == 405
    assert client.post('/unknown', json={}).status_code == 404
    assert client.post('/access-resource/', json={}).status_code == 404
    assert client.post('/clock', json={'timestamp': NOW}).status_code == 404


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('offset,status', [(-31, 401), (-30, 200), (0, 200), (330, 200), (331, 401)])
def test_ticket_time_boundaries_are_inclusive(lab, mode, offset, status):
    settings = replace(lab, defense_mode=mode)
    now = NOW + offset
    client = create_app(settings, clock=FrozenClock(now)).test_client()
    response = client.post('/access-resource', json=resource_request(settings, timestamp=now))
    assert response.status_code == status
    assert counter(settings) == (1 if status == 200 else 0)


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('offset,status', [(-31, 401), (-30, 200), (30, 200), (31, 401)])
def test_authenticator_time_boundaries_are_inclusive(lab, mode, offset, status):
    settings = replace(lab, defense_mode=mode)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    response = client.post('/access-resource', json=resource_request(settings, timestamp=NOW + offset))
    assert response.status_code == status
    assert counter(settings) == (1 if status == 200 else 0)


def test_one_logical_time_is_captured_for_validation_and_commit(lab):
    class SingleReadingClock:
        def __init__(self):
            self.read = False

        def now(self):
            if self.read:
                raise RuntimeError('request must not depend on a second clock reading')
            self.read = True
            return NOW

    client = create_app(lab, clock=SingleReadingClock()).test_client()
    assert client.post('/access-resource', json=resource_request(lab)).status_code == 200
    assert counter(lab) == 1


def test_authentication_precedes_replay_classification(lab):
    from copy import deepcopy
    clock = FrozenClock(NOW)
    client = create_app(lab, clock=clock).test_client()
    message = resource_request(lab)
    assert client.post('/access-resource', json=message).status_code == 200
    invalid = deepcopy(message)
    invalid['authenticator']['mac'] = encode_b64(bytes(32))
    assert client.post('/access-resource', json=invalid).status_code == 401
    clock.advance(331)
    assert client.post('/access-resource', json=message).status_code == 401
    assert counter(lab) == 1


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
@pytest.mark.parametrize('damage', ['missing', 'corrupt', 'wrong_run'])
def test_required_state_failure_rejects_access_without_reinitializing(lab, mode, damage):
    import sqlite3
    settings = replace(lab, defense_mode=mode)
    message = resource_request(settings)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    path = settings.run_dir / 'resource.sqlite'
    if damage == 'missing':
        path.unlink()
    elif damage == 'corrupt':
        path.write_bytes(b'corrupt SQLite')
    else:
        with sqlite3.connect(path) as connection:
            connection.execute('UPDATE metadata SET run_id=?', ('f' * 32,))
    response = client.post('/access-resource', json=message)
    assert response.status_code == 503
    assert response.get_json() == {'version': 1, 'error': 'replay_state_unavailable'}
    message['authenticator']['mac'] = encode_b64(bytes(32))
    assert client.post('/access-resource', json=message).status_code == 401
    if damage == 'missing':
        assert not path.exists()


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
def test_startup_requires_initialized_state_and_correct_role(lab, mode):
    from kerberos_lab.common.errors import MalformedRequest, ReplayStateUnavailable
    settings = replace(lab, defense_mode=mode)
    with pytest.raises(TypeError):
        create_app()
    with pytest.raises(MalformedRequest):
        create_app(replace(settings, role='kdc'))
    (settings.run_dir / 'resource.sqlite').unlink()
    with pytest.raises(ReplayStateUnavailable):
        create_app(settings)
    assert not (settings.run_dir / 'resource.sqlite').exists()


def test_capacity_preserves_duplicate_classification_and_counter(lab):
    settings = replace(lab, replay_capacity=1)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    first, second = resource_request(settings), resource_request(settings)
    assert client.post('/access-resource', json=first).status_code == 200
    assert client.post('/access-resource', json=first).status_code == 409
    response = client.post('/access-resource', json=second)
    assert response.status_code == 503
    assert response.get_json() == {'version': 1, 'error': 'replay_state_unavailable'}
    assert counter(settings) == 1


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
def test_locked_store_reports_failure_and_allows_later_retry(lab, mode):
    import sqlite3
    settings = replace(lab, defense_mode=mode, sqlite_busy_timeout_ms=10)
    client = create_app(settings, clock=FrozenClock(NOW)).test_client()
    message = resource_request(settings)
    connection = sqlite3.connect(settings.run_dir / 'resource.sqlite')
    try:
        connection.execute('BEGIN IMMEDIATE')
        response = client.post('/access-resource', json=message)
        assert response.status_code == 503
        assert response.get_json() == {'version': 1, 'error': 'replay_state_unavailable'}
    finally:
        connection.close()
    assert counter(settings) == 0
    assert client.post('/access-resource', json=message).get_json()['counter'] == 1


def test_failed_protected_operation_does_not_consume_request(lab):
    import sqlite3
    client = create_app(lab, clock=FrozenClock(NOW)).test_client()
    message = resource_request(lab)
    # Inject a valid saturated counter at the external storage boundary.
    with sqlite3.connect(lab.run_dir / 'resource.sqlite') as connection:
        connection.execute('INSERT INTO counters VALUES (?,?)', ('files', 9007199254740991))
    response = client.post('/access-resource', json=message)
    assert response.status_code == 503
    assert counter(lab) == 9007199254740991
    with sqlite3.connect(lab.run_dir / 'resource.sqlite') as connection:
        connection.execute('UPDATE counters SET value=0')
    assert client.post('/access-resource', json=message).get_json()['counter'] == 1


def test_resource_cli_exposes_only_released_local_controls():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-m', 'kerberos_lab.resource_server.app', '--help'],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    for option in ('--run-dir', '--config', '--port', '--clock-offset-seconds',
                   '--frozen-time-seconds', '--defense-mode'):
        assert option in result.stdout
    missing = subprocess.run([sys.executable, '-m', 'kerberos_lab.resource_server.app'],
                             capture_output=True, text=True, timeout=10)
    assert missing.returncode == 2
    assert '--run-dir' in missing.stderr


def test_no_cache_does_not_reserve_identities_or_apply_replay_capacity(lab):
    settings = replace(lab, replay_capacity=1)
    no_cache = create_app(replace(settings, defense_mode='authenticator_no_cache'), clock=FrozenClock(NOW)).test_client()
    defended = create_app(settings, clock=FrozenClock(NOW)).test_client()
    message = resource_request(settings)
    assert no_cache.post('/access-resource', json=message).get_json()['counter'] == 1
    assert no_cache.post('/access-resource', json=message).get_json()['counter'] == 2
    assert defended.post('/access-resource', json=message).get_json()['counter'] == 3
    assert defended.post('/access-resource', json=message).status_code == 409
    # Defended capacity is full, but the control still executes a valid new request.
    assert no_cache.post('/access-resource', json=resource_request(settings)).get_json()['counter'] == 4
    assert counter(settings) == 4
