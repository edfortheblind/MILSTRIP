"""Broker identity, owner invariants and retryable platform reconciliation."""
from copy import deepcopy
from dataclasses import replace
from contextlib import contextmanager
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api import app as api
from api.auth import ITERATIONS, password_digest
from api.authorization import (AuthorizationError, acquire_sharing_lease, authorize, authorize_person, list_users,
    record_sharing_result, save_user_access)
from api.broker_models import AcquireSharingLease, DirectoryPerson, SaveUserAccess, SharingResult
from api.control import ControlError, ControlStore, principal_key
from api.control_bootstrap import APP_IDS, SEED_ROLES, bootstrap_state, enforce_security


def synthetic_manifest():
    tenant = str(uuid4())
    members = []
    for name in SEED_ROLES:
        upn = name.lower().replace(" ", ".") + "@austinlighthouse.org"
        person = {"object_id": str(uuid4()), "upn": upn, "display_name": name,
                  "account_enabled": True, "user_type": "Member"}
        members.append({"seed_name": name, "expected_upn": upn, "verified_tenant_id": tenant, "directory": person})
    return {"schema_version": 1, "source": "verified-tenant-directory-export", "tenant_id": tenant,
            "members": members, "resources": {key: {"app_id": app_id, "flow_id": str(uuid4())} for key, app_id in APP_IDS.items()}}


@pytest.fixture
def control(api_credentials, monkeypatch):
    from api.profiles import runtime_config_path
    directory = runtime_config_path().parent
    path = directory / "control.json"
    monkeypatch.setenv("MILSTRIP_CONTROL_FILE", str(path))
    manifest = synthetic_manifest()
    state = bootstrap_state(manifest, [api_credentials[0], "synthetic-prod-reviewer"])
    # Unit-test platform acceptance fixture; no tenant grant is performed.
    for user in state["users"].values():
        user["access_state"] = "active"
    store = ControlStore(path)
    store.create(state)
    for profile in ("stage", "prod"):
        salt = "cd" * 32
        verifier = {"version": 1, "iterations": ITERATIONS, "username": f"synthetic-{profile}-broker",
                    "salt": salt, "digest": password_digest("synthetic-broker-password", salt)}
        (directory / f"broker-{profile}-credential.json").write_text(json.dumps(verifier), encoding="utf-8")
    return store, manifest


def actor(manifest, name="Ed Lopez"):
    return DirectoryPerson.model_validate(next(m["directory"] for m in manifest["members"] if m["seed_name"] == name))


def context(control, name="Ed Lopez", profile="stage"):
    store, manifest = control
    binding = store.read()["security"]["brokers"][profile]
    return authorize_person(binding, actor(manifest, name), uuid4(), store)


def access_command(control, *, person=None, active=True, role="OPERATOR", upn=None):
    store, _ = control
    if person is None and active:
        person = DirectoryPerson(object_id=uuid4(), upn="synthetic.operator@austinlighthouse.org",
                                 display_name="Synthetic Operator", account_enabled=True, user_type="Member")
    return SaveUserAccess(command_id=uuid4(), expected_revision=store.read()["acl_revision"],
                          target=person, target_upn=upn, role=role, active=active)


def complete(control, result, *, resources=None, error=None):
    store, _ = control
    plan = result["sharing_plan"]
    observations = [{key: resource[key] for key in ("kind", "resource_id", "permission", "present")} | {"verified": True}
                    for resource in (resources if resources is not None else plan["resources"])]
    state = store.read()
    binding = state["security"]["brokers"]["stage"]
    saved = state["sharing_plans"][plan["plan_id"]]
    key = principal_key(plan["target"]["tenant_id"], plan["target"]["object_id"])
    held = state.get("sharing_leases", {}).get(key)
    if saved["status"] == "completed":
        claim = next(reversed(saved["executions"].values()))
    elif held is not None and held["plan_id"] == plan["plan_id"]:
        claim = held
    else:
        claim = acquire_sharing_lease(binding, AcquireSharingLease(
            plan_id=plan["plan_id"], revision=plan["revision"], execution_id=uuid4()), store)
    return record_sharing_result(binding, SharingResult(plan_id=plan["plan_id"], revision=plan["revision"],
        lease_id=claim["lease_id"], execution_id=claim["execution_id"], external_calls_complete=True,
        observations=observations, error_code=error), store)


