"""Application-owned tables shared by PostgreSQL and Azure SQL/SQL Server.

Existing PostgreSQL tables are left in place. No operational dbo tables or
parser functions belong to this metadata.
"""
from sqlalchemy import (
    BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Identity, Index,
    Integer, JSON, MetaData, Table, Unicode, UnicodeText, UniqueConstraint, Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


SCHEMA_VERSION = 2
metadata = MetaData(schema="milstrip_app")


class utc_now(FunctionElement):
    type = DateTime(timezone=True)
    inherit_cache = True


@compiles(utc_now, "postgresql")
def _postgres_now(element, compiler, **kw):
    return "CURRENT_TIMESTAMP"


@compiles(utc_now, "mssql")
def _sqlserver_now(element, compiler, **kw):
    return "TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00')"


class CanonicalLength(CheckConstraint):
    """SQL Server LEN ignores the trailing spaces required by MILSTRIP."""


@compiles(CanonicalLength, "mssql")
def _sqlserver_canonical(constraint, compiler, **kw):
    return "CONSTRAINT milstrip_record_canonical_length_ck CHECK (canonical_record IS NULL OR DATALENGTH(canonical_record) = 160)"


def identifier(size=200):
    return Unicode(size).with_variant(Unicode(size, collation="Latin1_General_100_BIN2"), "mssql")


def large_text():
    # Explicit variant also renders correctly during offline DDL generation;
    # the default MSSQL UnicodeText type otherwise falls back to legacy NTEXT.
    return UnicodeText().with_variant(NVARCHAR(None), "mssql")


def timestamp(name, *, nullable=False, default=True):
    return Column(name, DateTime(timezone=True), nullable=nullable,
                  server_default=utc_now() if default else None)


STATUSES = "'RECEIVED', 'PROCESSING', 'REQUIRES_REVIEW', 'VALID', 'REJECTED', 'FAILED'"

intake_request = Table(
    "intake_request", metadata,
    Column("request_id", identifier(), primary_key=True),
    Column("source_type", Unicode(32), nullable=False),
    Column("source_id", large_text()),
    Column("source_sha256", Unicode(64), nullable=False),
    Column("source_text", large_text(), nullable=False),
    Column("status", Unicode(32), nullable=False, server_default=text("'RECEIVED'")),
    Column("submitted_by", large_text()),
    timestamp("received_at"), timestamp("completed_at", nullable=True, default=False),
    CheckConstraint("source_type IN ('PASTE', 'FILE', 'FRESHSERVICE')", name="intake_request_source_type_ck"),
    CheckConstraint(f"status IN ({STATUSES})", name="intake_request_status_ck"),
)

intake_workflow = Table(
    "intake_workflow", metadata,
    Column("request_id", identifier(), ForeignKey(intake_request.c.request_id), primary_key=True),
    Column("actor_key", Unicode(64), nullable=False),
    Column("fingerprint", Unicode(64), nullable=False),
    timestamp("created_at"),
)
Index("intake_workflow_actor_idx", intake_workflow.c.actor_key)
Index("intake_workflow_duplicate_idx", intake_workflow.c.fingerprint, intake_workflow.c.created_at)

milstrip_record = Table(
    "milstrip_record", metadata,
    Column("record_id", identifier(), primary_key=True),
    Column("request_id", identifier(), ForeignKey(intake_request.c.request_id), nullable=False),
    Column("record_sequence", Integer, nullable=False),
    Column("raw_candidate", large_text()),
    Column("normalized_record", large_text()),
    Column("canonical_record", UnicodeText().with_variant(Unicode(80), "mssql")),
    Column("status", Unicode(32), nullable=False, server_default=text("'RECEIVED'")),
    Column("review_version", Integer, nullable=False, server_default=text("0")),
    timestamp("created_at"),
    CheckConstraint("record_sequence > 0", name="milstrip_record_sequence_ck"),
    CheckConstraint("review_version >= 0", name="milstrip_record_review_version_ck"),
    CheckConstraint(f"status IN ({STATUSES})", name="milstrip_record_status_ck"),
    CanonicalLength("canonical_record IS NULL OR length(canonical_record) = 80", name="milstrip_record_canonical_length_ck"),
    UniqueConstraint("request_id", "record_sequence", name="milstrip_record_request_sequence_uq"),
)

validation_issue = Table(
    "validation_issue", metadata,
    Column("issue_id", BigInteger, Identity(always=True), primary_key=True),
    Column("record_id", identifier(), ForeignKey(milstrip_record.c.record_id), nullable=False),
    Column("issue_code", Unicode(100), nullable=False),
    Column("severity", Unicode(20), nullable=False),
    Column("field_name", Unicode(100)),
    Column("position_start", Integer), Column("position_end", Integer),
    Column("message", large_text(), nullable=False), timestamp("created_at"),
    CheckConstraint("severity IN ('INFO', 'WARNING', 'ERROR')", name="validation_issue_severity_ck"),
    CheckConstraint("position_start IS NULL OR (position_start BETWEEN 1 AND 80 AND (position_end IS NULL OR position_end BETWEEN position_start AND 80))", name="validation_issue_position_ck"),
)

review_decision = Table(
    "review_decision", metadata,
    Column("decision_id", BigInteger, Identity(always=True), primary_key=True),
    Column("record_id", identifier(), ForeignKey(milstrip_record.c.record_id), nullable=False),
    Column("decision", Unicode(20), nullable=False), Column("reason", large_text()),
    Column("decided_by", large_text(), nullable=False), timestamp("decided_at"),
    Column("command_id", Uuid(as_uuid=True)), Column("expected_version", Integer), Column("review_version", Integer),
    CheckConstraint("decision IN ('APPROVED', 'REJECTED')", name="review_decision_decision_ck"),
    CheckConstraint("expected_version >= 0", name="review_decision_expected_version_ck"),
    CheckConstraint("review_version > 0", name="review_decision_review_version_ck"),
)

audit_event = Table(
    "audit_event", metadata,
    Column("event_id", BigInteger, Identity(always=True), primary_key=True),
    Column("aggregate_type", Unicode(50), nullable=False), Column("aggregate_id", identifier(), nullable=False),
    Column("event_type", Unicode(50), nullable=False), Column("actor", large_text()),
    Column("correlation_id", identifier()),
    Column("event_data", JSON().with_variant(JSONB(), "postgresql"), nullable=False, server_default=text("'{}'")),
    timestamp("occurred_at"),
)

environment_identity = Table(
    "environment_identity", metadata,
    Column("singleton_id", Integer, primary_key=True, autoincrement=False),
    Column("profile_id", Unicode(10), nullable=False),
    Column("schema_version", Integer, nullable=False), timestamp("created_at"),
    CheckConstraint("singleton_id = 1", name="environment_identity_singleton_ck"),
    CheckConstraint("profile_id IN ('stage', 'prod')", name="environment_identity_profile_ck"),
    CheckConstraint("schema_version > 0", name="environment_identity_version_ck"),
)

Index("intake_request_page_idx", intake_request.c.received_at.desc(), intake_request.c.request_id.desc())
Index("intake_request_status_page_idx", intake_request.c.status, intake_request.c.received_at.desc(), intake_request.c.request_id.desc())
Index("milstrip_record_request_id_idx", milstrip_record.c.request_id)
Index("validation_issue_record_id_idx", validation_issue.c.record_id)
Index("review_decision_latest_idx", review_decision.c.record_id, review_decision.c.decision_id.desc())
# Existing decisions can lack a command/version. SQL Server needs filtered
# indexes to permit multiple NULLs, matching PostgreSQL's unique-index behavior.
Index("review_decision_command_uq", review_decision.c.record_id, review_decision.c.command_id,
      unique=True, mssql_where=review_decision.c.command_id.is_not(None))
Index("review_decision_version_uq", review_decision.c.record_id, review_decision.c.review_version,
      unique=True, mssql_where=review_decision.c.review_version.is_not(None))
Index("audit_event_aggregate_idx", audit_event.c.aggregate_type, audit_event.c.aggregate_id, audit_event.c.occurred_at.desc())
