"""Host-only recovery of the one reviewed, canceled-before-mutation run.

No broker route exposes this module. Apply obtains fresh evidence from a trusted
collector; captured JSON is usable only by the separate read-only preview.
The exception for the historical run is deliberately not a generic lease reset.
"""
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, ValidationError

from api.control import ControlError, append_audit, principal_key


HISTORICAL = {
    "tenant_id": "9f5c0ace-0780-4b48-8c24-b08bb5149210",
    "profile_id": "stage",
    "flow_id": "04d6229f-5ab8-f111-aaac-7ced8d6f317c",
    "run_id": "08584113137259107903122568693CU13",
    "command_id": "689cf9a0-cfe5-4fc7-9496-bb1e2db0c32c",
    "plan_id": "b68690a1-837a-44ce-9950-248e4eb52df4",
    "execution_id": "fe7ea517-271b-4393-bfd0-f51657b9f99e",
    "lease_id": "6ddd23d7-e3b6-458e-adfa-967bf5d91c81",
    "attached_flow_name": "4e2df4b9-e7fd-e446-63fa-678b9612ca1f",
    "definition_sha256": "51891943a03f543679fc6c5faa9cabe4005081f26fcc82b98edeac2454a1113e",
}
REASON = "NATIVE_CANCELED_BEFORE_MUTATION"
PROVENANCE = "docs/delivery/MAKERS_PERMISSION_PAGINATION_2026-09-24.md"
FRESHNESS = timedelta(minutes=5)
TOKEN = r"^[A-Za-z0-9_.-]{1,128}$"
BROKER_API = "shared_tab-5fmilstrip-20local-20dev-20api-5f9baef836fe8c097c"


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecoveryRequest(_ClosedModel):
    command_id: UUID
    plan_id: UUID
    revision: UUID
    execution_id: UUID
    lease_id: UUID
    intent: Literal["NATIVE_CANCELED_BEFORE_MUTATION"]


class _Run(_ClosedModel):
    status: Literal["Cancelled", "Canceled"]
    start_time: AwareDatetime
    end_time: AwareDatetime
    workflow_id: str
    workflow_name: str = Field(pattern=TOKEN)
    workflow_version: str | None = Field(default=None, pattern=TOKEN)


class _Action(_ClosedModel):
    name: str = Field(pattern=TOKEN)
    status: Literal["Succeeded", "Failed", "Running", "Waiting", "Skipped", "TimedOut", "Cancelled", "Canceled", "Aborted", "Suspended"]
    code: str | None = Field(default=None, pattern=TOKEN)
    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None


class _DefinitionAction(_ClosedModel):
    name: str = Field(pattern=TOKEN)
    type: Literal["If", "OpenApiConnection", "Response", "Compose", "Query", "Select", "Wait", "ParseJson"]
    connection: str | None = Field(default=None, pattern=TOKEN)
    operation: str | None = Field(default=None, pattern=TOKEN)
    broker_operation: str | None = Field(default=None, pattern=TOKEN)
    api_name: str | None = Field(default=None, pattern=TOKEN)
    ancestors: list[str] = Field(max_length=20)
    ancestor_branches: list[str] = Field(max_length=20)


