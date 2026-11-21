"""Real launcher, KDC, client and resource integration; no resource stubs."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from kerberos_lab.client import AuthenticationClient, RemoteError, check_health
from kerberos_lab.common.clock import FrozenClock
from kerberos_lab.common.material import initialize_run


ROOT = Path(__file__).resolve().parents[2]
NOW = 1_700_000_000
PASSWORD = 'disposable integration password'


def _free_ports():
    with socket.socket() as first, socket.socket() as second:
        first.bind(('127.0.0.1', 0))
        second.bind(('127.0.0.1', 0))
        return first.getsockname()[1], second.getsockname()[1]


def _port_closed(port):
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(('127.0.0.1', port)) != 0


@contextmanager
def running_lab(run, *, extra=(), frozen=True):
    ports = _free_ports()
    urls = tuple(f'http://127.0.0.1:{port}' for port in ports)
    command = [sys.executable, str(ROOT / 'scripts/run_lab.py'), '--run-dir', str(run),
               '--kdc-port', str(ports[0]), '--resource-port', str(ports[1]),
               *(['--kdc-frozen-time-seconds', str(NOW), '--resource-frozen-time-seconds', str(NOW)] if frozen else []), *extra]
    log = run.parent / f'launcher-{ports[0]}.log'
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    with log.open('w') as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **options)
        try:
            deadline = time.monotonic() + 12
            while True:
                if process.poll() is not None:
                    pytest.fail(f'Launcher exited before readiness:\n{log.read_text()}')
                try:
                    health = check_health(*urls, timeout=0.3)
                    assert all(item['stage'] == 'implemented' for item in health)
                    break
                except Exception as error:
                    if time.monotonic() >= deadline:
                        pytest.fail(f'Launcher readiness failed: {error}\n{log.read_text()}')
                    time.sleep(0.03)
            yield AuthenticationClient(*urls, clock=FrozenClock(NOW) if frozen else None), process, ports
        finally:
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT if os.name == 'nt' else signal.SIGINT)
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            deadline = time.monotonic() + 3
            while not all(_port_closed(port) for port in ports) and time.monotonic() < deadline:
                time.sleep(0.03)
            closed = all(_port_closed(port) for port in ports)
            if not closed and os.name != 'nt':
                # Emergency test cleanup, even if the launcher lost its children.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            assert closed, 'launcher left a listening child process'


@pytest.fixture
def run(tmp_path):
    path = tmp_path / 'private run with spaces'
    initialize_run(path, password=PASSWORD)
    return path


def test_real_login_tgs_and_fresh_requests_use_one_service_ticket(run):
    with running_lab(run) as (client, process, _ports):
        grant = client.authenticate('alice', PASSWORD)
        first = client.build_resource_request(grant)
        second = client.build_resource_request(grant)
        assert first.request_nonce != second.request_nonce
        assert client.send_resource_request(first)['counter'] == 1
        assert client.send_resource_request(second)['counter'] == 2
        with pytest.raises(RemoteError) as replay:
            client.send_resource_request(first)
        assert (replay.value.status, replay.value.code) == (409, 'replay_detected')
    assert process.returncode == 0


@pytest.mark.skipif(os.name == 'nt', reason='POSIX SIGTERM lifecycle check')
def test_launcher_termination_stops_both_children(run):
    with running_lab(run) as (_client, process, _ports):
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=12)
    assert process.returncode == 0


def _post(base, path, message):
    from kerberos_lab.common.models import canonical_bytes
    request = Request(base + path, data=canonical_bytes(message), headers={'Content-Type': 'application/json'})
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(request, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, json.load(error)


def _counter(run):
    from kerberos_lab.common.material import load_material
    from kerberos_lab.common.replay_cache import ReplayStore
    material = load_material(run, role='resource')
    return ReplayStore.open_existing(material.resource_store_path, expected_run_id=material.run_id,
                                     namespace='resource').counter(service_id='files')


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
def test_bad_credentials_and_unsupported_service_do_not_execute_resource(run, mode):
    with running_lab(run, extra=['--defense-mode', mode]) as (client, _process, _ports):
        for username, password in [('alice', 'wrong password'), ('unknown', PASSWORD)]:
            with pytest.raises(RemoteError) as invalid:
                client.authenticate(username, password)
            assert (invalid.value.status, invalid.value.code) == (401, 'invalid_credentials')
        with pytest.raises(RemoteError) as service:
            client.authenticate('alice', PASSWORD, service_id='other')
        assert (service.value.status, service.value.code) == (403, 'wrong_service')
        assert _counter(run) == 0
        grant = client.authenticate('alice', PASSWORD)
        assert client.send_resource_request(client.build_resource_request(grant))['counter'] == 1


@pytest.mark.parametrize('mode', ['authenticator_cache', 'authenticator_no_cache'])
def test_kdc_issued_artifacts_reject_tampering_role_and_context_changes(run, mode):
    from base64 import b64decode
    from copy import deepcopy
    from kerberos_lab.common.crypto import encode_b64
    with running_lab(run, extra=['--defense-mode', mode]) as (client, _process, _ports):
        login = client.login('alice', PASSWORD)
        grant = client.request_service_ticket(login)
        captured = client.build_resource_request(grant)
        valid = captured.message
        for fault in ('ticket', 'mac', 'identity', 'service', 'path', 'body', 'tgt'):
            message = deepcopy(valid)
            if fault == 'ticket':
                ciphertext = bytearray(b64decode(message['service_ticket']['ciphertext']))
                ciphertext[-1] ^= 1
                message['service_ticket']['ciphertext'] = encode_b64(bytes(ciphertext))
            elif fault == 'tgt':
                message['service_ticket'] = login.tgt
            elif fault == 'body':
                message['body'] = {'operation': 'delete'}
            else:
                field, value = {
                    'mac': ('mac', encode_b64(bytes(32))), 'identity': ('client_id', 'bob'),
                    'service': ('service_id', 'other'), 'path': ('path', '/service-ticket'),
                }[fault]
                message['authenticator'][field] = value
            status, body = _post(client.resource_url, '/access-resource', message)
            expected = (400, 'malformed_request') if fault == 'body' else (401, 'invalid_authentication')
            assert (status, body) == (expected[0], {'version': 1, 'error': expected[1]}), fault
            assert _counter(run) == 0
        assert client.send_resource_request(captured)['counter'] == 1


def test_expired_tgt_and_service_ticket_rejected_after_logical_time_restart(run):
    with running_lab(run) as (client, _process, _ports):
        login = client.login('alice', PASSWORD)
        grant = client.request_service_ticket(login)
    later = NOW + 331
    with running_lab(run, extra=['--kdc-frozen-time-seconds', str(later),
                                 '--resource-frozen-time-seconds', str(later)]) as (client, _process, _ports):
        client.clock = FrozenClock(later)
        with pytest.raises(RemoteError) as tgt:
            client.request_service_ticket(login)
        assert (tgt.value.status, tgt.value.code) == (401, 'invalid_authentication')
        with pytest.raises(RemoteError) as service:
            client.send_resource_request(client.build_resource_request(grant))
        assert (service.value.status, service.value.code) == (401, 'invalid_authentication')
        assert _counter(run) == 0
        fresh = client.authenticate('alice', PASSWORD)
        assert client.send_resource_request(client.build_resource_request(fresh))['counter'] == 1


@pytest.mark.parametrize('mode,second_status', [('authenticator_cache', 409), ('authenticator_no_cache', 200)])
def test_exact_capture_roundtrip_and_replay_after_full_lab_restart(run, mode, second_status):
    from kerberos_lab.client import load_capture, save_capture
    with running_lab(run, extra=['--defense-mode', mode]) as (client, _process, _ports):
        captured = client.build_resource_request(client.authenticate('alice', PASSWORD))
        name = save_capture(run, captured)
        restored = load_capture(run, name.removeprefix('captures/'))
        assert restored.raw_bytes == captured.raw_bytes
        assert client.send_resource_request(restored)['counter'] == 1
    with running_lab(run, extra=['--defense-mode', mode]) as (client, _process, _ports):
        if second_status == 409:
            with pytest.raises(RemoteError) as replay:
                client.send_resource_request(restored)
            assert (replay.value.status, replay.value.code) == (409, 'replay_detected')
            assert _counter(run) == 1
        else:
            assert client.send_resource_request(restored)['counter'] == 2


@pytest.mark.skipif(os.name == 'nt', reason='POSIX detached-stdin getpass smoke test; Windows console needs a separate check')
def test_documented_setup_health_client_capture_and_replay_commands(tmp_path):
    run = tmp_path / 'cli private run'
    setup = subprocess.run([sys.executable, str(ROOT / 'scripts/init_demo.py'), '--run-dir', str(run), '--password-stdin'],
                           input=PASSWORD + '\n', capture_output=True, text=True, timeout=10)
    assert setup.returncode == 0, setup.stderr
    with running_lab(run, frozen=False) as (client, _process, _ports):
        urls = ['--kdc-url', client.kdc_url, '--resource-url', client.resource_url]
        health = subprocess.run([sys.executable, '-m', 'kerberos_lab.client', 'health', *urls],
                                capture_output=True, text=True, timeout=10)
        assert health.returncode == 0, health.stderr
        assert len(health.stdout.splitlines()) == 2
        journey = subprocess.run([sys.executable, '-m', 'kerberos_lab.client', 'run', '--run-dir', str(run),
                                  '--count', '2', '--capture', *urls], input=PASSWORD + '\n',
                                 start_new_session=True, capture_output=True, text=True, timeout=10)
        assert journey.returncode == 0, journey.stderr
        operations = [json.loads(line) for line in journey.stdout.splitlines()]
        assert [item['counter'] for item in operations] == [1, 2]
        capture = operations[0]['capture'].removeprefix('captures/')
        replay = subprocess.run([sys.executable, '-m', 'kerberos_lab.client', 'replay', '--run-dir', str(run),
                                 '--capture', capture, '--resource-url', client.resource_url],
                                capture_output=True, text=True, timeout=10)
        assert replay.returncode == 1
        assert json.loads(replay.stderr) == {'error': 'replay_detected', 'http_status': 409}
        assert PASSWORD not in setup.stdout + setup.stderr + journey.stdout + journey.stderr
        assert 'session_key' not in journey.stdout and 'ciphertext' not in journey.stdout


def test_launcher_forwards_config_role_offsets_and_defense_override(run):
    config = run.parent / 'strict config.toml'
    config.write_text('[protocol]\nallowed_clock_skew_seconds = 0\n[resource]\ndefense_mode = "authenticator_cache"\n')
    with running_lab(run, extra=['--config', str(config), '--kdc-clock-offset-seconds', '10',
                                 '--resource-clock-offset-seconds', '10',
                                 '--defense-mode', 'authenticator_no_cache']) as (client, _process, _ports):
        client.clock = FrozenClock(NOW + 10)
        captured = client.build_resource_request(client.authenticate('alice', PASSWORD))
        assert client.send_resource_request(captured)['counter'] == 1
        assert client.send_resource_request(captured)['counter'] == 2


def test_launcher_stops_sibling_when_resource_startup_fails(run):
    kdc_port, resource_port = _free_ports()
    (run / 'resource.sqlite').unlink()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_lab.py'), '--run-dir', str(run),
                             '--kdc-port', str(kdc_port), '--resource-port', str(resource_port)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'A server exited; stopping the lab.' in result.stderr
    assert _port_closed(kdc_port) and _port_closed(resource_port)
    assert not (run / 'resource.sqlite').exists()


def test_launcher_rejects_conflicting_ports_before_startup(run):
    kdc_port, _resource_port = _free_ports()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_lab.py'), '--run-dir', str(run),
                             '--kdc-port', str(kdc_port), '--resource-port', str(kdc_port)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert 'server_ports_must_differ' in result.stderr
    assert _port_closed(kdc_port)
