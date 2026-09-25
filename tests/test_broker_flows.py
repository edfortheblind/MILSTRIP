"""Static transport/trust regressions; tenant execution is separate acceptance."""
from copy import deepcopy
import json
import subprocess
import sys
from typing import get_args

import jsonschema
import pytest

from scripts.build_broker_flows import (
    APP_IDS, OPERATIONS, OUT, build, default_bindings, validate_bindings, walk_actions,
)
from api.broker_models import BrokerEnvelope, Operation

INTERNAL_OPERATIONS = {"RecordSharingResult", "AcquireSharingLease",
                       "ReserveManagementCall", "RecordManagementCall"}

def named_actions(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, dict) and "type" in child and "runAfter" in child:
                yield key, child
            yield from named_actions(child)
    elif isinstance(value, list):
        for child in value:
            yield from named_actions(child)


@pytest.fixture
def flow():
    return build()["stage"]


def test_committed_source_is_deterministic():
    subprocess.run([sys.executable, "scripts/build_broker_flows.py", "--check"], check=True)
    assert build() == build()
    assert json.loads((OUT / "bindings.example.json").read_text()) == default_bindings()


def test_native_export_shape_and_official_wdl_builtins(flow):
    baseline = json.loads((OUT / "schema/native-powerapp-v2-baseline.json").read_text())
    assert flow.keys() == baseline.keys()
    assert flow["properties"].keys() == baseline["properties"].keys()
    definition = deepcopy(flow["properties"]["definition"])
    assert definition["triggers"]["manual"]["kind"] == baseline["properties"]["definition"]["triggers"]["manual"]["kind"]
    # Microsoft's WDL schema excludes the Power Automate-specific
    # OpenApiConnection and PowerAppV2 extensions (including native exports).
    # Validate its built-in structure after projecting ONLY those extensions;
    # connector actions are validated independently below. This is not an
    # assertion that the service has accepted the deployable document.
    for item in walk_actions(definition):
        if item["type"] == "OpenApiConnection":
            item["type"], item["inputs"] = "Compose", ""
            item["runtimeConfiguration"]["secureData"]["properties"] = ["inputs"]
        if item.get("kind") == "PowerAppV2":
            item["kind"] = "PowerApp"
    schema = json.loads((OUT / "schema/workflowdefinition-2016-06-01.json").read_text())
    jsonschema.Draft4Validator(schema).validate(definition)


def test_invoker_identity_cannot_be_selected_by_canvas(flow):
    definition = flow["properties"]["definition"]
    trigger = definition["triggers"]["manual"]["inputs"]["schema"]
    assert set(trigger["properties"]) == set(trigger["required"]) == {"operation", "payload_json"}
    assert trigger["additionalProperties"] is False
    actions = dict(named_actions(flow))
    assert actions["Invoker_profile"]["inputs"]["host"]["operationId"] == "MyProfile_V2"
    assert actions["Directory_caller"]["inputs"]["parameters"]["id"] == "@body('Invoker_profile')?['id']"
    actor = actions["Verified_actor"]["inputs"]
    assert set(actor) == {"object_id", "upn", "display_name", "account_enabled", "user_type"}
    assert all("Directory_caller" in value and "triggerBody" not in value for value in actor.values())
    gate = actions["Caller_and_operation_allowed"]["expression"]
    for required in ("accountEnabled", "userType", "Member", "austinlighthouse.org", "Invoker_profile", "Directory_caller"):
        assert required in gate
    refs = flow["properties"]["connectionReferences"]
    assert refs["invoker"]["runtimeSource"] == "invoker"
    assert all(refs[key]["runtimeSource"] == "embedded" for key in ("directory", "broker", "makers", "management"))


