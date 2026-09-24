-- Retained Stage publication runtime test. Run on localhost:5432 / trav3pl-psqldb-stage.
-- Request: ff3f3cb5-04f5-4135-af74-f8db41962673
-- All statements are read-only. Do not delete this test's records.
BEGIN READ ONLY;

-- Final result: one row per record, with its current review.
SELECT
    q.request_id,
    q.received_at,
    q.status AS intake_validation_status,
    r.record_sequence,
    r.status AS validation_status,
    d.decision AS review_decision,
    r.review_version,
    length(r.canonical_record) AS canonical_length,
    r.canonical_record,
    d.reason,
    d.decided_by,
    d.decided_at
FROM milstrip_app.intake_request AS q
JOIN milstrip_app.milstrip_record AS r ON r.request_id = q.request_id
LEFT JOIN milstrip_app.review_decision AS d
    ON d.record_id = r.record_id AND d.review_version = r.review_version
WHERE q.request_id = 'ff3f3cb5-04f5-4135-af74-f8db41962673'
ORDER BY r.record_sequence;

-- Validation evidence, without duplicating the summary rows above.
SELECT r.record_sequence, i.issue_code, i.severity, i.message
FROM milstrip_app.milstrip_record AS r
JOIN milstrip_app.validation_issue AS i ON i.record_id = r.record_id
WHERE r.request_id = 'ff3f3cb5-04f5-4135-af74-f8db41962673'
ORDER BY r.record_sequence, i.issue_id;

-- Full intake and review audit trail, once per event.
SELECT a.event_id, a.occurred_at, a.event_type, a.actor,
       a.aggregate_type, a.aggregate_id, a.correlation_id, a.event_data
FROM milstrip_app.audit_event AS a
WHERE (a.aggregate_type = 'intake_request'
       AND a.aggregate_id = 'ff3f3cb5-04f5-4135-af74-f8db41962673')
   OR (a.aggregate_type = 'milstrip_record' AND EXISTS (
       SELECT 1 FROM milstrip_app.milstrip_record AS r
       WHERE r.request_id = 'ff3f3cb5-04f5-4135-af74-f8db41962673'
         AND r.record_id = a.aggregate_id
   ))
ORDER BY a.occurred_at, a.event_id;

COMMIT;
