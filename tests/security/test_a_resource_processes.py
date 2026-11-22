"""Real resource HTTP workers sharing private keys and SQLite state."""

from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from kerberos_lab.common.crypto import encode_b64, new_identifier, new_key, seal_ticket, sign_authenticator
from kerberos_lab.common.material import initialize_run, load_material
from kerberos_lab.common.models import ClientSession, Ticket, canonical_bytes
from kerberos_lab.common.replay_cache import ReplayStore
from kerberos_lab.common.settings import Settings
from kerberos_lab.resource_server.app import create_app


NOW = 1_700_000_000


def _credentials(settings):
    material = load_material(settings.run_dir, role='resource')
    ticket = Ticket(version=1, kind='service', ticket_id=new_identifier(), client_id='alice',
                    service_id='files', issued_at=NOW, not_before=NOW, expires_at=NOW + 300,
                    session_key=encode_b64(new_key()))
    session = ClientSession(ticket.client_id, ticket.service_id, ticket.ticket_id,
                            ticket.session_key, ticket.expires_at)
    return session, seal_ticket(ticket, material.service_key)


def _message(session, envelope):
    body = {'operation': 'increment'}
    return canonical_bytes({
        'version': 1, 'service_ticket': envelope, 'body': body,
        'authenticator': sign_authenticator(session, envelope, body, purpose='resource', timestamp=NOW),
    })


def _http(port, raw=None):
    path = '/health' if raw is None else '/access-resource'
    request = Request(f'http://127.0.0.1:{port}{path}', data=raw,
                      headers={'Content-Type': 'application/json'})
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, json.load(error)


def _serve(settings, ready, stop):
    from werkzeug.serving import make_server
    server = make_server('127.0.0.1', 0, create_app(settings))
    server.timeout = 0.1
    ready.put(server.server_port)
    try:
        while not stop.is_set():
            server.handle_request()
    finally:
        server.server_close()


def _start(context, settings):
    ready, stop = context.Queue(), context.Event()
    process = context.Process(target=_serve, args=(settings, ready, stop))
    process.start()
    try:
        port = ready.get(timeout=15)
    except BaseException:
        process.terminate()
        process.join(5)
        ready.close()
        raise
    ready.close()
    return process, stop, port


def _stop(worker):
    process, stop, _port = worker
    stop.set()
    process.join(10)
    if process.is_alive():
        process.terminate()
        process.join(5)
    assert process.exitcode == 0


@pytest.mark.parametrize('mode,accepted,replayed', [
    ('authenticator_cache', 3, 3), ('authenticator_no_cache', 6, 0),
])
def test_same_key_workers_serialize_duplicates_and_keep_state_after_restart(tmp_path, mode, accepted, replayed):
    run = tmp_path / 'run'
    initialize_run(run, password='disposable process test password')
    settings = Settings(run_dir=run, role='resource', port=5001,
                        frozen_time_seconds=NOW, defense_mode=mode)
    session, envelope = _credentials(settings)
    duplicate = _message(session, envelope)
    requests = [duplicate] * 4 + [_message(session, envelope), _message(session, envelope)]
    context = multiprocessing.get_context('spawn')
    workers = []
    try:
        workers = [_start(context, settings)]
        workers.append(_start(context, settings))
        barrier = threading.Barrier(6)

        def send(index):
            barrier.wait(timeout=10)
            return _http(workers[index % 2][2], requests[index])

        with ThreadPoolExecutor(max_workers=6) as executor:
            responses = list(executor.map(send, range(6)))
        assert sum(status == 200 for status, _ in responses) == accepted
        assert sum(status == 409 for status, _ in responses) == replayed
        assert sorted(body['counter'] for status, body in responses if status == 200) == list(range(1, accepted + 1))
        for status, body in responses:
            if status == 409:
                assert body == {'version': 1, 'error': 'replay_detected'}
    finally:
        for worker in workers:
            _stop(worker)
    material = load_material(run, role='resource')
    store = ReplayStore.open_existing(material.resource_store_path, expected_run_id=material.run_id, namespace='resource')
    assert store.counter(service_id='files') == accepted
    restarted = _start(context, settings)
    try:
        status, body = _http(restarted[2], duplicate)
        if mode == 'authenticator_cache':
            assert (status, body) == (409, {'version': 1, 'error': 'replay_detected'})
            assert store.counter(service_id='files') == 3
        else:
            assert status == 200 and body['counter'] == 7
            assert store.counter(service_id='files') == 7
    finally:
        _stop(restarted)


