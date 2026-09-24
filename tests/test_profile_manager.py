"""A configuration apply cannot redirect a request already in progress."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from api import runtime
from api.profile_manager import ProfileBusy, ProfileManager, SingleWorkerLease
from api.profiles import ConfigurationError, load_runtime_config
from tests.test_administration import configured_admin


def wait_for_change(manager):
    deadline = time.monotonic() + 3
    while manager.status('stage') != 'CHANGING':
        if time.monotonic() > deadline:
            pytest.fail('Apply did not close the Stage request gate')
        threading.Event().wait(0.002)


def test_drain_waits_for_stage_but_prod_continues(api_credentials):
    config = load_runtime_config()
    manager = ProfileManager(config.profiles, {p: config.revision for p in config.profiles})
    next_profile = replace(config.profiles['stage'], label='New label')
    activated = threading.Event()
    def change():
        with manager.drain('stage', timeout=3):
            manager.publish(next_profile, 'next-revision')
            activated.set()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with manager.lease('stage') as pinned:
            future = executor.submit(change)
            wait_for_change(manager)
            with pytest.raises(ProfileBusy):
                with manager.lease('stage'):
                    pytest.fail('New Stage work must wait for activation')
            with manager.lease('prod') as prod:
                assert prod.profile.profile_id == 'prod'
            assert not activated.is_set() and pinned.profile == config.profiles['stage']
        future.result(timeout=3)
    with manager.lease('stage') as current:
        assert current.profile == next_profile and current.revision == 'next-revision'


def test_repository_lease_covers_commit_before_activation(api_credentials, monkeypatch):
    snapshot = runtime.load_runtime()
    manager = ProfileManager(snapshot.config.profiles, {p: snapshot.config.revision for p in snapshot.config.profiles})
    app = FastAPI()
    app.state.runtime, app.state.profile_manager = snapshot, manager
    request = Request({'type': 'http', 'app': app})
    request.state.context = runtime.RequestContext('synthetic', 'stage', snapshot.config.revision)
    commit_started, release_commit, activated = threading.Event(), threading.Event(), threading.Event()
    order = []

    @contextmanager
    def connection(provider, dsn):
        yield SimpleNamespace(validate_identity=lambda profile: None)
        commit_started.set()
        assert release_commit.wait(3)
        order.append('committed')

    monkeypatch.setattr(runtime, 'open_repository', connection)
    def work():
        with runtime.repository(request):
            order.append('write')
    def apply():
        with manager.drain('stage', timeout=3):
            order.append('activated')
            manager.publish(replace(snapshot.config.profiles['stage'], enabled=False), 'new-revision')
            activated.set()
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(work)
        assert commit_started.wait(3)
        changing = executor.submit(apply)
        wait_for_change(manager)
        assert not activated.is_set()
        release_commit.set()
        pending.result(timeout=3)
        changing.result(timeout=3)
    assert order == ['write', 'committed', 'activated']


def test_nested_business_scope_pins_once_and_rejects_profile_change(api_credentials):
    snapshot = runtime.load_runtime()
    manager = ProfileManager(snapshot.config.profiles, {p: snapshot.config.revision for p in snapshot.config.profiles})
    app = FastAPI()
    app.state.runtime, app.state.profile_manager = snapshot, manager
    request = Request({'type': 'http', 'app': app})
    with runtime.business_scope(request, 'stage') as first:
        with runtime.business_scope(request, 'stage') as second:
            assert first is second and runtime.profile_for(request) is first.profile
        with pytest.raises(HTTPException) as error:
            with runtime.business_scope(request, 'prod'):
                pass
        assert error.value.status_code == 403
    assert request.state.profile_lease is None and request.state.runtime_snapshot is None
    with manager.drain('stage', timeout=0.01):
        pass


def test_failed_request_releases_lease(api_credentials, monkeypatch):
    snapshot = runtime.load_runtime()
    manager = ProfileManager(snapshot.config.profiles, {p: snapshot.config.revision for p in snapshot.config.profiles})
    app = FastAPI()
    app.state.runtime, app.state.profile_manager = snapshot, manager
    request = Request({'type': 'http', 'app': app})
    with pytest.raises(RuntimeError):
        with runtime.business_scope(request, 'stage'):
            raise RuntimeError('Synthetic failed request')
    with manager.drain('stage', timeout=0.01):
        pass


def test_single_worker_lock_rejects_competing_instance_and_recovers_on_close(tmp_path):
    path = tmp_path / 'control.json'
    with SingleWorkerLease(path):
        with pytest.raises(RuntimeError, match='single API worker'):
            with SingleWorkerLease(path):
                pass
    with SingleWorkerLease(path):
        pass


def test_active_profiles_are_loaded_on_restart_and_second_worker_fails(api_credentials, configured_admin,
                                                                   monkeypatch):
    env = configured_admin
    # Fixtures are private stores only; no host runtime or tenant activation.
    monkeypatch.setenv('MILSTRIP_CONTROL_FILE', str(env.store.path))
    env.store.mutate(lambda state: state['runtime']['profiles']['stage'].update(label='Persisted active label'))
    first = FastAPI(lifespan=runtime.lifespan)
    second = FastAPI(lifespan=runtime.lifespan)
    with TestClient(first):
        assert first.state.profile_manager.snapshot('stage').profile.label == 'Persisted active label'
        with pytest.raises(RuntimeError, match='single API worker'):
            with TestClient(second):
                pass
    with TestClient(second):
        assert second.state.profile_manager.snapshot('stage').profile.label == 'Persisted active label'


def test_active_control_is_independent_of_missing_legacy_config(configured_admin, monkeypatch):
    def missing_legacy():
        raise ConfigurationError('Legacy files removed after cutover')
    monkeypatch.setattr(runtime, 'load_runtime', missing_legacy)
    app = FastAPI(lifespan=runtime.lifespan)
    with TestClient(app):
        assert app.state.control_active is True
        assert app.state.runtime.verifiers == ()
        assert app.state.profile_manager.snapshot('stage').profile == configured_admin.config.profiles['stage']
    assert app.state.control_active is False
