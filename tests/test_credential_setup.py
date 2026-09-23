import json
import os
from pathlib import Path
import subprocess

import pytest

from api.auth import password_digest
from scripts import configure_local_api as setup


def test_default_verifier_uses_project_credential_folder(monkeypatch):
    from api.auth import credential_path
    monkeypatch.delenv('MILSTRIP_API_CREDENTIAL_FILE', raising=False)
    assert credential_path() == Path(__file__).resolve().parents[1] / '.cred' / 'api-credential.json'


def test_short_and_mismatched_password_can_be_retried_privately(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'api-credential.json'
    monkeypatch.setenv('MILSTRIP_API_CREDENTIAL_FILE', str(path))
    monkeypatch.setattr('builtins.input', lambda prompt: 'synthetic-user')
    passwords = iter(['short', 'synthetic-password-long', 'mismatch', 'synthetic-password-long', 'synthetic-password-long'])
    monkeypatch.setattr(setup.getpass, 'getpass', lambda prompt: next(passwords))
    setup.main()
    saved = json.loads(path.read_text())
    assert saved['digest'] == password_digest('synthetic-password-long', saved['salt'])
    assert 'synthetic-password-long' not in path.read_text()
    assert 'synthetic-password-long' not in capsys.readouterr().out


def test_failed_rotation_preserves_existing_verifier(tmp_path, monkeypatch):
    path = tmp_path / 'api-credential.json'
    original = '{"existing": "unchanged"}'
    path.write_text(original)
    monkeypatch.setenv('MILSTRIP_API_CREDENTIAL_FILE', str(path))
    answers = iter(['y', 'synthetic-user'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))
    monkeypatch.setattr(setup.getpass, 'getpass', lambda prompt: 'short')
    with pytest.raises(SystemExit, match='No credential saved'):
        setup.main()
    assert path.read_text() == original


@pytest.mark.skipif(os.name != 'nt', reason='Windows DACL regression')
def test_private_acl_setup_is_repeatable_without_elevation(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'scripts/Protect-LocalApiDirectory.ps1'
    for attempt in range(2):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Directory', str(tmp_path / 'private')], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
