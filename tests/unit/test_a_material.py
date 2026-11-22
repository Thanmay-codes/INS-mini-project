"""Private setup and role-specific material at the released public seam."""
import os
import stat
import pytest


def test_fresh_run_is_private_and_resource_load_is_independent(tmp_path):
    from kerberos_lab.common.material import initialize_run, load_material
    from kerberos_lab.common.crypto import verify_password
    from kerberos_lab.common.errors import MalformedRequest
    run = tmp_path / 'run'
    initialize_run(run, password=' synthetic password ', run_id='a' * 32)
    kdc = load_material(run, role='kdc')
    assert kdc.client_id == 'alice' and kdc.service_id == 'files'
    assert len(kdc.service_key) == len(kdc.tgs_key) == 32
    assert verify_password(' synthetic password ', kdc.password_verifier)
    with pytest.raises(MalformedRequest):
        initialize_run(run, password='replacement')
    for filename in ('tgs.key', 'user.json', 'kdc.sqlite'):
        (run / filename).unlink()
    resource = load_material(run, role='resource')
    assert resource.service_key == kdc.service_key
    assert resource.tgs_key is resource.password_verifier is resource.kdc_store_path is None


def test_cli_initializes_without_exposing_password_or_overwriting(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    from kerberos_lab.common.material import load_material
    from kerberos_lab.common.crypto import verify_password
    command = [sys.executable, str(Path(__file__).resolve().parents[2] / 'scripts/init_demo.py'), '--run-dir', str(tmp_path / 'run'), '--password-stdin']
    result = subprocess.run(command, input=' private password \n', text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert 'private password' not in result.stdout + result.stderr
    assert verify_password(' private password ', load_material(tmp_path / 'run', role='kdc').password_verifier)
    again = subprocess.run(command, input='replacement\n', text=True, capture_output=True)
    assert again.returncode != 0
    assert 'Traceback' not in again.stderr


@pytest.mark.parametrize('filename,content', [
    ('manifest.json', b'{"version":1,"version":1}'),
    ('manifest.json', b'{"version":true,"run_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","client_id":"alice","service_id":"files"}'),
    ('service.key', b'short'), ('tgs.key', b'short'), ('user.json', b'{}')])
def test_invalid_credentials_are_rejected(tmp_path, filename, content):
    from kerberos_lab.common.material import initialize_run, load_material
    from kerberos_lab.common.errors import MalformedRequest
    run = tmp_path / 'run'
    initialize_run(run, password='synthetic')
    (run / filename).write_bytes(content)
    with pytest.raises(MalformedRequest):
        load_material(run, role='kdc')


@pytest.mark.parametrize('role,filename', [('kdc','kdc.sqlite'), ('resource','resource.sqlite')])
def test_loader_does_not_recreate_required_store(tmp_path, role, filename):
    from kerberos_lab.common.material import initialize_run, load_material
    from kerberos_lab.common.errors import ReplayStateUnavailable
    run = tmp_path / 'run'
    initialize_run(run, password='synthetic')
    (run / filename).unlink()
    with pytest.raises(ReplayStateUnavailable):
        load_material(run, role=role)
    assert not (run / filename).exists()


def test_invalid_password_creates_no_directory(tmp_path):
    from kerberos_lab.common.material import initialize_run
    from kerberos_lab.common.errors import MalformedRequest
    with pytest.raises(MalformedRequest):
        initialize_run(tmp_path / 'run', password='')
    assert not (tmp_path / 'run').exists()


@pytest.mark.skipif(os.name != 'posix', reason='POSIX mode bits do not establish Windows ACL protection')
def test_private_run_permissions_on_posix(tmp_path):
    from kerberos_lab.common.material import initialize_run
    run = tmp_path / 'run'
    initialize_run(run, password='disposable permission test password')
    assert stat.S_IMODE(run.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in run.iterdir())