def test_internal_sharing_callback_cannot_be_selected_by_canvas(flow):
    assert not INTERNAL_OPERATIONS.intersection(OPERATIONS)
    assert set(OPERATIONS) == set(get_args(Operation)) - INTERNAL_OPERATIONS
    actions = dict(named_actions(flow))
    gate = actions["Caller_and_operation_allowed"]["expression"]
    assert all(operation not in gate for operation in INTERNAL_OPERATIONS)
    for name, item in actions.items():
        if item["type"] != "OpenApiConnection" or item["inputs"]["host"]["connectionName"] != "broker":
            continue
        assert item["inputs"]["host"]["operationId"] == "InvokeBroker"
        envelope = item["inputs"]["parameters"]
        for field in ("object_id", "upn", "display_name", "account_enabled", "user_type"):
            assert envelope[f"body/actor/{field}"] == f"@outputs('Verified_actor')?['{field}']"
        if envelope["body/operation"] == "RecordSharingResult":
            assert name.startswith("Record_sharing_")
            assert "Sharing_result_" in envelope["body/payload_json"]
            assert "triggerBody" not in envelope["body/payload_json"]
        if envelope["body/operation"] == "AcquireSharingLease":
            assert name.startswith("Acquire_lease_")
            assert "Acquire_payload_" in envelope["body/payload_json"]
        if envelope["body/operation"] in {"ReserveManagementCall", "RecordManagementCall"}:
            assert "triggerBody" not in envelope["body/payload_json"]
            assert "Permit_" in envelope["body/payload_json"]
    for suffix in ("add", "remove"):
        data = actions[f"Sharing_result_{suffix}"]["inputs"]
        assert len(data["observations"]) == 4
        assert all(value.startswith("@outputs('Observed_") for value in data["observations"])
        assert "READBACK_FAILED" in data["error_code"]
        assert data["execution_id"] == "@outputs('Request_id')"
        assert "Leased_" in data["lease_id"]
        assert "Succeeded','Skipped" in data["external_calls_complete"]
        assert "Failed" not in data["external_calls_complete"]
        assert data["external_calls_complete"].count("actions(") == 8
        first = actions[f"Plan_{suffix}_stage_app"]
        assert list(first["runAfter"]) == [f"Leased_{suffix}"]


def test_add_uses_directory_but_remove_uses_stored_upn(flow):
    actions = dict(named_actions(flow))
    schema = actions["User_command"]["inputs"]["schema"]
    assert schema["additionalProperties"] is False
    assert "target" not in schema["properties"] and "object_id" not in schema["properties"]
    add = actions["Membership_payload_add"]["inputs"]
    assert all("Get_target" in value for value in add["target"].values())
    remove = actions["Membership_payload_remove"]["inputs"]
    assert "target" not in remove and "User_command" in remove["target_upn"]
    remove_branch = actions["Add_or_remove"]["else"]["actions"]
    assert not any(item["inputs"]["host"]["operationId"] == "UserProfile_V2"
                   for item in walk_actions(remove_branch) if item["type"] == "OpenApiConnection")


def test_no_secrets_in_unprotected_actions_and_no_connector_retries(flow):
    for item in walk_actions(flow):
        kind = item["type"]
        assert kind not in {"InitializeVariable", "SetVariable", "Http", "HttpWebhook"}
        if kind == "If":
            assert "runtimeConfiguration" not in item
            continue
        if kind == "Wait":
            assert "runtimeConfiguration" not in item
            assert set(item["inputs"]) == {"until"}
            assert set(item["inputs"]["until"]) == {"timestamp"}
            assert "['not_before']" in item["inputs"]["until"]["timestamp"]
            continue
        expected = ["inputs"] if kind in {"Compose", "ParseJson", "Response"} else ["inputs", "outputs"]
        assert item["runtimeConfiguration"]["secureData"]["properties"] == expected
        if kind == "OpenApiConnection":
            assert item["inputs"]["retryPolicy"] == {"type": "none"}


