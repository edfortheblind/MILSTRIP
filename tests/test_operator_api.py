from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app as api
from api import database as storage
from api.operator import _encode
from api.operator_models import RequestCursor
from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD


@pytest.fixture
def client(database, monkeypatch, api_credentials):
    @contextmanager
    def connect():
        with database.transaction():
            yield database
    monkeypatch.setattr(api, "_connect", connect)
    monkeypatch.setattr(storage, "connect", connect)
    monkeypatch.setenv("MILSTRIP_DATABASE_URL", "postgresql://localhost/trav3pl-psqldb-stage")
    with TestClient(api.app, client=("127.0.0.1", 50000)) as value:
        value.auth = api_credentials
        yield value


def intake(client, text=SYNTHETIC_RECORD):
    response = client.post("/api/v1/intake/requests", json={"source_type": "PASTE", "source_text": text})
    assert response.status_code == 201
    return response.json()["request_id"]


def command(version=0, decision="APPROVED"):
    return {"decision": decision, "reason": "Synthetic operator review", "expected_version": version, "command_id": str(uuid4())}


def review(client, request_id, body=None):
    return client.post(f"/api/v1/records/{request_id}:1/review-decisions", json=body if body is not None else command())


def test_request_pagination_ties_filters_and_new_arrivals(client, database):
    ids = [intake(client) for _ in range(3)]
    database.execute("UPDATE milstrip_app.intake_request SET received_at='2099-01-01T00:00:00Z' WHERE request_id=ANY(%s)", (ids,))
    expected = sorted(ids, reverse=True)
    first = client.get("/api/v1/intake/requests", params={"status": "VALID", "limit": 2}).json()
    assert [item["request_id"] for item in first["items"]] == expected[:2]
    assert all("source_text" not in item for item in first["items"])
    new_id = intake(client)
    database.execute("UPDATE milstrip_app.intake_request SET received_at='2100-01-01T00:00:00Z' WHERE request_id=%s", (new_id,))
    second = client.get("/api/v1/intake/requests", params={"status": "VALID", "limit": 1, "cursor": first["next_cursor"]}).json()
    assert second["items"][0]["request_id"] == expected[2]
    assert client.get("/api/v1/intake/requests", params={"status": "REJECTED", "cursor": first["next_cursor"]}).status_code == 422


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"limit": "abc"}, {"status": "APPROVED"}, {"cursor": "bad!"}, {"cursor": "e30="}, {"cursor": "x" * 2049}])
def test_invalid_list_query_returns_422(client, params):
    assert client.get("/api/v1/intake/requests", params=params).status_code == 422


def test_empty_request_page(client):
    cursor = _encode(RequestCursor(received_at=datetime(1, 1, 1, tzinfo=timezone.utc), request_id="0"))
    response = client.get("/api/v1/intake/requests", params={"cursor": cursor})
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_records_preserve_spaces_issues_order_and_original_contract(client):
    request_id = intake(client, SYNTHETIC_RECORD + "\nA2A")
    detail = client.get(f"/api/v1/intake/requests/{request_id}").json()
    assert set(detail) == {"request_id", "source_type", "source_id", "source_sha256", "status", "submitted_by", "received_at", "completed_at"}
    page = client.get(f"/api/v1/intake/requests/{request_id}/records", params={"limit": 1}).json()
    first = page["items"][0]
    assert first["record_sequence"] == 1
    assert first["canonical_record"] == SYNTHETIC_RECORD
    assert len(first["canonical_record"]) == 80
    assert first["latest_review"] is None and first["review_version"] == 0
    last = client.get(f"/api/v1/intake/requests/{request_id}/records", params={"limit": 1, "cursor": page["next_cursor"]}).json()
    assert last["next_cursor"] is None
    assert last["items"][0]["status"] == "REJECTED"
    assert last["items"][0]["canonical_record"] is None
    assert last["items"][0]["issues"][0]["issue_code"] == "MIL-STR-002"
    other = intake(client)
    assert client.get(f"/api/v1/intake/requests/{other}/records", params={"cursor": page["next_cursor"]}).status_code == 422
    assert client.get(f"/api/v1/intake/requests/{request_id}/audit-events", params={"cursor": page["next_cursor"]}).status_code == 422


@pytest.mark.parametrize("collection", ["records", "audit-events"])
def test_missing_parent_is_404(client, collection):
    assert client.get(f"/api/v1/intake/requests/{uuid4()}/{collection}").status_code == 404


def test_existing_request_without_records_returns_empty_page(client):
    request_id = intake(client, "No MILSTRIP candidates")
    assert client.get(f"/api/v1/intake/requests/{request_id}/records").json() == {"items": [], "next_cursor": None}


