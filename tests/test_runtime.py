"""Routing and activation behavior, independent of database driver internals."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api import runtime
from api.persistence import ProviderMismatch
from api.profiles import load_runtime_config, save_runtime_config, runtime_config_path


@pytest.fixture
def routed_runtime(api_credentials, monkeypatch):
    config = load_runtime_config()
    profiles = dict(config.profiles)
    profiles['prod'] = replace(profiles['prod'], enabled=True,
                              connection_string='postgresql://localhost/synthetic-prod')
    config = save_runtime_config(replace(config, profiles=profiles), expected_revision=config.revision)
    stores = {p.connection_string: {} for p in config.profiles.values()}
    calls = []

    class FakeRepository:
        def __init__(self, dsn):
            self.dsn = dsn

        def validate_identity(self, profile_id):
            assert config.profiles[profile_id].connection_string == self.dsn

        def health(self):
            return True

        def create_intake(self, **values):
            stores[self.dsn][values['request_id']] = {
                'request_id': values['request_id'], 'source_type': values['source_type'],
                'source_id': values['source_id'], 'source_sha256': values['source_sha256'],
                'status': 'REJECTED', 'submitted_by': values['actor'],
                'received_at': datetime.now(timezone.utc), 'completed_at': None}
            return dict(request_id=values['request_id'], status='REJECTED',
                        received_at=datetime.now(timezone.utc), records=0, rejected=0, requires_review=0)

        def get_request(self, request_id):
            return stores[self.dsn].get(request_id)

    @contextmanager
    def open_repository(provider, dsn):
        calls.append((provider, dsn))
        yield FakeRepository(dsn)

    monkeypatch.setattr(runtime, 'open_repository', open_repository)
    return config, stores, calls


def prod_credentials():
    # Fixture convention is explicit; no real credential file is read here.
    return ('synthetic-prod-reviewer', 'synthetic-prod-password-only')


def test_concurrent_credentials_are_isolated_and_headers_cannot_route(routed_runtime, api_credentials):
    config, stores, _ = routed_runtime
    with TestClient(app, client=('127.0.0.1', 5000)) as client:
        def submit(auth):
            return client.post('/api/v1/intake/requests', auth=auth,
                               headers={'X-Environment': 'prod', 'X-Forwarded-User': 'forged'},
                               params={'environment': 'prod'},
                               json={'source_type': 'PASTE', 'source_text': 'Synthetic test', 'submitted_by': 'forged'})
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(submit, [api_credentials, prod_credentials()]))
        assert [r.status_code for r in responses] == [201, 201]
        stage_id, prod_id = [r.json()['request_id'] for r in responses]
        assert client.get('/api/v1/intake/requests/' + prod_id, auth=api_credentials).status_code == 404
        assert client.get('/api/v1/intake/requests/' + stage_id, auth=prod_credentials()).status_code == 404
        stage = client.get('/api/v1/intake/requests/' + stage_id, auth=api_credentials).json()
        assert stage['submitted_by'] == api_credentials[0]
        assert set(stores[config.profiles['stage'].connection_string]) == {stage_id}
        assert set(stores[config.profiles['prod'].connection_string]) == {prod_id}


def test_disabled_profile_health_is_explicit_and_no_data_operation_connects(api_credentials, monkeypatch):
    def forbidden(*args):
        pytest.fail('Disabled profile must not open a database')
    monkeypatch.setattr(runtime, 'open_repository', forbidden)
    with TestClient(app, client=('127.0.0.1', 5000)) as client:
        health = client.get('/api/v1/health', auth=prod_credentials()).json()
        assert health['environment'] == 'prod' and health['ready'] is False
        assert health['database'] == 'DISABLED'
        assert client.get('/api/v1/intake/requests', auth=prod_credentials()).status_code == 503
        assert client.post('/api/v1/intake/requests', auth=prod_credentials(),
                           json={'source_type': 'PASTE', 'source_text': 'Synthetic'}).status_code == 503


def test_saved_revision_does_not_activate_until_restart(routed_runtime, api_credentials):
    config, _, _ = routed_runtime
    with TestClient(app, client=('127.0.0.1', 5000)) as client:
        before = client.get('/api/v1/health', auth=api_credentials).json()
        profiles = dict(config.profiles)
        profiles['stage'] = replace(profiles['stage'], enabled=False)
        saved = save_runtime_config(replace(config, profiles=profiles), expected_revision=config.revision)
        after = client.get('/api/v1/health', auth=api_credentials).json()
        assert after == before and after['ready']
    with TestClient(app, client=('127.0.0.1', 5000)) as restarted:
        result = restarted.get('/api/v1/health', auth=api_credentials).json()
        assert result['configuration_revision'] == saved.revision
        assert result['database'] == 'DISABLED' and not result['ready']


def test_wrong_database_identity_blocks_writes_and_reports_safe_health(api_credentials, monkeypatch):
    class WrongIdentity:
        def validate_identity(self, profile_id):
            raise ProviderMismatch('private connection details must never escape')

    @contextmanager
    def open_repository(*args):
        yield WrongIdentity()
    monkeypatch.setattr(runtime, 'open_repository', open_repository)
    with TestClient(app, client=('127.0.0.1', 5000)) as client:
        health = client.get('/api/v1/health', auth=api_credentials)
        assert health.status_code == 200 and not health.json()['ready']
        response = client.post('/api/v1/intake/requests', auth=api_credentials,
                               json={'source_type': 'PASTE', 'source_text': 'Synthetic'})
        assert response.status_code == 503
        assert 'private' not in health.text + response.text


def test_duplicate_identity_fails_closed(api_credentials):
    config = load_runtime_config()
    stage, prod = config.bindings
    prod.credential_file.write_bytes(stage.credential_file.read_bytes())
    with TestClient(app, client=('127.0.0.1', 5000)) as client:
        assert client.get('/api/v1/health', auth=api_credentials).status_code == 503
