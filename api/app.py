"""Small local API boundary for application-owned MILSTRIP persistence."""

from __future__ import annotations

import hashlib
import os
from typing import Any
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from milstrip.service import process_text


app = FastAPI(title="MILSTRIP API", version="0.1.0")


class IntakeRequest(BaseModel):
    source_type: str = Field(pattern="^(PASTE|FILE|FRESHSERVICE)$")
    source_id: str | None = None
    source_text: str = Field(min_length=1, max_length=1_000_000)
    submitted_by: str | None = None


def _database_url() -> str:
    value = os.getenv("MILSTRIP_DATABASE_URL")
    if not value:
        raise RuntimeError("MILSTRIP_DATABASE_URL is not configured")
    return value


def _connect() -> psycopg.Connection[Any]:
    return psycopg.connect(_database_url(), connect_timeout=5)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as error:
        return {"status": "DEGRADED", "database": "UNAVAILABLE", "detail": type(error).__name__}
    return {"status": "OK", "database": "AVAILABLE"}


@app.post("/api/v1/intake/requests", status_code=201)
def create_intake_request(request: IntakeRequest) -> dict[str, Any]:
    request_id = str(uuid4())
    source_sha256 = hashlib.sha256(request.source_text.encode("utf-8")).hexdigest()
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO milstrip_app.intake_request
                        (request_id, source_type, source_id, source_sha256, source_text, submitted_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING received_at
                    """,
                    (
                        request_id,
                        request.source_type,
                        request.source_id,
                        source_sha256,
                        request.source_text,
                        request.submitted_by,
                    ),
                )
                received_at = cursor.fetchone()[0]
                records = process_text(request.source_text)
                for sequence, record in enumerate(records, start=1):
                    record_id = f"{request_id}:{sequence}"
                    cursor.execute(
                        """
                        INSERT INTO milstrip_app.milstrip_record
                            (record_id, request_id, record_sequence, raw_candidate,
                             normalized_record, canonical_record, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            record_id,
                            request_id,
                            sequence,
                            record.fields.source,
                            record.fields.source,
                            record.canonical,
                            record.status,
                        ),
                    )
                    for issue in record.issues:
                        cursor.execute(
                            """
                            INSERT INTO milstrip_app.validation_issue
                                (record_id, issue_code, severity, message)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (record_id, issue.code, issue.severity, issue.message),
                        )
                request_status = (
                    "REJECTED" if not records or any(record.status == "REJECTED" for record in records)
                    else "REQUIRES_REVIEW" if any(record.status == "REQUIRES_REVIEW" for record in records)
                    else "VALID"
                )
                cursor.execute(
                    """
                    UPDATE milstrip_app.intake_request
                    SET status = %s, completed_at = now()
                    WHERE request_id = %s
                    """,
                    (request_status, request_id),
                )
                cursor.execute(
                    """
                    INSERT INTO milstrip_app.audit_event
                        (aggregate_type, aggregate_id, event_type, actor, correlation_id, event_data)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        "intake_request",
                        request_id,
                        request_status,
                        request.submitted_by,
                        request_id,
                        "{}",
                    ),
                )
        return {
            "request_id": request_id,
            "status": request_status,
            "received_at": received_at,
            "records": len(records),
            "rejected": sum(record.status == "REJECTED" for record in records),
            "requires_review": sum(record.status == "REQUIRES_REVIEW" for record in records),
        }
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error


@app.get("/api/v1/intake/requests/{request_id}")
def get_intake_request(request_id: str) -> dict[str, Any]:
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT request_id, source_type, source_id, source_sha256,
                           status, submitted_by, received_at, completed_at
                    FROM milstrip_app.intake_request
                    WHERE request_id = %s
                    """,
                    (request_id,),
                )
                row = cursor.fetchone()
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    if row is None:
        raise HTTPException(status_code=404, detail="Intake request not found")
    fields = ("request_id", "source_type", "source_id", "source_sha256", "status", "submitted_by", "received_at", "completed_at")
    return dict(zip(fields, row))