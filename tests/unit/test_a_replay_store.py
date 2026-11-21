"""Replay behavior observed through the released store API."""

import pytest
from kerberos_lab.common.errors import ReplayDetected
from kerberos_lab.common.replay_cache import ReplayStore, initialize_store


RUN_ID = "a" * 32
REQUEST = dict(service_id="files", ticket_id="1" * 32,
               request_nonce="2" * 32, accepted_at=1000)


def test_consumed_request_is_rejected_after_reopening_the_store(tmp_path):
    from kerberos_lab.common.errors import ReplayDetected
    from kerberos_lab.common.replay_cache import ReplayStore, initialize_store

    path = tmp_path / "resource.sqlite"
    initialize_store(path, run_id=RUN_ID, namespace="resource")
    store = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace="resource")
    store.consume(**REQUEST)
    reopened = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace="resource")
    with pytest.raises(ReplayDetected):
        reopened.consume(**REQUEST)


def test_counter_commit_and_capacity_are_atomic(tmp_path):
    from kerberos_lab.common.errors import ReplayStateUnavailable
    path = tmp_path / 'resource.sqlite'
    initialize_store(path, run_id=RUN_ID, namespace='resource')
    store = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource', capacity=1)
    assert store.counter(service_id='files') == 0
    assert store.consume_and_increment(**REQUEST) == 1
    with pytest.raises(ReplayDetected):
        store.consume_and_increment(**REQUEST)
    with pytest.raises(ReplayStateUnavailable):
        store.consume_and_increment(**{**REQUEST, 'request_nonce': '3' * 32})
    assert store.counter(service_id='files') == 1
    assert store.increment_without_replay_tracking(service_id='files') == 2


@pytest.mark.parametrize('damage', ['delete', 'replace', 'schema', 'corrupt', 'metadata'])
def test_damaged_state_fails_closed(tmp_path, damage):
    import sqlite3
    from kerberos_lab.common.errors import ReplayStateUnavailable
    path = tmp_path / 'resource.sqlite'
    initialize_store(path, run_id=RUN_ID, namespace='resource')
    store = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource')
    if damage in ('delete', 'replace'):
        path.rename(tmp_path / 'old.sqlite')
        if damage == 'replace':
            initialize_store(path, run_id=RUN_ID, namespace='resource')
    elif damage == 'corrupt':
        path.write_bytes(b'broken')
    else:
        with sqlite3.connect(path) as connection:
            connection.execute('DROP TABLE consumed' if damage == 'schema' else 'DELETE FROM metadata')
    with pytest.raises(ReplayStateUnavailable):
        store.counter(service_id='files')
    if damage == 'delete':
        assert not path.exists()


def test_failed_counter_update_rolls_back_nonce_and_lock_timeout(tmp_path):
    import sqlite3
    from kerberos_lab.common._validation import MAX_INTEGER
    from kerberos_lab.common.errors import ReplayStateUnavailable
    path = tmp_path / 'resource.sqlite'
    initialize_store(path, run_id=RUN_ID, namespace='resource')
    store = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource', busy_timeout_ms=10)
    with sqlite3.connect(path) as connection:
        connection.execute('INSERT INTO counters VALUES (?,?)', ('files', MAX_INTEGER))
    with pytest.raises(ReplayStateUnavailable):
        store.consume_and_increment(**REQUEST)
    assert store.counter(service_id='files') == MAX_INTEGER
    store.consume(**REQUEST)  # Failed operation did not reserve this nonce.
    lock = sqlite3.connect(path)
    try:
        lock.execute('BEGIN IMMEDIATE')
        with pytest.raises(ReplayStateUnavailable):
            store.consume(**{**REQUEST, 'request_nonce': '3' * 32})
    finally:
        lock.close()
    store.consume(**{**REQUEST, 'request_nonce': '3' * 32})


def _worker(path, nonce, start, results):
    from kerberos_lab.common.errors import LabError
    store = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource')
    start.wait(10)
    try:
        store.consume_and_increment(**{**REQUEST, 'request_nonce': nonce})
        results.put('accepted')
    except LabError as error:
        results.put(error.code)


def test_process_race_and_restart(tmp_path):
    import multiprocessing
    path = tmp_path / 'resource.sqlite'
    initialize_store(path, run_id=RUN_ID, namespace='resource')
    context = multiprocessing.get_context('spawn')
    start, results = context.Event(), context.Queue()
    processes = [context.Process(target=_worker, args=(path, nonce, start, results))
                 for nonce in ['2' * 32, '2' * 32, '3' * 32, '4' * 32]]
    try:
        for process in processes:
            process.start()
        start.set()
        outcomes = [results.get(timeout=15) for _ in processes]
        for process in processes:
            process.join(15)
            assert process.exitcode == 0
        assert outcomes.count('accepted') == 3
        assert outcomes.count('replay_detected') == 1
        reopened = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource')
        assert reopened.counter(service_id='files') == 3
        with pytest.raises(ReplayDetected):
            reopened.consume(**REQUEST)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()
        results.close()


def test_scope_and_exclusive_initialization(tmp_path):
    from kerberos_lab.common.errors import ReplayStateUnavailable, MalformedRequest
    path = tmp_path / 'resource.sqlite'
    initialize_store(path, run_id=RUN_ID, namespace='resource')
    with pytest.raises(ReplayStateUnavailable):
        initialize_store(path, run_id=RUN_ID, namespace='resource')
    for run_id, namespace in [('b' * 32, 'resource'), (RUN_ID, 'tgs')]:
        with pytest.raises(ReplayStateUnavailable):
            ReplayStore.open_existing(path, expected_run_id=run_id, namespace=namespace)
    store = ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource')
    store.consume(**REQUEST)
    store.consume(**{**REQUEST, 'service_id': 'other'})
    store.consume(**{**REQUEST, 'ticket_id': '3' * 32})
    with pytest.raises(MalformedRequest):
        store.consume(**{**REQUEST, 'accepted_at': True})
    tgs_path = tmp_path / 'tgs.sqlite'
    initialize_store(tgs_path, run_id=RUN_ID, namespace='tgs')
    ReplayStore.open_existing(tgs_path, expected_run_id=RUN_ID, namespace='tgs').consume(**REQUEST)


def test_unexpected_journal_mode_is_not_silently_used(tmp_path):
    import sqlite3
    from kerberos_lab.common.errors import ReplayStateUnavailable
    path = tmp_path / 'resource.sqlite'
    initialize_store(path, run_id=RUN_ID, namespace='resource')
    with sqlite3.connect(path) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
    with pytest.raises(ReplayStateUnavailable):
        ReplayStore.open_existing(path, expected_run_id=RUN_ID, namespace='resource')
