-- Additive workflow tracking; preserves all historical requests.
CREATE TABLE IF NOT EXISTS milstrip_app.intake_workflow (
	request_id VARCHAR(200) NOT NULL,
	actor_key VARCHAR(64) NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (request_id),
	FOREIGN KEY(request_id) REFERENCES milstrip_app.intake_request (request_id)
);
CREATE INDEX IF NOT EXISTS intake_workflow_actor_idx ON milstrip_app.intake_workflow (actor_key);
CREATE INDEX IF NOT EXISTS intake_workflow_duplicate_idx ON milstrip_app.intake_workflow (fingerprint, created_at);
DO $$ BEGIN
IF to_regclass('milstrip_app.environment_identity') IS NOT NULL THEN
    UPDATE milstrip_app.environment_identity SET schema_version = 2 WHERE schema_version = 1;
END IF;
END $$;