def test_review_idempotency_latest_version_and_audit_scope(client, database):
    request_id, other = intake(client), intake(client)
    body = command()
    first = review(client, request_id, body)
    assert first.status_code == 201
    assert first.json()["decided_by"] == "synthetic-reviewer"
    assert first.json()["review_version"] == 1
    again = review(client, request_id, body)
    assert again.status_code == 200 and again.json() == first.json()
    second = review(client, request_id, command(1, "REJECTED"))
    assert second.status_code == 201
    assert review(client, request_id, body).json() == first.json()
    record = client.get(f"/api/v1/intake/requests/{request_id}/records").json()["items"][0]
    assert record["status"] == "VALID"
    assert record["review_version"] == 2
    assert record["latest_review"]["decision"] == "REJECTED"
    # Matching correlation or aggregate ID alone must not leak unrelated events.
    database.execute("INSERT INTO milstrip_app.audit_event(aggregate_type,aggregate_id,event_type,correlation_id) VALUES ('other', %s, 'UNRELATED', %s)", (request_id, request_id))
    events, cursor = [], None
    while True:
        params = {"limit": 1}
        if cursor:
            params["cursor"] = cursor
        page = client.get(f"/api/v1/intake/requests/{request_id}/audit-events", params=params).json()
        events.extend(page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
        assert client.get(f"/api/v1/intake/requests/{other}/audit-events", params={"cursor": cursor}).status_code == 422
    assert len(events) == 3
    assert sum(event["event_type"] == "REVIEW_DECIDED" for event in events) == 2
    assert [event["event_id"] for event in events] == sorted((event["event_id"] for event in events), reverse=True)


def test_stale_version_and_command_reuse_are_conflicts(client, monkeypatch):
    request_id = intake(client)
    body = command()
    assert review(client, request_id, body).status_code == 201
    assert review(client, request_id, command()).status_code == 409
    assert review(client, request_id, {**body, "reason": "Changed reason"}).status_code == 409
    import json
    import os
    from pathlib import Path
    path = Path(os.environ["MILSTRIP_API_CREDENTIAL_FILE"])
    config = json.loads(path.read_text())
    config["username"] = "another-reviewer"
    path.write_text(json.dumps(config))
    client.auth = ("another-reviewer", "synthetic-test-password-only")
    assert review(client, request_id, body).status_code == 409


def test_rejected_record_cannot_be_approved(client):
    request_id = intake(client, "A2A")
    assert review(client, request_id).status_code == 409
    assert review(client, request_id, command(decision="REJECTED")).status_code == 201


def test_review_required_record_remains_review_required_after_approval(client):
    request_id = intake(client, "A5E" + SYNTHETIC_RECORD[3:])
    assert review(client, request_id).status_code == 201
    record = client.get(f"/api/v1/intake/requests/{request_id}/records").json()["items"][0]
    assert record["status"] == "REQUIRES_REVIEW"
    assert record["issues"]


@pytest.mark.parametrize("changes", [{"reason": "  "}, {"reason": "x" * 1001}, {"expected_version": -1}, {"expected_version": True}, {"decision": "VALID"}, {"command_id": "bad"}, {"actor": "spoofed"}])
def test_invalid_review_body_returns_422(client, changes):
    assert review(client, "missing", {**command(), **changes}).status_code == 422


def test_missing_record_is_404(client):
    assert review(client, "missing").status_code == 404


def test_credentials_configuration_is_required(client, monkeypatch):
    monkeypatch.setenv("MILSTRIP_API_CREDENTIAL_FILE", "missing-credential.json")
    assert review(client, "missing").status_code == 503


def test_remote_database_or_peer_cannot_review(client, monkeypatch):
    monkeypatch.setenv("MILSTRIP_DATABASE_URL", "postgresql://remote.example/test")
    assert review(client, "missing").status_code == 403
    monkeypatch.setenv("MILSTRIP_DATABASE_URL", "postgresql://localhost/trav3pl-psqldb-stage")
    with TestClient(api.app, client=("192.0.2.1", 50000)) as remote:
        assert review(remote, "missing").status_code == 403


def test_review_failure_rolls_back_decision_version_and_audit(client, database):
    request_id = intake(client)
    database.execute("ALTER TABLE milstrip_app.audit_event ADD CONSTRAINT test_review_failure CHECK(event_type <> 'REVIEW_DECIDED') NOT VALID")
    assert review(client, request_id).status_code == 503
    assert database.execute("SELECT review_version FROM milstrip_app.milstrip_record WHERE record_id=%s", (request_id + ":1",)).fetchone()[0] == 0
    assert database.execute("SELECT count(*) FROM milstrip_app.review_decision WHERE record_id=%s", (request_id + ":1",)).fetchone()[0] == 0
    assert database.execute("SELECT count(*) FROM milstrip_app.audit_event WHERE aggregate_type='milstrip_record' AND aggregate_id=%s", (request_id + ":1",)).fetchone()[0] == 0


def test_database_failure_is_controlled(client, monkeypatch):
    def fail():
        raise psycopg.OperationalError("Sensitive connection detail")
    monkeypatch.setattr(storage, "connect", fail)
    response = client.get("/api/v1/intake/requests")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_openapi_exposes_typed_operator_contract():
    schema = api.app.openapi()
    assert schema["info"]["version"] == "0.3.0"
    assert "/api/v1/records/{record_id}/review-decisions" in schema["paths"]
    assert schema["components"]["schemas"]["ReviewCommand"]["additionalProperties"] is False


def test_commit_failure_does_not_return_success(client, database, monkeypatch):
    request_id = intake(client)

    @contextmanager
    def failed_commit():
        with database.transaction():
            yield database
            raise psycopg.OperationalError("Simulated commit failure")

    monkeypatch.setattr(storage, "connect", failed_commit)
    response = review(client, request_id)
    assert response.status_code == 503
    assert database.execute("SELECT review_version FROM milstrip_app.milstrip_record WHERE record_id=%s", (request_id + ":1",)).fetchone()[0] == 0
    assert database.execute("SELECT count(*) FROM milstrip_app.review_decision WHERE record_id=%s", (request_id + ":1",)).fetchone()[0] == 0


def test_invalid_connection_configuration_is_controlled(client, monkeypatch):
    monkeypatch.setenv("MILSTRIP_DATABASE_URL", "invalid connection string")
    assert review(client, "missing").status_code == 503


def test_concurrent_commands_have_one_winner(monkeypatch, api_credentials):
    """Two real sessions commit against one synthetic record; remove it afterward."""
    import os
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from psycopg.conninfo import conninfo_to_dict

    url = os.getenv("MILSTRIP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set MILSTRIP_TEST_DATABASE_URL for local concurrency verification")
    config = conninfo_to_dict(url)
    assert config.get("host") in {"localhost", "127.0.0.1", "::1"}
    assert config.get("dbname") == "trav3pl-psqldb-stage"
    monkeypatch.setenv("MILSTRIP_DATABASE_URL", url)
    request_id = str(uuid4())
    record_id = request_id + ":1"
    try:
        with psycopg.connect(url, connect_timeout=5) as db:
            db.execute("INSERT INTO milstrip_app.intake_request (request_id,source_type,source_sha256,source_text,status) VALUES (%s,'PASTE',%s,%s,'VALID')", (request_id, "0" * 64, SYNTHETIC_RECORD))
            db.execute("INSERT INTO milstrip_app.milstrip_record(record_id,request_id,record_sequence,canonical_record,status) VALUES (%s,%s,1,%s,'VALID')", (record_id, request_id, SYNTHETIC_RECORD))
        barrier = Barrier(2)

        def submit(body):
            with TestClient(api.app, client=("127.0.0.1", 50000)) as client:
                client.auth = api_credentials
                barrier.wait(timeout=5)
                return review(client, request_id, body)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, [command(), command(decision="REJECTED")]))
        assert sorted(result.status_code for result in results) == [201, 409]
        with psycopg.connect(url, connect_timeout=5) as db:
            assert db.execute("SELECT review_version FROM milstrip_app.milstrip_record WHERE record_id=%s", (record_id,)).fetchone()[0] == 1
            assert db.execute("SELECT count(*) FROM milstrip_app.review_decision WHERE record_id=%s", (record_id,)).fetchone()[0] == 1
            assert db.execute("SELECT count(*) FROM milstrip_app.audit_event WHERE aggregate_type='milstrip_record' AND aggregate_id=%s", (record_id,)).fetchone()[0] == 1
    finally:
        with psycopg.connect(url, connect_timeout=5) as db:
            db.execute("DELETE FROM milstrip_app.audit_event WHERE aggregate_type='milstrip_record' AND aggregate_id=%s", (record_id,))
            db.execute("DELETE FROM milstrip_app.review_decision WHERE record_id=%s", (record_id,))
            db.execute("DELETE FROM milstrip_app.milstrip_record WHERE record_id=%s", (record_id,))
            db.execute("DELETE FROM milstrip_app.intake_request WHERE request_id=%s", (request_id,))
            assert db.execute("SELECT count(*) FROM milstrip_app.intake_request WHERE request_id=%s", (request_id,)).fetchone()[0] == 0


def test_authenticated_identity_overrides_intake_claim_and_headers(client, monkeypatch):
    monkeypatch.setenv("MILSTRIP_LOCAL_REVIEWER", "spoofed-config")
    response = client.post("/api/v1/intake/requests", json={"source_type": "PASTE", "source_text": SYNTHETIC_RECORD, "submitted_by": "spoofed-body"}, headers={"X-Forwarded-User": "spoofed-header"})
    request_id = response.json()["request_id"]
    assert client.get(f"/api/v1/intake/requests/{request_id}").json()["submitted_by"] == "synthetic-reviewer"
    assert review(client, request_id).json()["decided_by"] == "synthetic-reviewer"
    assert all(event["actor"] == "synthetic-reviewer" for event in client.get(f"/api/v1/intake/requests/{request_id}/audit-events").json()["items"])
