-- Application-owned SQL Server / Azure SQL schema only. No legacy dbo objects.

-- Generated from api.persistence.schema; regeneration is checked by tests.

-- Execute only against an explicitly selected, approved database.

-- Does not label stage/prod: use the explicit provisioning command to set identity.

SET XACT_ABORT ON;

BEGIN TRANSACTION;

IF SCHEMA_ID(N'milstrip_app') IS NULL EXEC(N'CREATE SCHEMA milstrip_app');

IF OBJECT_ID(N'milstrip_app.audit_event', N'U') IS NULL
BEGIN
CREATE TABLE milstrip_app.audit_event (
	event_id BIGINT NOT NULL IDENTITY,
	aggregate_type NVARCHAR(50) NOT NULL,
	aggregate_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
	event_type NVARCHAR(50) NOT NULL,
	actor NVARCHAR(max) NULL,
	correlation_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NULL,
	event_data NVARCHAR(max) NOT NULL DEFAULT '{}',
	occurred_at DATETIMEOFFSET NOT NULL DEFAULT TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
	PRIMARY KEY (event_id)
);
CREATE INDEX audit_event_aggregate_idx ON milstrip_app.audit_event (aggregate_type, aggregate_id, occurred_at DESC);
END;

IF OBJECT_ID(N'milstrip_app.environment_identity', N'U') IS NULL
BEGIN
CREATE TABLE milstrip_app.environment_identity (
	singleton_id INTEGER NOT NULL,
	profile_id NVARCHAR(10) NOT NULL,
	schema_version INTEGER NOT NULL,
	created_at DATETIMEOFFSET NOT NULL DEFAULT TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
	PRIMARY KEY (singleton_id),
	CONSTRAINT environment_identity_singleton_ck CHECK (singleton_id = 1),
	CONSTRAINT environment_identity_profile_ck CHECK (profile_id IN ('stage', 'prod')),
	CONSTRAINT environment_identity_version_ck CHECK (schema_version > 0)
);

END;

IF OBJECT_ID(N'milstrip_app.intake_request', N'U') IS NULL
BEGIN
CREATE TABLE milstrip_app.intake_request (
	request_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
	source_type NVARCHAR(32) NOT NULL,
	source_id NVARCHAR(max) NULL,
	source_sha256 NVARCHAR(64) NOT NULL,
	source_text NVARCHAR(max) NOT NULL,
	status NVARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
	submitted_by NVARCHAR(max) NULL,
	received_at DATETIMEOFFSET NOT NULL DEFAULT TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
	completed_at DATETIMEOFFSET NULL,
	PRIMARY KEY (request_id),
	CONSTRAINT intake_request_source_type_ck CHECK (source_type IN ('PASTE', 'FILE', 'FRESHSERVICE')),
	CONSTRAINT intake_request_status_ck CHECK (status IN ('RECEIVED', 'PROCESSING', 'REQUIRES_REVIEW', 'VALID', 'REJECTED', 'FAILED'))
);
CREATE INDEX intake_request_page_idx ON milstrip_app.intake_request (received_at DESC, request_id DESC);
CREATE INDEX intake_request_status_page_idx ON milstrip_app.intake_request (status, received_at DESC, request_id DESC);
END;

IF OBJECT_ID(N'milstrip_app.milstrip_record', N'U') IS NULL
BEGIN
CREATE TABLE milstrip_app.milstrip_record (
	record_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
	request_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
	record_sequence INTEGER NOT NULL,
	raw_candidate NVARCHAR(max) NULL,
	normalized_record NVARCHAR(max) NULL,
	canonical_record NVARCHAR(80) NULL,
	status NVARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
	review_version INTEGER NOT NULL DEFAULT 0,
	created_at DATETIMEOFFSET NOT NULL DEFAULT TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
	PRIMARY KEY (record_id),
	CONSTRAINT milstrip_record_sequence_ck CHECK (record_sequence > 0),
	CONSTRAINT milstrip_record_review_version_ck CHECK (review_version >= 0),
	CONSTRAINT milstrip_record_status_ck CHECK (status IN ('RECEIVED', 'PROCESSING', 'REQUIRES_REVIEW', 'VALID', 'REJECTED', 'FAILED')),
	CONSTRAINT milstrip_record_canonical_length_ck CHECK (canonical_record IS NULL OR DATALENGTH(canonical_record) = 160),
	CONSTRAINT milstrip_record_request_sequence_uq UNIQUE (request_id, record_sequence),
	FOREIGN KEY(request_id) REFERENCES milstrip_app.intake_request (request_id)
);
CREATE INDEX milstrip_record_request_id_idx ON milstrip_app.milstrip_record (request_id);
END;

IF OBJECT_ID(N'milstrip_app.review_decision', N'U') IS NULL
BEGIN
CREATE TABLE milstrip_app.review_decision (
	decision_id BIGINT NOT NULL IDENTITY,
	record_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
	decision NVARCHAR(20) NOT NULL,
	reason NVARCHAR(max) NULL,
	decided_by NVARCHAR(max) NOT NULL,
	decided_at DATETIMEOFFSET NOT NULL DEFAULT TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
	command_id UNIQUEIDENTIFIER NULL,
	expected_version INTEGER NULL,
	review_version INTEGER NULL,
	PRIMARY KEY (decision_id),
	CONSTRAINT review_decision_decision_ck CHECK (decision IN ('APPROVED', 'REJECTED')),
	CONSTRAINT review_decision_expected_version_ck CHECK (expected_version >= 0),
	CONSTRAINT review_decision_review_version_ck CHECK (review_version > 0),
	FOREIGN KEY(record_id) REFERENCES milstrip_app.milstrip_record (record_id)
);
CREATE UNIQUE INDEX review_decision_command_uq ON milstrip_app.review_decision (record_id, command_id) WHERE command_id IS NOT NULL;
CREATE INDEX review_decision_latest_idx ON milstrip_app.review_decision (record_id, decision_id DESC);
CREATE UNIQUE INDEX review_decision_version_uq ON milstrip_app.review_decision (record_id, review_version) WHERE review_version IS NOT NULL;
END;

IF OBJECT_ID(N'milstrip_app.validation_issue', N'U') IS NULL
BEGIN
CREATE TABLE milstrip_app.validation_issue (
	issue_id BIGINT NOT NULL IDENTITY,
	record_id NVARCHAR(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
	issue_code NVARCHAR(100) NOT NULL,
	severity NVARCHAR(20) NOT NULL,
	field_name NVARCHAR(100) NULL,
	position_start INTEGER NULL,
	position_end INTEGER NULL,
	message NVARCHAR(max) NOT NULL,
	created_at DATETIMEOFFSET NOT NULL DEFAULT TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
	PRIMARY KEY (issue_id),
	CONSTRAINT validation_issue_severity_ck CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
	CONSTRAINT validation_issue_position_ck CHECK (position_start IS NULL OR (position_start BETWEEN 1 AND 80 AND (position_end IS NULL OR position_end BETWEEN position_start AND 80))),
	FOREIGN KEY(record_id) REFERENCES milstrip_app.milstrip_record (record_id)
);
CREATE INDEX validation_issue_record_id_idx ON milstrip_app.validation_issue (record_id);
END;

COMMIT TRANSACTION;
