"""Exclusive, private initialization for disposable local experiment runs."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path

from ._validation import exact_fields, nonce_id
from .crypto import make_password_verifier, new_identifier, new_key, verify_password
from .errors import MalformedRequest
from .models import Role
from .replay_cache import ReplayStore, initialize_store


@dataclass(frozen=True)
class LabMaterial:
    run_id: str
    client_id: str
    service_id: str
    service_key: bytes = field(repr=False)
    tgs_key: bytes | None = field(repr=False)
    password_verifier: dict[str, object] | None = field(repr=False)
    kdc_store_path: Path | None
    resource_store_path: Path


def _write(path: Path, value: bytes) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(value)


def initialize_run(run_dir: Path, *, password: str, run_id: str | None = None) -> None:
    if not isinstance(run_dir, Path):
        raise MalformedRequest('invalid_run_directory')
    run_id = new_identifier() if run_id is None else run_id
    nonce_id(run_id)
    verifier = make_password_verifier(password)
    try:
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        _write(run_dir / 'tgs.key', new_key())
        _write(run_dir / 'service.key', new_key())
        _write(run_dir / 'user.json', json.dumps(dict(version=1, username='alice', verifier=verifier)).encode())
        initialize_store(run_dir / 'kdc.sqlite', run_id=run_id, namespace='tgs')
        initialize_store(run_dir / 'resource.sqlite', run_id=run_id, namespace='resource')
        _write(run_dir / 'manifest.json', json.dumps(dict(version=1, run_id=run_id, client_id='alice', service_id='files')).encode())
    except OSError:
        raise MalformedRequest('run_initialization_failed') from None


def _json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def load_material(run_dir: Path, *, role: Role) -> LabMaterial:
    if not isinstance(run_dir, Path) or role not in ('kdc', 'resource'):
        raise MalformedRequest('invalid_material_configuration')
    try:
        manifest = _json(run_dir / 'manifest.json')
        exact_fields(manifest, {'version', 'run_id', 'client_id', 'service_id'})
        nonce_id(manifest['run_id'])
        if type(manifest['version']) is not int or manifest['version'] != 1 or manifest['client_id'] != 'alice' or manifest['service_id'] != 'files':
            raise ValueError('manifest')
        service_key = (run_dir / 'service.key').read_bytes()
        if len(service_key) != 32:
            raise ValueError('key_length')
        tgs_key = verifier = kdc_path = None
        if role == 'kdc':
            tgs_key = (run_dir / 'tgs.key').read_bytes()
            if len(tgs_key) != 32:
                raise ValueError('key_length')
            user = _json(run_dir / 'user.json')
            exact_fields(user, {'version', 'username', 'verifier'})
            if type(user['version']) is not int or user['version'] != 1 or user['username'] != 'alice':
                raise ValueError('user')
            verifier = user['verifier']
            verify_password('profile validation only', verifier)
            kdc_path = run_dir / 'kdc.sqlite'
        resource_path = run_dir / 'resource.sqlite'
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        raise MalformedRequest('invalid_run_material') from None
    ReplayStore.open_existing(kdc_path if role == 'kdc' else resource_path,
                              expected_run_id=manifest['run_id'],
                              namespace='tgs' if role == 'kdc' else 'resource')
    return LabMaterial(manifest['run_id'], 'alice', 'files', service_key, tgs_key,
                       verifier, kdc_path, resource_path)
