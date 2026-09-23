-- Additive local metadata only; legacy schemas are not referenced.
ALTER TABLE milstrip_app.milstrip_record
    ADD COLUMN IF NOT EXISTS review_version integer NOT NULL DEFAULT 0
    CHECK (review_version >= 0);

-- Nullable on pre-existing decisions. New API decisions supply all three.
ALTER TABLE milstrip_app.review_decision
    ADD COLUMN IF NOT EXISTS command_id uuid,
    ADD COLUMN IF NOT EXISTS expected_version integer CHECK (expected_version >= 0),
    ADD COLUMN IF NOT EXISTS review_version integer CHECK (review_version > 0);

CREATE UNIQUE INDEX IF NOT EXISTS review_decision_command_uq
    ON milstrip_app.review_decision (record_id, command_id);
CREATE UNIQUE INDEX IF NOT EXISTS review_decision_version_uq
    ON milstrip_app.review_decision (record_id, review_version);
CREATE INDEX IF NOT EXISTS review_decision_latest_idx
    ON milstrip_app.review_decision (record_id, decision_id DESC);
CREATE INDEX IF NOT EXISTS intake_request_page_idx
    ON milstrip_app.intake_request (received_at DESC, request_id DESC);
CREATE INDEX IF NOT EXISTS intake_request_status_page_idx
    ON milstrip_app.intake_request (status, received_at DESC, request_id DESC);
