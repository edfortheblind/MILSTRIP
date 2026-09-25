"""Explicit host-administrator bootstrap from verified directory readback."""
from uuid import UUID, uuid4
from pydantic import ValidationError

from api.authorization import sharing_plan
from api.broker_models import DirectoryPerson
from api.control import ControlError, append_audit, principal_key
from api.persistence import open_repository


SEED_ROLES = {"Claude Furry": "OWNER", "Mike Thompson": "OWNER", "Ed Lopez": "ADMIN",
              "Kristen Fleming": "ADMIN", "Thomas Stivers": "ADMIN", "Shawn Hinkle": "ADMIN"}
SEED_UPNS = {"Claude Furry": "claude.furry@austinlighthouse.org", "Mike Thompson": "mike.thompson@austinlighthouse.org",
             "Ed Lopez": "ed.lopez@austinlighthouse.org", "Kristen Fleming": "kristen.fleming@austinlighthouse.org",
             "Thomas Stivers": "thomas.stivers@austinlighthouse.org", "Shawn Hinkle": "shawn.hinkle@austinlighthouse.org"}
APP_IDS = {"stage": "7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82", "prod": "0aa02d8b-c7fa-42cc-87e8-6d287bd4c897"}


def bootstrap_state(manifest, legacy_usernames):
    """Input is an administrator-reviewed directory export, not canvas data.

    The caller must obtain tenant/object IDs from the real tenant. This function
    validates the export's shape and approved identity mapping; it does not
    claim to contact Microsoft or authenticate the export independently.
    """
    try:
        if (manifest["schema_version"] != 1 or manifest["source"] != "verified-tenant-directory-export"
                or set(manifest["resources"]) != {"stage", "prod"}):
            raise ValueError
        tenant = str(UUID(manifest["tenant_id"]))
        members = manifest["members"]
        if len(members) != 6 or {m["seed_name"] for m in members} != set(SEED_ROLES):
            raise ValueError
        resources = {}
        for profile, value in manifest["resources"].items():
            if str(UUID(value["app_id"])) != APP_IDS[profile]:
                raise ValueError
            resources[profile] = {"app_id": APP_IDS[profile], "flow_id": str(UUID(value["flow_id"]))}
        if resources["stage"]["flow_id"] == resources["prod"]["flow_id"]:
            raise ValueError
        state = {"version": 1, "revision": str(uuid4()), "acl_revision": str(uuid4()),
                 "security": {"enforced": False, "tenant_id": tenant, "allowed_domain": "austinlighthouse.org",
                     "legacy_usernames": list(legacy_usernames), "brokers": {
                         p: {"broker_id": "milstrip-" + p + "-broker", "profile_id": p, "tenant_id": tenant,
                             "credential_file": "broker-" + p + "-credential.json"} for p in ("stage", "prod")}},
                 "resources": resources, "users": {}, "protected_owners": [], "sharing_plans": {}, "sharing_leases": {}, "operations": {},
                 "audit": [], "runtime": {"active": False, "profiles": {}, "drafts": {}, "tests": {}}}
        upns = set()
        for member in members:
            person = DirectoryPerson.model_validate(member["directory"])
            if (str(UUID(member["verified_tenant_id"])) != tenant or not person.account_enabled or person.user_type != "Member"
                    or person.upn.casefold() != member["expected_upn"].casefold()
                    or person.upn.count("@") != 1 or person.upn.rsplit("@", 1)[1].casefold() != "austinlighthouse.org"
                    or "#ext#" in person.upn.casefold()):
                raise ValueError
            if person.upn.casefold() != SEED_UPNS[member["seed_name"]]:
                raise ValueError
            key = principal_key(tenant, person.object_id)
            if key in state["users"] or person.upn.casefold() in upns:
                raise ValueError
            upns.add(person.upn.casefold())
            user = {"tenant_id": tenant, "object_id": str(person.object_id), "upn": person.upn,
                    "display_name": person.display_name, "role": SEED_ROLES[member["seed_name"]],
                    "desired_active": True, "access_state": "pending"}
            command_id = str(uuid4())
            plan = sharing_plan(state, user, True, command_id)
            user["access_revision"] = plan["revision"]
            state["users"][key] = user
            state["sharing_plans"][plan["plan_id"]] = plan
            if user["role"] == "OWNER":
                state["protected_owners"].append(key)
        append_audit(state, "CONTROL_BOOTSTRAPPED", "host-administrator", seeded_members=6, security_enforced=False)
        return state
    except (KeyError, TypeError, ValueError, ValidationError):
        raise ControlError(422, "Bootstrap requires the reviewed six-person directory manifest and fixed resources") from None


def enforce_security(store, expected_revision):
    """One-way explicit cutover; never called from a canvas operation."""
    def change(state):
        if state["runtime"].get("active") or state["security"].get("enforced"):
            if not state["runtime"].get("active") or not state["security"].get("enforced"):
                raise ControlError(409, "Control activation is incomplete; review private state before continuing")
            return {"enforced": True, "restart_required": True}
        if len(state["users"]) < 6 or any(user["access_state"] != "active" for user in state["users"].values() if user["desired_active"]):
            raise ControlError(409, "Complete and verify platform sharing before enforcement")
        if set(state["runtime"]["profiles"]) != {"stage", "prod"}:
            raise ControlError(409, "Import and verify runtime profiles before enforcement")
        from api.administration import validate_control_profiles
        validate_control_profiles(state["runtime"]["profiles"], require_revisions=True)
        from api.profiles import ConfigurationError, load_runtime_config
        try:
            # Host saves use this same control lock. Read the selected legacy
            # authority inside it so a later save cannot race this comparison.
            source = load_runtime_config()
        except ConfigurationError:
            raise ControlError(409, "Current legacy runtime configuration must be available before enforcement") from None
        for profile_id, profile in source.profiles.items():
            expected = {"revision": source.revision, "provider": profile.provider,
                        "label": profile.label, "connection_string": profile.connection_string,
                        "enabled": profile.enabled}
            imported = state["runtime"]["profiles"][profile_id]
            if any(imported.get(field) != value for field, value in expected.items()):
                raise ControlError(409, "Legacy runtime changed after import; back up and review the inactive import before enforcement")
            if profile.enabled:
                try:
                    with open_repository(profile.provider, profile.connection_string) as repository:
                        if not repository.health():
                            raise ValueError("Database unavailable")
                        repository.validate_identity(profile_id)
                        repository.validate_workflow_tracking()
                except Exception:
                    raise ControlError(409, "Enabled database requires verified schema, environment identity and complete intake workflow tracking before enforcement") from None
        # A stale import is never automatically refreshed: that would discard
        # administrator-reviewed profiles or invalidate existing draft receipts.
        state["security"]["enforced"] = True
        state["runtime"]["active"] = True
        append_audit(state, "BROKER_ONLY_ENFORCED", "host-administrator")
        return {"enforced": True, "restart_required": True}
    return store.mutate(change, expected_revision=expected_revision)
