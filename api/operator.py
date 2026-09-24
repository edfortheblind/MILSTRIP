"""Bounded operator reads and auditable review commands."""
import base64
import binascii
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import ValidationError

from api.runtime import repository
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
        raise HTTPException(422, "Invalid pagination cursor") from error


def _scoped_cursor(value, model, request_id):
    decoded = _decode(value, model)
    if decoded is not None and decoded.request_id != request_id:
        raise HTTPException(422, "Cursor belongs to another request")
    return decoded


@router.get("/intake/requests", response_model=RequestPage, operation_id="ListIntakeRequests")
def list_requests(request: Request, limit: Limit = 50, status: ValidationStatus | None = None, cursor: Cursor = None):
    boundary = _decode(cursor, RequestCursor)
    if boundary is not None and boundary.status != status:
        raise HTTPException(422, "Cursor status filter differs")
    with repository(request) as value:
        page = value.list_requests(limit, status, boundary)
    next_cursor = None
    if page.has_more:
        last = page.items[-1]
        next_cursor = _encode(RequestCursor(received_at=last["received_at"], request_id=last["request_id"], status=status))
    return {"items": page.items, "next_cursor": next_cursor}


@router.get("/intake/requests/{request_id}/records", response_model=RecordPage, operation_id="ListRecordResults")
def list_records(request_id: str, request: Request, limit: Limit = 50, cursor: Cursor = None):
    boundary = _scoped_cursor(cursor, RecordCursor, request_id)
    with repository(request) as value:
        page = value.list_records(request_id, limit, boundary)
    next_cursor = _encode(RecordCursor(request_id=request_id, sequence=page.items[-1]["record_sequence"])) if page.has_more else None
    return {"items": page.items, "next_cursor": next_cursor}


@router.get("/intake/requests/{request_id}/audit-events", response_model=EventPage, operation_id="ListAuditEvents")
def list_events(request_id: str, request: Request, limit: Limit = 50, cursor: Cursor = None):
    boundary = _scoped_cursor(cursor, EventCursor, request_id)
    with repository(request) as value:
        page = value.list_events(request_id, limit, boundary)
    next_cursor = _encode(EventCursor(request_id=request_id, occurred_at=page.items[-1]["occurred_at"], event_id=page.items[-1]["event_id"])) if page.has_more else None
    return {"items": page.items, "next_cursor": next_cursor}


@router.post("/records/{record_id}/review-decisions", status_code=201,
             response_model=ReviewDecision, responses={200: {"model": ReviewDecision}}, operation_id="CreateReviewDecision")
def review_record(record_id: str, command: ReviewCommand, request: Request, response: Response):
    with repository(request) as value:
        result = value.review_record(record_id, command, request.state.context.actor)
    if result.replayed:
        response.status_code = 200
    return result.decision
