"""Launcher/editor boundaries use the active authority without live starts."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from api.control import ControlError, ControlStore
from api.profile_manager import SingleWorkerLease
from api.profiles import ConfigurationError, load_runtime_config, runtime_config_path
from scripts import runtime_host
from tests.test_administration import configured_admin as base_configured_admin


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def configured_admin(base_configured_admin):
    from api.auth import ITERATIONS, password_digest
    env = base_configured_admin
    for profile, binding in env.store.read()['security']['brokers'].items():
        salt = 'ef' * 32
        (env.store.path.parent / binding['credential_file']).write_text(json.dumps({
            'version': 1, 'iterations': ITERATIONS, 'username': 'synthetic-' + profile + '-broker',
            'salt': salt, 'digest': password_digest('synthetic-broker-password', salt)}), encoding='utf-8')
    return env


def test_host_preflight_uses_legacy_before_cutover(api_credentials):
    assert asyncio.run(runtime_host.check_startup()) == 'legacy'


def test_host_preflight_uses_active_control_without_legacy_files(configured_admin, monkeypatch):
    monkeypatch.setenv('MILSTRIP_RUNTIME_CONFIG_FILE', str(configured_admin.store.path.parent / 'missing.json'))
    assert asyncio.run(runtime_host.check_startup()) == 'control'
    assert runtime_host.configured_profile('stage') == configured_admin.config.profiles['stage']


def test_failed_active_control_never_falls_back_to_legacy(api_credentials, configured_admin):
    configured_admin.store.path.write_text('PRIVATE_SENTINEL', encoding='utf-8')
    with pytest.raises(ControlError):
        asyncio.run(runtime_host.check_startup())
    with pytest.raises(ConfigurationError, match='remains closed'):
        runtime_host.require_legacy_editor()


def test_preflight_error_never_prints_private_state(configured_admin, capsys):
    configured_admin.store.path.write_text('PRIVATE_SENTINEL', encoding='utf-8')
    assert runtime_host.main(['check-startup']) == 1
    output = capsys.readouterr()
    assert 'PRIVATE_SENTINEL' not in output.out + output.err


def test_active_worker_lock_rejects_second_host_preflight(configured_admin):
    with SingleWorkerLease(configured_admin.store.path):
        with pytest.raises(RuntimeError, match='single API worker'):
            asyncio.run(runtime_host.check_startup())


def test_active_preflight_requires_only_valid_distinct_broker_verifiers(configured_admin):
    env = configured_admin
    bindings = env.store.read()['security']['brokers']
    stage = env.store.path.parent / bindings['stage']['credential_file']
    prod = env.store.path.parent / bindings['prod']['credential_file']
    original = prod.read_bytes()
    prod.write_bytes(stage.read_bytes())
    with pytest.raises(ConfigurationError, match='Broker authentication'):
        asyncio.run(runtime_host.check_startup())
    prod.write_bytes(original)
    stage.unlink()
    with pytest.raises(ConfigurationError, match='Broker authentication'):
        asyncio.run(runtime_host.check_startup())


def test_legacy_save_blocks_cutover_until_write_finishes(api_credentials, monkeypatch):
    path = runtime_config_path()
    config = load_runtime_config()
    store = ControlStore()
    original = runtime_host.save_runtime_config
    attempted = []
    def save_while_cutover_attempts(*args, **kwargs):
        with pytest.raises(ControlError, match='busy'):
            store.mutate(lambda state: state['runtime'].update(active=True))
        attempted.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(runtime_host, 'save_runtime_config', save_while_cutover_attempts)
    result = runtime_host.save_legacy_configuration(config, path, expected_revision=config.revision)
    assert attempted == [True] and result.revision != config.revision


def test_stale_open_editor_cannot_save_after_cutover(api_credentials, configured_admin):
    path = runtime_config_path()
    config = load_runtime_config()
    before = path.read_bytes()
    with pytest.raises(ConfigurationError, match='Host configuration is closed'):
        runtime_host.save_legacy_configuration(config, path, expected_revision=config.revision)
    assert path.read_bytes() == before


def test_direct_python_editor_is_blocked_before_window_creation(configured_admin, monkeypatch):
    from scripts import configure_runtime
    monkeypatch.setattr(configure_runtime.tk, 'Tk', lambda: pytest.fail('Active mode must not open the legacy screen'))
    assert configure_runtime.main() == 1


def powershell(script, *arguments):
    executable = shutil.which('powershell.exe') or shutil.which('pwsh')
    if not executable:
        pytest.skip('PowerShell is required for launcher execution tests')
    return subprocess.run([executable, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                           '-File', str(ROOT / 'scripts' / script), *map(str, arguments)],
                          cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, timeout=20)


def test_powershell_start_validation_accepts_control_without_runtime_json(configured_admin):
    result = powershell('Start-LocalApi.ps1', '-ValidateOnly', '-ControlFile', configured_admin.store.path,
                        '-ConfigFile', configured_admin.store.path.parent / 'missing.json')
    assert result.returncode == 0, result.stderr
    assert 'Active control configuration verified.' in result.stdout
    assert 'stage-secret' not in result.stdout + result.stderr


def test_powershell_legacy_editor_refuses_active_control(configured_admin):
    missing = configured_admin.store.path.parent / 'missing.json'
    result = powershell('Configure-Runtime.ps1', '-ValidateOnly', '-ControlFile', configured_admin.store.path,
                        '-ConfigFile', missing)
    assert result.returncode != 0 and 'Host configuration is closed' in result.stderr
    assert not missing.exists()


def test_powershell_validation_preserves_legacy_mode(api_credentials):
    result = powershell('Start-LocalApi.ps1', '-ValidateOnly')
    assert result.returncode == 0, result.stderr
    assert 'Legacy runtime configuration verified.' in result.stdout


def test_provisioning_preview_uses_active_profile_and_never_connects(configured_admin, monkeypatch, capsys):
    from scripts import initialize_application_database
    monkeypatch.setattr(initialize_application_database, 'provision_schema', lambda *args: pytest.fail('Preview cannot provision'))
    monkeypatch.setattr('sys.argv', ['initialize_application_database.py', '--environment', 'stage'])
    initialize_application_database.main()
    output = capsys.readouterr().out
    assert 'synthetic_stage' in output and 'Preview only.' in output
    assert 'stage-secret' not in output


def test_standalone_http_launcher_isolates_runtime_and_control(tmp_path, monkeypatch):
    from scripts.check_local_api_http import isolated_runtime_environment
    from api.auth import load_verifier, password_digest
    monkeypatch.setenv('MILSTRIP_CONTROL_FILE', str(tmp_path / 'live' / '.cred' / 'control.json'))
    monkeypatch.setenv('MILSTRIP_RUNTIME_CONFIG_FILE', str(tmp_path / 'live' / '.cred' / 'runtime.json'))
    environment, username, password = isolated_runtime_environment(tmp_path, 'postgresql://localhost/synthetic_http')
    private = tmp_path / '.cred'
    assert environment['MILSTRIP_CONTROL_FILE'] == str(private / 'control.json')
    config = load_runtime_config(Path(environment['MILSTRIP_RUNTIME_CONFIG_FILE']))
    assert config.profiles['stage'].connection_string == 'postgresql://localhost/synthetic_http'
    assert not config.profiles['prod'].enabled and not (private / 'control.json').exists()
    stage, prod = [load_verifier(binding.credential_file, binding.profile_id) for binding in config.bindings]
    assert stage.username == username and prod.username != stage.username
    assert password_digest(password, stage.salt) == stage.digest
