"""Configuration isolation, secret redaction and restart snapshot behavior."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from uuid import uuid4

import pytest

from api.profiles import (
    ConfigurationError, CredentialBinding, RuntimeConfig, RuntimeProfile,
    empty_runtime_config, load_runtime_config, normalized_target,
    save_runtime_config, target_summary, validate_runtime_config,
)


def configured(path, stage="host=localhost dbname=stage user=test password=PRIVATE_SENTINEL", prod=""):
    config = empty_runtime_config(path)
    profiles = dict(config.profiles)
    profiles["stage"] = replace(profiles["stage"], connection_string=stage, enabled=True)
    profiles["prod"] = replace(profiles["prod"], connection_string=prod)
    return replace(config, profiles=profiles)


@pytest.fixture
def private_path(tmp_path):
    directory = tmp_path / ".cred"
    directory.mkdir()
    return directory / "runtime.json"


def test_saved_snapshot_is_immutable_and_does_not_hot_swap(private_path):
    initial = save_runtime_config(configured(private_path), private_path)
    loaded = load_runtime_config(private_path)
    assert loaded == initial
    with pytest.raises(TypeError):
        loaded.profiles["prod"] = loaded.profiles["stage"]
    with pytest.raises(FrozenInstanceError):
        loaded.profiles["stage"].enabled = False
    changed = configured(private_path, stage="host=localhost dbname=newstage")
    saved = save_runtime_config(changed, private_path, expected_revision=loaded.revision)
    assert saved.revision != loaded.revision
    assert "newstage" not in loaded.profiles["stage"].connection_string
    assert "newstage" in load_runtime_config(private_path).profiles["stage"].connection_string
    assert loaded.bindings[0].credential_file == private_path.parent / "api-credential.json"


def test_repr_and_summary_never_include_credentials(private_path):
    config = configured(private_path)
    assert "PRIVATE_SENTINEL" not in repr(config)
    assert "PRIVATE_SENTINEL" not in repr(config.profiles["stage"])
    summary = target_summary(config.profiles["stage"])
    assert summary == "postgresql | localhost:5432 | stage"
    assert "user" not in summary and "password" not in summary


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1", "LOCALHOST."])
def test_postgres_aliases_cannot_point_both_profiles_at_same_database(private_path, host):
    config = configured(private_path, prod=f"host={host} port=5432 dbname=stage")
    with pytest.raises(ConfigurationError, match="different databases"):
        validate_runtime_config(config)


def test_postgres_url_and_keywords_identify_same_target(private_path):
    config = configured(private_path, prod="postgresql://other:secret@127.0.0.1:5432/stage")
    with pytest.raises(ConfigurationError, match="different databases"):
        validate_runtime_config(config)


@pytest.mark.parametrize("connection", [
    "host=db.example.test dbname=stage", "host=db.example.test dbname=stage sslmode=require",
    "host=localhost,other dbname=stage", "host=localhost dbname=stage service=other",
    "host=localhost hostaddr=10.0.0.1 dbname=stage", "host=localhost dbname=stage options='-c search_path=other'",
    "host=localhost dbname=stage port=99999", "dbname=stage", "host=localhost",
])
def test_invalid_or_unverified_postgres_destinations_are_rejected(private_path, connection):
    with pytest.raises(ConfigurationError):
        validate_runtime_config(configured(private_path, stage=connection))


def test_remote_postgres_requires_hostname_verification(private_path):
    config = configured(private_path, stage="host=db.example.test dbname=stage sslmode=verify-full")
    assert validate_runtime_config(config) is config


SQL = "Driver={ODBC Driver 18 for SQL Server};Server=tcp:db.database.windows.net,1433;Database=Stage;Encrypt=yes;TrustServerCertificate=no;UID=demo;PWD={a;b}}c};"


def test_sql_server_braces_and_attribute_aliases_normalize(private_path):
    config = empty_runtime_config(private_path)
    stage = RuntimeProfile("stage", "sqlserver", "SQL stage", SQL, True)
    assert target_summary(stage) == "sqlserver | db.database.windows.net:1433 | stage"
    prod = RuntimeProfile("prod", "sqlserver", "SQL prod", SQL.replace("Database=Stage", "Initial Catalog=STAGE"), False)
    with pytest.raises(ConfigurationError, match="different databases"):
        validate_runtime_config(replace(config, profiles={"stage": stage, "prod": prod}))
    assert "a;b" not in repr(stage)


@pytest.mark.parametrize("connection", [
    SQL.replace("Encrypt=yes", "Encrypt=no"),
    SQL.replace("TrustServerCertificate=no", "TrustServerCertificate=yes"),
    SQL.replace("ODBC Driver 18 for SQL Server", "C:/other.dll"),
    SQL + "AttachDBFilename=C:/other.mdf;",
    SQL + "Server=other;", SQL + "Data Source=other;",
    SQL.replace("PWD={a;b}}c};", "PWD={unfinished;"),
    SQL.replace("PWD={a;b}}c};", "PWD={done}extra;"),
])
def test_unsafe_or_ambiguous_sql_server_strings_fail_without_echo(connection):
    profile = RuntimeProfile("stage", "sqlserver", "stage", connection, True)
    with pytest.raises(ConfigurationError) as caught:
        normalized_target(profile)
    assert connection not in str(caught.value)
    assert "a;b" not in str(caught.value)


def test_disabled_unconfigured_prod_is_valid_but_enabled_is_not(private_path):
    config = configured(private_path)
    assert validate_runtime_config(config) is config
    profiles = dict(config.profiles)
    profiles["prod"] = replace(profiles["prod"], enabled=True)
    with pytest.raises(ConfigurationError, match="requires a connection string"):
        validate_runtime_config(replace(config, profiles=profiles))


def test_stage_and_prod_cannot_share_credentials(private_path):
    config = configured(private_path)
    bindings = (CredentialBinding("stage", Path("same.json")), CredentialBinding("prod", Path("SAME.json")))
    with pytest.raises(ConfigurationError, match="different credential"):
        validate_runtime_config(replace(config, bindings=bindings))


def test_stale_editor_cannot_overwrite_newer_revision(private_path):
    saved = save_runtime_config(configured(private_path), private_path)
    newer = save_runtime_config(saved, private_path, expected_revision=saved.revision)
    before = private_path.read_bytes()
    with pytest.raises(ConfigurationError, match="changed since"):
        save_runtime_config(saved, private_path, expected_revision=saved.revision)
    assert private_path.read_bytes() == before
    assert load_runtime_config(private_path).revision == newer.revision
    assert not private_path.with_suffix(".lock").exists()


def test_failed_replace_preserves_original(private_path, monkeypatch):
    saved = save_runtime_config(configured(private_path), private_path)
    before = private_path.read_bytes()
    def fail_replace(*_args):
        raise OSError("PRIVATE_SENTINEL")
    monkeypatch.setattr("api.profiles.os.replace", fail_replace)
    with pytest.raises(ConfigurationError) as caught:
        save_runtime_config(saved, private_path, expected_revision=saved.revision)
    assert "PRIVATE_SENTINEL" not in str(caught.value)
    assert private_path.read_bytes() == before
    assert list(private_path.parent.iterdir()) == [private_path]


def test_existing_writer_lock_prevents_overwrite(private_path):
    config = configured(private_path)
    private_path.with_suffix(".lock").touch()
    with pytest.raises(ConfigurationError, match="saved elsewhere"):
        save_runtime_config(config, private_path)
    assert not private_path.exists()


@pytest.mark.parametrize("mutate", [
    lambda raw: raw.update(revision="PRIVATE_SENTINEL"),
    lambda raw: raw["profiles"]["stage"].update(provider=["PRIVATE_SENTINEL"]),
    lambda raw: raw["bindings"][0].update(credential_file="../PRIVATE_SENTINEL.json"),
    lambda raw: raw["bindings"][0].update(profile_id=["PRIVATE_SENTINEL"]),
    lambda raw: raw["profiles"]["stage"].update(unknown="PRIVATE_SENTINEL"),
])
def test_malformed_config_rejected_without_sensitive_values(private_path, mutate):
    save_runtime_config(configured(private_path), private_path)
    raw = json.loads(private_path.read_text())
    mutate(raw)
    private_path.write_text(json.dumps(raw))
    with pytest.raises(ConfigurationError) as caught:
        load_runtime_config(private_path)
    assert "PRIVATE_SENTINEL" not in str(caught.value)


def test_config_cannot_be_saved_outside_private_directory(tmp_path, private_path):
    with pytest.raises(ConfigurationError, match="inside .cred"):
        save_runtime_config(configured(private_path), tmp_path / "runtime.json")


def test_bindings_cannot_reference_another_private_directory(private_path, tmp_path):
    config = configured(private_path)
    other = tmp_path / "other" / ".cred" / "api-credential.json"
    bindings = (CredentialBinding("stage", other), config.bindings[1])
    with pytest.raises(ConfigurationError, match="configuration's .cred"):
        save_runtime_config(replace(config, bindings=bindings), private_path)


def test_version_and_revision_are_explicit(private_path):
    config = configured(private_path)
    for invalid in (replace(config, version=True), replace(config, version=2), replace(config, revision="latest")):
        with pytest.raises(ConfigurationError):
            validate_runtime_config(invalid)
    assert validate_runtime_config(replace(config, revision=str(uuid4())))


def test_configuration_screen_requires_exact_target_test_before_activation(private_path):
    from scripts.configure_runtime import ConfigurationScreen
    class Variable:
        def __init__(self, value):
            self.value = value
        def get(self):
            return self.value
        def set(self, value):
            self.value = value
    screen = ConfigurationScreen.__new__(ConfigurationScreen)
    screen.path, screen.config = private_path, empty_runtime_config(private_path)
    screen.saved_revision, screen.selected, screen.verified = None, 'stage', set()
    screen.provider, screen.label = Variable('postgresql'), Variable('Stage')
    screen.connection, screen.enabled = Variable('host=localhost dbname=stage'), Variable(True)
    screen.status = Variable('')
    screen.show_profile = lambda: None
    screen.save()
    assert not private_path.exists()
    assert 'Test the new destination' in screen.status.get()
    screen.verified.add(screen.identity(screen.candidate().profiles['stage']))
    screen.save()
    assert load_runtime_config(private_path).profiles['stage'].enabled
    before = private_path.read_bytes()
    screen.connection.set('host=localhost dbname=different_stage')
    screen.save()
    assert private_path.read_bytes() == before
    assert 'Test the new destination' in screen.status.get()


def test_configuration_connection_test_only_reads_health_and_identity(monkeypatch, private_path):
    from contextlib import contextmanager
    from scripts.configure_runtime import test_profile
    events = []
    class ReadOnlyRepository:
        def health(self):
            events.append('health')
            return True
        def validate_identity(self, profile_id):
            events.append(('identity', profile_id))
    @contextmanager
    def fake_open(provider, connection_string):
        assert provider == 'postgresql'
        yield ReadOnlyRepository()
    monkeypatch.setattr('api.persistence.open_repository', fake_open)
    assert test_profile(configured(private_path).profiles['stage']) is True
    assert events == ['health', ('identity', 'stage')]
