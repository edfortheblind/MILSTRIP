"""Host-only Ed bootstrap from reviewed native permission captures.

The host administrator supplies authenticated readbacks; this module does not
authenticate JSON files or contact Microsoft. It derives the four observations
from their native records and records host provenance, never a flow callback.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from .control import ControlError, append_audit, principal_key
from .control_bootstrap import APP_IDS, SEED_ROLES, SEED_UPNS


ED_OBJECT_ID = "87cf5ad7-422d-4c31-b8b9-df645ee64a4d"
APP_CAPTURE = "ed-app-permissions-current.json"
FLOW_CAPTURE = "ed-flow-permissions-after.json"
MAX_AGE = timedelta(hours=1)


def _require(condition, message="Native bootstrap permission evidence is invalid"):
    if not condition:
        raise ControlError(422, message)


def _time(value, now):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0)
    _require(now - MAX_AGE <= parsed <= now + timedelta(seconds=30),
             "Refresh the authenticated permission captures before bootstrap acceptance")
    return parsed.isoformat()


def _read_private_json(path, store, filename, now, *, fresh=True):
    path = Path(path).absolute()
    _require(path.name == filename and path.parent == store.path.parent
             and not path.is_symlink(), "Bootstrap evidence must use the named files in the private control directory")
    with path.open("rb") as stream:
        raw = stream.read(1_048_577)
        _require(len(raw) <= 1_048_576)
        file_written_at = datetime.fromtimestamp(os.fstat(stream.fileno()).st_mtime, timezone.utc).isoformat()
    if fresh:
        _time(file_written_at, now)
    value = json.loads(raw.decode("utf-8-sig"))
    return value, {"file": filename, "sha256": sha256(raw).hexdigest(), "file_written_at": file_written_at}


def _read_capture(path, store, filename, now):
    value, evidence = _read_private_json(path, store, filename, now)
    _require(isinstance(value, list) and len(value) == 2 and all(isinstance(item, dict) for item in value))
    return value, evidence


def _observations(state, apps, flows, now, *, object_id=ED_OBJECT_ID, app_role="Owner", flow_timestamps=False):
    tenant = state["security"]["tenant_id"]
    environment = "Default-" + tenant
    expected_apps = {value["app_id"] for value in state["resources"].values()}
    expected_flows = {value["flow_id"] for value in state["resources"].values()}
    _require(expected_apps == set(APP_IDS.values()))
    _require({item["app_id"] for item in apps} == expected_apps)
    _require({item["flow_id"] for item in flows} == expected_flows)
    observations = {}
    verified_at = {}
    for item in apps:
        app_id = item["app_id"]
        _require(item["environment_name"] == environment)
        assignment = item["assignment"]
        properties = assignment["properties"]
        principal = properties["principal"]
        _require(principal["id"] == object_id and principal["type"] == "User"
                 and principal["tenantId"] == tenant and properties["roleName"] == app_role)
        _require(assignment["id"] == f"/providers/Microsoft.PowerApps/apps/{app_id}/permissions/{object_id}"
                 and assignment["name"] == object_id and assignment["type"] == "Microsoft.PowerApps/apps/permissions",
                 "Native app permission does not belong to the selected app")
        verified_at[app_id] = _time(item["verified_at"], now)
        observations["app|" + app_id] = {"kind": "app", "resource_id": app_id,
            "permission": "CanView", "present": True, "verified": True, "native_role": app_role}
    for item in flows:
        flow_id = item["flow_id"]
        # The native users endpoint has no roleName: CanRun. Ignore the earlier
        # capture's erroneous run_only_present boolean and its owners collection.
        _require(isinstance(item["users"], list))
        matches = [row for row in item["users"] if row.get("properties", {}).get("principal", {}).get("id") == object_id]
        _require(len(matches) == 1, "Exactly one native run-only entry is required for the selected member on each flow")
        row = matches[0]
        properties = row["properties"]
        principal = properties["principal"]
        expected_id = f"/providers/Microsoft.ProcessSimple/environments/{environment}/flows/{flow_id}/users/{object_id}"
        _require(row["id"] == expected_id and row["type"] == "/providers/Microsoft.ProcessSimple/environments/flows/users"
                 and properties["permissionType"] == "Principal" and principal["type"] == "User"
                 and principal["tenantId"] == tenant)
        if flow_timestamps:
            _require(item["environment_name"] == environment and not item.get("next_link"))
            verified_at[flow_id] = _time(item["verified_at"], now)
        observations["flow|" + flow_id] = {"kind": "flow", "resource_id": flow_id,
            "permission": "run-only", "present": True, "verified": True}
    return observations, verified_at


def accept_bootstrap_member(store, expected_revision, app_capture, flow_capture, *, apply=False, clock=None):
    """Preview by default; explicit apply accepts only the initial Ed membership."""
    now = clock() if clock else datetime.now(timezone.utc)
    try:
        UUID(str(expected_revision))
        apps, app_source = _read_capture(app_capture, store, APP_CAPTURE, now)
        flows, flow_source = _read_capture(flow_capture, store, FLOW_CAPTURE, now)

        def verify(state):
            _require(state["security"]["enforced"] is False and state["runtime"].get("active") is False,
                     "Bootstrap acceptance is closed after control activation")
            _require(len(state["users"]) == 6 and {u["upn"].casefold() for u in state["users"].values()} == set(SEED_UPNS.values()),
                     "Bootstrap acceptance requires the unchanged six-person seed")
            for name, upn in SEED_UPNS.items():
                member = next(u for u in state["users"].values() if u["upn"].casefold() == upn)
                _require(member["role"] == SEED_ROLES[name] and member["desired_active"] is True
                         and member["access_state"] == "pending", "Bootstrap acceptance requires six pending seed memberships")
            key = principal_key(state["security"]["tenant_id"], ED_OBJECT_ID)
            user = state["users"].get(key)
            _require(user is not None and user["upn"].casefold() == SEED_UPNS["Ed Lopez"] and user["role"] == "ADMIN",
                     "Only the verified Ed deployment identity can be accepted")
            plans = [plan for plan in state["sharing_plans"].values()
                     if plan["target"] == {"tenant_id": user["tenant_id"], "object_id": ED_OBJECT_ID}
                     and plan["revision"] == user["access_revision"]]
            _require(len(plans) == 1)
            plan = plans[0]
            _require(plan["status"] == "pending" and not plan.get("executions")
                     and not plan.get("observations") and plan["command_id"] not in state["operations"],
                     "Only an untouched current bootstrap plan can be accepted")
            _require(not state.get("sharing_leases") and state.get("management_pacing", {}).get("active") is None,
                     "Finish or recover outstanding sharing and management operations first")
            observations, verified_at = _observations(state, apps, flows, now)
            expected = {(item["kind"], item["resource_id"], item["permission"], item["environment"], item["present"])
                        for item in plan["resources"]}
            required = {(kind, resource[kind + "_id"], permission, profile, True)
                        for profile, resource in state["resources"].items()
                        for kind, permission in (("app", "CanView"), ("flow", "run-only"))}
            _require(len(plan["resources"]) == 4 and expected == required)
            evidence = [{**app_source, "native_verified_at": verified_at}, flow_source]
            if apply:
                user["access_state"] = "active"
                plan.update(status="completed", error_code=None, observations=observations,
                            host_acceptance={"at": now.isoformat(), "evidence": evidence})
                state["acl_revision"] = str(uuid4())
                append_audit(state, "HOST_BOOTSTRAP_ACCESS_VERIFIED", "host-administrator", target_id=key,
                             plan_id=plan["plan_id"], evidence=evidence)
            return {"changed": apply, "membership": "active" if apply else "pending", "reviewed_resources": 4,
                    "security_enforced": False, "runtime_active": False,
                    "evidence_sha256": {item["file"]: item["sha256"] for item in evidence}}

        if apply:
            return store.mutate(verify, expected_revision=expected_revision)
        state = store.read()
        if state["revision"] != str(expected_revision):
            raise ControlError(409, "Administration revision changed; reload")
        return verify(state)
    except ControlError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        raise ControlError(422, "Bootstrap evidence or pending seed state is invalid; inspect the private readbacks") from None
