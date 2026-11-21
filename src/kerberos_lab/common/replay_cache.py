"""SQLite replay identities retained for one bounded local experiment run."""

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import stat

from ._validation import MAX_INTEGER, identifier, integer, nonce_id
from .errors import MalformedRequest, ReplayDetected, ReplayStateUnavailable
from .models import Purpose


_SCHEMA = (
    f"CREATE TABLE counters (service_id TEXT PRIMARY KEY NOT NULL, value INTEGER NOT NULL CHECK(typeof(value)='integer' AND value>=0 AND value<={MAX_INTEGER}))",
    "CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
    "run_id TEXT NOT NULL, schema_version INTEGER NOT NULL CHECK(schema_version=1), "
    "namespace TEXT NOT NULL CHECK(namespace IN ('tgs','resource')))",
    "CREATE TABLE consumed (namespace TEXT NOT NULL, service_id TEXT NOT NULL, "
    "ticket_id TEXT NOT NULL, request_nonce TEXT NOT NULL, accepted_at INTEGER NOT NULL, "
    "PRIMARY KEY(namespace,service_id,ticket_id,request_nonce))",
)


def _validate_location(path: Path, run_id: str, namespace: Purpose) -> None:
    if not isinstance(path, Path) or namespace not in ("tgs", "resource"):
        raise MalformedRequest("invalid_store_configuration")
    nonce_id(run_id)


def _connect(path: Path, timeout_ms: int) -> sqlite3.Connection:
    connection = sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True,
                                 isolation_level=None, timeout=timeout_ms / 1000)
    try:
        connection.execute("PRAGMA synchronous=FULL")
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def initialize_store(path: Path, *, run_id: str, namespace: Purpose) -> None:
    _validate_location(path, run_id, namespace)
    connection = None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        connection = _connect(path, 5000)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        for statement in _SCHEMA:
            connection.execute(statement)
        connection.execute("INSERT INTO metadata VALUES (1,?,1,?)", (run_id, namespace))
        connection.commit()
    except (OSError, sqlite3.Error):
        raise ReplayStateUnavailable("store_initialization_failed") from None
    finally:
        if connection is not None:
            connection.close()


@dataclass(frozen=True)
class ReplayStore:
    _path: Path
    _run_id: str
    _namespace: Purpose
    _capacity: int
    _timeout_ms: int
    _identity: tuple[int, int]

    @classmethod
    def open_existing(cls, path: Path, *, expected_run_id: str, namespace: Purpose,
                      capacity: int = 10000, busy_timeout_ms: int = 5000) -> "ReplayStore":
        _validate_location(path, expected_run_id, namespace)
        integer(capacity, minimum=1)
        integer(busy_timeout_ms, minimum=1)
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise OSError("not_regular")
        except OSError:
            raise ReplayStateUnavailable("missing_store") from None
        store = cls(path.absolute(), expected_run_id, namespace, capacity, busy_timeout_ms, (info.st_dev, info.st_ino))
        with store._connection():
            pass
        return store

    @contextmanager
    def _connection(self, *, write: bool = False):
        connection = None
        try:
            info = self._path.lstat()
            if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != self._identity:
                raise ReplayStateUnavailable("store_replaced")
            connection = _connect(self._path, self._timeout_ms)
            info = self._path.lstat()
            if (info.st_dev, info.st_ino) != self._identity:
                raise ReplayStateUnavailable("store_replaced")
            if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
                raise ReplayStateUnavailable("store_journal_mismatch")
            if write:
                connection.execute("BEGIN IMMEDIATE")
            schema = connection.execute("SELECT sql FROM sqlite_master WHERE type IN ('table','view','trigger') ORDER BY name").fetchall()
            if sorted(row[0] for row in schema) != sorted(_SCHEMA):
                raise ReplayStateUnavailable("store_schema_mismatch")
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ReplayStateUnavailable("store_integrity_failure")
            rows = connection.execute("SELECT run_id,schema_version,namespace FROM metadata").fetchall()
            if rows != [(self._run_id, 1, self._namespace)]:
                raise ReplayStateUnavailable("store_metadata_mismatch")
            yield connection
            if write:
                connection.commit()
        except (OSError, sqlite3.Error):
            raise ReplayStateUnavailable("storage_error") from None
        finally:
            if connection is not None:
                connection.close()  # Closing an uncommitted transaction rolls it back.

    def _consume(self, *, service_id: str, ticket_id: str, request_nonce: str,
                accepted_at: int, increment: bool = False) -> int | None:
        identifier(service_id)
        nonce_id(ticket_id)
        nonce_id(request_nonce)
        integer(accepted_at)
        key = (self._namespace, service_id, ticket_id, request_nonce)
        with self._connection(write=True) as connection:
            if connection.execute(
                "SELECT 1 FROM consumed WHERE namespace=? AND service_id=? AND ticket_id=? AND request_nonce=?",
                key,
            ).fetchone():
                raise ReplayDetected("duplicate")
            if connection.execute("SELECT count(*) FROM consumed").fetchone()[0] >= self._capacity:
                raise ReplayStateUnavailable("store_capacity_exceeded")
            connection.execute("INSERT INTO consumed VALUES (?,?,?,?,?)", (*key, accepted_at))
            if increment:
                return self._increment(connection, service_id)

    @staticmethod
    def _increment(connection, service_id):
        connection.execute("INSERT INTO counters VALUES (?,1) ON CONFLICT(service_id) DO UPDATE SET value=value+1", (service_id,))
        return connection.execute("SELECT value FROM counters WHERE service_id=?", (service_id,)).fetchone()[0]

    def consume(self, *, service_id: str, ticket_id: str, request_nonce: str, accepted_at: int) -> None:
        self._consume(service_id=service_id, ticket_id=ticket_id, request_nonce=request_nonce, accepted_at=accepted_at)

    def consume_and_increment(self, *, service_id: str, ticket_id: str, request_nonce: str, accepted_at: int) -> int:
        return self._consume(service_id=service_id, ticket_id=ticket_id, request_nonce=request_nonce, accepted_at=accepted_at, increment=True)

    def increment_without_replay_tracking(self, *, service_id: str) -> int:
        identifier(service_id)
        with self._connection(write=True) as connection:
            return self._increment(connection, service_id)

    def counter(self, *, service_id: str) -> int:
        identifier(service_id)
        with self._connection() as connection:
            row = connection.execute("SELECT value FROM counters WHERE service_id=?", (service_id,)).fetchone()
            return row[0] if row else 0