def test_bootstrap_requires_exact_verified_six_person_mapping_and_pins_two_owners():
    manifest = synthetic_manifest()
    state = bootstrap_state(manifest, ["legacy-stage", "legacy-prod"])
    assert len(state["users"]) == 6 and len(state["protected_owners"]) == 2
    assert not state["security"]["enforced"] and not state["runtime"]["active"]
    assert all(user["access_state"] == "pending" for user in state["users"].values())
    changed = deepcopy(manifest)
    changed["members"][0]["directory"]["upn"] = "replacement@austinlighthouse.org"
    with pytest.raises(ControlError):
        bootstrap_state(changed, [])
    changed = deepcopy(manifest)
    changed["members"][0]["verified_tenant_id"] = str(uuid4())
    with pytest.raises(ControlError):
        bootstrap_state(changed, [])


@pytest.mark.parametrize("seed_name", list(SEED_ROLES))
def test_bootstrap_cannot_assign_requested_seed_role_to_another_upn(seed_name):
    manifest = synthetic_manifest()
    member = next(item for item in manifest["members"] if item["seed_name"] == seed_name)
    member["expected_upn"] = member["directory"]["upn"] = "unrequested.admin@austinlighthouse.org"
    with pytest.raises(ControlError):
        bootstrap_state(manifest, [])


def test_bootstrap_upn_matching_is_case_insensitive():
    manifest = synthetic_manifest()
    member = next(item for item in manifest["members"] if item["seed_name"] == "Kristen Fleming")
    member["directory"]["upn"] = "Kristen.Fleming@austinlighthouse.org"
    state = bootstrap_state(manifest, [])
    assert next(user for user in state["users"].values() if user["upn"].startswith("Kristen"))["role"] == "ADMIN"


def test_initialize_commits_membership_and_inactive_runtime_in_one_write(api_credentials, monkeypatch):
    import sys
    from scripts.initialize_control import main
    from api.profiles import runtime_config_path
    directory = runtime_config_path().parent
    manifest = directory / "directory-verified.json"
    manifest.write_text(json.dumps(synthetic_manifest()), encoding="utf-8")
    monkeypatch.setenv("MILSTRIP_CONTROL_FILE", str(directory / "control.json"))
    monkeypatch.setattr(sys, "argv", ["initialize_control.py", "--initialize", "--verified-manifest", str(manifest)])
    writes = []
    original = ControlStore._write

    def observed_write(self, state):
        writes.append(deepcopy(state))
        original(self, state)
    monkeypatch.setattr(ControlStore, "_write", observed_write)
    assert main() == 0
    assert len(writes) == 1
    assert set(writes[0]["runtime"]["profiles"]) == {"stage", "prod"}
    assert len(writes[0]["users"]) == 6
    assert writes[0]["runtime"]["active"] is False
    assert writes[0]["security"]["enforced"] is False


def test_atomic_cas_and_failed_replace_preserve_state(control, monkeypatch):
    store, _ = control
    before = store.path.read_bytes()
    with pytest.raises(ControlError, match="revision changed"):
        store.mutate(lambda state: None, expected_revision=str(uuid4()))
    assert store.path.read_bytes() == before
    monkeypatch.setattr("api.control.os.replace", lambda *args: (_ for _ in ()).throw(OSError("PRIVATE_SENTINEL")))
    with pytest.raises(ControlError) as caught:
        store.mutate(lambda state: state["runtime"].update(drafts={"new": {}}))
    assert "PRIVATE_SENTINEL" not in str(caught.value)
    assert store.path.read_bytes() == before
    assert not list(store.path.parent.glob("control-*.tmp"))


def test_existing_lock_file_is_not_stale_ownership_and_live_lock_rejects_concurrent_writer(control):
    store, _ = control
    assert store.path.with_suffix(".lock").exists()
    store.mutate(lambda state: state["runtime"].update(test_marker="recovered"))
    assert store.read()["runtime"]["test_marker"] == "recovered"
    descriptor = store._lock()
    try:
        with pytest.raises(ControlError, match="busy") as error:
            ControlStore(store.path).mutate(lambda state: None)
        assert error.value.status_code == 503
    finally:
        store._unlock(descriptor)
    store.mutate(lambda state: state["runtime"].pop("test_marker"))