def test_management_shapes_match_official_connector_metadata(flow):
    contracts = json.loads((OUT / "schema/management-contracts.json").read_text())["operations"]
    for name, item in named_actions(flow):
        if item["type"] != "OpenApiConnection":
            continue
        operation = item["inputs"]["host"]["operationId"]
        if operation not in contracts:
            continue
        contract = contracts[operation]
        params = item["inputs"]["parameters"]
        root = contract["body_parameter"]
        assert root + "/put" in params and root + "/delete" in params
        # Dynamic deletion arrays are validated by the Select contract below.
        body = {key: params[root + "/" + key] for key in ("put", "delete")}
        if isinstance(body["delete"], str):
            body["delete"] = [{"id": "fixture-permission-id"}]
        jsonschema.Draft4Validator(contract["schema"]).validate(body)
        if operation == "Edit-AppRoleAssignment" and body["put"]:
            properties = body["put"][0]["properties"]
            assert properties["roleName"] == "CanView"
            assert properties["NotifyShareTargetOption"] == "DoNotNotify"
        assert params.get("app", params.get("flowName")) in {
            *APP_IDS.values(), "__STAGE_FLOW_ID__", "__PROD_FLOW_ID__"}
        assert "triggerBody" not in json.dumps(params)


@pytest.mark.parametrize("bound", [False, True])
def test_app_permission_calls_use_official_versions_and_fixed_write_environment(bound):
    contract = json.loads((OUT / "schema/app-role-assignment-contract.json").read_text())["operations"]
    deployment = bindings() if bound else default_bindings()
    counts = {"Get-AppRoleAssignment": 0, "Edit-AppRoleAssignment": 0}
    for flow in build(deployment).values():
        for item in walk_actions(flow):
            if item["type"] != "OpenApiConnection":
                continue
            operation = item["inputs"]["host"]["operationId"]
            if operation not in contract:
                continue
            counts[operation] += 1
            params = item["inputs"]["parameters"]
            metadata = {p["name"]: p for p in contract[operation]["parameters"]}
            assert params["api-version"] == metadata["api-version"]["default"]
            assert params["app"] in APP_IDS.values()
            if operation == "Get-AppRoleAssignment":
                # The Makers GET action exposes no environment filter; select
                # its documented GET version and fixed app ID instead.
                assert contract[operation]["method"] == "get"
                assert "$filter" not in metadata and "$filter" not in params
                assert params["$top"] == 1000
            else:
                assert contract[operation]["method"] == "post"
                assert metadata["$filter"]["in"] == "query"
                assert params["$filter"] == f"environment eq '{deployment['environment_name']}'"
            assert "triggerBody" not in json.dumps(params)
    assert counts == {"Get-AppRoleAssignment": 16, "Edit-AppRoleAssignment": 16}


def test_makers_permission_reads_do_not_aggregate_and_keep_completeness_guards():
    contract = json.loads((OUT / "schema/app-role-assignment-contract.json").read_text())["operations"]
    assert contract["Get-AppRoleAssignment"]["x-ms-pageable"] == {"nextLinkName": "nextLink"}
    for flow in build().values():
        actions = dict(named_actions(flow))
        paginated = []
        for name, item in actions.items():
            runtime = item.get("runtimeConfiguration", {})
            if item["type"] != "OpenApiConnection":
                assert "paginationPolicy" not in runtime
                continue
            host = item["inputs"]["host"]
            eligible = host["connectionName"] == "makers" and host["operationId"] == "Get-AppRoleAssignment"
            if not eligible:
                assert "paginationPolicy" not in runtime
                continue
            paginated.append(name)
            assert runtime == {"secureData": {"properties": ["inputs", "outputs"]}}
            assert item["inputs"]["retryPolicy"] == {"type": "none"}
            assert "uri" not in item["inputs"] and "url" not in item["inputs"]
        assert set(paginated) == {
            f"{phase}_{mode}_{profile}_app" for phase in ("Before", "Readback")
            for mode in ("add", "remove") for profile in ("stage", "prod")}
        # A single page with a continuation or at the row limit is incomplete.
        # Host diagnostics do not authorize this native mutation branch.
        for mode in ("add", "remove"):
            for profile in ("stage", "prod"):
                key = f"{mode}_{profile}_app"
                for name, expression, read in (
                    (f"Mutate_{key}", actions[f"Mutate_{key}"]["expression"], f"Before_{key}"),
                    (f"Observed_{key}", actions[f"Observed_{key}"]["inputs"]["verified"], f"Readback_{key}"),
                ):
                    assert f"empty(body('{read}')?['nextLink'])" in expression, name
                    assert f"empty(body('{read}')?['@odata.nextLink'])" in expression, name
                    assert f"less(length(coalesce(body('{read}')?['value'], json('[]'))), 1000)" in expression, name
                verified = actions[f"Observed_{key}"]["inputs"]["verified"]
                assert f"equals(actions('Readback_{key}')?['status'], 'Succeeded')" in verified
                assert f"equals(actions('Found_{key}')?['status'], 'Succeeded')" in verified
                assert f"equals(length(coalesce(body('Plan_{key}'), json('[]'))), 1)" in verified


