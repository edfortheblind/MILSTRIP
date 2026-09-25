"""Strict, bounded broker envelopes; no client-selected routes or identities."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectoryPerson(StrictModel):
    object_id: UUID
    upn: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=200)
    account_enabled: bool = Field(strict=True)
    user_type: Literal["Member", "Guest"]

    @field_validator("upn", "display_name")
    @classmethod
    def visible_text(cls, value):
        if value != value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("Identity text must be visible and unpadded")
        return value


Operation = Literal[
    "GetCurrentUser", "GetHealth", "ListIntakeRequests", "GetIntakeRequest",
    "ListRecordResults", "ListAuditEvents", "CreateIntakeRequest", "CreateReviewDecision",
    "ListUsers", "SaveUserAccess", "AcquireSharingLease", "RecordSharingResult",
    "ReserveManagementCall", "RecordManagementCall", "GetRuntimeProfiles",
    "SaveRuntimeDraft", "TestRuntimeDraft", "ApplyRuntimeDraft", "GetAdministrationOperation",
    "InitializeRuntimeDraft", "GetIntakeWorkflow",
]


class BrokerEnvelope(StrictModel):
    schema_version: Literal[1]
    request_id: UUID
    actor: DirectoryPerson
    operation: Operation
    payload_json: str = Field(min_length=2, max_length=1_100_000)


class BrokerResult(StrictModel):
    request_id: UUID
    result_json: str


class EmptyPayload(StrictModel):
    pass


class IntakeWorkflowPayload(StrictModel):
    source_id: str | None = Field(default=None, min_length=1, max_length=200)


class IntakePayload(StrictModel):
    source_type: Literal["PASTE", "FILE", "FRESHSERVICE"]
    source_id: str | None = Field(default=None, max_length=200)
    source_text: str = Field(min_length=1, max_length=1_000_000)
    duplicate_override_reason: str | None = Field(default=None, min_length=1, max_length=1000)


class RequestPayload(StrictModel):
    request_id: str = Field(min_length=1, max_length=200)


class PagePayload(StrictModel):
    limit: int = Field(default=50, ge=1, le=100, strict=True)
    cursor: str | None = Field(default=None, max_length=2048)


class RequestPagePayload(PagePayload):
    status: Literal["RECEIVED", "PROCESSING", "REQUIRES_REVIEW", "VALID", "REJECTED", "FAILED"] | None = None


class ChildPagePayload(RequestPayload, PagePayload):
    pass


class ReviewPayload(StrictModel):
    record_id: str = Field(min_length=1, max_length=200)
    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(ge=0, le=2147483646, strict=True)
    command_id: UUID


class SaveUserAccess(StrictModel):
    command_id: UUID
    expected_revision: UUID
    target: DirectoryPerson | None = None
    target_upn: str | None = Field(default=None, min_length=3, max_length=254)
    role: Literal["ADMIN", "OPERATOR"]
    active: bool = Field(strict=True)

    @model_validator(mode="after")
    def target_contract(self):
        if self.active and (self.target is None or self.target_upn is not None):
            raise ValueError("Adding access requires a directory-verified target")
        if not self.active and ((self.target is None) == (self.target_upn is None)):
            raise ValueError("Removal requires exactly one existing target reference")
        return self


class SharingObservation(StrictModel):
    kind: Literal["app", "flow"]
    resource_id: UUID
    permission: Literal["CanView", "run-only"]
    present: bool = Field(strict=True)
    verified: bool = Field(strict=True)


class SharingExecutionRef(StrictModel):
    plan_id: UUID
    revision: UUID
    execution_id: UUID


class NativeSharingRun(StrictModel):
    environment_name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9-]+$")
    flow_id: UUID
    run_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class AcquireSharingLease(SharingExecutionRef):
    # Optional only for compatibility with already-deployed flows. Unbound
    # executions are never eligible for generic metadata-only host recovery.
    native_run: NativeSharingRun | None = None


# Only fixed diagnostics cross this private broker boundary. Native response
# bodies, continuation links and identity text must never become error codes.
SharingErrorCode = Literal[
    "PLATFORM_FAILED", "READBACK_FAILED",
    "READBACK_PLAN_MISMATCH_STAGE_APP", "READBACK_PLAN_MISMATCH_STAGE_FLOW",
    "READBACK_PLAN_MISMATCH_PROD_APP", "READBACK_PLAN_MISMATCH_PROD_FLOW",
    "READBACK_CALL_FAILED_STAGE_APP", "READBACK_CALL_FAILED_STAGE_FLOW",
    "READBACK_CALL_FAILED_PROD_APP", "READBACK_CALL_FAILED_PROD_FLOW",
    "READBACK_FILTER_FAILED_STAGE_APP", "READBACK_FILTER_FAILED_STAGE_FLOW",
    "READBACK_FILTER_FAILED_PROD_APP", "READBACK_FILTER_FAILED_PROD_FLOW",
    "READBACK_PAGINATED_STAGE_APP", "READBACK_PAGINATED_STAGE_FLOW",
    "READBACK_PAGINATED_PROD_APP", "READBACK_PAGINATED_PROD_FLOW",
    "READBACK_ROW_LIMIT_STAGE_APP", "READBACK_ROW_LIMIT_STAGE_FLOW",
    "READBACK_ROW_LIMIT_PROD_APP", "READBACK_ROW_LIMIT_PROD_FLOW",
    "READBACK_PERMISSION_MISMATCH_STAGE_APP", "READBACK_PERMISSION_MISMATCH_STAGE_FLOW",
    "READBACK_PERMISSION_MISMATCH_PROD_APP", "READBACK_PERMISSION_MISMATCH_PROD_FLOW",
]


class SharingResult(SharingExecutionRef):
    lease_id: UUID
    external_calls_complete: bool = Field(strict=True)
    observations: list[SharingObservation] = Field(max_length=4)
    error_code: SharingErrorCode | None = None


ManagementStep = Literal[
    "Before_add_stage_flow", "Add_add_stage_flow", "Remove_add_stage_flow", "Readback_add_stage_flow",
    "Before_add_prod_flow", "Add_add_prod_flow", "Remove_add_prod_flow", "Readback_add_prod_flow",
    "Before_remove_stage_flow", "Add_remove_stage_flow", "Remove_remove_stage_flow", "Readback_remove_stage_flow",
    "Before_remove_prod_flow", "Add_remove_prod_flow", "Remove_remove_prod_flow", "Readback_remove_prod_flow",
]


class ReserveManagementCall(SharingExecutionRef):
    lease_id: UUID
    step: ManagementStep


class RecordManagementCall(ReserveManagementCall):
    reservation_id: UUID
    outcome_known: bool = Field(strict=True)


class AdministrationOperationPayload(StrictModel):
    command_id: UUID