def test_process_death_releases_control_lock(control):
    import subprocess
    import sys
    store, _ = control
    script = "from api.control import ControlStore; import os,sys; s=ControlStore(sys.argv[1]); s._lock(); os._exit(0)"
    result = subprocess.run([sys.executable, "-c", script, str(store.path)],
                            capture_output=True, timeout=10)
    assert result.returncode == 0
    store.mutate(lambda state: state["runtime"].update(crash_recovered=True))
    assert store.read()["runtime"]["crash_recovered"]


@pytest.mark.parametrize("name", ["Claude Furry", "Mike Thompson"])
@pytest.mark.parametrize("active", [True, False])
def test_protected_owners_cannot_be_changed_by_admin_or_owner(control, name, active):
    store, manifest = control
    for caller in ("Ed Lopez", "Claude Furry"):
        command = access_command(control, person=actor(manifest, name), active=active, role="ADMIN")
        with pytest.raises(AuthorizationError, match="Protected owners"):
            save_user_access(context(control, caller), command, store)
    assert store.read()["users"][principal_key(manifest["tenant_id"], actor(manifest, name).object_id)]["role"] == "OWNER"


def test_control_store_invariant_prevents_generic_owner_demotion(control):
    store, _ = control
    before = store.path.read_bytes()
    def demote(state):
        state["users"][state["protected_owners"][0]]["role"] = "ADMIN"
    with pytest.raises(ControlError):
        store.mutate(demote)
    assert store.path.read_bytes() == before


def test_control_security_invariants_survive_python_optimization(control):
    import subprocess
    import sys
    store, _ = control
    before = store.path.read_bytes()
    script = '''
import sys
from api.control import ControlStore, ControlError
store = ControlStore(sys.argv[1])
def demote(state):
    state['users'][state['protected_owners'][0]]['role'] = 'ADMIN'
try:
    store.mutate(demote)
except ControlError:
    sys.exit(0)
sys.exit(9)
'''
    result = subprocess.run([sys.executable, '-O', '-c', script, str(store.path)], capture_output=True, timeout=10)
    assert result.returncode == 0 and store.path.read_bytes() == before


def test_unknown_oid_corporate_email_and_disabled_guest_cannot_authorize(control):
    store, manifest = control
    binding = store.read()["security"]["brokers"]["stage"]
    for changes in ({"object_id": uuid4()}, {"upn": "ed.lopez@other.invalid"},
                    {"account_enabled": False}, {"user_type": "Guest"}):
        with pytest.raises(AuthorizationError):
            authorize_person(binding, actor(manifest).model_copy(update=changes), uuid4(), store)
    with pytest.raises(AuthorizationError):
        authorize_person({**binding, "tenant_id": str(uuid4())}, actor(manifest), uuid4(), store)


def test_both_named_owner_and_admin_can_manage_and_configure(control):
    store, _ = control
    for name in SEED_ROLES:
        person = context(control, name)
        for capability in ("business", "users.manage", "runtime.configure"):
            assert capability in authorize(person, capability, store).capabilities


def test_add_pending_partial_readback_retry_and_operator_capabilities(control):
    store, _ = control
    admin = context(control)
    command = access_command(control)
    result = save_user_access(admin, command, store)
    binding = store.read()["security"]["brokers"]["stage"]
    with pytest.raises(AuthorizationError):
        authorize_person(binding, command.target, uuid4(), store)
    partial = complete(control, result, resources=result["sharing_plan"]["resources"][:2], error="PLATFORM_FAILED")
    assert partial["sharing_plan"]["status"] == "pending" and partial["membership"]["access_state"] == "pending"
    replay = save_user_access(admin, command, store)
    assert replay["sharing_plan"]["plan_id"] == result["sharing_plan"]["plan_id"]
    still_partial = complete(control, result, resources=result["sharing_plan"]["resources"][2:])
    assert still_partial["membership"]["access_state"] == "pending"
    accepted = complete(control, result)
    assert accepted["membership"]["access_state"] == "active"
    operator = authorize_person(binding, command.target, uuid4(), store)
    assert authorize(operator, "business", store)
    for capability in ("users.manage", "runtime.configure"):
        with pytest.raises(AuthorizationError):
            authorize(operator, capability, store)
    assert complete(control, result)["sharing_plan"]["status"] == "completed"
    assert all(resource["permission"] in {"CanView", "run-only"} for resource in result["sharing_plan"]["resources"])


