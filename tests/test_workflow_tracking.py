"""Isolated SQLite behavior checks; target-database acceptance remains separate."""
from uuid import uuid4
import hashlib
import json
from contextlib import contextmanager

import pytest
from sqlalchemy import BigInteger, Integer, MetaData, create_engine, select
from sqlalchemy.ext.compiler import compiles

from api.persistence import ProviderMismatch, Repository, RepositoryConflict
from api.persistence.repository import intake_fingerprint
from api.persistence.schema import environment_identity, intake_request, intake_workflow, metadata, milstrip_record, utc_now
from milstrip.service import process_text
from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD
from tests.test_control_broker import control, envelope


@compiles(utc_now, "sqlite")
def sqlite_now(element, compiler, **kwargs):
    return "CURRENT_TIMESTAMP"


@pytest.fixture
def isolated_repository():
    # Only surrogate-key storage differs: SQLite auto-generates INTEGER keys.
    schema = MetaData()
    for table in metadata.sorted_tables:
        copied = table.to_metadata(schema)
        for column in copied.c:
            if column.primary_key and isinstance(column.type, BigInteger):
                column.type = Integer()
    engine = create_engine("sqlite://", execution_options={"schema_translate_map": {"milstrip_app": None}})
    try:
        with engine.begin() as connection:
            schema.create_all(connection)
            connection.execute(environment_identity.insert().values(singleton_id=1, profile_id="stage", schema_version=2))
            yield Repository(connection)
    finally:
        engine.dispose()


def submit(repository, actor="synthetic-person", source_id="synthetic-source", source=SYNTHETIC_RECORD, **options):
    return repository.create_intake(str(uuid4()), "PASTE", source_id, source,
        hashlib.sha256(source.encode()).hexdigest(), actor, process_text(source), **options)


def test_legacy_intakes_are_tracked_without_enforcing_legacy_workflow(isolated_repository):
    repository = isolated_repository
    first = submit(repository, actor="legacy-shared-identity")
    second = submit(repository, actor="legacy-shared-identity")
    rows = repository.connection.execute(select(intake_workflow)).mappings().all()
    assert {row["request_id"] for row in rows} == {first["request_id"], second["request_id"]}
    assert all(row["fingerprint"] == intake_fingerprint(process_text(SYNTHETIC_RECORD), SYNTHETIC_RECORD) for row in rows)
    assert all(row["actor_key"] == hashlib.sha256(b"legacy-shared-identity").hexdigest() for row in rows)
    repository.validate_workflow_tracking()
    with pytest.raises(RepositoryConflict, match="last 2 hours"):
        submit(repository, actor="verified-person", enforce_workflow=True)


def test_missing_tracking_is_rejected_without_creating_ownership(isolated_repository):
    repository = isolated_repository
    receipt = submit(repository, actor="legacy-shared-identity")
    repository.connection.execute(intake_workflow.delete())
    with pytest.raises(ProviderMismatch, match="tracking is incomplete"):
        repository.validate_workflow_tracking()
    assert repository.connection.scalar(select(intake_workflow.c.request_id)) is None
    assert repository.get_request(receipt["request_id"])["submitted_by"] == "legacy-shared-identity"


@pytest.mark.parametrize("completed", [False, True])
def test_exact_source_receipt_survives_review_completion(isolated_repository, completed):
    repository = isolated_repository
    receipt = submit(repository)
    if completed:
        repository.connection.execute(milstrip_record.update().values(review_version=1))
    result = repository.workflow_status("synthetic-person", "synthetic-source")
    assert result["source_resolution"] == "matched"
    assert result["source_receipts"][0]["request_id"] == receipt["request_id"]
    assert result["source_receipts"][0]["review_complete"] is completed
    assert result["can_start"] is completed
    assert result["source_receipts"][0]["records"] == 1


def test_zero_record_receipt_confirms_submission_even_without_active_review(isolated_repository):
    repository = isolated_repository
    receipt = submit(repository, source="No candidates in this synthetic message")
    result = repository.workflow_status("synthetic-person", "synthetic-source")
    assert result["can_start"] and result["active_request_id"] is None
    assert result["source_resolution"] == "matched"
    assert result["source_receipts"][0]["request_id"] == receipt["request_id"]
    assert result["source_receipts"][0]["records"] == 0


def test_absence_and_other_person_receipts_cannot_resolve_unknown_submission(isolated_repository):
    repository = isolated_repository
    before = repository.workflow_status("synthetic-person", "synthetic-source")
    assert before["can_start"] and before["source_resolution"] == "unconfirmed"
    submit(repository, actor="another-person")
    result = repository.workflow_status("synthetic-person", "synthetic-source")
    assert result["source_resolution"] == "unconfirmed" and result["source_receipts"] == []
    submit(repository)
    assert repository.workflow_status("synthetic-person", "synthetic-source")["source_resolution"] == "matched"
    assert repository.workflow_status("synthetic-person", "different-source")["source_resolution"] == "unconfirmed"


def test_multiple_receipts_for_same_source_require_manual_reconciliation(isolated_repository):
    submit(isolated_repository)
    submit(isolated_repository)
    result = isolated_repository.workflow_status("synthetic-person", "synthetic-source")
    assert result["source_resolution"] == "ambiguous" and len(result["source_receipts"]) == 2


def test_broker_source_reconciliation_uses_verified_identity_and_strict_payload(control, monkeypatch):
    from fastapi.testclient import TestClient
    from api.app import app
    from api import runtime
    captured = []

    class ScopedRepository:
        def validate_identity(self, profile_id):
            assert profile_id == "stage"

        def workflow_status(self, actor, source_id=None):
            captured.append((actor, source_id))
            return {"active_request_id": None, "can_start": True, "duplicate_window_hours": 2,
                    "source_resolution": "unconfirmed", "source_receipts": []}

    @contextmanager
    def connect(*args):
        yield ScopedRepository()

    monkeypatch.setattr(runtime, "open_repository", connect)
    with TestClient(app, client=("127.0.0.1", 5000)) as client:
        client.auth = ("synthetic-stage-broker", "synthetic-broker-password")
        body = envelope(control, "GetIntakeWorkflow", {"source_id": "exact-source"})
        response = client.post("/api/v1/broker/invoke", json=body)
        assert response.status_code == 200
        assert json.loads(response.json()["result_json"])["source_resolution"] == "unconfirmed"
        tenant = control[1]["tenant_id"]
        assert captured == [("entra:" + tenant + ":" + body["actor"]["object_id"], "exact-source")]
        for payload in ({"source_id": "x" * 201}, {"source_id": "exact-source", "actor": "someone-else"}):
            rejected = client.post("/api/v1/broker/invoke", json=envelope(control, "GetIntakeWorkflow", payload))
            assert rejected.status_code == 422
        assert len(captured) == 1
