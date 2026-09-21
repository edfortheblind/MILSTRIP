-- MILSTRIP application-owned database objects.
-- This migration may create objects only inside milstrip_app.
-- It must not alter, reference, or write to existing operational tables.

CREATE SCHEMA IF NOT EXISTS milstrip_app;

CREATE TABLE IF NOT EXISTS milstrip_app.intake_request (
    request_id text PRIMARY KEY,
    source_type text NOT NULL,
    source_id text,
    source_sha256 char(64) NOT NULL,
    source_text text NOT NULL,
    status text NOT NULL DEFAULT 'RECEIVED',
    submitted_by text,
    received_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CONSTRAINT intake_request_source_type_ck
        CHECK (source_type IN ('PASTE', 'FILE', 'FRESHSERVICE')),
    CONSTRAINT intake_request_status_ck
        CHECK (status IN ('RECEIVED', 'PROCESSING', 'REQUIRES_REVIEW', 'VALID', 'REJECTED', 'FAILED'))
);

CREATE TABLE IF NOT EXISTS milstrip_app.milstrip_record (
    record_id text PRIMARY KEY,
    request_id text NOT NULL REFERENCES milstrip_app.intake_request(request_id),
    record_sequence integer NOT NULL,
    raw_candidate text,
    normalized_record text,
    canonical_record char(80),
    status text NOT NULL DEFAULT 'RECEIVED',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT milstrip_record_sequence_ck CHECK (record_sequence > 0),
    CONSTRAINT milstrip_record_status_ck
        CHECK (status IN ('RECEIVED', 'PROCESSING', 'REQUIRES_REVIEW', 'VALID', 'REJECTED', 'FAILED')),
    CONSTRAINT milstrip_record_canonical_length_ck
        CHECK (canonical_record IS NULL OR length(canonical_record) = 80),
    CONSTRAINT milstrip_record_request_sequence_uq UNIQUE (request_id, record_sequence)
);

CREATE TABLE IF NOT EXISTS milstrip_app.validation_issue (
    issue_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id text NOT NULL REFERENCES milstrip_app.milstrip_record(record_id),
    issue_code text NOT NULL,
    severity text NOT NULL,
    field_name text,
    position_start integer,
    position_end integer,
    message text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT validation_issue_severity_ck
        CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
    CONSTRAINT validation_issue_position_ck
        CHECK (position_start IS NULL OR (position_start BETWEEN 1 AND 80
            AND (position_end IS NULL OR position_end BETWEEN position_start AND 80)))
);

CREATE TABLE IF NOT EXISTS milstrip_app.review_decision (
    decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id text NOT NULL REFERENCES milstrip_app.milstrip_record(record_id),
    decision text NOT NULL,
    reason text,
    decided_by text NOT NULL,
    decided_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT review_decision_decision_ck CHECK (decision IN ('APPROVED', 'REJECTED'))
);

CREATE TABLE IF NOT EXISTS milstrip_app.audit_event (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    event_type text NOT NULL,
    actor text,
    correlation_id text,
    event_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS intake_request_received_at_idx
    ON milstrip_app.intake_request (received_at DESC);
CREATE INDEX IF NOT EXISTS milstrip_record_request_id_idx
    ON milstrip_app.milstrip_record (request_id);
CREATE INDEX IF NOT EXISTS validation_issue_record_id_idx
    ON milstrip_app.validation_issue (record_id);
CREATE INDEX IF NOT EXISTS audit_event_aggregate_idx
    ON milstrip_app.audit_event (aggregate_type, aggregate_id, occurred_at DESC);