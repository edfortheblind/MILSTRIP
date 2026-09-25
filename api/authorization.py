"""Object-ID authorization and bounded platform-sharing reconciliation."""
from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import uuid4

from .control import ControlStore, append_audit, principal_key


class AuthorizationError(Exception):
    def __init__(self, status_code, message):
        self.status_code, self.message = status_code, message
        super().__init__(message)


ROLE_CAPABILITIES = {"OWNER": frozenset({"business", "users.manage", "runtime.configure"}),
                     "ADMIN": frozenset({"business", "users.manage", "runtime.configure"}),
                     "OPERATOR": frozenset({"business"})}


@dataclass(frozen=True)
class VerifiedPrincipal:
    tenant_id: str
    object_id: str
    upn: str
    display_name: str
    role: str
    capabilities: frozenset


@dataclass(frozen=True)
class BrokerContext:
    principal: VerifiedPrincipal
    profile_id: str
    broker_id: str
    request_id: str

    @property
    def tenant_id(self):
        return self.principal.tenant_id

    @property
    def object_id(self):
        return self.principal.object_id

    @property
    def actor_id(self):
        return "entra:" + principal_key(self.tenant_id, self.object_id)


def _directory_person(state, actor):
    domain = state["security"]["allowed_domain"]
    if (not actor.account_enabled or actor.user_type != "Member" or "#ext#" in actor.upn.casefold()
            or actor.upn.count("@") != 1 or actor.upn.rsplit("@", 1)[1].casefold() != domain):
        raise AuthorizationError(403, "An enabled internal directory member is required")


def _authorized(state, context, capability=None):
    if context.tenant_id != state["security"]["tenant_id"]:
        raise AuthorizationError(403, "Tenant is not authorized")
    user = state["users"].get(principal_key(context.tenant_id, context.object_id))
    if (user is None or not user["desired_active"] or user["access_state"] != "active"
            or user["upn"].casefold() != context.principal.upn.casefold()):
        raise AuthorizationError(403, "User access is not active")
    capabilities = ROLE_CAPABILITIES[user["role"]]
    if capability and capability not in capabilities:
        raise AuthorizationError(403, "Operation is not permitted for this user")
    return VerifiedPrincipal(user["tenant_id"], user["object_id"], user["upn"], user["display_name"], user["role"], capabilities)


def authorize(context, capability=None, store=None):
    return _authorized((store or ControlStore()).read(), context, capability)


def authorize_person(binding, actor, request_id, store=None):
    state = (store or ControlStore()).read()
    _directory_person(state, actor)
    principal = VerifiedPrincipal(binding["tenant_id"], str(actor.object_id), actor.upn,
                                  actor.display_name, "", frozenset())
    context = BrokerContext(principal, binding["profile_id"], binding["broker_id"], str(request_id))
    verified = _authorized(state, context)
    return BrokerContext(verified, context.profile_id, context.broker_id, context.request_id)


def public_user(user):
    return {field: user[field] for field in ("tenant_id", "object_id", "upn", "display_name", "role", "desired_active", "access_state")}


def current_user(context, store=None):
    principal = authorize(context, store=store)
    return {"tenant_id": principal.tenant_id, "object_id": principal.object_id, "upn": principal.upn,
            "display_name": principal.display_name, "role": principal.role,
            "capabilities": sorted(principal.capabilities), "environment": context.profile_id}


def list_users(context, store=None):
    state = (store or ControlStore()).read()
    _authorized(state, context, "users.manage")
    return {"revision": state["acl_revision"], "items": [public_user(user) for user in state["users"].values()]}


def sharing_plan(state, target, desired_active, command_id):
    revision = str(uuid4())
    resources = []
    for environment, resource in state["resources"].items():
        for kind, permission in (("app", "CanView"), ("flow", "run-only")):
            resources.append({"kind": kind, "environment": environment, "resource_id": resource[kind + "_id"],
                              "permission": permission, "present": desired_active})
    return {"plan_id": str(uuid4()), "revision": revision, "command_id": command_id,
            "target": {"tenant_id": target["tenant_id"], "object_id": target["object_id"]},
            "resources": resources, "observations": {}, "status": "pending", "error_code": None}