def test_real_cli_applies_config_and_clock_overrides(tmp_path):
    import socket
    run = tmp_path / 'run'
    initialize_run(run, password='disposable CLI test password')
    settings = Settings(run_dir=run, role='resource', port=5001)
    message = _message(*_credentials(settings))
    config = tmp_path / 'lab.toml'
    config.write_text('[protocol]\nallowed_clock_skew_seconds = 0\n[resource]\ndefense_mode = "authenticator_cache"\n')
    # A temporary port reservation chooses a free loopback port for the actual CLI.
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    command = [sys.executable, '-m', 'kerberos_lab.resource_server.app', '--run-dir', str(run),
               '--config', str(config), '--port', str(port), '--frozen-time-seconds', str(NOW - 10),
               '--clock-offset-seconds', '10', '--defense-mode', 'authenticator_no_cache']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        while True:
            if process.poll() is not None:
                out, err = process.communicate()
                pytest.fail(f'CLI exited before health: {out}\n{err}')
            try:
                assert _http(port) == (200, {'status': 'ok', 'role': 'resource_server', 'stage': 'implemented'})
                break
            except (URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    pytest.fail('CLI health readiness timed out')
                time.sleep(0.02)
        # Config's zero skew and CLI's combined clock make this exactly current.
        # CLI defense override must beat the cached mode in TOML.
        assert _http(port, message)[1]['counter'] == 1
        assert _http(port, message)[1]['counter'] == 2
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_cli_refuses_missing_state_and_non_loopback_controls(tmp_path):
    command = [sys.executable, '-m', 'kerberos_lab.resource_server.app', '--run-dir', str(tmp_path / 'missing')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert 'Resource startup failed:' in result.stderr
    assert 'Traceback' not in result.stderr
    assert not (tmp_path / 'missing').exists()
    unknown = subprocess.run(command + ['--host', '0.0.0.0'], capture_output=True, text=True, timeout=10)
    assert unknown.returncode == 2
    assert 'unrecognized arguments' in unknown.stderr


@pytest.mark.parametrize('mode,retry_status,final_count', [
    ('authenticator_cache', 409, 1), ('authenticator_no_cache', 200, 2),
])
def test_unread_response_then_process_termination_preserves_commit(tmp_path, mode, retry_status, final_count):
    import socket
    run = tmp_path / 'run'
    initialize_run(run, password='disposable lost-response test password')
    settings = Settings(run_dir=run, role='resource', port=5001,
                        frozen_time_seconds=NOW, defense_mode=mode)
    captured = _message(*_credentials(settings))
    material = load_material(run, role='resource')
    store = ReplayStore.open_existing(material.resource_store_path, expected_run_id=material.run_id, namespace='resource')
    context = multiprocessing.get_context('spawn')
    worker = _start(context, settings)
    try:
        # Send the real request, then discard the connection without reading a
        # response. Public committed state is our oracle, not an HTTP success.
        with socket.create_connection(('127.0.0.1', worker[2]), timeout=5) as connection:
            headers = (f'POST /access-resource HTTP/1.1\r\nHost: 127.0.0.1\r\n'
                       f'Content-Type: application/json\r\nContent-Length: {len(captured)}\r\n'
                       'Connection: close\r\n\r\n').encode('ascii')
            connection.sendall(headers + captured)
            connection.shutdown(socket.SHUT_WR)
        deadline = time.monotonic() + 5
        while store.counter(service_id='files') != 1:
            assert time.monotonic() < deadline, 'request did not commit before process termination'
            time.sleep(0.02)
        worker[0].terminate()
        worker[0].join(10)
        assert not worker[0].is_alive()
    finally:
        if worker[0].is_alive():
            worker[0].terminate()
            worker[0].join(10)
    restarted = _start(context, settings)
    try:
        status, body = _http(restarted[2], captured)
        assert status == retry_status
        if status == 409:
            assert body == {'version': 1, 'error': 'replay_detected'}
        else:
            assert body['counter'] == 2
        assert store.counter(service_id='files') == final_count
    finally:
        _stop(restarted)
