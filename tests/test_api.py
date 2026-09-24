from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app as api
from api import runtime
from tests.fixtures.real_examples import REAL_EXAMPLES


@pytest.fixture
def connected_api(portable_database):
    return portable_database.driver


@pytest.fixture
def client(runtime_client):
    return runtime_client


def submit(client, source):
    return client.post("/api/v1/intake/requests", json={"source_type": "PASTE", "source_text": source})


@pytest.mark.parametrize("text,status,count", [
    (REAL_EXAMPLES[0]["line"], "VALID", 1),
    (REAL_EXAMPLES[4]["line"], "REQUIRES_REVIEW", 1),
    ("A2?" + REAL_EXAMPLES[0]["line"][3:], "REJECTED", 1),
    ("No records here", "REJECTED", 0),
    (REAL_EXAMPLES[0]["line"] + "\nA2A", "REJECTED", 2),
])
def test_intake_persists_records_issues_status_and_audit(client, connected_api, text, status, count):
    http_response = submit(client, text)
    assert http_response.status_code == 201
    response = http_response.json()
    assert response["status"] == status
    assert response["records"] == count
    request_id = response["request_id"]
    assert client.get(f"/api/v1/intake/requests/{request_id}").json()["status"] == status
    records = connected_api.execute("SELECT canonical_record, status FROM milstrip_app.milstrip_record WHERE request_id=%s", (request_id,)).fetchall()
    assert len(records) == count
    assert all(canonical is None or len(canonical) == 80 for canonical, _ in records)
    assert connected_api.execute("SELECT event_type FROM milstrip_app.audit_event WHERE aggregate_id=%s", (request_id,)).fetchone() == (status,)
    issues = connected_api.execute("SELECT count(*) FROM milstrip_app.validation_issue i JOIN milstrip_app.milstrip_record r USING(record_id) WHERE r.request_id=%s", (request_id,)).fetchone()[0]
    assert issues > 0 if count and status != "VALID" else issues == 0


def test_late_database_failure_rolls_back_request_records_and_issues(client, connected_api, monkeypatch):
    request_id = str(uuid4())
    monkeypatch.setattr(api, "uuid4", lambda: request_id)
    # A constraint on the last write injects failure after records/issues exist.
    connected_api.execute("ALTER TABLE milstrip_app.audit_event ADD CONSTRAINT test_reject_event CHECK (event_type <> 'REQUIRES_REVIEW') NOT VALID")
    response = submit(client, REAL_EXAMPLES[4]["line"])
    assert response.status_code == 503
    for table, column in [("intake_request", "request_id"), ("milstrip_record", "request_id"), ("audit_event", "aggregate_id")]:
        query = psycopg.sql.SQL("SELECT count(*) FROM milstrip_app.{} WHERE {}=%s").format(psycopg.sql.Identifier(table), psycopg.sql.Identifier(column))
        assert connected_api.execute(query, (request_id,)).fetchone()[0] == 0
    assert connected_api.execute("SELECT count(*) FROM milstrip_app.validation_issue WHERE record_id=%s", (request_id + ":1",)).fetchone()[0] == 0


def test_missing_request_returns_404(client):
    assert client.get(f"/api/v1/intake/requests/{uuid4()}").status_code == 404


def test_database_unavailable_returns_controlled_error(client, monkeypatch):
    def fail(provider, connection_string):
        raise psycopg.OperationalError("test database unavailable")
    monkeypatch.setattr(runtime, "open_repository", fail)
    assert client.get("/api/v1/health").json()["status"] == "DEGRADED"
    response = submit(client, "A2A")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_missing_configuration_returns_503(monkeypatch, tmp_path, api_credentials):
    monkeypatch.setenv("MILSTRIP_RUNTIME_CONFIG_FILE", str(tmp_path / "missing-runtime.json"))
    with TestClient(api.app, client=("127.0.0.1", 50000)) as client:
        client.auth = api_credentials
        assert client.get("/api/v1/intake/requests/missing").status_code == 503


def test_repaired_record_preserves_raw_candidate(client, connected_api):
    from tests.test_service import REPAIRABLE_DOT_SAMPLE

    response = submit(client, REPAIRABLE_DOT_SAMPLE).json()
    raw, normalized, canonical = connected_api.execute("SELECT raw_candidate, normalized_record, canonical_record FROM milstrip_app.milstrip_record WHERE request_id=%s", (response["request_id"],)).fetchone()
    assert raw == REPAIRABLE_DOT_SAMPLE
    assert raw != normalized
    assert canonical == normalized.ljust(80)
