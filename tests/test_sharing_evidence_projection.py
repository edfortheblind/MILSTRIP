"""Exercise the actual host collector offline; no credentials or tenant calls."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/Read-SharingRecoveryEvidence.ps1"
SHELL = shutil.which("powershell.exe") or shutil.which("pwsh")
TENANT = "9f5c0ace-0780-4b48-8c24-b08bb5149210"
ENVIRONMENT = "Default-" + TENANT
FLOW = "04d6229f-5ab8-f111-aaac-7ced8d6f317c"
RUN = "08584113137259107903122568693CU13"
ACTOR = "11111111-1111-4111-8111-111111111111"
TARGET = "22222222-2222-4222-8222-222222222222"
APP = "7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82"
SNAPSHOT = "4e2df4b9-e7fd-e446-63fa-678b9612ca1f"
RUN_ROUTE = ("https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/"
             f"environments/{ENVIRONMENT}/flows/{FLOW}/runs/{RUN}")
ACTIONS_ROUTE = RUN_ROUTE + "/actions?api-version=2016-11-01"
PERMISSIONS_ROUTE = (f"https://api.powerapps.com/providers/Microsoft.PowerApps/apps/{APP}"
                     "/permissions?api-version=2017-06-01&%24filter="
                     + quote(f"environment eq '{ENVIRONMENT}'", safe=""))
SENTINEL = "PRIVATE_PAYLOAD_MUST_NEVER_APPEAR"


pytestmark = pytest.mark.skipif(SHELL is None, reason="PowerShell host is required")


def envelope(body, *, status=200, elapsed=0):
    return {"http_status": status, "elapsed_ms": elapsed, "body": body}


def action(name="Acquire_lease_add", status="Succeeded"):
    return {"name": name, "properties": {
        "status": status, "code": "OK", "startTime": "2026-09-24T23:39:20Z",
        "endTime": "2026-09-24T23:39:21Z",
        "inputsLink": {"uri": "https://invalid.example/?sig=" + SENTINEL},
        "outputsLink": {"uri": "https://invalid.example/" + SENTINEL},
        "inputs": {"secret": SENTINEL}, "outputs": {"identity": SENTINEL},
    }}


def permission(index=1, *, principal=TARGET, role="CanView"):
    return {"id": f"/providers/Microsoft.PowerApps/apps/{APP}/permissions/{index}",
            "name": str(index), "properties": {"roleName": role, "principal": {
                "id": principal, "type": "User", "tenantId": TENANT,
                "displayName": SENTINEL, "email": SENTINEL}}}


def definition_action(operation="AcquireSharingLease"):
    return {"type": "OpenApiConnection", "inputs": {
        "host": {"connectionName": "broker", "operationId": "InvokeBroker",
                 "apiId": "/providers/Microsoft.PowerApps/apis/shared_milstrip"},
        "parameters": {"body/operation": operation, "body/payload_json": SENTINEL},
    }}


def attached_flow(actions=None):
    return {"id": f"/providers/Microsoft.ProcessSimple/environments/{ENVIRONMENT}/flows/{SNAPSHOT}",
            "name": SNAPSHOT, "properties": {"workflowEntityId": FLOW, "definition": {
                "metadata": {"workflowEntityId": FLOW, "creator": SENTINEL},
                "contentVersion": "1.0.0.0", "parameters": {"secret": SENTINEL},
                "actions": actions if actions is not None else {"Acquire_lease_add": definition_action()},
            }}}


def fixtures(directory):
    documents = {
        "context.json": {"tenant_id": TENANT, "actor_object_id": ACTOR},
        "run.json": envelope({"name": RUN, "properties": {
            "status": "Cancelled", "startTime": "2026-09-24T23:39:19Z",
            "endTime": "2026-09-24T23:48:10Z", "trigger": {"inputsLink": SENTINEL},
            "workflow": {"id": f"/providers/Microsoft.ProcessSimple/environments/{ENVIRONMENT}/flows/{SNAPSHOT}",
                         "name": SNAPSHOT, "version": "1"},
            "flow": attached_flow(),
        }}),
        "actions-001.json": envelope({"value": [action()]}),
    }
    return documents


def collect(tmp_path, documents, *arguments):
    for name, content in documents.items():
        (tmp_path / name).write_text(json.dumps(content), encoding="utf-8")
    output = tmp_path / "evidence.json"
    completed = subprocess.run([
        SHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
        str(SCRIPT), "-OfflineDirectory", str(tmp_path), "-OutputFile", str(output),
        *arguments,
    ], capture_output=True, text=True, timeout=30)
    serialized = output.read_text(encoding="utf-8-sig") if output.exists() else ""
    assert SENTINEL not in serialized + completed.stdout + completed.stderr
    return completed, json.loads(serialized) if serialized else None


def assert_failure(completed, evidence, expected=None):
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert evidence is None
    diagnostic = json.loads(completed.stderr)
    assert diagnostic["error"] == "SHARING_EVIDENCE_READBACK_FAILED"
    if expected:
        assert diagnostic["code"] == expected


def test_complete_action_traversal_projects_only_metadata(tmp_path):
    docs = fixtures(tmp_path)
    # This additional index key was observed in the actual ProcessSimple
    # continuation shape; cursor values remain opaque and are never exported.
    docs["actions-001.json"]["body"]["nextLink"] = ACTIONS_ROUTE + "&%24skiptoken=opaque%2Ftoken%3D&skiptokenSourceIndex=0"
    docs["actions-002.json"] = envelope({"value": [action("Add_stage_app", "Skipped")]})
    docs["run.json"]["body"]["properties"]["flow"]["properties"]["definition"]["actions"]["Add_stage_app"] = {
        "type": "OpenApiConnection", "inputs": {"host": {"connectionName": "makers", "operationId": "Edit-AppRoleAssignment"}}}
    completed, evidence = collect(tmp_path, docs)
    assert completed.returncode == 0, completed.stderr
    assert evidence["source"] == "offline-sharing-recovery-metadata"
    assert evidence["schema_version"] == 1
    assert evidence["completeness"] == {"run": True, "actions": True, "definition": True}
    assert [item["name"] for item in evidence["actions"]] == ["Acquire_lease_add", "Add_stage_app"]
    assert evidence["run"]["workflow_version"] == "1"
    assert evidence["definition"]["attached_flow_name"] == SNAPSHOT
    assert evidence["definition"]["snapshot_identity_source"] == "run.properties.flow.name"
    assert evidence["definition"]["actions"][0]["broker_operation"] == "AcquireSharingLease"
    assert set(evidence["actions"][0]) == {"name", "status", "code", "start_time", "end_time"}


def test_native_missing_workflow_version_is_not_invented(tmp_path):
    docs = fixtures(tmp_path)
    del docs["run.json"]["body"]["properties"]["workflow"]
    completed, evidence = collect(tmp_path, docs)
    assert completed.returncode == 0, completed.stderr
    assert evidence["run"]["workflow_version"] is None
    assert evidence["definition"]["attached_flow_name"] == SNAPSHOT


@pytest.mark.parametrize("field,value", [("id", "/workflows/contradictory"), ("name", "contradictory")])
def test_contradictory_native_workflow_reference_cannot_be_normalized_away(tmp_path, field, value):
    docs = fixtures(tmp_path)
    docs["run.json"]["body"]["properties"]["workflow"][field] = value
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "RUN_WORKFLOW_REFERENCE_CONFLICT")


@pytest.mark.parametrize("link", [
    ACTIONS_ROUTE.replace("https://", "http://"),
    ACTIONS_ROUTE.replace("api.flow.microsoft.com", "api.flow.microsoft.com.evil.invalid"),
    ACTIONS_ROUTE.replace("https://", "https://attacker@"),
    ACTIONS_ROUTE.replace("/actions?", "/outputs?"),
    ACTIONS_ROUTE.replace("2016-11-01", "2017-06-01"),
    ACTIONS_ROUTE + "#fragment",
    ACTIONS_ROUTE + "&evil=1",
    ACTIONS_ROUTE + "&api-version=2016-11-01",
    ACTIONS_ROUTE + "&skiptokenSourceIndex=arbitrary",
    ACTIONS_ROUTE + "&%24expand=properties%2Fflow",
    ACTIONS_ROUTE.replace("/actions?", "/../actions?"),
    ACTIONS_ROUTE.replace("/actions?", "/%2e%2e/actions?"),
    {"uri": SENTINEL},
])
def test_continuation_cannot_escape_fixed_read_route(tmp_path, link):
    docs = fixtures(tmp_path)
    docs["actions-001.json"]["body"]["nextLink"] = link
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "INVALID_CONTINUATION")


def test_conflicting_continuation_markers_fail_closed(tmp_path):
    docs = fixtures(tmp_path)
    docs["actions-001.json"]["body"].update({"nextLink": ACTIONS_ROUTE + "&$skip=1",
                                          "@odata.nextLink": ACTIONS_ROUTE + "&$skip=2"})
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "CONFLICTING_CONTINUATION")


def test_repeated_url_and_duplicate_action_fail_closed(tmp_path):
    docs = fixtures(tmp_path)
    docs["actions-001.json"]["body"]["nextLink"] = ACTIONS_ROUTE
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "CONTINUATION_LOOP")


def test_duplicate_action_across_pages_fails_closed(tmp_path):
    docs = fixtures(tmp_path)
    docs["actions-001.json"]["body"]["nextLink"] = ACTIONS_ROUTE + "&$skip=1"
    docs["actions-002.json"] = copy.deepcopy(docs["actions-001.json"])
    del docs["actions-002.json"]["body"]["nextLink"]
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "DUPLICATE_RESOURCE")


@pytest.mark.parametrize("status", [302, 403, 500])
def test_redirect_and_http_failures_never_disclose_body(tmp_path, status):
    docs = fixtures(tmp_path)
    docs["actions-001.json"] = envelope({"error": {"message": SENTINEL}}, status=status)
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "HTTP_READ_FAILED")


@pytest.mark.parametrize("fault,code", [
    ("request-time", "REQUEST_DEADLINE"), ("total-time", "REQUEST_DEADLINE"),
    ("page-limit", "PAGE_LIMIT"), ("row-limit", "ROW_LIMIT"),
    ("bad-status", "UNKNOWN_STATUS"), ("bad-time", "INVALID_TIMESTAMP"),
    ("bad-run", "RUN_BINDING_OR_COMPLETENESS"), ("bad-tenant", "AUTH_TENANT_MISMATCH"),
    ("bad-actor", "INVALID_IDENTITY"), ("bad-array", "MALFORMED_COLLECTION"),
])
def test_bounds_and_malformed_evidence_fail_closed(tmp_path, fault, code):
    docs = fixtures(tmp_path)
    if fault == "request-time":
        docs["actions-001.json"]["elapsed_ms"] = 30000
    elif fault == "total-time":
        docs["run.json"]["elapsed_ms"] = 29000
        for page in range(1, 5):
            docs[f"actions-{page:03}.json"] = envelope({
                "value": [action(f"Action_{page}")], "nextLink": ACTIONS_ROUTE + f"&$skip={page}"}, elapsed=29000)
    elif fault == "page-limit":
        for page in range(1, 21):
            docs[f"actions-{page:03}.json"] = envelope({"value": [action(f"Action_{page}")], "nextLink": ACTIONS_ROUTE + f"&$skip={page}"})
    elif fault == "row-limit":
        docs["actions-001.json"]["body"]["value"] = [action(f"Action_{index}") for index in range(1000)]
    elif fault == "bad-status":
        docs["actions-001.json"]["body"]["value"][0]["properties"]["status"] = SENTINEL
    elif fault == "bad-time":
        docs["actions-001.json"]["body"]["value"][0]["properties"]["startTime"] = SENTINEL
    elif fault == "bad-run":
        docs["run.json"]["body"]["name"] = "another-run"
    elif fault == "bad-tenant":
        docs["context.json"]["tenant_id"] = ACTOR
    elif fault == "bad-actor":
        docs["context.json"]["actor_object_id"] = SENTINEL
    elif fault == "bad-array":
        docs["actions-001.json"]["body"]["value"] = {}
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, code)


def test_app_permission_target_on_later_page_requires_complete_traversal(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [permission(principal=ACTOR)],
                                            "nextLink": PERMISSIONS_ROUTE + "&%24skiptoken=opaque"})
    docs["permissions-002.json"] = envelope({"value": [permission(2)]})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert completed.returncode == 0, completed.stderr
    assert evidence["source"] == "offline-app-permission-metadata"
    assert evidence["complete"] and evidence["can_view_verified"]
    assert evidence["assignment_count"] == 2 and len(evidence["matches"]) == 1


def test_target_on_first_page_does_not_bypass_incomplete_later_page(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [permission()],
                                            "nextLink": PERMISSIONS_ROUTE + "&%24skiptoken=opaque"})
    docs["permissions-002.json"] = envelope({"error": {"message": SENTINEL}}, status=403)
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert_failure(completed, evidence, "HTTP_READ_FAILED")


def test_ambiguous_permission_never_verifies_membership(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [permission(), permission(2)]})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert_failure(completed, evidence, "AMBIGUOUS_PERMISSION")


def test_empty_page_with_advancing_cursor_does_not_prove_absence(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [], "nextLink": PERMISSIONS_ROUTE + "&$skip=1"})
    docs["permissions-002.json"] = envelope({"value": [permission()]})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert completed.returncode == 0, completed.stderr
    assert evidence["can_view_verified"]


def test_repeated_empty_page_with_new_cursor_remains_unverified(tmp_path):
    docs = fixtures(tmp_path)
    docs["actions-001.json"] = envelope({"value": [], "nextLink": ACTIONS_ROUTE + "&$skip=1"})
    docs["actions-002.json"] = envelope({"value": [], "nextLink": ACTIONS_ROUTE + "&$skip=2"})
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, "REPEATED_PAGE")


def test_nonviewer_role_remains_unverified(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [permission(role="CanEdit")]})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert completed.returncode == 0, completed.stderr
    assert evidence["complete"] and not evidence["can_view_verified"]


def test_app_continuation_cannot_change_environment_scope(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [permission()],
        "nextLink": PERMISSIONS_ROUTE.replace(ENVIRONMENT, "Default-" + ACTOR)})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert_failure(completed, evidence, "INVALID_CONTINUATION")


def test_action_only_cursor_index_is_refused_for_app_permissions(tmp_path):
    docs = fixtures(tmp_path)
    docs["permissions-001.json"] = envelope({"value": [permission()],
        "nextLink": PERMISSIONS_ROUTE + "&skiptokenSourceIndex=0"})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert_failure(completed, evidence, "INVALID_CONTINUATION")


@pytest.mark.parametrize("mismatch", ["app", "assignment_name"])
def test_permission_row_must_belong_to_requested_app_and_assignment(tmp_path, mismatch):
    docs = fixtures(tmp_path)
    item = permission()
    if mismatch == "app":
        item["id"] = item["id"].replace(APP, ACTOR)
    else:
        item["name"] = "another-assignment"
    docs["permissions-001.json"] = envelope({"value": [item]})
    completed, evidence = collect(tmp_path, docs, "-PermissionProfile", "Stage", "-PrincipalObjectId", TARGET)
    assert_failure(completed, evidence, "PERMISSION_RESOURCE_MISMATCH")


def test_later_request_exception_does_not_report_previous_http_success(tmp_path):
    docs = fixtures(tmp_path)
    docs["actions-001.json"]["body"]["nextLink"] = ACTIONS_ROUTE + "&$skip=1"
    # The fixture for the next request is absent; its read fails before any
    # response, exactly as a native transport exception would.
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence)
    assert json.loads(completed.stderr)["http_status"] is None


def test_existing_output_is_preserved_and_never_reused_as_a_new_capture(tmp_path):
    output = tmp_path / "evidence.json"
    output.write_text('{"previous": true}', encoding="utf-8")
    completed, evidence = collect(tmp_path, fixtures(tmp_path))
    assert completed.returncode == 1
    assert evidence == {"previous": True}
    assert json.loads(completed.stderr)["code"] == "OUTPUT_EXISTS"


def test_clr_watchdog_terminates_a_blocked_powershell_pipeline(tmp_path):
    # Execute the production timer independently of authentication and HTTP.
    # Thread.Sleep blocks PowerShell; the CLR callback must still end the worker.
    source = SCRIPT.read_text(encoding="utf-8")
    watchdog = re.search(r"Add-Type -TypeDefinition @'\n(.*?)\n'@", source, re.S).group(1)
    probe = tmp_path / "watchdog.ps1"
    probe.write_text("Add-Type -TypeDefinition @'\n" + watchdog + "\n'@\n"
                     "[MilstripSharingReadDeadline]::Arm(100)\n"
                     "[Threading.Thread]::Sleep(30000)\n"
                     "Write-Output 'DEADLINE_DID_NOT_FIRE'\n", encoding="utf-8")
    completed = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File", str(probe)],
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 1 and "DEADLINE_DID_NOT_FIRE" not in completed.stdout
    assert json.loads(completed.stderr)["code"] == "WATCHDOG_DEADLINE"


def test_session_reuse_requires_selected_audience_expiry_before_collection(tmp_path):
    source = SCRIPT.read_text(encoding="utf-8")
    function = re.search(r"function Test-FreshMicrosoftSession\(.*?\n}\n", source, re.S).group(0)
    probe = tmp_path / "session-expiry.ps1"
    probe.write_text("$ErrorActionPreference='Stop'\n" + function + "\n" + r'''
$tenantId='9f5c0ace-0780-4b48-8c24-b08bb5149210'
$audience='https://service.flow.microsoft.com/'
$global:currentSession=@{loggedIn=$true;endpoint='prod';tenantId=$tenantId;resourceTokens=@{}}
if (Test-FreshMicrosoftSession $audience) {throw 'Missing audience accepted'}
$global:currentSession.resourceTokens['https://service.powerapps.com/']=@{expiresOn=[DateTimeOffset]::UtcNow.AddHours(1)}
if (Test-FreshMicrosoftSession $audience) {throw 'Wrong audience accepted'}
$global:currentSession.resourceTokens[$audience]=@{expiresOn=[DateTimeOffset]::UtcNow.AddSeconds(60)}
if (Test-FreshMicrosoftSession $audience) {throw 'Near expiry accepted'}
$global:currentSession.resourceTokens[$audience].expiresOn=[DateTimeOffset]::UtcNow.AddMinutes(5)
if (-not (Test-FreshMicrosoftSession $audience)) {throw 'Fresh correct audience refused'}
$global:currentSession.tenantId='11111111-1111-4111-8111-111111111111'
if (Test-FreshMicrosoftSession $audience) {throw 'Wrong tenant accepted'}
Write-Output 'Session metadata guard passed without credential access.'
''', encoding="utf-8")
    completed = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File", str(probe)],
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("fault,code", [
    ("missing-flow", "MISSING_RUN_ATTACHED_DEFINITION"),
    ("snapshot", "HISTORICAL_SNAPSHOT_MISMATCH"),
    ("snapshot-path", "SNAPSHOT_PATH_MISMATCH"),
    ("logical-flow", "SNAPSHOT_LOGICAL_FLOW_MISMATCH"),
    ("metadata-logical-flow", "SNAPSHOT_LOGICAL_FLOW_MISMATCH"),
    ("missing-action", "DEFINITION_ACTION_SET_MISMATCH"),
    ("unexpected-action", "DEFINITION_ACTION_SET_MISMATCH"),
    ("duplicate-action", "DUPLICATE_DEFINITION_ACTION"),
    ("non-object-actions", "MISSING_RUN_ATTACHED_DEFINITION"),
])
def test_attached_definition_and_complete_inventory_are_required(tmp_path, fault, code):
    docs = fixtures(tmp_path)
    props = docs["run.json"]["body"]["properties"]
    flow = props["flow"]
    definition = flow["properties"]["definition"]
    if fault == "missing-flow":
        del props["flow"]
    elif fault == "snapshot":
        flow["name"] = ACTOR
    elif fault == "snapshot-path":
        flow["id"] = flow["id"].replace(SNAPSHOT, ACTOR)
    elif fault == "logical-flow":
        flow["properties"]["workflowEntityId"] = ACTOR
    elif fault == "metadata-logical-flow":
        definition["metadata"]["workflowEntityId"] = ACTOR
    elif fault == "missing-action":
        definition["actions"] = {}
    elif fault == "unexpected-action":
        definition["actions"]["Unknown_external_action"] = definition_action()
    elif fault == "duplicate-action":
        definition["actions"]["Container"] = {"type": "If", "actions": {
            "Acquire_lease_add": definition_action()}}
    elif fault == "non-object-actions":
        definition["actions"] = []
    completed, evidence = collect(tmp_path, docs)
    assert_failure(completed, evidence, code)


def test_definition_inventory_preserves_nested_branch_ancestry(tmp_path):
    docs = fixtures(tmp_path)
    nested = {"Gate": {"type": "If", "actions": {}, "else": {"actions": {
        "Reserve_step": definition_action("ReserveManagementCall")}}}}
    docs["run.json"]["body"]["properties"]["flow"] = attached_flow(nested)
    docs["actions-001.json"]["body"]["value"] = [action("Gate", "Skipped"), action("Reserve_step", "Skipped")]
    completed, evidence = collect(tmp_path, docs)
    assert completed.returncode == 0, completed.stderr
    reserve = evidence["definition"]["actions"][1]
    assert reserve["name"] == "Reserve_step"
    assert reserve["ancestors"] == ["Gate"] and reserve["ancestor_branches"] == ["Gate:else"]
    assert reserve["broker_operation"] == "ReserveManagementCall"


def test_unrecognized_broker_operation_never_exports_raw_definition_parameter(tmp_path):
    docs = fixtures(tmp_path)
    docs["run.json"]["body"]["properties"]["flow"] = attached_flow({
        "Acquire_lease_add": definition_action(SENTINEL)})
    completed, evidence = collect(tmp_path, docs)
    assert completed.returncode == 0, completed.stderr
    assert evidence["definition"]["actions"][0]["broker_operation"] is None
    assert len(evidence["definition"]["sha256"]) == 64
    assert "version" not in evidence["definition"]
