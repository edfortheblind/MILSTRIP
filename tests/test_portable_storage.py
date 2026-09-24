"""Dialect contracts plus opt-in PostgreSQL operations rolled back in full.

SQL Server compilation is not a live SQL Server acceptance test. These tests
never connect to Azure SQL or any production database.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from uuid import uuid4

import pytest
import psycopg
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import select, text
from sqlalchemy.dialects import mssql, postgresql
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.schema import CreateIndex, CreateTable

from api.operator_models import ReviewCommand
from api.persistence import ProviderMismatch, Repository, RepositoryConflict, RepositoryNotFound, make_engine
from api.persistence import repository as implementation
from api.persistence.repository import locked_record_statement
from api.persistence.schema import (
    SCHEMA_VERSION, audit_event, environment_identity, intake_request, metadata,
    milstrip_record, review_decision,
)
from milstrip.service import process_text
from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD


def test_sqlserver_native_schema_preserves_padding_unicode_and_time():
    ddl = "\n".join(str(CreateTable(table).compile(dialect=mssql.dialect())) for table in metadata.sorted_tables)
    assert "canonical_record NVARCHAR(80)" in ddl
    assert "DATALENGTH(canonical_record) = 160" in ddl
    assert "DATETIMEOFFSET" in ddl and "SYSUTCDATETIME()" in ddl
    assert "UNIQUEIDENTIFIER" in ddl and "NVARCHAR(max)" in ddl
    assert "Latin1_General_100_BIN2" in ddl
    assert "NTEXT" not in ddl and "dbo." not in ddl
    identity = str(CreateTable(environment_identity).compile(dialect=mssql.dialect()))
    assert "IDENTITY" not in identity
    assert all(table.schema == "milstrip_app" for table in metadata.tables.values())


def test_nullable_review_uniqueness_and_locking_use_native_dialects():
    indexes = {index.name: index for index in review_decision.indexes}
    for name, column in [("review_decision_command_uq", "command_id"), ("review_decision_version_uq", "review_version")]:
        sql = str(CreateIndex(indexes[name]).compile(dialect=mssql.dialect()))
        assert f"WHERE {column} IS NOT NULL" in sql
        assert "UNIQUE INDEX" in sql
    pg_lock = str(locked_record_statement("synthetic").compile(dialect=postgresql.dialect()))
    ms_lock = str(locked_record_statement("synthetic").compile(dialect=mssql.dialect()))
    assert "FOR UPDATE" in pg_lock
    assert "WITH (UPDLOCK, HOLDLOCK, ROWLOCK)" in ms_lock
    assert "FOR UPDATE" not in ms_lock


def test_checked_in_sqlserver_ddl_matches_metadata():
    ddl = Path("db/sqlserver/001_application_schema.sql").read_text(encoding="utf-8")
    for table in metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=mssql.dialect())).strip() in ddl
        for index in table.indexes:
            assert str(CreateIndex(index).compile(dialect=mssql.dialect())).strip() in ddl


def test_unknown_provider_fails_before_network_access():
    with pytest.raises(ValueError, match="Unsupported database provider"):
        make_engine("unexpected", "synthetic")


@pytest.mark.parametrize("variable", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS", "PGPASSFILE"])
def test_postgres_environment_overrides_cannot_redirect_a_saved_profile(monkeypatch, variable):
    monkeypatch.setenv(variable, "PRIVATE_SYNTHETIC_OVERRIDE")
    with pytest.raises(psycopg.OperationalError) as caught:
        make_engine("postgresql", "host=localhost dbname=synthetic_stage")
    assert "PRIVATE_SYNTHETIC_OVERRIDE" not in str(caught.value)


@pytest.fixture
def repository():
    value = os.getenv("MILSTRIP_TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set MILSTRIP_TEST_DATABASE_URL for rollback-only local PostgreSQL integration")
    config = conninfo_to_dict(value)
    if config.get("host") not in {"localhost", "127.0.0.1", "::1"} or config.get("dbname") != "trav3pl-psqldb-stage":
        pytest.fail("Portable storage tests require the approved localhost stage database")
    engine = make_engine("postgresql", value)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET LOCAL lock_timeout = '5s'"))
                connection.execute(text("SET LOCAL statement_timeout = '15s'"))
                metadata.create_all(connection)
                # Restart is transactional, unlike nextval. Rollback restores
                # the pre-test sequence positions as well as all synthetic rows.
                for table_name, column in [("validation_issue", "issue_id"), ("review_decision", "decision_id"), ("audit_event", "event_id")]:
                    next_id = connection.scalar(text(f"SELECT coalesce(max({column}), 0) + 1 FROM milstrip_app.{table_name}"))
                    connection.execute(text(f"ALTER TABLE milstrip_app.{table_name} ALTER COLUMN {column} RESTART WITH {int(next_id)}"))
                if connection.scalar(select(environment_identity.c.singleton_id)) is None:
                    connection.execute(environment_identity.insert().values(singleton_id=1, profile_id="stage", schema_version=SCHEMA_VERSION))
                yield Repository(connection)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def intake(repository, source=SYNTHETIC_RECORD, request_id=None):
    request_id = request_id or str(uuid4())
    return repository.create_intake(request_id, "PASTE", "synthetic-storage-test", source,
                                    hashlib.sha256(source.encode()).hexdigest(), "synthetic-reviewer", process_text(source))


def command(version=0, decision="APPROVED", reason="Synthetic review: caf\u00e9 \u03b2"):
    return ReviewCommand(decision=decision, reason=reason, expected_version=version, command_id=uuid4())


def test_persisted_intake_receipt_records_and_issues(repository):
    receipt = intake(repository, SYNTHETIC_RECORD + "\nA2A")
    assert receipt["status"] == "REJECTED" and receipt["records"] == 2 and receipt["rejected"] == 1
    assert receipt["received_at"].tzinfo is not None
    detail = repository.get_request(receipt["request_id"])
    assert "source_text" not in detail and detail["completed_at"] is not None
    first = repository.list_records(receipt["request_id"], limit=1)
    assert first.has_more and first.items[0]["canonical_record"] == SYNTHETIC_RECORD
    assert len(first.items[0]["canonical_record"]) == 80
    last = repository.list_records(receipt["request_id"], limit=1, boundary={"sequence": 1})
    assert not last.has_more and last.items[0]["status"] == "REJECTED"
    assert last.items[0]["issues"][0]["issue_code"] == "MIL-STR-002"


def test_review_replay_unicode_version_and_scoped_audit(repository):
    request_id = intake(repository)["request_id"]
    first_command = command()
    first = repository.review_record(request_id + ":1", first_command, "synthetic-reviewer")
    replay = repository.review_record(request_id + ":1", first_command, "synthetic-reviewer")
    assert not first.replayed and replay.replayed and replay.decision == first.decision
    assert first.decision["reason"] == first_command.reason
    assert first.decision["decided_at"].tzinfo is not None
    repository.review_record(request_id + ":1", command(1, "REJECTED"), "synthetic-reviewer")
    record = repository.list_records(request_id).items[0]
    assert record["status"] == "VALID" and record["review_version"] == 2
    assert record["latest_review"]["decision"] == "REJECTED"
    repository.connection.execute(audit_event.insert().values(
        aggregate_type="other", aggregate_id=request_id, event_type="UNRELATED", correlation_id=request_id, event_data={}))
    events = repository.list_events(request_id)
    assert len(events.items) == 3
    assert events.items[0]["event_data"]["review_version"] == 2
    assert events.items[1]["event_data"]["reason"] == first_command.reason
    assert repository.review_record(request_id + ":1", first_command, "synthetic-reviewer").replayed


def test_conflicts_remain_case_sensitive_and_rejected_cannot_be_approved(repository):
    request_id = intake(repository)["request_id"]
    original = command()
    repository.review_record(request_id + ":1", original, "synthetic-reviewer")
    for revised, actor in [(command(), "synthetic-reviewer"),
                           (original.model_copy(update={"reason": original.reason.upper()}), "synthetic-reviewer"),
                           (original, "SYNTHETIC-REVIEWER")]:
        with pytest.raises(RepositoryConflict):
            repository.review_record(request_id + ":1", revised, actor)
    rejected = intake(repository, "A2A")["request_id"]
    with pytest.raises(RepositoryConflict, match="does not permit approval"):
        repository.review_record(rejected + ":1", command(), "synthetic-reviewer")
    assert repository.review_record(rejected + ":1", command(decision="REJECTED"), "synthetic-reviewer").decision["review_version"] == 1
    with pytest.raises(RepositoryNotFound):
        repository.review_record("missing", command(), "synthetic-reviewer")


def test_keyset_pagination_ties_and_parent_scope(repository):
    ids = [intake(repository)["request_id"] for _ in range(3)]
    stamp = datetime(2099, 1, 1, tzinfo=timezone.utc)
    repository.connection.execute(intake_request.update().where(intake_request.c.request_id.in_(ids)).values(received_at=stamp))
    first = repository.list_requests(2, "VALID")
    assert first.has_more and [row["request_id"] for row in first.items] == sorted(ids, reverse=True)[:2]
    second = repository.list_requests(1, "VALID", first.items[-1])
    assert second.items[0]["request_id"] == sorted(ids, reverse=True)[2]
    request_id = ids[0]
    repository.review_record(request_id + ":1", command(), "synthetic-reviewer")
    first_events = repository.list_events(request_id, 1)
    last_events = repository.list_events(request_id, 1, first_events.items[-1])
    assert first_events.has_more and not last_events.has_more
    assert first_events.items[0]["event_id"] > last_events.items[0]["event_id"]
    for method in [repository.list_records, repository.list_events]:
        with pytest.raises(RepositoryNotFound):
            method(str(uuid4()))


def test_zero_records_and_atomic_failure(repository):
    empty = intake(repository, "No record candidates")
    assert empty["records"] == 0 and empty["status"] == "REJECTED"
    assert repository.list_records(empty["request_id"]).items == []
    request_id = str(uuid4())
    bad_record = replace(process_text(SYNTHETIC_RECORD)[0], canonical="A" * 79)
    with pytest.raises(IntegrityError):
        with repository.connection.begin_nested():
            repository.create_intake(request_id, "PASTE", None, "synthetic", "0" * 64, "synthetic-reviewer", [bad_record])
    assert repository.get_request(request_id) is None
    assert repository.connection.scalar(select(milstrip_record.c.record_id).where(milstrip_record.c.request_id == request_id)) is None


def test_identity_cannot_cross_stage_prod_and_provision_preserves_rows(repository, monkeypatch):
    repository.validate_identity("stage")
    with pytest.raises(ProviderMismatch):
        repository.validate_identity("prod")
    request_id = intake(repository)["request_id"]

    @contextmanager
    def reuse_transaction(provider, connection_string):
        yield repository
    monkeypatch.setattr(implementation, "open_repository", reuse_transaction)
    assert implementation.provision_schema("postgresql", "synthetic", "stage") == {"profile_id": "stage", "schema_version": SCHEMA_VERSION}
    assert repository.get_request(request_id) is not None
    with pytest.raises(ProviderMismatch):
        implementation.provision_schema("postgresql", "synthetic", "prod")
    repository.validate_identity("stage")
    with repository.connection.begin_nested() as savepoint:
        repository.connection.execute(environment_identity.update().values(schema_version=999))
        with pytest.raises(ProviderMismatch):
            repository.validate_identity("stage")
        savepoint.rollback()


def test_health_detects_schema_drift_without_reading_application_rows(repository):
    assert repository.health()
    with pytest.raises(ProgrammingError):
        with repository.connection.begin_nested():
            repository.connection.execute(text("ALTER TABLE milstrip_app.validation_issue RENAME COLUMN message TO synthetic_missing_message"))
            repository.health()
    assert repository.health()
