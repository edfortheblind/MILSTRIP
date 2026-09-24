"""Host bootstrap derives permissions from native rows without flow callbacks."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from uuid import uuid4

import pytest

from api.authorization import acquire_sharing_lease
from api.bootstrap_acceptance import APP_CAPTURE, ED_OBJECT_ID, FLOW_CAPTURE, accept_bootstrap_member
from api.broker_models import AcquireSharingLease
from api.control import ControlError, ControlStore, principal_key
from api.control_bootstrap import bootstrap_state
from api.profiles import runtime_config_path
from scripts.accept_bootstrap_ed import main
from tests.test_control_broker import synthetic_manifest


@pytest.fixture
def bootstrap(api_credentials, monkeypatch):
    manifest = synthetic_manifest()
    for member in manifest["members"]:
        if member["seed_name"] == "Ed Lopez":
            member["directory"]["object_id"] = ED_OBJECT_ID
    state = bootstrap_state(manifest, [api_credentials[0], "synthetic-prod-reviewer"])
    store = ControlStore(runtime_config_path().parent / "control.json")
    store.create(state)
    monkeypatch.setenv("MILSTRIP_CONTROL_FILE", str(store.path))
    now = datetime.now(timezone.utc)
    tenant = manifest["tenant_id"]
    apps, flows = [], []
    for resource in manifest["resources"].values():
        app_id, flow_id = resource["app_id"], resource["flow_id"]
        principal = {"id": ED_OBJECT_ID, "type": "User", "tenantId": tenant}
        apps.append({"app_id": app_id, "environment_name": "Default-" + tenant,
                     "verified_at": now.isoformat(), "assignment": {
                         "id": f"/providers/Microsoft.PowerApps/apps/{app_id}/permissions/{ED_OBJECT_ID}",
                         "name": ED_OBJECT_ID, "type": "Microsoft.PowerApps/apps/permissions",
                         "properties": {"principal": principal, "roleName": "Owner"}}})
        flows.append({"flow_id": flow_id, "owner_present": True, "run_only_present": False, "owners": [], "users": [{
            "id": f"/providers/Microsoft.ProcessSimple/environments/Default-{tenant}/flows/{flow_id}/users/{ED_OBJECT_ID}",
            "type": "/providers/Microsoft.ProcessSimple/environments/flows/users",
            "properties": {"permissionType": "Principal", "principal": principal}}]})
    paths = [store.path.parent / APP_CAPTURE, store.path.parent / FLOW_CAPTURE]
    for path, value in zip(paths, (apps, flows)):
        path.write_text(json.dumps(value), encoding="utf-8")
    return store, paths, now


def accept(bootstrap, *, apply=False, revision=None):
    store, paths, now = bootstrap
    return accept_bootstrap_member(store, revision or store.read()["revision"], *paths, apply=apply, clock=lambda: now)


def change_capture(bootstrap, index, change):
    path = bootstrap[1][index]
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_preview_uses_actual_flow_user_rows_ignoring_false_summary_without_writing(bootstrap):
    store, _, _ = bootstrap
    before = store.path.read_bytes()
    result = accept(bootstrap)
    assert result["changed"] is False and result["membership"] == "pending" and result["reviewed_resources"] == 4
    assert store.path.read_bytes() == before


def test_apply_changes_only_ed_and_honest_host_evidence_without_execution_or_cutover(bootstrap):
    store, paths, _ = bootstrap
    before = store.read()
    result = accept(bootstrap, apply=True)
    after = store.read()
    key = principal_key(before["security"]["tenant_id"], ED_OBJECT_ID)
    assert result["changed"] is True and result["membership"] == "active"
    for user_key, member in before["users"].items():
        assert after["users"][user_key] == (member | {"access_state": "active"} if user_key == key else member)
    for field in ("security", "runtime", "protected_owners", "resources", "sharing_leases", "operations"):
        assert before[field] == after[field]
    plan = next(p for p in after["sharing_plans"].values() if p["target"]["object_id"] == ED_OBJECT_ID)
    assert plan["status"] == "completed" and len(plan["observations"]) == 4 and "executions" not in plan
    assert after["acl_revision"] != before["acl_revision"]
    assert len(after["audit"]) == len(before["audit"]) + 1
    audit = after["audit"][-1]
    assert audit["event_type"] == "HOST_BOOTSTRAP_ACCESS_VERIFIED" and audit["actor_id"] == "host-administrator"
    assert {e["sha256"] for e in audit["evidence"]} == {sha256(p.read_bytes()).hexdigest() for p in paths}
    assert "file_written_at" in audit["evidence"][1] and "native_verified_at" not in audit["evidence"][1]


def test_summary_boolean_and_owner_membership_do_not_replace_flow_run_only_row(bootstrap):
    def remove_users(items):
        for item in items:
            item["run_only_present"] = True
            item["owners"] = deepcopy(item["users"])
            item["users"] = []
    change_capture(bootstrap, 1, remove_users)
    with pytest.raises(ControlError, match="native run-only"):
        accept(bootstrap, apply=True)


@pytest.mark.parametrize("alter", [
    lambda items: items[0]["assignment"]["properties"].update(roleName="CanView"),
    lambda items: items[0]["assignment"]["properties"]["principal"].update(id=str(uuid4())),
    lambda items: items[0]["assignment"]["properties"]["principal"].update(tenantId=str(uuid4())),
    lambda items: items[0].update(environment_name="Default-" + str(uuid4())),
    lambda items: items[0]["assignment"].update(id=items[1]["assignment"]["id"]),
    lambda items: items[0].pop("assignment"),
])
def test_app_evidence_requires_exact_native_owner_identity_and_resource(bootstrap, alter):
    before = bootstrap[0].read()
    change_capture(bootstrap, 0, alter)
    with pytest.raises(ControlError):
        accept(bootstrap, apply=True)
    assert bootstrap[0].read() == before


@pytest.mark.parametrize("alter", [
    lambda items: items[0]["users"][0]["properties"]["principal"].update(tenantId=str(uuid4())),
    lambda items: items[0]["users"][0]["properties"]["principal"].update(type="Group"),
    lambda items: items[0]["users"][0].update(id=items[1]["users"][0]["id"]),
    lambda items: items[0]["users"].append(deepcopy(items[0]["users"][0])),
    lambda items: items.pop(),
])
def test_flow_evidence_requires_exact_unambiguous_four_resource_readback(bootstrap, alter):
    before = bootstrap[0].read()
    change_capture(bootstrap, 1, alter)
    with pytest.raises(ControlError):
        accept(bootstrap, apply=True)
    assert bootstrap[0].read() == before


def test_old_or_future_native_timestamps_and_stale_files_are_rejected(bootstrap):
    store, paths, now = bootstrap
    change_capture(bootstrap, 0, lambda items: items[0].update(verified_at=(now - timedelta(hours=2)).isoformat()))
    with pytest.raises(ControlError, match="Refresh"):
        accept(bootstrap)
    change_capture(bootstrap, 0, lambda items: items[0].update(verified_at=(now + timedelta(minutes=2)).isoformat()))
    with pytest.raises(ControlError, match="Refresh"):
        accept(bootstrap)
    change_capture(bootstrap, 0, lambda items: items[0].update(verified_at=now.isoformat()))
    old = (now - timedelta(hours=2)).timestamp()
    os.utime(paths[1], (old, old))
    with pytest.raises(ControlError, match="Refresh"):
        accept(bootstrap)


def test_prior_execution_and_stale_revision_prevent_acceptance(bootstrap):
    store, _, _ = bootstrap
    previous_revision = store.read()["revision"]
    plan = next(p for p in store.read()["sharing_plans"].values() if p["target"]["object_id"] == ED_OBJECT_ID)
    acquire_sharing_lease(store.read()["security"]["brokers"]["stage"],
        AcquireSharingLease(plan_id=plan["plan_id"], revision=plan["revision"], execution_id=uuid4()), store)
    with pytest.raises(ControlError, match="revision changed"):
        accept(bootstrap, apply=True, revision=previous_revision)
    with pytest.raises(ControlError, match="untouched"):
        accept(bootstrap, apply=True)


def test_repeated_acceptance_and_active_authority_are_rejected(bootstrap):
    store, _, _ = bootstrap
    accept(bootstrap, apply=True)
    with pytest.raises(ControlError, match="six pending"):
        accept(bootstrap, apply=True)
    store.mutate(lambda state: state["security"].update(enforced=True))
    with pytest.raises(ControlError, match="closed after"):
        accept(bootstrap)


def test_cli_defaults_to_preview_and_requires_explicit_apply(bootstrap, capsys):
    store, _, _ = bootstrap
    revision = store.read()["revision"]
    original = store.path.read_bytes()
    assert main(["--expected-revision", revision]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is False
    assert store.path.read_bytes() == original
    assert main(["--expected-revision", revision, "--accept-ed"]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True


def test_other_paths_cannot_supply_bootstrap_evidence(bootstrap, tmp_path):
    store, paths, _ = bootstrap
    outside = tmp_path / APP_CAPTURE
    outside.write_bytes(paths[0].read_bytes())
    with pytest.raises(ControlError, match="named files"):
        accept_bootstrap_member(store, store.read()["revision"], outside, paths[1])
