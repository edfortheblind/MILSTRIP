"""Protected in-app Owners retain ordinary platform permissions at bootstrap."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

from api.bootstrap_acceptance import ED_OBJECT_ID
from api.bootstrap_owner_acceptance import OWNER_FILES, accept_bootstrap_owner, owner_capture_spec
from api.control import ControlError
from api.control_bootstrap import SEED_UPNS
from scripts.accept_bootstrap_owner import main
from tests.test_bootstrap_acceptance import accept, bootstrap


@pytest.fixture
def owner_bootstrap(bootstrap):
    store, paths, now = bootstrap
    accept(bootstrap, apply=True)
    state = store.read()
    manifest = {"schema_version": 1, "source": "verified-tenant-directory-export", "tenant_id": state["security"]["tenant_id"],
                "resources": state["resources"], "members": []}
    for name, upn in SEED_UPNS.items():
        user = next(u for u in state["users"].values() if u["upn"] == upn)
        manifest["members"].append({"seed_name": name, "expected_upn": upn, "verified_tenant_id": user["tenant_id"],
            "directory": {"object_id": user["object_id"], "upn": upn, "display_name": user["display_name"],
                          "account_enabled": True, "user_type": "Member"}})
    (store.path.parent / "bootstrap-verified.json").write_text(json.dumps(manifest), encoding="utf-8")
    original_apps, original_flows = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    for name, stem in OWNER_FILES.items():
        member = next(u for u in state["users"].values() if u["upn"] == SEED_UPNS[name])
        object_id = member["object_id"]
        apps, flows = deepcopy(original_apps), deepcopy(original_flows)
        for app in apps:
            assignment = app["assignment"]
            assignment["id"] = assignment["id"].replace(ED_OBJECT_ID, object_id)
            assignment["name"] = object_id
            assignment["properties"]["principal"]["id"] = object_id
            assignment["properties"]["roleName"] = "CanView"
        for flow in flows:
            flow["environment_name"] = "Default-" + member["tenant_id"]
            flow["verified_at"] = now.isoformat()
            flow["next_link"] = None
            flow["users"][0]["id"] = flow["users"][0]["id"].replace(ED_OBJECT_ID, object_id)
            flow["users"][0]["properties"]["principal"]["id"] = object_id
        for kind, value in (("app", apps), ("flow", flows)):
            (store.path.parent / (stem + "-" + kind + "-permissions.json")).write_text(json.dumps(value), encoding="utf-8")
    return store, now


def owner_accept(fixture, name="Claude Furry", *, apply=False, revision=None):
    store, now = fixture
    return accept_bootstrap_owner(store, revision or store.read()["revision"], name, apply=apply, clock=lambda: now)


def change_file(fixture, filename, edit):
    path = fixture[0].path.parent / filename
    value = json.loads(path.read_text(encoding="utf-8"))
    edit(value)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_preview_is_read_only_and_capture_spec_pins_manifest_resources(owner_bootstrap):
    store, _ = owner_bootstrap
    before = store.path.read_bytes()
    result = owner_accept(owner_bootstrap)
    spec = owner_capture_spec(store, "Claude Furry")
    assert not result["changed"] and result["role"] == "OWNER" and result["reviewed_resources"] == 4
    assert spec["resources"] == store.read()["resources"]
    assert spec["object_id"] != ED_OBJECT_ID
    assert Path(spec["app_capture"]).name == "claude-furry-app-permissions.json"
    assert store.path.read_bytes() == before


def test_both_owners_can_be_accepted_sequentially_after_ed_without_altering_roles_or_others(owner_bootstrap):
    store, _ = owner_bootstrap
    before = store.read()
    for name in OWNER_FILES:
        previous = store.read()
        result = owner_accept(owner_bootstrap, name, apply=True)
        current = store.read()
        selected = next(key for key, user in current["users"].items() if user["upn"] == SEED_UPNS[name])
        assert result["changed"] and result["role"] == "OWNER"
        assert current["users"][selected] == previous["users"][selected] | {"access_state": "active"}
        assert all(current["users"][key] == value for key, value in previous["users"].items() if key != selected)
        plan = next(p for p in current["sharing_plans"].values() if p["target"]["object_id"] == current["users"][selected]["object_id"])
        assert plan["status"] == "completed" and "executions" not in plan and len(plan["observations"]) == 4
        assert all(o.get("native_role", "CanView") == "CanView" for o in plan["observations"].values())
        audit = current["audit"][-1]
        assert audit["event_type"] == "HOST_BOOTSTRAP_OWNER_VERIFIED" and len(audit["evidence"]) == 3
    after = store.read()
    for field in ("protected_owners", "security", "runtime", "resources", "operations", "sharing_leases"):
        assert after[field] == before[field]
    assert sum(u["access_state"] == "active" for u in after["users"].values()) == 3


@pytest.mark.parametrize("role", ["Owner", "CanEdit"])
def test_protected_owner_does_not_accept_platform_ownership_or_edit_grants(owner_bootstrap, role):
    change_file(owner_bootstrap, "claude-furry-app-permissions.json",
                lambda items: items[0]["assignment"]["properties"].update(roleName=role))
    with pytest.raises(ControlError):
        owner_accept(owner_bootstrap, apply=True)


@pytest.mark.parametrize("change", [
    lambda manifest: manifest.update(tenant_id=str(uuid4())),
    lambda manifest: manifest["members"][0]["directory"].update(object_id=str(uuid4())),
    lambda manifest: manifest["resources"]["stage"].update(flow_id=str(uuid4())),
])
def test_manifest_identity_tenant_and_resource_drift_are_rejected(owner_bootstrap, change):
    store, _ = owner_bootstrap
    before = store.path.read_bytes()
    change_file(owner_bootstrap, "bootstrap-verified.json", change)
    with pytest.raises(ControlError):
        owner_accept(owner_bootstrap, apply=True)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("change", [
    lambda items: items[0].pop("verified_at"),
    lambda items: items[0].update(environment_name="Default-" + str(uuid4())),
    lambda items: items[0].update(next_link="more-results"),
    lambda items: items[0]["users"][0]["properties"]["principal"].update(id=ED_OBJECT_ID),
])
def test_native_flow_timestamp_context_and_identity_are_required(owner_bootstrap, change):
    change_file(owner_bootstrap, "claude-furry-flow-permissions.json", change)
    with pytest.raises(ControlError):
        owner_accept(owner_bootstrap, apply=True)


def test_only_protected_pending_current_plan_without_active_lease_can_be_accepted(owner_bootstrap):
    from api.authorization import acquire_sharing_lease
    from api.broker_models import AcquireSharingLease
    store, _ = owner_bootstrap
    with pytest.raises(ControlError, match="two approved"):
        owner_accept(owner_bootstrap, "Ed Lopez")
    before_revision = store.read()["revision"]
    user = next(u for u in store.read()["users"].values() if u["upn"] == SEED_UPNS["Claude Furry"])
    plan = next(p for p in store.read()["sharing_plans"].values() if p["target"]["object_id"] == user["object_id"])
    acquire_sharing_lease(store.read()["security"]["brokers"]["stage"],
                         AcquireSharingLease(plan_id=plan["plan_id"], revision=plan["revision"], execution_id=uuid4()), store)
    with pytest.raises(ControlError, match="revision changed"):
        owner_accept(owner_bootstrap, apply=True, revision=before_revision)
    with pytest.raises(ControlError, match="untouched"):
        owner_accept(owner_bootstrap, apply=True)
    with pytest.raises(ControlError, match="outstanding"):
        owner_accept(owner_bootstrap, "Mike Thompson", apply=True)


def test_cli_preview_apply_and_repeat_cannot_bypass_pending_or_cutover_guards(owner_bootstrap, capsys):
    store, _ = owner_bootstrap
    revision = store.read()["revision"]
    original = store.path.read_bytes()
    args = ["--owner", "Claude Furry", "--expected-revision", revision]
    assert main(args) == 0 and json.loads(capsys.readouterr().out)["changed"] is False
    assert store.path.read_bytes() == original
    assert main(args + ["--accept-owner"]) == 0 and json.loads(capsys.readouterr().out)["role"] == "OWNER"
    with pytest.raises(ControlError, match="pending protected"):
        owner_accept(owner_bootstrap)
    store.mutate(lambda state: state["security"].update(enforced=True))
    with pytest.raises(ControlError, match="closed after"):
        owner_accept(owner_bootstrap, "Mike Thompson")


def test_capture_script_is_valid_powershell_and_only_reads_platform_permissions():
    path = Path(__file__).resolve().parents[1] / "scripts/Capture-BootstrapOwnerPermissions.ps1"
    source = path.read_text(encoding="utf-8")
    assert "InvokeApi -Method GET" in source and "Get-PowerAppRoleAssignment" in source
    assert not any(term in source for term in ("Set-PowerAppRoleAssignment", "Set-Admin", "-Method POST", "-Method PATCH", "-Method DELETE", "--accept-owner"))
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell is required for the native capture script syntax check")
    command = "$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile('" + str(path).replace("'", "''") + "',[ref]$tokens,[ref]$errors) | Out-Null; if($errors.Count){exit 1}"
    completed = subprocess.run([shell, "-NoProfile", "-Command", command], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