def test_removal_denies_immediately_even_if_directory_deleted_and_platform_fails(control):
    store, manifest = control
    old_context = context(control, "Shawn Hinkle")
    command = access_command(control, active=False, upn=actor(manifest, "Shawn Hinkle").upn, role="ADMIN")
    result = save_user_access(context(control), command, store)
    with pytest.raises(AuthorizationError):
        authorize(old_context, "business", store)
    incomplete = complete(control, result, resources=[], error="PLATFORM_FAILED")
    assert incomplete["membership"]["access_state"] == "denied"
    assert incomplete["sharing_plan"]["status"] == "pending"
    with pytest.raises(AuthorizationError):
        authorize(old_context, "users.manage", store)
    assert complete(control, result)["membership"]["access_state"] == "denied"


def test_old_add_callback_cannot_restore_removed_user(control):
    store, _ = control
    admin = context(control)
    command = access_command(control)
    added = save_user_access(admin, command, store)
    removed = save_user_access(admin, access_command(control, active=False, upn=command.target.upn), store)
    with pytest.raises(AuthorizationError, match="superseded"):
        complete(control, added)
    assert complete(control, removed)["membership"]["access_state"] == "denied"


def test_sharing_callback_cannot_choose_a_different_resource_or_permission(control):
    store, _ = control
    result = save_user_access(context(control), access_command(control), store)
    wrong = {**result["sharing_plan"]["resources"][0], "resource_id": str(uuid4())}
    with pytest.raises(AuthorizationError, match="authorized sharing plan"):
        complete(control, result, resources=[wrong])
    wrong = {**result["sharing_plan"]["resources"][0], "permission": "run-only"}
    with pytest.raises(AuthorizationError):
        complete(control, result, resources=[wrong])


def envelope(control, operation="GetCurrentUser", payload=None):
    return {"schema_version": 1, "request_id": str(uuid4()), "actor": actor(control[1]).model_dump(mode="json"),
            "operation": operation, "payload_json": json.dumps(payload or {})}


def test_broker_only_transport_rejects_shared_credentials_and_fake_headers(control, api_credentials):
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke", json=envelope(control), auth=api_credentials,
                               headers={"X-Forwarded-User": "ed.lopez@austinlighthouse.org"})
        assert response.status_code == 401
        response = client.post("/api/v1/broker/invoke", json=envelope(control),
                               auth=("synthetic-stage-broker", "synthetic-broker-password"))
        assert response.status_code == 200
        result = json.loads(response.json()["result_json"])
        assert result["role"] == "ADMIN" and result["environment"] == "stage"


def test_enforced_cutover_denies_every_legacy_route(control, api_credentials):
    store, _ = control
    store.mutate(lambda state: state["security"].update(enforced=True))
    routes = [("get", "/api/v1/health"), ("get", "/api/v1/intake/requests"),
              ("get", "/api/v1/intake/requests/missing"), ("get", "/api/v1/intake/requests/missing/records"),
              ("get", "/api/v1/intake/requests/missing/audit-events"), ("post", "/api/v1/intake/requests"),
              ("post", "/api/v1/records/missing/review-decisions")]
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        for method, path in routes:
            assert client.request(method, path, auth=api_credentials, json={}).status_code == 403


def test_broker_validation_does_not_echo_secrets_or_allow_client_actor(control):
    auth = ("synthetic-stage-broker", "synthetic-broker-password")
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        body = envelope(control)
        body["unexpected"] = "PRIVATE_SENTINEL"
        response = client.post("/api/v1/broker/invoke", auth=auth, json=body)
        assert response.status_code == 422 and "PRIVATE_SENTINEL" not in response.text
        body = envelope(control, "GetCurrentUser", {"actor": "PRIVATE_SENTINEL"})
        response = client.post("/api/v1/broker/invoke", auth=auth, json=body)
        assert response.status_code == 422 and "PRIVATE_SENTINEL" not in response.text
        body = envelope(control)
        body["actor"]["object_id"] = str(uuid4())
        assert client.post("/api/v1/broker/invoke", auth=auth, json=body).status_code == 403


def test_disabled_prod_authorized_user_administration_needs_no_database(control, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("User administration must not connect to a business database")
    monkeypatch.setattr("api.runtime.open_repository", forbidden)
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke", auth=("synthetic-prod-broker", "synthetic-broker-password"),
                               json=envelope(control, "ListUsers"))
        assert response.status_code == 200 and len(json.loads(response.json()["result_json"])["items"]) == 6


