from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

ValidationStatus = Literal["RECEIVED", "PROCESSING", "REQUIRES_REVIEW", "VALID", "REJECTED", "FAILED"]


class RequestSummary(BaseModel):
    request_id: str
    source_type: str
    source_id: str | None
    source_sha256: str
    status: ValidationStatus
    submitted_by: str | None
    received_at: datetime
    completed_at: datetime | None


class ReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "decision": "REJECTED", "reason": "Corrected source requested",
        "expected_version": 0, "command_id": "10000000-0000-4000-8000-000000000001",
    }]})
    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(ge=0, le=2147483646, strict=True)
    command_id: UUID

    @field_validator("reason")
    @classmethod
    def reason_required(cls, value):
        if not value.strip():
            raise ValueError("Reason must not be blank")
        return value


class ReviewDecision(BaseModel):
    decision_id: int
    record_id: str
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None
    decided_by: str
    decided_at: datetime
    command_id: UUID | None
    expected_version: int | None
    review_version: int | None


class ValidationIssue(BaseModel):
    issue_id: int
    issue_code: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    field_name: str | None
    position_start: int | None
    position_end: int | None
    message: str


class RecordDetail(BaseModel):
    record_id: str
    request_id: str
    record_sequence: int
    raw_candidate: str | None
    normalized_record: str | None
    canonical_record: str | None
    status: ValidationStatus
    review_version: int
    issues: list[ValidationIssue]
    latest_review: ReviewDecision | None


class AuditEvent(BaseModel):
    event_id: int
    aggregate_type: str
    aggregate_id: str
    event_type: str
    actor: str | None
    correlation_id: str | None
    event_data: dict
    occurred_at: datetime


class RequestPage(BaseModel):
    items: list[RequestSummary]
    next_cursor: str | None


class RecordPage(BaseModel):
    items: list[RecordDetail]
    next_cursor: str | None


class EventPage(BaseModel):
    items: list[AuditEvent]
    next_cursor: str | None


class RequestCursor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["requests"] = "requests"
    received_at: AwareDatetime
    request_id: str = Field(min_length=1, max_length=200)
    status: ValidationStatus | None = None


class RecordCursor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["records"] = "records"
    request_id: str = Field(min_length=1, max_length=200)
    sequence: int = Field(gt=0, le=2147483647, strict=True)


class EventCursor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["events"] = "events"
    request_id: str = Field(min_length=1, max_length=200)
    occurred_at: AwareDatetime
    event_id: int = Field(gt=0, le=9223372036854775807, strict=True)
