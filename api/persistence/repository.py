"""Intake/review operations; callers own HTTP and cursor serialization."""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import and_, create_engine, event, exists, func, inspect, or_, select, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema

from .schema import (
    SCHEMA_VERSION, audit_event, environment_identity, intake_request,
    metadata, milstrip_record, review_decision, utc_now, validation_issue,
)


class RepositoryNotFound(Exception):
    pass


class RepositoryConflict(Exception):
    pass


class ProviderMismatch(Exception):
    """Database is not provisioned for the requested environment/version."""


@dataclass(frozen=True)
class Page:
    items: list[dict[str, Any]]
    has_more: bool


@dataclass(frozen=True)
class ReviewResult:
    decision: dict[str, Any]
    replayed: bool


def make_engine(provider: str, connection_string: str):
    """Create an unpooled engine. Never place a connection string in errors/logs."""
    if provider == "postgresql":
        # libpq otherwise inherits these even when host/dbname are explicit.
        # In particular PGHOSTADDR can connect to another server while the
        # configuration screen still displays the saved host. Do not mutate
        # process-wide environment variables in a concurrent API process.
        if any(os.getenv(name) for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS", "PGPASSFILE")):
            raise psycopg.OperationalError("PostgreSQL environment overrides are not supported")
        # psycopg accepts both libpq conninfo and postgres/postgresql URLs.
        port = conninfo_to_dict(connection_string).get("port", "5432")
        return create_engine("postgresql+psycopg://", poolclass=NullPool,
                             creator=lambda: psycopg.connect(connection_string, port=port, connect_timeout=5),
                             hide_parameters=True)
    if provider == "sqlserver":
        engine = create_engine(URL.create("mssql+pyodbc", query={"odbc_connect": connection_string}),
                               poolclass=NullPool, connect_args={"timeout": 5}, hide_parameters=True)

        @event.listens_for(engine, "connect")
        def set_query_timeout(dbapi_connection, connection_record):
            dbapi_connection.timeout = 15
        return engine
    raise ValueError("Unsupported database provider")


@contextmanager
def open_repository(provider: str, connection_string: str):
    """One operation, one transaction. Commit only after the caller succeeds."""
    engine = make_engine(provider, connection_string)
    try:
        with engine.begin() as connection:
            if provider == "postgresql":
                connection.execute(text("SET LOCAL lock_timeout = '5s'"))
                connection.execute(text("SET LOCAL statement_timeout = '15s'"))
            else:
                connection.execute(text("SET LOCK_TIMEOUT 5000"))
            yield Repository(connection)
    finally:
        engine.dispose()


def provision_schema(provider: str, connection_string: str, profile_id: str):
    """Explicit application-schema provisioning; never invoked by a data read.

    Existing tables and data are preserved. An incompatible old schema or a
    differently labeled database fails instead of being relabeled or migrated.
    """
    if profile_id not in {"stage", "prod"}:
        raise ValueError("Profile must be stage or prod")
    with open_repository(provider, connection_string) as repository:
        connection = repository.connection
        if provider == "postgresql":
            connection.execute(CreateSchema("milstrip_app", if_not_exists=True))
        else:
            connection.execute(text("IF SCHEMA_ID(N'milstrip_app') IS NULL EXEC(N'CREATE SCHEMA milstrip_app')"))
        metadata.create_all(connection)
        inspector = inspect(connection)
        for table in metadata.sorted_tables:
            present = {column["name"] for column in inspector.get_columns(table.name, schema="milstrip_app")}
            if not set(table.c.keys()).issubset(present):
                raise ProviderMismatch("Application schema requires an explicit migration")
        identity = connection.execute(select(environment_identity)).mappings().first()
        if identity is None:
            connection.execute(environment_identity.insert().values(singleton_id=1, profile_id=profile_id,
                                                                   schema_version=SCHEMA_VERSION))
        repository.validate_identity(profile_id)
        return {"profile_id": profile_id, "schema_version": SCHEMA_VERSION}


REQUEST_COLUMNS = tuple(intake_request.c[name] for name in (
    "request_id", "source_type", "source_id", "source_sha256", "status", "submitted_by", "received_at", "completed_at"))
RECORD_COLUMNS = tuple(milstrip_record.c[name] for name in (
    "record_id", "request_id", "record_sequence", "raw_candidate", "normalized_record", "canonical_record", "status", "review_version"))
ISSUE_COLUMNS = tuple(validation_issue.c[name] for name in (
    "issue_id", "record_id", "issue_code", "severity", "field_name", "position_start", "position_end", "message"))


def _boundary(boundary, name):
    return boundary[name] if isinstance(boundary, dict) else getattr(boundary, name)


def _page(rows, limit):
    return Page([dict(row) for row in rows[:limit]], len(rows) > limit)


def _limit(limit):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Page size must be between 1 and 100")


def locked_record_statement(record_id):
    # SQLAlchemy's FOR UPDATE has no SQL Server rendering. Explicit lock hints
    # serialize review commands on that record through the whole transaction.
    return select(milstrip_record.c.request_id, milstrip_record.c.status, milstrip_record.c.review_version).where(
        milstrip_record.c.record_id == record_id).with_for_update().with_hint(
            milstrip_record, "WITH (UPDLOCK, HOLDLOCK, ROWLOCK)", dialect_name="mssql")


class Repository:
    def __init__(self, connection):
        self.connection = connection

    def health(self):
        if self.connection.scalar(select(1)) != 1:
            return False
        # Probe the required application columns without reading any rows.
        # An identity row alone does not prove the application schema is usable.
        for table in metadata.sorted_tables:
            self.connection.execute(select(table).limit(0)).close()
        return True

    def validate_identity(self, profile_id):
        row = self.connection.execute(select(environment_identity.c.profile_id, environment_identity.c.schema_version).where(
            environment_identity.c.singleton_id == 1)).mappings().first()
        if row is None or row["profile_id"] != profile_id or row["schema_version"] != SCHEMA_VERSION:
            raise ProviderMismatch("Database environment or schema version does not match the profile")

    def create_intake(self, request_id, source_type, source_id, source_text, source_sha256, actor, records):
        records = list(records)
        received_at = self.connection.execute(intake_request.insert().values(
            request_id=request_id, source_type=source_type, source_id=source_id,
            source_text=source_text, source_sha256=source_sha256, submitted_by=actor,
        ).returning(intake_request.c.received_at)).scalar_one()
        for sequence, record in enumerate(records, start=1):
            record_id = f"{request_id}:{sequence}"
            self.connection.execute(milstrip_record.insert().values(
                record_id=record_id, request_id=request_id, record_sequence=sequence,
                raw_candidate=record.raw_candidate, normalized_record=record.fields.source,
                canonical_record=record.canonical, status=record.status,
            ))
            for issue in record.issues:
                self.connection.execute(validation_issue.insert().values(
                    record_id=record_id, issue_code=issue.code, severity=issue.severity,
                    message=issue.message, field_name=issue.field_name,
                ))
        status = ("REJECTED" if not records or any(record.status == "REJECTED" for record in records)
                  else "REQUIRES_REVIEW" if any(record.status == "REQUIRES_REVIEW" for record in records)
                  else "VALID")
        self.connection.execute(intake_request.update().where(intake_request.c.request_id == request_id).values(
            status=status, completed_at=utc_now()))
        self.connection.execute(audit_event.insert().values(
            aggregate_type="intake_request", aggregate_id=request_id, event_type=status,
            actor=actor, correlation_id=request_id, event_data={},
        ))
        return {"request_id": request_id, "status": status, "received_at": received_at,
                "records": len(records), "rejected": sum(record.status == "REJECTED" for record in records),
                "requires_review": sum(record.status == "REQUIRES_REVIEW" for record in records)}

    def get_request(self, request_id):
        row = self.connection.execute(select(*REQUEST_COLUMNS).where(intake_request.c.request_id == request_id)).mappings().first()
        return dict(row) if row is not None else None

    def _parent(self, request_id):
        if self.connection.scalar(select(intake_request.c.request_id).where(intake_request.c.request_id == request_id)) is None:
            raise RepositoryNotFound("Intake request not found")

    def list_requests(self, limit=50, status=None, boundary=None):
        _limit(limit)
        statement = select(*REQUEST_COLUMNS)
        if status is not None:
            statement = statement.where(intake_request.c.status == status)
        if boundary is not None:
            received_at, request_id = _boundary(boundary, "received_at"), _boundary(boundary, "request_id")
            statement = statement.where(or_(intake_request.c.received_at < received_at, and_(
                intake_request.c.received_at == received_at, intake_request.c.request_id < request_id)))
        rows = self.connection.execute(statement.order_by(intake_request.c.received_at.desc(), intake_request.c.request_id.desc()).limit(limit + 1)).mappings().all()
        return _page(rows, limit)

    def list_records(self, request_id, limit=50, boundary=None):
        _limit(limit)
        self._parent(request_id)
        sequence = _boundary(boundary, "sequence") if boundary is not None else 0
        rows = self.connection.execute(select(*RECORD_COLUMNS).where(
            milstrip_record.c.request_id == request_id, milstrip_record.c.record_sequence > sequence,
        ).order_by(milstrip_record.c.record_sequence).limit(limit + 1)).mappings().all()
        page = _page(rows, limit)
        indexed = {item["record_id"]: item for item in page.items}
        for item in page.items:
            item.update(issues=[], latest_review=None)
        if indexed:
            issues = self.connection.execute(select(*ISSUE_COLUMNS).where(validation_issue.c.record_id.in_(indexed)).order_by(validation_issue.c.issue_id)).mappings()
            for row in issues:
                issue = dict(row)
                indexed[issue.pop("record_id")]["issues"].append(issue)
            latest = select(func.max(review_decision.c.decision_id).label("decision_id")).where(
                review_decision.c.record_id.in_(indexed)).group_by(review_decision.c.record_id)
            reviews = self.connection.execute(select(review_decision).where(review_decision.c.decision_id.in_(latest))).mappings()
            for row in reviews:
                indexed[row["record_id"]]["latest_review"] = dict(row)
        return page

    def list_events(self, request_id, limit=50, boundary=None):
        _limit(limit)
        self._parent(request_id)
        child_record = exists(select(1).where(milstrip_record.c.request_id == request_id,
                                              milstrip_record.c.record_id == audit_event.c.aggregate_id))
        statement = select(audit_event).where(or_(
            and_(audit_event.c.aggregate_type == "intake_request", audit_event.c.aggregate_id == request_id),
            and_(audit_event.c.aggregate_type == "milstrip_record", child_record),
        ))
        if boundary is not None:
            occurred_at, event_id = _boundary(boundary, "occurred_at"), _boundary(boundary, "event_id")
            statement = statement.where(or_(audit_event.c.occurred_at < occurred_at,
                and_(audit_event.c.occurred_at == occurred_at, audit_event.c.event_id < event_id)))
        rows = self.connection.execute(statement.order_by(audit_event.c.occurred_at.desc(), audit_event.c.event_id.desc()).limit(limit + 1)).mappings().all()
        return _page(rows, limit)

    def review_record(self, record_id, command, actor):
        record = self.connection.execute(locked_record_statement(record_id)).mappings().first()
        if record is None:
            raise RepositoryNotFound("Record not found")
        previous = self.connection.execute(select(review_decision).where(
            review_decision.c.record_id == record_id, review_decision.c.command_id == command.command_id,
        )).mappings().first()
        if previous is not None:
            # Compare in Python, where SQL Server's case-insensitive text
            # collation cannot make changed actor/reason content look identical.
            if (previous["decision"], previous["reason"], previous["expected_version"], previous["decided_by"]) != (
                    command.decision, command.reason, command.expected_version, actor):
                raise RepositoryConflict("Command ID was already used with different content")
            return ReviewResult(dict(previous), True)
        if record["review_version"] != command.expected_version:
            raise RepositoryConflict("Review version changed; reload the record")
        if command.decision == "APPROVED" and record["status"] not in {"VALID", "REQUIRES_REVIEW"}:
            raise RepositoryConflict("Record validation does not permit approval")
        version = command.expected_version + 1
        result = dict(self.connection.execute(review_decision.insert().values(
            record_id=record_id, decision=command.decision, reason=command.reason, decided_by=actor,
            command_id=command.command_id, expected_version=command.expected_version, review_version=version,
        ).returning(*review_decision.c)).mappings().one())
        self.connection.execute(milstrip_record.update().where(milstrip_record.c.record_id == record_id).values(review_version=version))
        self.connection.execute(audit_event.insert().values(
            aggregate_type="milstrip_record", aggregate_id=record_id, event_type="REVIEW_DECIDED",
            actor=actor, correlation_id=record["request_id"], event_data={
                "decision_id": result["decision_id"], "decision": command.decision, "reason": command.reason,
                "command_id": str(command.command_id), "review_version": version,
            },
        ))
        return ReviewResult(result, False)
