"""Write-only administration contracts used inside the trusted broker."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool


class AdminPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyPayload(AdminPayload):
    pass


class SaveRuntimeDraftPayload(AdminPayload):
    command_id: UUID
    expected_active_revision: UUID
    provider: Literal["postgresql", "sqlserver"]
    label: str = Field(min_length=1, max_length=80)
    enabled: StrictBool
    replacement_connection_string: SecretStr | None = Field(default=None, json_schema_extra={"writeOnly": True})


class TestRuntimeDraftPayload(AdminPayload):
    command_id: UUID
    draft_id: UUID
    draft_revision: UUID


class ApplyRuntimeDraftPayload(TestRuntimeDraftPayload):
    expected_active_revision: UUID
    test_id: UUID | None = None


class AdministrationOperationPayload(AdminPayload):
    command_id: UUID
