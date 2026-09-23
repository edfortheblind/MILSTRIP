"""Local operator reads and auditable review commands; no legacy writes."""
import base64
import binascii
import ipaddress
import os
from typing import Annotated

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request, Response
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from api.database import connection
from api.operator_models import (
    EventCursor, EventPage, RecordCursor, RecordPage, RequestCursor,
    RequestPage, ReviewCommand, ReviewDecision, ValidationStatus,
)

router = APIRouter(prefix="/api/v1", tags=["operator"])
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=2048)]


def _encode(value):
    return base64.urlsafe_b64encode(value.model_dump_json().encode()).decode()


def _decode(value, model):
    if value is None:
        return None
    try:
        data = base64.b64decode(value, altchars=b"-_", validate=True)
        return model.model_validate_json(data)
    except (ValueError, binascii.Error, ValidationError) as error:
        raise HTTPException(status_code=422, detail="Invalid pagination cursor") from error


def _parent(cursor, request_id):
    cursor.execute("SELECT 1 FROM milstrip_app.intake_request WHERE request_id=%s", (request_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Intake request not found")


def _scoped_cursor(value, model, request_id):
    decoded = _decode(value, model)
    if decoded is not None and decoded.request_id != request_id:
        raise HTTPException(status_code=422, detail="Cursor belongs to another request")
    return decoded


@router.get("/intake/requests", response_model=RequestPage)
def list_requests(limit: Limit = 50, status: ValidationStatus | None = None, cursor: Cursor = None):
    boundary = _decode(cursor, RequestCursor)
    if boundary is not None and boundary.status != status:
        raise HTTPException(status_code=422, detail="Cursor status filter differs")
    where, parameters = [], []
    if status is not None:
        where.append("status = %s")
        parameters.append(status)
    if boundary is not None:
        where.append("(received_at, request_id) < (%s, %s)")
        parameters.extend([boundary.received_at, boundary.request_id])
    query = """SELECT request_id, source_type, source_id, source_sha256, status,
        submitted_by, received_at, completed_at FROM milstrip_app.intake_request"""
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY received_at DESC, request_id DESC LIMIT %s"
    with connection() as database, database.cursor(row_factory=dict_row) as db:
        db.execute(query, (*parameters, limit + 1))
        rows = db.fetchall()
    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        next_cursor = _encode(RequestCursor(received_at=last["received_at"], request_id=last["request_id"], status=status))
    return {"items": items, "next_cursor": next_cursor}


@router.get("/intake/requests/{request_id}/records", response_model=RecordPage)
def list_records(request_id: str, limit: Limit = 50, cursor: Cursor = None):
    boundary = _scoped_cursor(cursor, RecordCursor, request_id)
    with connection() as database, database.cursor(row_factory=dict_row) as db:
        _parent(db, request_id)
        db.execute("""SELECT record_id, request_id, record_sequence, raw_candidate,
            normalized_record, canonical_record, status, review_version
            FROM milstrip_app.milstrip_record WHERE request_id=%s AND record_sequence > %s
            ORDER BY record_sequence LIMIT %s""", (request_id, boundary.sequence if boundary else 0, limit + 1))
        rows = db.fetchall()
        items = rows[:limit]
        indexed = {row["record_id"]: row for row in items}
        for row in items:
            row.update(issues=[], latest_review=None)
        if items:
            db.execute("""SELECT issue_id, record_id, issue_code, severity, field_name,
                position_start, position_end, message FROM milstrip_app.validation_issue
                WHERE record_id = ANY(%s) ORDER BY issue_id""", (list(indexed),))
            for issue in db.fetchall():
                indexed[issue.pop("record_id")]["issues"].append(issue)
            db.execute("""SELECT DISTINCT ON (record_id) decision_id, record_id, decision,
                reason, decided_by, decided_at, command_id, expected_version, review_version
                FROM milstrip_app.review_decision WHERE record_id = ANY(%s)
                ORDER BY record_id, decision_id DESC""", (list(indexed),))
            for review in db.fetchall():
                indexed[review["record_id"]]["latest_review"] = review
    next_cursor = _encode(RecordCursor(request_id=request_id, sequence=items[-1]["record_sequence"])) if len(rows) > limit else None
    return {"items": items, "next_cursor": next_cursor}


@router.get("/intake/requests/{request_id}/audit-events", response_model=EventPage)
def list_events(request_id: str, limit: Limit = 50, cursor: Cursor = None):
    boundary = _scoped_cursor(cursor, EventCursor, request_id)
    query = """SELECT a.event_id, a.aggregate_type, a.aggregate_id, a.event_type,
        a.actor, a.correlation_id, a.event_data, a.occurred_at
        FROM milstrip_app.audit_event a WHERE (
            (a.aggregate_type='intake_request' AND a.aggregate_id=%s) OR
            (a.aggregate_type='milstrip_record' AND EXISTS (
                SELECT 1 FROM milstrip_app.milstrip_record r
                WHERE r.request_id=%s AND r.record_id=a.aggregate_id)))"""
    parameters = [request_id, request_id]
    if boundary:
        query += " AND (a.occurred_at, a.event_id) < (%s, %s)"
        parameters.extend([boundary.occurred_at, boundary.event_id])
    query += " ORDER BY a.occurred_at DESC, a.event_id DESC LIMIT %s"
    with connection() as database, database.cursor(row_factory=dict_row) as db:
        _parent(db, request_id)
        db.execute(query, (*parameters, limit + 1))
        rows = db.fetchall()
    items = rows[:limit]
    next_cursor = _encode(EventCursor(request_id=request_id, occurred_at=items[-1]["occurred_at"], event_id=items[-1]["event_id"])) if len(rows) > limit else None
    return {"items": items, "next_cursor": next_cursor}


def _local_reviewer(request):
    reviewer = os.getenv("MILSTRIP_LOCAL_REVIEWER", "").strip()
    if not reviewer or len(reviewer) > 200:
        raise HTTPException(status_code=503, detail="Local reviewer is not configured")
    try:
        peer_is_local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        host = conninfo_to_dict(os.getenv("MILSTRIP_DATABASE_URL", "")).get("host")
    except ValueError:
        peer_is_local, host = False, None
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    if not peer_is_local or host not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="Review commands are restricted to local development")
    return reviewer


@router.post("/records/{record_id}/review-decisions", status_code=201,
             response_model=ReviewDecision, responses={200: {"model": ReviewDecision}})
def review_record(record_id: str, command: ReviewCommand, request: Request, response: Response):
    reviewer = _local_reviewer(request)
    with connection() as database, database.cursor(row_factory=dict_row) as db:
        db.execute("""SELECT request_id, status, review_version FROM milstrip_app.milstrip_record
            WHERE record_id=%s FOR UPDATE""", (record_id,))
        record = db.fetchone()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        db.execute("SELECT * FROM milstrip_app.review_decision WHERE record_id=%s AND command_id=%s", (record_id, command.command_id))
        previous = db.fetchone()
        if previous is not None:
            if (previous["decision"], previous["reason"], previous["expected_version"], previous["decided_by"]) != (command.decision, command.reason, command.expected_version, reviewer):
                raise HTTPException(status_code=409, detail="Command ID was already used with different content")
            response.status_code = 200
            return previous
        if record["review_version"] != command.expected_version:
            raise HTTPException(status_code=409, detail="Review version changed; reload the record")
        if command.decision == "APPROVED" and record["status"] not in {"VALID", "REQUIRES_REVIEW"}:
            raise HTTPException(status_code=409, detail="Record validation does not permit approval")
        version = command.expected_version + 1
        db.execute("""INSERT INTO milstrip_app.review_decision
            (record_id, decision, reason, decided_by, command_id, expected_version, review_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (record_id, command.decision, command.reason, reviewer, command.command_id, command.expected_version, version))
        result = db.fetchone()
        db.execute("UPDATE milstrip_app.milstrip_record SET review_version=%s WHERE record_id=%s", (version, record_id))
        event = {"decision_id": result["decision_id"], "decision": command.decision,
                 "reason": command.reason, "command_id": str(command.command_id), "review_version": version}
        db.execute("""INSERT INTO milstrip_app.audit_event
            (aggregate_type, aggregate_id, event_type, actor, correlation_id, event_data)
            VALUES ('milstrip_record', %s, 'REVIEW_DECIDED', %s, %s, %s)""",
            (record_id, reviewer, record["request_id"], Jsonb(event)))
    return result
