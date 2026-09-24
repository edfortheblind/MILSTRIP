"""Host-only initial acceptance of the two immutable application Owners.

These users remain ordinary CanView/run-only users on the platform. This module
never grants permissions, invokes a broker callback, or enables security cutover.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .bootstrap_acceptance import _observations, _read_capture, _read_private_json, _require
from .control import ControlError, append_audit, principal_key
from .control_bootstrap import SEED_UPNS, bootstrap_state


OWNER_FILES = {"Claude Furry": "claude-furry", "Mike Thompson": "mike-thompson"}
MANIFEST_FILE = "bootstrap-verified.json"


def _context(state, manifest, owner_name):
    _require(owner_name in OWNER_FILES, "Only the two approved protected Owners use this bootstrap path")
    _require(state["security"]["enforced"] is False and state["runtime"].get("active") is False,
             "Bootstrap acceptance is closed after control activation")
    seed = bootstrap_state(manifest, state["security"]["legacy_usernames"])
    _require(state["security"]["tenant_id"] == seed["security"]["tenant_id"]
             and state["resources"] == seed["resources"] and set(state["users"]) == set(seed["users"])
             and set(state["protected_owners"]) == set(seed["protected_owners"]),
             "The reviewed directory manifest must match the original six-person seed and fixed resources")
    for key, original in seed["users"].items():
        current = state["users"][key]
        _require(all(current[field] == original[field] for field in
                     ("tenant_id", "object_id", "upn", "display_name", "role", "desired_active"))
                 and current["access_state"] in {"pending", "active"},
                 "Seed identity or role changed; this bootstrap path cannot reconcile it")
    selected = next(member for member in state["users"].values()
                    if member["upn"].casefold() == SEED_UPNS[owner_name])
    key = principal_key(selected["tenant_id"], selected["object_id"])
    _require(key in state["protected_owners"] and selected["role"] == "OWNER"
             and selected["access_state"] == "pending", "Only the pending protected Owner can be accepted")
    plans = [plan for plan in state["sharing_plans"].values()
             if plan["target"] == {"tenant_id": selected["tenant_id"], "object_id": selected["object_id"]}
             and plan["revision"] == selected["access_revision"]]
    _require(len(plans) == 1)
    plan = plans[0]
    _require(plan["status"] == "pending" and not plan.get("executions") and not plan.get("observations")
             and plan["command_id"] not in state["operations"], "Only an untouched current bootstrap plan can be accepted")
    _require(not state.get("sharing_leases") and state.get("management_pacing", {}).get("active") is None,
             "Finish or recover outstanding sharing and management operations first")
    expected = {(item["kind"], item["resource_id"], item["permission"], item["environment"], item["present"])
                for item in plan["resources"]}
    required = {(kind, resource[kind + "_id"], permission, profile, True)
                for profile, resource in state["resources"].items()
                for kind, permission in (("app", "CanView"), ("flow", "run-only"))}
    _require(len(plan["resources"]) == 4 and expected == required)
    return key, selected, plan


def owner_capture_spec(store, owner_name):
    """Read-only, fixed-resource input for the host's native capture script."""
    try:
        manifest, _ = _read_private_json(store.path.parent / MANIFEST_FILE, store, MANIFEST_FILE,
                                         datetime.now(timezone.utc), fresh=False)
        state = store.read()
        _, selected, _ = _context(state, manifest, owner_name)
        stem = OWNER_FILES[owner_name]
        return {"owner_name": owner_name, "object_id": selected["object_id"], "tenant_id": selected["tenant_id"],
                "environment_name": "Default-" + selected["tenant_id"], "resources": state["resources"],
                "app_capture": str(store.path.parent / (stem + "-app-permissions.json")),
                "flow_capture": str(store.path.parent / (stem + "-flow-permissions.json"))}
    except ControlError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        raise ControlError(422, "Reviewed Owner seed state is invalid; inspect the private manifest") from None


def accept_bootstrap_owner(store, expected_revision, owner_name, *, apply=False, clock=None):
    """Accept one protected Owner after reviewing exactly four native grants."""
    now = clock() if clock else datetime.now(timezone.utc)
    try:
        _require(owner_name in OWNER_FILES, "Only the two approved protected Owners use this bootstrap path")
        UUID(str(expected_revision))
        manifest, manifest_source = _read_private_json(store.path.parent / MANIFEST_FILE, store, MANIFEST_FILE,
                                                       now, fresh=False)
        stem = OWNER_FILES[owner_name]
        app_file, flow_file = stem + "-app-permissions.json", stem + "-flow-permissions.json"
        apps, app_source = _read_capture(store.path.parent / app_file, store, app_file, now)
        flows, flow_source = _read_capture(store.path.parent / flow_file, store, flow_file, now)

        def verify(state):
            key, selected, plan = _context(state, manifest, owner_name)
            observations, timestamps = _observations(state, apps, flows, now, object_id=selected["object_id"],
                                                      app_role="CanView", flow_timestamps=True)
            evidence = [manifest_source, {**app_source, "native_verified_at": {item["app_id"]: timestamps[item["app_id"]] for item in apps}},
                        {**flow_source, "native_verified_at": {item["flow_id"]: timestamps[item["flow_id"]] for item in flows}}]
            if apply:
                selected["access_state"] = "active"
                plan.update(status="completed", error_code=None, observations=observations,
                            host_acceptance={"at": now.isoformat(), "evidence": evidence})
                state["acl_revision"] = str(uuid4())
                append_audit(state, "HOST_BOOTSTRAP_OWNER_VERIFIED", "host-administrator", target_id=key,
                             plan_id=plan["plan_id"], evidence=evidence)
            return {"changed": apply, "owner_name": owner_name, "membership": "active" if apply else "pending",
                    "role": "OWNER", "reviewed_resources": 4, "security_enforced": False, "runtime_active": False,
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
        raise ControlError(422, "Protected Owner evidence or pending seed state is invalid; inspect the private readbacks") from None