def test_corrupt_control_present_after_startup_fails_closed_without_legacy_fallback(control, api_credentials):
    store, _ = control
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        store.path.write_text('{"PRIVATE_SENTINEL":', encoding="utf-8")
        legacy = client.get("/api/v1/health", auth=api_credentials)
        broker = client.post("/api/v1/broker/invoke", auth=("synthetic-stage-broker", "synthetic-broker-password"),
                             json=envelope(control))
        assert legacy.status_code == broker.status_code == 503
        assert "PRIVATE_SENTINEL" not in legacy.text + broker.text


def test_business_uses_verified_human_identity_and_returns_no_receipt_on_commit_failure(control, monkeypatch):
    import psycopg
    from datetime import datetime, timezone
    captured = []

    class FakeRepository:
        def validate_identity(self, profile):
            assert profile == "stage"

        def create_intake(self, **values):
            captured.append(values)
            return {"request_id": values["request_id"], "status": "REJECTED", "received_at": datetime.now(timezone.utc),
                    "records": 0, "rejected": 0, "requires_review": 0}

    @contextmanager
    def failed_commit(provider, connection_string):
        yield FakeRepository()
        raise psycopg.OperationalError("PRIVATE_COMMIT_SENTINEL")

    monkeypatch.setattr("api.runtime.open_repository", failed_commit)
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke", auth=("synthetic-stage-broker", "synthetic-broker-password"),
                               json=envelope(control, "CreateIntakeRequest", {"source_type": "PASTE", "source_text": "Synthetic"}))
    assert response.status_code == 503 and "PRIVATE_COMMIT_SENTINEL" not in response.text
    assert len(captured) == 1
    assert captured[0]["actor"] == context(control).actor_id


def test_operator_cannot_use_duplicate_override(control, monkeypatch):
    store,manifest=control
    person=actor(manifest)
    key=principal_key(manifest['tenant_id'],str(person.object_id))
    store.mutate(lambda state: state['users'][key].update(role='OPERATOR'))
    from types import SimpleNamespace
    from api import runtime as runtime_module
    @contextmanager
    def scope(request,profile):
        yield SimpleNamespace(revision='synthetic')
    monkeypatch.setattr(runtime_module,'business_scope',scope)
    with TestClient(api.app,client=('127.0.0.1',5000)) as client:
        response=client.post('/api/v1/broker/invoke',auth=('synthetic-stage-broker','synthetic-broker-password'),
            json=envelope(control,'CreateIntakeRequest',{'source_type':'PASTE','source_text':'A2A',
                 'duplicate_override_reason':'Operator must not bypass duplicates'}))
    assert response.status_code==403


def test_verified_broker_intake_resume_completion_and_override(control, portable_database, monkeypatch):
    from api import runtime as runtime_module
    from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD
    @contextmanager
    def database(provider, connection_string):
        yield portable_database.repository
    monkeypatch.setattr(runtime_module,'open_repository',database)
    with TestClient(api.app,client=('127.0.0.1',5000)) as client:
        def call(operation,payload=None,status=200):
            response=client.post('/api/v1/broker/invoke',
                auth=('synthetic-stage-broker','synthetic-broker-password'),
                json=envelope(control,operation,payload))
            assert response.status_code==status
            return json.loads(response.json()['result_json']) if status==200 else None
        source=SYNTHETIC_RECORD[:30]+str(uuid4())[:10]+SYNTHETIC_RECORD[40:]
        payload={'source_type':'PASTE','source_text':source}
        first=call('CreateIntakeRequest',payload)
        workflow=call('GetIntakeWorkflow')
        assert workflow['active_request_id']==first['request_id'] and not workflow['can_start']
        call('CreateIntakeRequest',{**payload,'source_text':source+'\nA2A'},409)
        call('CreateReviewDecision',{'record_id':first['request_id']+':1','decision':'REJECTED',
             'reason':'Synthetic final decision','expected_version':0,'command_id':str(uuid4())})
        assert call('GetIntakeWorkflow')['can_start']
        call('CreateIntakeRequest',payload,409)
        second=call('CreateIntakeRequest',{**payload,'duplicate_override_reason':'Authorized synthetic override'})
        assert second['request_id']!=first['request_id']
        assert call('GetIntakeWorkflow')['active_request_id']==second['request_id']