class _Definition(_ClosedModel):
    attached_flow_name: UUID
    attached_flow_id: str
    snapshot_identity_source: Literal["run.properties.flow.name"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    hash_serialization: Literal["powershell-converttojson-depth100-compress-utf8-no-bom"]
    logical_flow_id: UUID
    metadata_logical_flow_id: UUID
    content_version: str = Field(pattern=TOKEN)
    actions: list[_DefinitionAction] = Field(min_length=1, max_length=999)


class _Completeness(_ClosedModel):
    run: StrictBool
    actions: StrictBool
    definition: StrictBool


class RecoveryEvidence(_ClosedModel):
    source: Literal["native-sharing-recovery-metadata", "offline-sharing-recovery-metadata"]
    schema_version: Literal[1]
    collected_at: AwareDatetime
    tenant_id: UUID
    environment: str
    actor_object_id: UUID
    flow_id: UUID
    run_id: str = Field(pattern=TOKEN)
    run: _Run
    actions: list[_Action] = Field(min_length=1, max_length=999)
    definition: _Definition
    completeness: _Completeness


class NativeRecoveryCollector(ABC):
    """Trusted host-code seam. Implementations authenticate and fetch afresh.

    A file reader/offline fixture adapter must never implement this interface in
    a shipped entry point. The CLI's concrete implementation runs the fixed
    Microsoft-authenticated collector without an OfflineDirectory argument.
    """

    @abstractmethod
    def collect(self) -> dict:
        raise NotImplementedError


def _require(condition, message, status=409):
    if not condition:
        raise ControlError(status, message)


def _parse(request, evidence):
    try:
        return RecoveryRequest.model_validate(request), RecoveryEvidence.model_validate(evidence)
    except (ValidationError, ValueError, TypeError):
        raise ControlError(422, "Recovery evidence or request is invalid or incomplete") from None


def _qualify_evidence(request, evidence, now):
    _require(now.tzinfo is not None, "Recovery clock must include a timezone", 503)
    _require(now - FRESHNESS <= evidence.collected_at <= now,
             "Recovery evidence is stale or from the future")
    _require(evidence.run.start_time <= evidence.run.end_time <= evidence.collected_at,
             "Recovery timestamps do not establish collection after cancellation")
    _require(all(evidence.completeness.model_dump().values()), "Recovery evidence traversal is incomplete")
    for name in ("command_id", "plan_id", "execution_id", "lease_id"):
        _require(str(getattr(request, name)) == HISTORICAL[name], "Recovery is limited to the reviewed historical mapping")
    for name in ("tenant_id", "flow_id", "run_id"):
        _require(str(getattr(evidence, name)) == HISTORICAL[name], "Native run does not match the reviewed mapping")
    environment = "Default-" + HISTORICAL["tenant_id"]
    attached_path = ("/providers/Microsoft.ProcessSimple/environments/" + environment
                     + "/flows/" + HISTORICAL["attached_flow_name"])
    definition = evidence.definition
    _require(evidence.environment == environment
             and str(definition.attached_flow_name) == HISTORICAL["attached_flow_name"]
             and definition.attached_flow_id == attached_path
             and evidence.run.workflow_id == attached_path
             and evidence.run.workflow_name == HISTORICAL["attached_flow_name"]
             and str(definition.logical_flow_id) == HISTORICAL["flow_id"]
             and str(definition.metadata_logical_flow_id) == HISTORICAL["flow_id"]
             and definition.sha256 == HISTORICAL["definition_sha256"],
             "Run-attached definition does not match the independently reviewed snapshot")
    actions = {item.name: item for item in evidence.actions}
    inventory = {item.name: item for item in definition.actions}
    _require(len(actions) == len(evidence.actions) == len(inventory) == len(definition.actions) == 225
             and actions.keys() == inventory.keys(), "Executed action inventory is incomplete or contains duplicates")
    for action in evidence.actions:
        for timestamp in (action.start_time, action.end_time):
            _require(timestamp is None or evidence.run.start_time <= timestamp <= evidence.run.end_time,
                     "Action timestamps are outside the canceled run")
        _require(action.start_time is None or action.end_time is None or action.start_time <= action.end_time,
                 "Action timestamps are reversed")
    started_broker = {"Save_membership_add": "SaveUserAccess", "Acquire_lease_add": "AcquireSharingLease"}
    external_contract = {
        ("invoker", "MyProfile_V2"): "shared_office365users",
        ("directory", "UserProfile_V2"): "shared_office365users",
        ("makers", "Get-AppRoleAssignment"): "shared_powerappsforappmakers",
        ("makers", "Edit-AppRoleAssignment"): "shared_powerappsforappmakers",
        ("management", "ListFlowUsers"): "shared_flowmanagement",
        ("management", "ModifyRunOnlyUsers"): "shared_flowmanagement",
        ("broker", "InvokeBroker"): BROKER_API,
    }
    mutations, management, pacing = set(), set(), set()
    for name, item in inventory.items():
        _require(len(item.ancestors) == len(set(item.ancestors)) == len(item.ancestor_branches)
                 and all(parent in inventory and parent != name for parent in item.ancestors)
                 and all(branch in {parent + ":actions", parent + ":else"}
                         for parent, branch in zip(item.ancestors, item.ancestor_branches)),
                 "Executed definition ancestry is invalid")
        observed = actions[name]
        if item.type != "OpenApiConnection":
            _require(not any((item.connection, item.operation, item.broker_operation, item.api_name)),
                     "Unexpected external action metadata")
            continue
        _require(external_contract.get((item.connection, item.operation)) == item.api_name
                 and item.api_name is not None, "Executed definition has an unexpected external action")
        if item.operation in {"Edit-AppRoleAssignment", "ModifyRunOnlyUsers"}:
            mutations.add(name)
            _require(observed.status == "Skipped", "A permission mutation was not explicitly skipped")
        if item.connection == "management":
            management.add(name)
            _require(observed.status == "Skipped", "A Management action may have started")
        if item.connection == "broker":
            if item.broker_operation in {"ReserveManagementCall", "RecordManagementCall"}:
                pacing.add(name)
            if name in started_broker:
                _require(item.broker_operation == started_broker[name] and observed.status == "Succeeded"
                         and observed.start_time is not None and observed.end_time is not None,
                         "The reviewed membership and lease acquisition did not succeed")
            else:
                # The generic dynamic business invocation exists in this
                # snapshot, but its whole branch must be explicitly skipped.
                _require(observed.status == "Skipped", "An additional broker action may have started")
        elif item.connection == "makers":
            if name == "Before_add_stage_app":
                _require(item.operation == "Get-AppRoleAssignment" and observed.status in {"Cancelled", "Canceled"}
                         and observed.start_time is not None and observed.end_time is not None,
                         "First permission read does not match the retained cancellation")
            else:
                _require(observed.status == "Skipped", "Another permission action may have started")
    _require(set(started_broker).issubset(actions) and "Before_add_stage_app" in actions,
             "Reviewed acquisition or first-read evidence is missing")
    _require(len(mutations) == 16 and len(management) == 16 and len(pacing) == 32,
             "Permission or Management action inventory does not match the reviewed snapshot")
    _require(actions["Save_membership_add"].end_time <= actions["Acquire_lease_add"].start_time
             <= actions["Acquire_lease_add"].end_time <= actions["Before_add_stage_app"].start_time,
             "Membership, lease and first-read ordering is invalid")
    # Capture time changes at every fresh collection; it is validated above,
    # not included in the semantic approval digest.
    semantic = evidence.model_dump(mode="json", exclude={"collected_at", "source"})
    semantic["actions"] = sorted(semantic["actions"], key=lambda item: item["name"])
    semantic["definition"]["actions"] = sorted(semantic["definition"]["actions"], key=lambda item: item["name"])
    return sha256(json.dumps({"request": request.model_dump(mode="json"), "evidence": semantic},
                             sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _authority_and_binding(state, request, evidence):
    tenant = str(evidence.tenant_id)
    actor_key = principal_key(tenant, evidence.actor_object_id)
    actor = state["users"].get(actor_key)
    _require(state["security"]["tenant_id"] == tenant and actor is not None
             and actor["desired_active"] and actor["access_state"] == "active"
             and actor["role"] in {"ADMIN", "OWNER"}, "Recovery requires a currently active Admin or Owner", 403)
    profile = HISTORICAL["profile_id"]
    _require(state["resources"][profile]["flow_id"] == str(evidence.flow_id), "Bound flow changed")
    broker = state["security"]["brokers"][profile]
    plan = state["sharing_plans"].get(str(request.plan_id))
    _require(plan is not None and plan["plan_id"] == str(request.plan_id)
             and plan["revision"] == str(request.revision) and plan["command_id"] == str(request.command_id),
             "Sharing plan or command binding changed")
    operation = state["operations"].get(str(request.command_id))
    _require(operation is not None and operation["domain"] == "users" and operation["capability"] == "users.manage"
             and operation["profile_id"] == profile and operation["plan_id"] == plan["plan_id"]
             and operation["actor_id"].startswith("entra:" + tenant + ":")
             and operation["actor_id"].removeprefix("entra:") in state["users"],
             "Sharing operation ownership does not match the recovery target")
    key = principal_key(plan["target"]["tenant_id"], plan["target"]["object_id"])
    user = state["users"].get(key)
    execution = plan.get("executions", {}).get(str(request.execution_id))
    _require(user is not None and execution is not None
             and execution["execution_id"] == str(request.execution_id)
             and execution["lease_id"] == str(request.lease_id)
             and execution["plan_id"] == str(request.plan_id)
             and execution["revision"] == str(request.revision)
             and execution["broker_id"] == broker["broker_id"], "Sharing execution binding changed")
    native = execution.get("native_run")
    _require(native is None or native == {"environment_name": evidence.environment,
             "flow_id": str(evidence.flow_id), "run_id": evidence.run_id}, "Stored native run binding conflicts with recovery")
    return "entra:" + actor_key, plan, operation, key, user, execution


def _pending_state(state, request, plan, operation, key, user, execution):
    _require(execution["status"] in {"RUNNING", "UNKNOWN"}, "Sharing execution is not recoverable")
    _require(plan["status"] == "pending" and operation["status"] == "pending"
             and user["access_revision"] == plan["revision"] and user["access_state"] in {"pending", "denied"},
             "Sharing plan is completed, superseded or membership is already active")
    held = state.get("sharing_leases", {}).get(key)
    _require(held == execution, "Recovery does not own the current sharing lease")
    pacing = state.get("management_pacing", {})
    _require(pacing.get("active") is None, "Management connection still holds a permit")
    _require(not any(reservation["lease_id"] == str(request.lease_id)
                     for reservation in pacing.get("reservations", {}).values()),
             "Recorded Management activity contradicts canceled-before-mutation evidence")


def _summary(state, request, evidence, digest, *, trusted):
    return {"changed": False, "eligible": True, "trusted_live_collection": trusted,
            "control_revision": state["revision"], "evidence_digest": digest,
            "collected_at": evidence.collected_at.isoformat(), "reason": REASON,
            "plan_id": str(request.plan_id), "execution_id": str(request.execution_id),
            "lease_id": str(request.lease_id), "run_id": evidence.run_id,
            "transition": "Close canceled execution and release its lease; preserve pending membership, plan and command"}


def preview_captured_evidence(state, request, evidence, *, now=None):
    """Read-only qualification. Never returns an apply-capable collector."""
    request, evidence = _parse(request, evidence)
    digest = _qualify_evidence(request, evidence, now or datetime.now(timezone.utc))
    _, plan, operation, key, user, execution = _authority_and_binding(state, request, evidence)
    _pending_state(state, request, plan, operation, key, user, execution)
    return _summary(state, request, evidence, digest, trusted=False)


class RecoveryService:
    def __init__(self, store, collector: NativeRecoveryCollector, *, clock=None):
        if not isinstance(collector, NativeRecoveryCollector):
            raise TypeError("Recovery requires a trusted live collector implementation")
        self.store, self.collector = store, collector
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _collect(self, request):
        try:
            request, evidence = _parse(request, self.collector.collect())
        except ControlError:
            raise
        except Exception:
            raise ControlError(503, "Fresh authenticated recovery collection failed") from None
        _require(evidence.source == "native-sharing-recovery-metadata",
                 "Offline evidence cannot authorize a recovery transition", 403)
        return request, evidence

    def preview(self, request):
        request, evidence = self._collect(request)
        digest = _qualify_evidence(request, evidence, self.clock())
        state = self.store.read()
        _, plan, operation, key, user, execution = _authority_and_binding(state, request, evidence)
        _pending_state(state, request, plan, operation, key, user, execution)
        return _summary(state, request, evidence, digest, trusted=True)

    def apply(self, request, *, expected_revision, evidence_digest):
        try:
            expected_revision = str(UUID(str(expected_revision)))
        except (TypeError, ValueError, AttributeError):
            raise ControlError(422, "Recovery apply requires the exact preview control revision") from None
        _require(isinstance(evidence_digest, str) and len(evidence_digest) == 64
                 and all(char in "0123456789abcdef" for char in evidence_digest),
                 "Recovery apply requires the exact preview evidence digest", 422)
        request, evidence = self._collect(request)
        digest = _qualify_evidence(request, evidence, self.clock())
        _require(digest == evidence_digest, "Recovery evidence changed; obtain a new preview")

        def inspect(state):
            actor, plan, operation, key, user, execution = _authority_and_binding(state, request, evidence)
            recorded = execution.get("recovery")
            if execution["status"] == "CLOSED":
                _require(recorded is not None and recorded["evidence_digest"] == digest
                         and recorded["preview_control_revision"] == str(expected_revision),
                         "Sharing execution was already closed with another outcome")
                return deepcopy(recorded["result"]), None
            _pending_state(state, request, plan, operation, key, user, execution)
            return None, (actor, plan, key, user, execution)

        # Identical replay does not rotate the control revision or append audit.
        replay, _ = inspect(self.store.read())
        if replay is not None:
            return replay

        def transition(state):
            _qualify_evidence(request, evidence, self.clock())
            replay, details = inspect(state)
            if replay is not None:
                return replay
            actor, plan, key, user, execution = details
            result = {"changed": True, "status": "CLOSED", "reason": REASON,
                      "plan_id": str(request.plan_id), "execution_id": str(request.execution_id),
                      "lease_id": str(request.lease_id), "command_id": str(request.command_id),
                      "evidence_digest": digest, "plan_status": plan["status"], "membership_state": user["access_state"]}
            execution["status"] = "CLOSED"
            # Prefix distinguishes this transition from every broker callback
            # digest, so a late callback cannot overwrite recovered history.
            execution["result_digest"] = "host-recovery:" + digest
            execution["recovery"] = {"reason": REASON, "evidence_digest": digest,
                "preview_control_revision": str(expected_revision), "collected_at": evidence.collected_at.isoformat(),
                "recovered_at": self.clock().isoformat(), "actor_id": actor,
                "native_run": {"environment_name": evidence.environment, "flow_id": str(evidence.flow_id), "run_id": evidence.run_id},
                "historical_mapping_provenance": PROVENANCE, "definition_sha256": evidence.definition.sha256,
                "result": deepcopy(result)}
            del state["sharing_leases"][key]
            append_audit(state, "SHARING_EXECUTION_HOST_RECOVERED", actor,
                         plan_id=str(request.plan_id), execution_id=str(request.execution_id),
                         lease_id=str(request.lease_id), native_run_id=evidence.run_id,
                         reason=REASON, evidence_digest=digest, collected_at=evidence.collected_at.isoformat())
            return result

        return self.store.mutate(transition, expected_revision=expected_revision)