def test_broker_body_uses_nine_native_designer_parameter_leaves(flow):
    schema = BrokerEnvelope.model_json_schema()
    actor = schema["$defs"]["DirectoryPerson"]
    expected = {"body/" + field for field in schema["required"] if field != "actor"}
    expected |= {"body/actor/" + field for field in actor["required"]}
    assert len(expected) == 9
    count = 0
    for item in walk_actions(flow):
        if item["type"] != "OpenApiConnection" or item["inputs"]["host"]["operationId"] != "InvokeBroker":
            continue
        count += 1
        parameters = item["inputs"]["parameters"]
        assert set(parameters) == expected
        assert "body" not in parameters and "body/actor" not in parameters
        assert parameters["body/schema_version"] == 1
        assert parameters["body/request_id"] == "@outputs('Request_id')"
        assert all(parameters["body/actor/" + field] == f"@outputs('Verified_actor')?['{field}']"
                   for field in actor["required"])
    assert count == 39


def test_readback_does_not_treat_failure_or_pagination_as_verified_absence(flow):
    actions = dict(named_actions(flow))
    for name, item in named_actions(flow):
        if name.startswith("Observed_"):
            value = item["inputs"]["verified"]
            assert "Succeeded" in value and "nextLink" in value and "@odata.nextLink" in value
            assert "1000" in value and "length(coalesce" in value
        if name.startswith("Readback_") and item["type"] == "OpenApiConnection":
            prerequisite = actions["Permit_payload_" + name] if name.endswith("_flow") else item
            assert list(prerequisite["runAfter"].values()) == [["Succeeded", "Failed", "Skipped", "TimedOut"]]


def test_readback_diagnostics_distinguish_guard_failures_without_disclosing_content(flow):
    from api.broker_models import SharingResult

    codes = SharingResult.model_json_schema()["properties"]["error_code"]["anyOf"][0]["enum"]
    actions = dict(named_actions(flow))
    expected_reasons = ("PLAN_MISMATCH", "CALL_FAILED", "FILTER_FAILED", "PAGINATED", "ROW_LIMIT", "PERMISSION_MISMATCH")
    for mode in ("add", "remove"):
        names = []
        for profile in ("stage", "prod"):
            for kind in ("app", "flow"):
                key = f"{mode}_{profile}_{kind}"
                name = f"Readback_reason_{key}"
                names.append(name)
                diagnostic = actions[name]
                assert diagnostic["type"] == "Compose"
                assert diagnostic["runAfter"] == {f"Observed_{key}": ["Succeeded"]}
                expression = diagnostic["inputs"]
                reason_codes = [f"READBACK_{reason}_{profile.upper()}_{kind.upper()}" for reason in expected_reasons]
                assert all(code in codes for code in reason_codes)
                assert [expression.index(code) for code in reason_codes] == sorted(expression.index(code) for code in reason_codes)
                # Native successful GET/filter with a continuation must remain
                # unverified, but now identifies pagination rather than hiding
                # it behind the generic READBACK_FAILED result.
                assert f"not(equals(length(coalesce(body('Plan_{key}'), json('[]'))), 1))" in expression
                assert f"actions('Readback_{key}')?['status']" in expression
                assert f"actions('Found_{key}')?['status']" in expression
                assert f"not(empty(body('Readback_{key}')?['nextLink']))" in expression
                assert f"not(empty(body('Readback_{key}')?['@odata.nextLink']))" in expression
                assert f"length(coalesce(body('Readback_{key}')?['value'], json('[]'))), 1000" in expression
                assert f"outputs('Observed_{key}')?['present']" in expression
                assert "triggerBody" not in expression and "principal" not in expression and "target" not in expression
                # Every return arm is a closed code or null, never the source
                # body, an identity field, a URL or an exception message.
                import re
                assert re.findall(r", '(READBACK_[A-Z_]+)',", expression) == reason_codes
                assert expression.endswith("null))))))")
                assert diagnostic["runtimeConfiguration"]["secureData"]["properties"] == ["inputs"]
        error = actions[f"Sharing_result_{mode}"]["inputs"]["error_code"]
        assert error.startswith("@coalesce(" + ",".join(f"outputs('{name}')" for name in names))
        # Sharing mutations and verification predicates remain fail-closed;
        # diagnostic values never replace the original observations.
        for name in names:
            key = name.removeprefix("Readback_reason_")
            assert "Succeeded" in actions[f"Observed_{key}"]["inputs"]["verified"]