def public_plan(plan):
    return {key: plan[key] for key in ("plan_id", "revision", "target", "resources", "status", "error_code")}


def save_user_access(context, command, store=None):
    store = store or ControlStore()
    digest = sha256(command.model_dump_json().encode()).hexdigest()

    def change(state):
        _authorized(state, context, "users.manage")
        command_id = str(command.command_id)
        previous = state["operations"].get(command_id)
        if previous:
            if (previous["domain"], previous["actor_id"], previous["payload_digest"]) != ("users", context.actor_id, digest):
                raise AuthorizationError(409, "Command ID was already used with different content")
            plan = state["sharing_plans"][previous["plan_id"]]
            key = principal_key(plan["target"]["tenant_id"], plan["target"]["object_id"])
            user = state["users"][key]
            if user["access_revision"] != plan["revision"]:
                latest = next(item for item in state["sharing_plans"].values()
                              if item["revision"] == user["access_revision"] and item["target"] == plan["target"])
                return {**previous["result"], "sharing_plan": public_plan(latest),
                        "membership": public_user(user), "superseded": True}
            return {**previous["result"], "sharing_plan": public_plan(plan)}
        if state["acl_revision"] != str(command.expected_revision):
            raise AuthorizationError(409, "User revision changed; reload users")
        if command.active:
            _directory_person(state, command.target)
            key = principal_key(context.tenant_id, command.target.object_id)
            target = {"tenant_id": context.tenant_id, "object_id": str(command.target.object_id), "upn": command.target.upn,
                      "display_name": command.target.display_name}
        else:
            # Removal must remain possible after directory disablement/deletion.
            # Only a currently stored member can be selected by this path.
            matches = [(key, user) for key, user in state["users"].items()
                       if user["tenant_id"] == context.tenant_id and (
                           user["upn"].casefold() == command.target_upn.casefold() if command.target_upn is not None
                           else user["object_id"] == str(command.target.object_id) and user["upn"].casefold() == command.target.upn.casefold())]
            if len(matches) != 1:
                raise AuthorizationError(404, "Existing member was not found")
            key, existing = matches[0]
            target = {field: existing[field] for field in ("tenant_id", "object_id", "upn", "display_name")}
        if key in state["protected_owners"]:
            raise AuthorizationError(403, "Protected owners cannot be changed")
        if key == principal_key(context.tenant_id, context.object_id):
            # Reconciliation requires its original actor to remain active.
            # Even saving the same role would otherwise put this actor pending.
            raise AuthorizationError(403, "You cannot change your own access; ask another Admin or Owner to make this change")
        target.update(role=command.role, desired_active=command.active, access_state="pending" if command.active else "denied")
        # A changed membership is never active until its exact sharing plan has
        # been read back. Disables become denied before any platform action.
        plan = sharing_plan(state, target, command.active, command_id)
        target["access_revision"] = plan["revision"]
        state["users"][key] = target
        state["sharing_plans"][plan["plan_id"]] = plan
        state["acl_revision"] = str(uuid4())
        result = {"operation_id": command_id, "acl_revision": state["acl_revision"],
                  "sharing_plan": public_plan(plan), "membership": public_user(target)}
        state["operations"][command_id] = {"domain": "users", "capability": "users.manage", "actor_id": context.actor_id,
                                           "profile_id": context.profile_id, "payload_digest": digest, "plan_id": plan["plan_id"],
                                           "status": "pending", "result": result}
        append_audit(state, "USER_ACCESS_REQUESTED", context.actor_id, operation_id=command_id, target_id=key,
                     role=command.role, desired_active=command.active, broker_id=context.broker_id)
        return result
    return store.mutate(change)


