"""Authenticated MILSTRIP intake with isolated Stage and Prod persistence."""
import hashlib
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from milstrip.service import process_text
from api.auth import authenticate
from api.operator import router as operator_router
from api.operator_models import IntakeAcknowledgement, RequestSummary, HealthResponse
from api.runtime import lifespan, profile_for, repository, snapshot_for

app = FastAPI(title="MILSTRIP API", version="0.4.0", lifespan=lifespan, dependencies=[Depends(authenticate)])
app.include_router(operator_router)


class IntakeRequest(BaseModel):
    source_type: str = Field(pattern="^(PASTE|FILE|FRESHSERVICE)$")
    source_id: str | None = None
    source_text: str = Field(min_length=1, max_length=1_000_000)
    submitted_by: str | None = None


@app.get("/api/v1/health", response_model=HealthResponse, operation_id="GetHealth")
def health(request: Request):
    profile = profile_for(request)
    result = {"status": "DEGRADED", "database": "UNAVAILABLE",
              "environment": profile.profile_id, "provider": profile.provider,
              "target_label": profile.label, "configuration_revision": snapshot_for(request).config.revision,
              "ready": False}
    if not profile.enabled:
        return {**result, "database": "DISABLED", "detail": "Environment is disabled"}
    try:
        with repository(request) as value:
            if not value.health():
                return result
    except HTTPException as error:
        return {**result, "detail": error.detail}
    return {**result, "status": "OK", "database": "AVAILABLE", "ready": True}


@app.post("/api/v1/intake/requests", status_code=201, response_model=IntakeAcknowledgement, operation_id="CreateIntakeRequest")
def create_intake_request(request: IntakeRequest, http_request: Request):
    with repository(http_request) as value:
        result = value.create_intake(
            request_id=str(uuid4()), source_type=request.source_type, source_id=request.source_id,
            source_text=request.source_text, source_sha256=hashlib.sha256(request.source_text.encode("utf-8")).hexdigest(),
            actor=http_request.state.context.actor, records=process_text(request.source_text))
    return result  # Receipt is returned only after the transaction commits.


@app.get("/api/v1/intake/requests/{request_id}", response_model=RequestSummary, operation_id="GetIntakeRequest")
def get_intake_request(request_id: str, request: Request):
    with repository(request) as value:
        result = value.get_request(request_id)
    if result is None:
        raise HTTPException(404, "Intake request not found")
    return result
