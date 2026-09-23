import pytest
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
    from api import app as api
    from contextlib import contextmanager
    @contextmanager
    def unavailable():
        raise RuntimeError("Private diagnostic")
        yield
    monkeypatch.setattr(api, "_connect", unavailable)
    monkeypatch.setenv("MILSTRIP_LOCAL_REVIEWER", "spoofed")
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials, headers={"X-Forwarded-User": "spoofed"})
    assert response.status_code == 200
    assert "Private diagnostic" not in response.text


@pytest.mark.parametrize("url", ["postgresql://remote.example/trav3pl-psqldb-stage", "postgresql://localhost/other", "host=localhost hostaddr=192.0.2.1 dbname=trav3pl-psqldb-stage", "postgresql://localhost:5433/trav3pl-psqldb-stage"])
def test_database_boundary_on_reads(api_credentials, monkeypatch, url):
    monkeypatch.setenv("MILSTRIP_DATABASE_URL", url)
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        assert client.get("/api/v1/intake/requests", auth=api_credentials).status_code == 403


def test_remote_peer_cannot_spoof_loopback(api_credentials):
    with TestClient(app, client=("192.0.2.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials, headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403


def test_corrupt_configuration_fails_closed(api_credentials, monkeypatch, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"username": "private"}')
    monkeypatch.setenv("MILSTRIP_API_CREDENTIAL_FILE", str(path))
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        response = client.get("/api/v1/health", auth=api_credentials)
    assert response.status_code == 503
    assert "private" not in response.text