def _sharing_context(state, binding, command):
    expected_binding = state["security"]["brokers"].get(binding.get("profile_id"))
    if (expected_binding is None or any(binding.get(key) != expected_binding[key]
            for key in ("broker_id", "profile_id", "tenant_id"))):
        raise AuthorizationError(403, "Sharing broker is not authorized")
    plan = state["sharing_plans"].get(str(command.plan_id))
    if plan is None:
        raise AuthorizationError(404, "Sharing plan not found")
    if plan["revision"] != str(command.revision):
        raise AuthorizationError(409, "Sharing plan revision changed")
    key = principal_key(plan["target"]["tenant_id"], plan["target"]["object_id"])
    return plan, key, state["users"][key]


def _sharing_response(state, plan, user):
    result = {"sharing_plan": public_plan(plan), "membership": public_user(user)}
    if user["access_revision"] != plan["revision"]:
        latest = next((item for item in state["sharing_plans"].values()
                       if item["revision"] == user["access_revision"] and item["target"] == plan["target"]), None)
        if latest is not None:
            result["latest_sharing_plan"] = public_plan(latest)
    return result


def _sharing_operation(state, plan, user):
    operation = state["operations"].get(plan["command_id"])
    if operation:
        operation["status"] = plan["status"]
        operation["result"].update(sharing_plan=public_plan(plan), membership=public_user(user))


def acquire_sharing_lease(binding, command, store=None):
    """Serialize every external grant sequence for one directory identity.

    The durable lease has no expiry: an unknown in-flight platform call cannot
    be fenced by this API. A trusted completion callback must close it first.
    """
    store = store or ControlStore()

    def change(state):
        plan, key, user = _sharing_context(state, binding, command)
        if user["access_revision"] != plan["revision"]:
            raise AuthorizationError(409, "Sharing plan was superseded; reconcile the latest request")
        if plan["status"] == "completed":
            raise AuthorizationError(409, "Sharing plan is completed; inspect its recorded outcome")
        executions = plan.setdefault("executions", {})
        execution_id = str(command.execution_id)
        native_run = command.native_run.model_dump(mode="json") if command.native_run else None
        if native_run is not None and (
                native_run["flow_id"] != state["resources"][binding["profile_id"]]["flow_id"]
                or native_run["environment_name"] != "Default-" + state["security"]["tenant_id"]):
            raise AuthorizationError(422, "Native sharing run does not match the bound flow and environment")
        previous = executions.get(execution_id)
        leases = state.setdefault("sharing_leases", {})
        held = leases.get(key)
        if previous is not None:
            if (previous["broker_id"] != binding["broker_id"] or previous["status"] != "RUNNING"
                    or held is None or held["lease_id"] != previous["lease_id"]
                    or previous.get("native_run") != native_run):
                raise AuthorizationError(409, "This sharing execution cannot restart; inspect its recorded outcome")
            return {"lease_id": previous["lease_id"], "execution_id": execution_id, "sharing_plan": public_plan(plan)}
        if held is not None:
            raise AuthorizationError(409, "An earlier sharing execution must finish or be recovered before reconciliation")
        lease = {"lease_id": str(uuid4()), "execution_id": execution_id, "plan_id": plan["plan_id"],
                 "revision": plan["revision"], "broker_id": binding["broker_id"], "status": "RUNNING"}
        if native_run is not None:
            lease["native_run"] = native_run
        leases[key] = lease
        executions[execution_id] = dict(lease)
        # Every attempt must read back all four grants; do not combine stale
        # observations from separate platform executions.
        plan["observations"] = {}
        plan["error_code"] = None
        append_audit(state, "SHARING_LEASE_ACQUIRED", "broker:" + binding["broker_id"],
                     plan_id=plan["plan_id"], execution_id=execution_id, target_id=key)
        return {"lease_id": lease["lease_id"], "execution_id": execution_id, "sharing_plan": public_plan(plan)}
    return store.mutate(change)


