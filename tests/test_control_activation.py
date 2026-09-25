"""Security cutover cannot revive an obsolete imported database target."""
from dataclasses import replace
from contextlib import contextmanager
from uuid import uuid4

import pytest

from api.administration import import_runtime_config
from api.control import ControlError
from api.control_bootstrap import enforce_security
from api.profiles import load_runtime_config, runtime_config_path
from scripts.runtime_host import save_legacy_configuration
from tests.test_control_broker import control


@pytest.fixture(autouse=True)
def verified_database(monkeypatch):
    calls = []

    class VerifiedRepository:
        def health(self):
            calls.append("health")
            return True

        def validate_identity(self, profile_id):
            calls.append(("identity", profile_id))

        def validate_workflow_tracking(self):
            calls.append("tracking")

    @contextmanager
    def connect(provider, connection_string):
        calls.append("connect")
        yield VerifiedRepository()

    monkeypatch.setattr("api.control_bootstrap.open_repository", connect)
    return calls


def imported(control):
    store, _ = control
    config = load_runtime_config()
    import_runtime_config(store, config)
    return store, config


def test_cutover_accepts_exact_import_and_preserves_drafts(control, verified_database):
    store, _ = imported(control)
    store.mutate(lambda state: state["runtime"]["drafts"].update({"synthetic-draft": {"retained": True}}))
    before = store.read()
    assert enforce_security(store, before["revision"]) == {"enforced": True, "restart_required": True}
    after = store.read()
    assert after["runtime"]["active"] and after["security"]["enforced"]
    assert after["runtime"]["profiles"] == before["runtime"]["profiles"]
    assert after["runtime"]["drafts"] == before["runtime"]["drafts"]
    assert verified_database == ["connect", "health", ("identity", "stage"), "tracking"]


def test_missing_tracking_blocks_activation_without_changing_control(control, monkeypatch):
    store, _ = imported(control)
    before = store.read()

    class MissingTracking:
        def health(self):
            return True

        def validate_identity(self, profile_id):
            pass

        def validate_workflow_tracking(self):
            raise ValueError("PRIVATE_DRIVER_DETAIL")

    @contextmanager
    def connect(*args):
        yield MissingTracking()

    monkeypatch.setattr("api.control_bootstrap.open_repository", connect)
    with pytest.raises(ControlError, match="complete intake workflow tracking") as caught:
        enforce_security(store, before["revision"])
    assert "PRIVATE_DRIVER_DETAIL" not in str(caught.value)
    assert store.read() == before


@pytest.mark.parametrize("changed_content", [False, True])
def test_cutover_rejects_host_save_after_bootstrap_without_overwriting_import(control, changed_content):
    store, config = imported(control)
    profiles = dict(config.profiles)
    if changed_content:
        profiles["stage"] = replace(profiles["stage"], label="Synthetic revised target")
    updated = replace(config, revision=str(uuid4()), profiles=profiles)
    save_legacy_configuration(updated, runtime_config_path(), expected_revision=config.revision)
    before = store.read()
    with pytest.raises(ControlError, match="Legacy runtime changed after import"):
        enforce_security(store, before["revision"])
    assert store.read() == before


def test_matching_revision_does_not_hide_different_imported_content(control):
    store, _ = imported(control)
    store.mutate(lambda state: state["runtime"]["profiles"]["stage"].update(label="Unreviewed imported label"))
    before = store.read()
    with pytest.raises(ControlError, match="Legacy runtime changed after import"):
        enforce_security(store, before["revision"])
    assert store.read() == before


def test_cutover_requires_current_legacy_file_but_active_retry_does_not(control):
    store, _ = imported(control)
    path = runtime_config_path()
    source = path.read_bytes()
    path.unlink()
    before = store.read()
    with pytest.raises(ControlError, match="must be available"):
        enforce_security(store, before["revision"])
    assert store.read() == before
    path.write_bytes(source)
    enforce_security(store, before["revision"])
    path.unlink()
    assert enforce_security(store, store.read()["revision"])["enforced"] is True


def test_source_comparison_holds_same_lock_as_host_save(control, monkeypatch):
    from api import profiles
    store, config = imported(control)
    observed = []

    def locked_read():
        with pytest.raises(ControlError, match="busy"):
            store._lock()
        observed.append(True)
        return config

    monkeypatch.setattr(profiles, "load_runtime_config", locked_read)
    enforce_security(store, store.read()["revision"])
    assert observed == [True]