def test_every_management_call_holds_global_permit_through_completion(flow):
    actions = dict(named_actions(flow))
    steps = set()
    for name, item in actions.items():
        if item["type"] != "OpenApiConnection" or item["inputs"]["host"]["connectionName"] != "management":
            continue
        steps.add(name)
        identity = actions["Permit_payload_" + name]["inputs"]
        assert set(identity) == {"plan_id", "revision", "lease_id", "execution_id", "step"}
        assert identity["step"] == name
        assert identity["execution_id"] == "@outputs('Request_id')"
        assert all("Leased_" in identity[key] for key in ("plan_id", "revision", "lease_id"))
        assert "triggerBody" not in json.dumps(identity)
        reserve = actions["Reserve_" + name]
        assert reserve["inputs"]["parameters"]["body/operation"] == "ReserveManagementCall"
        assert reserve["runAfter"] == {"Permit_payload_" + name: ["Succeeded"]}
        wait = actions["Wait_" + name]
        assert wait["type"] == "Wait"
        assert wait["runAfter"] == {"Reserve_" + name: ["Succeeded"]}
        assert "Reserve_" + name in wait["inputs"]["until"]["timestamp"]
        assert item["runAfter"] == {"Wait_" + name: ["Succeeded"]}
        result = actions["Permit_result_" + name]
        assert result["runAfter"] == {
            name: ["Succeeded", "Failed", "Skipped", "TimedOut"],
            "Reserve_" + name: ["Succeeded"],
        }
        assert all(result["inputs"][key] == value for key, value in identity.items())
        known = result["inputs"]["outcome_known"]
        assert "'Succeeded','Skipped'" in known and "Failed" not in known and "TimedOut" not in known
        assert "Reserve_" + name in result["inputs"]["reservation_id"]
        record = actions["Record_permit_" + name]
        assert record["inputs"]["parameters"]["body/operation"] == "RecordManagementCall"
        assert record["runAfter"] == {"Permit_result_" + name: ["Succeeded"]}
        if name.startswith(("Before_", "Readback_")):
            consumer = ("Matched_" if name.startswith("Before_") else "Found_") + name.split("_", 1)[1]
            assert actions[consumer]["runAfter"] == {
                name: ["Succeeded"], "Record_permit_" + name: ["Succeeded"]}
    expected = {f"{prefix}_{mode}_{environment}_flow" for prefix in ("Before", "Add", "Remove", "Readback")
                for mode in ("add", "remove") for environment in ("stage", "prod")}
    assert steps == expected


def test_action_dependencies_are_in_scope_and_nesting_is_bounded(flow):
    def check_group(group, depth=0):
        assert depth <= 8
        for item in group.values():
            assert set(item.get("runAfter", {})) <= set(group)
            if item["type"] == "If":
                check_group(item["actions"], depth + 1)
                check_group(item["else"]["actions"], depth + 1)
    check_group(flow["properties"]["definition"]["actions"])