def record_sharing_result(binding, command, store=None):
    """Close a broker-owned external execution, never an unleased readback."""
    store = store or ControlStore()

    def change(state):
        plan, key, user = _sharing_context(state, binding, command)
        execution = plan.get("executions", {}).get(str(command.execution_id))
        if (execution is None or execution["lease_id"] != str(command.lease_id)
                or execution["broker_id"] != binding["broker_id"]):
            raise AuthorizationError(409, "Sharing callback does not own the execution lease")
        digest = sha256(command.model_dump_json().encode()).hexdigest()
        if execution["status"] == "CLOSED":
            if execution.get("result_digest") != digest:
                raise AuthorizationError(409, "Sharing execution already closed with a different outcome")
            return _sharing_response(state, plan, user)
        lease = state.setdefault("sharing_leases", {}).get(key)
        if lease is None or lease["lease_id"] != str(command.lease_id):
            raise AuthorizationError(409, "Sharing callback does not hold the target lease")
        pacing = state.get("management_pacing", {})
        management_call = pacing.get("reservations", {}).get(pacing.get("active"))
        if (command.external_calls_complete and management_call is not None
                and management_call["lease_id"] == str(command.lease_id)):
            raise AuthorizationError(409, "Management call must finish before the sharing execution can close")
        expected = {(item["kind"], item["resource_id"]): item for item in plan["resources"]}
        seen = set()
        observations = {}
        for observed in command.observations:
            resource_key = (observed.kind, str(observed.resource_id))
            item = expected.get(resource_key)
            if item is None or item["permission"] != observed.permission or resource_key in seen:
                raise AuthorizationError(422, "Readback does not match the authorized sharing plan")
            seen.add(resource_key)
            observations["|".join(resource_key)] = observed.model_dump(mode="json")
        plan["observations"] = observations
        if not command.external_calls_complete:
            lease["status"] = execution["status"] = "UNKNOWN"
            plan["error_code"] = "PLATFORM_OUTCOME_UNKNOWN"
            plan["status"] = "pending"
            _sharing_operation(state, plan, user)
            append_audit(state, "SHARING_EXECUTION_UNKNOWN", "broker:" + binding["broker_id"],
                         plan_id=plan["plan_id"], execution_id=str(command.execution_id), target_id=key)
            return _sharing_response(state, plan, user)
        execution["status"] = "CLOSED"
        execution["result_digest"] = digest
        del state["sharing_leases"][key]
        if user["access_revision"] != plan["revision"]:
            plan["status"] = "superseded"
            plan["error_code"] = None
            _sharing_operation(state, plan, user)
            append_audit(state, "SHARING_EXECUTION_SUPERSEDED", "broker:" + binding["broker_id"],
                         plan_id=plan["plan_id"], execution_id=str(command.execution_id), target_id=key)
            return _sharing_response(state, plan, user)
        complete = all((observation := observations.get("|".join(resource_key)))
                       and observation["verified"] and observation["present"] == item["present"]
                       for resource_key, item in expected.items())
        plan["error_code"] = command.error_code
        plan["status"] = "completed" if complete else "pending"
        if complete:
            user["access_state"] = "active" if user["desired_active"] else "denied"
            state["acl_revision"] = str(uuid4())
            plan["error_code"] = None
        _sharing_operation(state, plan, user)
        append_audit(state, "SHARING_RECONCILED", "broker:" + binding["broker_id"], plan_id=plan["plan_id"],
                     target_id=key, status=plan["status"], error_code=plan["error_code"])
        return {"sharing_plan": public_plan(plan), "membership": public_user(user)}
    return store.mutate(change)


def administration_operation(context, operation_id, store=None):
    state = (store or ControlStore()).read()
    principal = _authorized(state, context)
    operation = state["operations"].get(str(operation_id))
    if operation is None:
        raise AuthorizationError(404, "Administration operation not found")
    if operation["domain"] == "runtime" and operation["profile_id"] != context.profile_id:
        raise AuthorizationError(403, "Runtime operation belongs to another environment")
    if operation["actor_id"] != context.actor_id and operation["capability"] not in principal.capabilities:
        raise AuthorizationError(403, "Administration operation is not visible to this user")
    return {"operation_id": str(operation_id), "status": operation["status"], "result": operation["result"]}
