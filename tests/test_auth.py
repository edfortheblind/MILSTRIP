import pytest
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient
from api.app import app

ROUTES = [
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/intake/requests"),
    ("POST", "/api/v1/intake/requests"),
    ("GET", "/api/v1/intake/requests/missing"),
    ("GET", "/api/v1/intake/requests/missing/records"),
    ("GET", "/api/v1/intake/requests/missing/audit-events"),
    ("POST", "/api/v1/records/missing/review-decisions"),
]


@pytest.mark.parametrize("method,path", ROUTES)
@pytest.mark.parametrize("auth", [None, ("synthetic-reviewer", "wrong"), ("wrong", "synthetic-test-password-only")])
def test_all_routes_reject_missing_and_invalid_credentials(api_credentials, method, path, auth):
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        response = client.request(method, path, auth=auth)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")


@pytest.mark.parametrize("authorization", ["Basic !!!", "Bearer fake", "Basic bm9jb2xvbg=="])
def test_malformed_auth_is_401(api_credentials, authorization):
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        assert client.get("/api/v1/health", headers={"Authorization": authorization}).status_code == 401


def test_valid_auth_and_forwarded_identity_ignored(api_credentials, monkeypatch):
    from api import runtime
    from contextlib import contextmanager
    observed = []
    class Available:
        def health(self):
            return True
        def validate_identity(self, profile_id):
            observed.append(profile_id)
    @contextmanager
    def available(provider, connection_string):
        yield Available()
    monkeypatch.setattr(runtime, "open_repository", available)
    monkeypatch.setenv("MILSTRIP_LOCAL_REVIEWER", "spoofed")
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials, headers={"X-Forwarded-User": "spoofed"})
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert observed == ["stage"]
    assert "spoofed" not in response.text


@pytest.mark.parametrize("url", ["postgresql://remote.example/trav3pl-psqldb-stage", "postgresql://localhost/other", "host=localhost hostaddr=192.0.2.1 dbname=trav3pl-psqldb-stage", "postgresql://localhost:5433/trav3pl-psqldb-stage"])
def test_legacy_environment_variable_cannot_redirect_authenticated_profile(api_credentials, monkeypatch, url):
    from contextlib import contextmanager
    from api import runtime
    from api.profiles import load_runtime_config
    expected = load_runtime_config().profiles["stage"].connection_string
    destinations = []
    class Available:
        def health(self):
            return True
        def validate_identity(self, profile_id):
            assert profile_id == "stage"
    @contextmanager
    def available(provider, connection_string):
        destinations.append((provider, connection_string))
        yield Available()
    monkeypatch.setattr(runtime, "open_repository", available)
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        monkeypatch.setenv("MILSTRIP_DATABASE_URL", url)
        response = client.get("/api/v1/health", auth=api_credentials)
    assert response.status_code == 200
    assert destinations == [("postgresql", expected)]


def test_remote_peer_cannot_spoof_loopback(api_credentials):
    with TestClient(app, client=("192.0.2.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials, headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403


def test_corrupt_configuration_fails_closed(api_credentials):
    path = Path(os.environ["MILSTRIP_RUNTIME_CONFIG_FILE"]).parent / "api-credential.json"
    path.write_text('{"username": "private"}')
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials)
    assert response.status_code == 503
    assert "private" not in response.text


def test_credential_changes_require_restart(api_credentials, monkeypatch):
    from contextlib import contextmanager
    from api import runtime
    class Available:
        def health(self):
            return True
        def validate_identity(self, profile_id):
            assert profile_id == "stage"
    @contextmanager
    def available(provider, connection_string):
        yield Available()
    monkeypatch.setattr(runtime, "open_repository", available)
    path = Path(os.environ["MILSTRIP_RUNTIME_CONFIG_FILE"]).parent / "api-credential.json"
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        path.write_text('{"username":"replacement"}')
        assert client.get("/api/v1/health", auth=api_credentials).json()["status"] == "OK"
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        assert client.get("/api/v1/health", auth=api_credentials).status_code == 503


def test_duplicate_usernames_cannot_bind_to_two_environments(api_credentials):
    directory = Path(os.environ["MILSTRIP_RUNTIME_CONFIG_FILE"]).parent
    stage = json.loads((directory / "api-credential.json").read_text())
    (directory / "api-prod-credential.json").write_text(json.dumps(stage))
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials)
    assert response.status_code == 503
    assert stage["digest"] not in response.text


def test_disabled_prod_does_not_open_database(api_credentials, monkeypatch):
    from api import runtime
    def forbidden(*_args):
        pytest.fail("Disabled Prod must not open a database")
    monkeypatch.setattr(runtime, "open_repository", forbidden)
    auth = ("synthetic-prod-reviewer", "synthetic-prod-password-only")
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        health = client.get("/api/v1/health", auth=auth)
        submit = client.post("/api/v1/intake/requests", auth=auth,
                             json={"source_type": "PASTE", "source_text": "A2A"})
    assert health.status_code == 200
    assert health.json()["database"] == "DISABLED"
    assert health.json()["ready"] is False
    assert submit.status_code == 503