def bindings():
    value = default_bindings()
    value.update(tenant_id="11111111-1111-4111-8111-111111111111", environment_name="Default-test",
                 deployed_owner_object_id="33333333-3333-4333-8333-333333333333",
                 management_metadata_verified=True)
    for key, item in value["shared_connections"].items():
        item.update(logical_name="tab_" + key, connection_name="connection-" + key)
    for index, (profile, item) in enumerate(value["profiles"].items(), 1):
        item.update(flow_id=f"22222222-2222-4222-8222-{index:012d}",
                    broker_reference="tab_broker_" + profile, broker_connection="broker-" + profile)
    return value


def test_binding_requires_resolved_resources_and_distinct_trust_connections():
    value = bindings()
    validate_bindings(value)
    with pytest.raises(ValueError):
        validate_bindings(default_bindings())
    for mutator in (
        lambda x: x.update(management_metadata_verified=False),
        lambda x: x.update(connector_api_id="different"),
        lambda x: x["profiles"]["prod"].update(app_id=APP_IDS["stage"]),
        lambda x: x["profiles"]["prod"].update(flow_id=x["profiles"]["stage"]["flow_id"]),
        lambda x: x["profiles"]["prod"].update(broker_connection=x["profiles"]["stage"]["broker_connection"]),
        lambda x: x["profiles"]["prod"].update(broker_reference=x["profiles"]["stage"]["broker_reference"]),
        lambda x: x["shared_connections"]["directory"].update(logical_name=x["shared_connections"]["invoker"]["logical_name"]),
    ):
        invalid = deepcopy(value)
        mutator(invalid)
        with pytest.raises(ValueError):
            validate_bindings(invalid)


def test_only_verified_deployment_owner_is_a_view_access_exception(flow):
    for name, item in named_actions(flow):
        if name.startswith("Observed_") and name.endswith("_app"):
            present = item["inputs"]["present"]
            assert "VERIFIED_DEPLOYMENT_OWNER_OBJECT_ID" in present
            assert "'Owner'" in present and "'CanView'" in present and "'CanEdit'" not in present
        if name.startswith("Mutate_") and name.endswith("_app"):
            # Existing ownership is never a grant/edit target.
            assert "'CanView'" in item["expression"]
            assert "'Owner'" not in item["expression"] and "'CanEdit'" not in item["expression"]


@pytest.mark.parametrize("environment", ["stage", "prod"])
def test_native_run_only_record_without_role_name_counts_as_present(flow, environment):
    fixture = json.loads((OUT / "schema/native-run-only-permissions.json").read_text())
    native = fixture["profiles"][environment]
    target = native["users"][0]["properties"]["principal"]["id"]
    assert native["owners"][0]["properties"]["principal"]["id"] == target
    row = native["users"][0]
    assert row["type"] == "/providers/Microsoft.ProcessSimple/environments/flows/users"
    assert row["properties"]["permissionType"] == "Principal"
    assert row["properties"]["principal"]["type"] == "User"
    assert "roleName" not in row["properties"]
    actions = dict(named_actions(flow))
    for mode in ("add", "remove"):
        key = f"{mode}_{environment}_flow"
        readback = actions[f"Readback_{key}"]
        assert readback["inputs"]["host"]["operationId"] == "ListFlowUsers"
        found = actions[f"Found_{key}"]["inputs"]
        assert found["from"] == f"@coalesce(body('Readback_{key}')?['value'], json('[]'))"
        assert found["where"] == (
            "@equals(toLower(coalesce(item()?['properties']?['principal']?['id'], '')), "
            f"toLower(outputs('Leased_{mode}')?['sharing_plan']?['target']?['object_id']))")
        present = actions[f"Observed_{key}"]["inputs"]["present"]
        assert present == f"@greater(length(coalesce(body('Found_{key}'), json('[]'))), 0)"
        # Evaluate those exact ID-equality/count semantics on the native item
        # shape, including case-insensitive matching and a different principal.
        for requested, expected in ((target.upper(), True), ("unlisted-principal", False)):
            matched = [item for item in native["users"]
                       if item["properties"]["principal"]["id"].lower() == requested.lower()]
            assert (len(matched) > 0) is expected
