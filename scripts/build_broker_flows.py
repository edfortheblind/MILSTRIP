"""Build deterministic, disabled solution cloud-flow source. Does not deploy.

The checked-in templates intentionally contain unresolved connection bindings.
See powerapps/flows/README.md for the Microsoft source/schema references and the
remaining tenant acceptance requirements.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID, NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerapps" / "flows"
SCHEMA = "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
DOMAIN = "austinlighthouse.org"
OPERATIONS = (
    "GetCurrentUser", "GetHealth", "ListIntakeRequests", "GetIntakeRequest",
    "ListRecordResults", "ListAuditEvents", "CreateIntakeRequest", "CreateReviewDecision",
    "ListUsers", "SaveUserAccess", "GetRuntimeProfiles", "SaveRuntimeDraft",
    "TestRuntimeDraft", "ApplyRuntimeDraft", "GetAdministrationOperation",
    "InitializeRuntimeDraft", "GetIntakeWorkflow",
)
TERMINAL = ["Succeeded", "Failed", "Skipped", "TimedOut"]
API_PREFIX = "/providers/Microsoft.PowerApps/apis/"
APIS = {"invoker": "shared_office365users", "directory": "shared_office365users",
        "makers": "shared_powerappsforappmakers", "management": "shared_flowmanagement"}
PROFILE_FIELDS = "id,userPrincipalName,displayName,accountEnabled,userType"
APP_IDS = {"stage": "7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82",
           "prod": "0aa02d8b-c7fa-42cc-87e8-6d287bd4c897"}
BODY_SCHEMAS = {"ok": "boolean", "status": "integer", "request_id": "string",
                "result_json": "string", "error_code": "string", "error_message": "string"}


def default_bindings():
    canvas = json.loads((ROOT / "powerapps/canvas/deployment-manifest.json").read_text())
    return {
        "tenant_id": "__TENANT_ID__", "environment_name": "__POWER_PLATFORM_ENVIRONMENT__",
        "deployed_owner_object_id": "__VERIFIED_DEPLOYMENT_OWNER_OBJECT_ID__",
        "connector_api_id": canvas["connector_api_id"],
        "management_metadata_verified": False,
        "shared_connections": {key: {"logical_name": f"__{key.upper()}_REFERENCE__",
                                     "connection_name": f"__{key.upper()}_CONNECTION__"}
                               for key in APIS},
        "profiles": {profile: {
            "app_id": APP_IDS[profile], "flow_id": f"__{profile.upper()}_FLOW_ID__",
            "broker_reference": f"__{profile.upper()}_BROKER_REFERENCE__",
            "broker_connection": f"__{profile.upper()}_PRIVATE_BROKER_CONNECTION__",
        } for profile in ("stage", "prod")},
    }


def after(name=None, statuses=None):
    return {} if name is None else {name: statuses or ["Succeeded"]}


def action(action_type, inputs=None, previous=None, secure=True, **other):
    result = {"type": action_type, "runAfter": after(previous), **other}
    if inputs is not None:
        result["inputs"] = inputs
    if secure:
        # Microsoft documents inputs-only protection for these built-ins; their
        # outputs are hidden as a consequence. Variables/scopes are never used
        # as secret containers.
        props = ["inputs"] if action_type in {"Compose", "ParseJson", "Response"} else ["inputs", "outputs"]
        result["runtimeConfiguration"] = {"secureData": {"properties": props}}
    return result


def response(ok=False, status=403, code="ACCESS_DENIED", message="Access is not authorized.",
             result="", previous=None):
    return action("Response", {
        "statusCode": 200,
        "body": {"ok": ok, "status": status, "request_id": "@outputs('Request_id')",
                 "result_json": result, "error_code": code, "error_message": message},
        "schema": {"type": "object", "properties": {
            key: {"type": value, "title": key, "x-ms-dynamically-added": True}
            for key, value in BODY_SCHEMAS.items()}},
    }, previous, kind="PowerApp")


def condition(expression, yes, no=None, previous=None):
    return action("If", previous=previous, secure=False, expression=expression,
                  actions=yes, **{"else": {"actions": no or {}}})


def compose(inputs, previous=None):
    return action("Compose", inputs, previous)


def query(source, predicate, previous=None):
    return action("Query", {"from": source, "where": predicate}, previous)


def readback_reason(key, plan, readback, found, observation):
    """Return only a fixed reason code; never return rows or continuation URLs."""
    resource = key.split("_", 1)[1].upper()
    checks = (
        (f"not(equals(length(coalesce(body('{plan}'), json('[]'))), 1))", "PLAN_MISMATCH"),
        (f"not(equals(actions('{readback}')?['status'], 'Succeeded'))", "CALL_FAILED"),
        (f"not(equals(actions('{found}')?['status'], 'Succeeded'))", "FILTER_FAILED"),
        (f"or(not(empty(body('{readback}')?['nextLink'])), not(empty(body('{readback}')?['@odata.nextLink'])))", "PAGINATED"),
        (f"not(less(length(coalesce(body('{readback}')?['value'], json('[]'))), 1000))", "ROW_LIMIT"),
        (f"not(equals(outputs('{observation}')?['present'], first(union(coalesce(body('{plan}'), json('[]')), createArray(json('{{}}'))))?['present']))", "PERMISSION_MISMATCH"),
    )
    result = "null"
    for predicate, code in reversed(checks):
        result = f"if({predicate}, 'READBACK_{code}_{resource}', {result})"
    return "@" + result


class Builder:
    def __init__(self, profile, bindings):
        self.profile, self.bindings = profile, bindings
        self.connector = bindings["connector_api_id"].split("/")[-1]

    def connection(self, name, operation, params, previous=None):
        api = self.connector if name == "broker" else APIS[name]
        result = action("OpenApiConnection", {
            "host": {"apiId": API_PREFIX + api, "connectionName": name, "operationId": operation},
            "parameters": params, "authentication": "@parameters('$authentication')",
            "retryPolicy": {"type": "none"},
        }, previous)
        # Do not turn on connector-side aggregation: the native trial stalled
        # indefinitely. A continuation on a single page remains unverified;
        # host diagnostics are not an alternative authorization path.
        return result

    def invoke(self, operation, payload, previous=None):
        # Native designer serializes the required body leaves as parameter paths.
        # Whole-object `body` works at runtime but is not recognized by its Save
        # validation; keep only the nine schema-derived native parameter keys.
        parameters = {"body/schema_version": 1, "body/request_id": "@outputs('Request_id')",
                      "body/operation": operation, "body/payload_json": payload}
        parameters.update({f"body/actor/{field}": f"@outputs('Verified_actor')?['{field}']"
                           for field in ("object_id", "upn", "display_name", "account_enabled", "user_type")})
        return self.connection("broker", "InvokeBroker", parameters, previous)

    def fail_after(self, source, code="REQUEST_FAILED"):
        result = response(status=f"@coalesce(outputs('{source}')?['statusCode'], 503)",
                          code=code, message="Request did not complete. Check its status before retrying.")
        result["runAfter"] = after(source, ["Failed", "TimedOut"])
        return result

    def complete_invoke(self, name, operation, payload):
        return {
            name: self.invoke(operation, payload),
            name + "_response": response(True, 200, "", "", f"@body('{name}')?['result_json']", name),
            name + "_failure": self.fail_after(name),
        }

    def pace_management(self, group, suffix):
        """Hold the shared connector permit through each external call.

        Waiting uses the server timestamp, then completion starts the next
        cooldown. A delayed flow cannot consume an expired future slot alongside
        another flow. Unknown outcomes retain the permit for host recovery.
        """
        paced = {}
        completed = {}
        for name, item in group.items():
            if item["type"] == "If":
                self.pace_management(item["actions"], suffix)
                self.pace_management(item["else"]["actions"], suffix)
            is_management = (item["type"] == "OpenApiConnection" and
                item["inputs"]["host"]["connectionName"] == "management")
            if not is_management:
                paced[name] = item
                continue
            payload, reserve, wait, result, record = (
                f"{prefix}_{name}" for prefix in
                ("Permit_payload", "Reserve", "Wait", "Permit_result", "Record_permit"))
            identity = {
                "plan_id": f"@outputs('Leased_{suffix}')?['sharing_plan']?['plan_id']",
                "revision": f"@outputs('Leased_{suffix}')?['sharing_plan']?['revision']",
                "lease_id": f"@outputs('Leased_{suffix}')?['lease_id']",
                "execution_id": "@outputs('Request_id')", "step": name,
            }
            paced[payload] = compose(identity)
            paced[payload]["runAfter"] = item["runAfter"]
            paced[reserve] = self.invoke("ReserveManagementCall", f"@string(outputs('{payload}'))", payload)
            paced[wait] = action("Wait", {"until": {
                "timestamp": f"@json(body('{reserve}')?['result_json'])?['not_before']"}},
                reserve, secure=False)
            item["runAfter"] = after(wait)
            paced[name] = item
            paced[result] = compose({**identity,
                "reservation_id": f"@json(body('{reserve}')?['result_json'])?['reservation_id']",
                "outcome_known": f"@contains(createArray('Succeeded','Skipped'), actions('{name}')?['status'])"})
            # No callback is fabricated when reservation failed or was skipped.
            paced[result]["runAfter"] = {**after(name, TERMINAL), **after(reserve)}
            paced[record] = self.invoke("RecordManagementCall", f"@string(outputs('{result}'))", result)
            completed[name] = record
        # Consumers retain the original action-status condition AND require its
        # permit callback. Readback still starts after every mutation outcome.
        for name, item in paced.items():
            if name.startswith("Permit_result_"):
                continue
            for dependency in list(item["runAfter"]):
                if dependency in completed:
                    item["runAfter"][completed[dependency]] = ["Succeeded"]
        group.clear()
        group.update(paced)

    def membership(self, adding):
        suffix = "add" if adding else "remove"
        result = {}
        if adding:
            result["Get_target"] = self.connection("directory", "UserProfile_V2", {
                "id": "@toLower(trim(body('User_command')?['target_upn']))", "$select": PROFILE_FIELDS})
            result["Get_target_failure"] = self.fail_after("Get_target", "DIRECTORY_UNAVAILABLE")
        command = {key: f"@body('User_command')?['{key}']" for key in
                   ("command_id", "expected_revision", "role", "active")}
        if adding:
            command["target"] = {key: f"@body('Get_target')?['{source}']" for key, source in {
                "object_id": "id", "upn": "userPrincipalName", "display_name": "displayName",
                "account_enabled": "accountEnabled", "user_type": "userType"}.items()}
        else:
            # Removal deliberately does not require a surviving directory object.
            command["target_upn"] = "@toLower(trim(body('User_command')?['target_upn']))"
        save = {
            f"Membership_payload_{suffix}": compose(command),
            f"Save_membership_{suffix}": self.invoke("SaveUserAccess", f"@string(outputs('Membership_payload_{suffix}'))",
                                                     f"Membership_payload_{suffix}"),
            f"Save_failure_{suffix}": self.fail_after(f"Save_membership_{suffix}"),
            f"Saved_{suffix}": compose(f"@json(body('Save_membership_{suffix}')?['result_json'])",
                                        f"Save_membership_{suffix}"),
            f"Saved_response_failure_{suffix}": self.fail_after(f"Saved_{suffix}", "SHARING_PENDING"),
        }
        save.update(self.reconcile(suffix))
        if adding:
            valid = "@and(equals(body('Get_target')?['accountEnabled'], true), equals(body('Get_target')?['userType'], 'Member'), equals(toLower(coalesce(body('Get_target')?['userPrincipalName'], '')), toLower(trim(body('User_command')?['target_upn']))))"
            result["Target_is_internal"] = condition(valid, save,
                {"Target_denied": response(code="INVALID_TARGET", message="Select an enabled corporate member.")}, "Get_target")
        else:
            result.update(save)
        return result

    def reconcile(self, suffix):
        """Reconcile the four fixed resources, then submit only observed results.

        Connector edit parameter shapes are draft until checked against tenant
        metadata. Readback failure/pagination never becomes a verified absence.
        """
        saved = f"outputs('Leased_{suffix}')"
        target = f"{saved}?['sharing_plan']?['target']?['object_id']"
        resources = f"{saved}?['sharing_plan']?['resources']"
        actions = {
            f"Acquire_payload_{suffix}": compose({
                "plan_id": f"@outputs('Saved_{suffix}')?['sharing_plan']?['plan_id']",
                "revision": f"@outputs('Saved_{suffix}')?['sharing_plan']?['revision']",
                "execution_id": "@outputs('Request_id')",
                "native_run": {"environment_name": self.bindings["environment_name"],
                               "flow_id": self.bindings["profiles"][self.profile]["flow_id"],
                               "run_id": "@workflow().run.name"}}),
            f"Acquire_lease_{suffix}": self.invoke("AcquireSharingLease",
                f"@string(outputs('Acquire_payload_{suffix}'))", f"Acquire_payload_{suffix}"),
            f"Lease_failure_{suffix}": self.fail_after(f"Acquire_lease_{suffix}", "SHARING_PENDING"),
            f"Leased_{suffix}": compose(f"@json(body('Acquire_lease_{suffix}')?['result_json'])", f"Acquire_lease_{suffix}"),
            f"Leased_response_failure_{suffix}": self.fail_after(f"Leased_{suffix}", "SHARING_PENDING"),
        }
        previous = f"Leased_{suffix}"
        observations = []
        diagnostics = []
        external_actions = []
        for environment in ("stage", "prod"):
            for kind in ("app", "flow"):
                key = f"{suffix}_{environment}_{kind}"
                resource_id = self.bindings["profiles"][environment][kind + "_id"]
                permission = "CanView" if kind == "app" else "run-only"
                plan, before, matched, mutate, readback, found, observation = (
                    f"{x}_{key}" for x in ("Plan", "Before", "Matched", "Mutate", "Readback", "Found", "Observed"))
                actions[plan] = query("@" + resources,
                    f"@and(equals(item()?['kind'], '{kind}'), equals(item()?['resource_id'], '{resource_id}'), equals(item()?['permission'], '{permission}'), equals(item()?['environment'], '{environment}'))", previous)
                params = {"app": resource_id, "api-version": "2017-06-01", "$top": 1000} if kind == "app" else {
                    "environmentName": self.bindings["environment_name"], "flowName": resource_id}
                connector, get_op = ("makers", "Get-AppRoleAssignment") if kind == "app" else ("management", "ListFlowUsers")
                actions[before] = self.connection(connector, get_op, params, plan)
                predicate = f"@equals(toLower(coalesce(item()?['properties']?['principal']?['id'], '')), toLower({target}))"
                actions[matched] = query(f"@coalesce(body('{before}')?['value'], json('[]'))", predicate, before)
                # Fixed IDs and exact API-issued plan are checked before any mutation.
                valid = f"@and(equals(length(body('{plan}')), 1), equals({saved}?['sharing_plan']?['target']?['tenant_id'], '{self.bindings['tenant_id']}'), not(empty({target})), empty(body('{before}')?['nextLink']), empty(body('{before}')?['@odata.nextLink']), less(length(coalesce(body('{before}')?['value'], json('[]'))), 1000))"
                principal = {"id": "@" + target, "type": "User"}
                if kind == "app":
                    edit_scope = {"app": resource_id, "api-version": "2016-11-01",
                                  "$filter": f"environment eq '{self.bindings['environment_name']}'"}
                    add_params = {**edit_scope, "body/put": [{"properties": {
                        "principal": {**principal, "tenantId": self.bindings["tenant_id"]}, "roleName": "CanView",
                        "NotifyShareTargetOption": "DoNotNotify"}}], "body/delete": []}
                    remove_params = {**edit_scope, "body/put": [],
                                     "body/delete": f"@body('Assignment_ids_{key}')"}
                    edit_op = "Edit-AppRoleAssignment"
                    may_edit = f"@or(empty(body('{matched}')), and(equals(length(body('{matched}')), 1), equals(first(union(body('{matched}'), createArray(json('{{}}'))))?['properties']?['roleName'], 'CanView')))"
                else:
                    add_params = {**params, "permissions/put": [{"properties": {"principal": principal}}], "permissions/delete": []}
                    remove_params = {**params, "permissions/put": [], "permissions/delete": [{"properties": {"principal": principal}}]}
                    edit_op, may_edit = "ModifyRunOnlyUsers", "@true"
                remove_actions = {}
                if kind == "app":
                    remove_actions[f"Assignment_ids_{key}"] = action("Select", {
                        "from": f"@body('{matched}')", "select": {"id": "@item()?['id']"}})
                remove_actions[f"Remove_{key}"] = self.connection(connector, edit_op, remove_params,
                    f"Assignment_ids_{key}" if kind == "app" else None)
                external_actions.extend((f"Add_{key}", f"Remove_{key}"))
                mutation = condition(f"@equals(first(body('{plan}'))?['present'], true)",
                    {f"Add_{key}": self.connection(connector, edit_op, add_params)}, remove_actions)
                desired = f"first(union(body('{plan}'), createArray(json('{{}}'))))?['present']"
                needs_write = f"or(and(equals({desired}, true), empty(body('{matched}'))), and(equals({desired}, false), not(empty(body('{matched}')))))"
                actions[mutate] = condition(f"@and({valid[1:]}, {may_edit[1:]}, {needs_write})",
                    {f"Desired_{key}": mutation}, previous=matched)
                actions[readback] = self.connection(connector, get_op, params)
                actions[readback]["runAfter"] = after(mutate, TERMINAL)
                actions[found] = query(f"@coalesce(body('{readback}')?['value'], json('[]'))", predicate, readback)
                verified = f"@and(equals(actions('{readback}')?['status'], 'Succeeded'), equals(actions('{found}')?['status'], 'Succeeded'), equals(length(coalesce(body('{plan}'), json('[]'))), 1), empty(body('{readback}')?['nextLink']), empty(body('{readback}')?['@odata.nextLink']), less(length(coalesce(body('{readback}')?['value'], json('[]'))), 1000))"
                present = f"@greater(length(coalesce(body('{found}'), json('[]'))), 0)"
                if kind == "app":
                    # The one verified deployment Owner already has view access.
                    # Never grant/downgrade ownership or accept other edit grants.
                    role = f"first(union(coalesce(body('{found}'), json('[]')), createArray(json('{{}}'))))?['properties']?['roleName']"
                    owner = self.bindings["deployed_owner_object_id"]
                    present = f"@and(equals(length(coalesce(body('{found}'), json('[]'))), 1), or(equals({role}, 'CanView'), and(equals({role}, 'Owner'), equals(toLower({target}), '{owner}'))))"
                actions[observation] = compose({"kind": kind, "resource_id": resource_id,
                    "permission": permission, "present": present, "verified": verified})
                actions[observation]["runAfter"] = after(found, TERMINAL)
                observations.append("@outputs('" + observation + "')")
                diagnostic = f"Readback_reason_{key}"
                actions[diagnostic] = compose(readback_reason(key, plan, readback, found, observation), observation)
                diagnostics.append(f"outputs('{diagnostic}')")
                previous = diagnostic
        payload = {"plan_id": "@" + saved + "?['sharing_plan']?['plan_id']",
                   "revision": "@" + saved + "?['sharing_plan']?['revision']",
                   "lease_id": "@" + saved + "?['lease_id']",
                   "execution_id": "@outputs('Request_id')",
                   "external_calls_complete": "@and(" + ",".join(
                       f"contains(createArray('Succeeded','Skipped'), actions('{name}')?['status'])"
                       for name in external_actions) + ")",
                   "observations": observations,
                   "error_code": "@coalesce(" + ",".join(diagnostics) + ",if(and(" + ",".join(
                       item[1:] + "?['verified']" for item in observations) + "), null, 'READBACK_FAILED'))"}
        actions[f"Sharing_result_{suffix}"] = compose(payload, previous)
        actions[f"Record_sharing_{suffix}"] = self.invoke("RecordSharingResult",
            f"@string(outputs('Sharing_result_{suffix}'))", f"Sharing_result_{suffix}")
        actions[f"Sharing_response_{suffix}"] = response(True, 200, "", "",
            f"@body('Record_sharing_{suffix}')?['result_json']", f"Record_sharing_{suffix}")
        actions[f"Sharing_failure_{suffix}"] = self.fail_after(f"Record_sharing_{suffix}", "SHARING_PENDING")
        self.pace_management(actions, suffix)
        return {f"Sharing_needed_{suffix}": condition(
            f"@not(equals(outputs('Saved_{suffix}')?['sharing_plan']?['status'], 'completed'))", actions,
            {f"Already_shared_{suffix}": response(True, 200, "", "",
                f"@body('Save_membership_{suffix}')?['result_json']")}, f"Saved_{suffix}")}

    def build(self):
        props = {key: {"title": key, "type": "string", "x-ms-dynamically-added": True,
                       "description": key, "x-ms-content-hint": "TEXT"}
                 for key in ("operation", "payload_json")}
        trigger = action("Request", {"schema": {"type": "object", "properties": props,
                         "required": list(props), "additionalProperties": False}}, kind="PowerAppV2")
        trigger.pop("runAfter")
        ordinary = self.complete_invoke("Invoke_operation", "@triggerBody()?['operation']", "@triggerBody()?['payload_json']")
        fields = {"command_id": {"type": "string", "format": "uuid"},
                  "expected_revision": {"type": "string", "format": "uuid"},
                  "target_upn": {"type": "string", "minLength": 3, "maxLength": 254},
                  "role": {"type": "string", "enum": ["ADMIN", "OPERATOR"]}, "active": {"type": "boolean"}}
        membership = {
            "User_command": action("ParseJson", {"content": "@json(triggerBody()?['payload_json'])",
                "schema": {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}}),
            "Invalid_user_command": self.fail_after("User_command", "INVALID_COMMAND"),
            "Corporate_target": condition(
                f"@and(endsWith(toLower(trim(body('User_command')?['target_upn'])), '@{DOMAIN}'), equals(length(split(trim(body('User_command')?['target_upn']), '@')), 2))",
                {"Add_or_remove": condition("@equals(body('User_command')?['active'], true)",
                    self.membership(True), self.membership(False))},
                {"Target_domain_denied": response(code="INVALID_TARGET", message="Select a corporate user.")}, "User_command"),
        }
        dispatch = condition("@equals(triggerBody()?['operation'], 'SaveUserAccess')", membership, ordinary)
        actor = {key: f"@body('Directory_caller')?['{source}']" for key, source in {
            "object_id": "id", "upn": "userPrincipalName", "display_name": "displayName",
            "account_enabled": "accountEnabled", "user_type": "userType"}.items()}
        valid = f"@and(equals(toLower(coalesce(body('Invoker_profile')?['id'], '')), toLower(coalesce(body('Directory_caller')?['id'], ''))), not(empty(body('Invoker_profile')?['id'])), equals(body('Directory_caller')?['accountEnabled'], true), equals(body('Directory_caller')?['userType'], 'Member'), endsWith(toLower(coalesce(body('Directory_caller')?['userPrincipalName'], '')), '@{DOMAIN}'))"
        allowed = "@contains(createArray(" + ",".join("'" + op + "'" for op in OPERATIONS) + "), triggerBody()?['operation'])"
        actions = {
            "Request_id": compose("@guid()"),
            "Invoker_profile": self.connection("invoker", "MyProfile_V2", {"$select": "id"}, "Request_id"),
            "Invoker_failure": self.fail_after("Invoker_profile", "IDENTITY_UNAVAILABLE"),
            "Directory_caller": self.connection("directory", "UserProfile_V2", {
                "id": "@body('Invoker_profile')?['id']", "$select": PROFILE_FIELDS}, "Invoker_profile"),
            "Directory_failure": self.fail_after("Directory_caller", "IDENTITY_UNAVAILABLE"),
            "Verified_actor": compose(actor, "Directory_caller"),
            "Caller_and_operation_allowed": condition(f"@and({valid[1:]}, {allowed[1:]})",
                {"Dispatch": dispatch}, {"Caller_or_operation_denied": response()}, "Verified_actor"),
        }
        references = {}
        for key, api in APIS.items():
            binding = self.bindings["shared_connections"][key]
            references[key] = {"runtimeSource": "invoker" if key == "invoker" else "embedded",
                "connection": {"connectionReferenceLogicalName": binding["logical_name"]}, "api": {"name": api}}
            if key != "invoker":
                references[key]["connection"]["name"] = binding["connection_name"]
        binding = self.bindings["profiles"][self.profile]
        references["broker"] = {"runtimeSource": "embedded", "connection": {
            "connectionReferenceLogicalName": binding["broker_reference"], "name": binding["broker_connection"]},
            "api": {"name": self.connector}}
        definition = {"$schema": SCHEMA, "contentVersion": "1.0.0.0", "parameters": {
            "$connections": {"defaultValue": {}, "type": "Object"},
            "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
            "triggers": {"manual": trigger}, "actions": actions}
        add_metadata(definition, self.profile)
        return {"properties": {"connectionReferences": references, "definition": definition,
                               "templateName": ""}, "schemaVersion": "1.0.0.0"}


def add_metadata(value, profile, path=""):
    if isinstance(value, dict):
        if value.get("type") in {"Request", "OpenApiConnection", "Response", "If", "Compose", "Query", "Select", "ParseJson", "Wait"}:
            value["metadata"] = {"operationMetadataId": str(uuid5(NAMESPACE_URL, f"milstrip/{profile}/{path}"))}
        for key, child in list(value.items()):
            if key != "metadata":
                add_metadata(child, profile, path + "/" + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            add_metadata(child, profile, path + f"/{i}")


def walk_actions(value):
    if isinstance(value, dict):
        if "type" in value and ("runAfter" in value or value.get("type") == "Request"):
            yield value
        for child in value.values():
            yield from walk_actions(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_actions(child)


def validate_bindings(bindings):
    if set(bindings) != set(default_bindings()):
        raise ValueError("Binding keys differ from the source manifest")
    if re.search(r"__[A-Z_]+__", json.dumps(bindings)):
        raise ValueError("Resolve all deployment binding placeholders")
    UUID(bindings["tenant_id"])
    UUID(bindings["deployed_owner_object_id"])
    if bindings["management_metadata_verified"] is not True:
        raise ValueError("Verify management connector parameter metadata before binding")
    if not re.fullmatch(r"[A-Za-z0-9-]+", bindings["environment_name"]):
        raise ValueError("Invalid environment name")
    if bindings["connector_api_id"].lower() != default_bindings()["connector_api_id"].lower():
        raise ValueError("Reuse the existing MILSTRIP connector")
    if set(bindings["shared_connections"]) != set(APIS) or set(bindings["profiles"]) != {"stage", "prod"}:
        raise ValueError("Unexpected connection or profile binding")
    for key in APIS:
        value = bindings["shared_connections"][key]
        if set(value) != {"logical_name", "connection_name"} or any(not re.fullmatch(r"[A-Za-z0-9_-]+", x) for x in value.values()):
            raise ValueError("Invalid connection binding")
    for profile in ("stage", "prod"):
        value = bindings["profiles"][profile]
        if set(value) != {"app_id", "flow_id", "broker_reference", "broker_connection"}:
            raise ValueError("Unexpected profile binding")
        if value["app_id"] != APP_IDS[profile]:
            raise ValueError("Reuse the existing app IDs")
        UUID(value["flow_id"])
        for key in ("broker_reference", "broker_connection"):
            if not re.fullmatch(r"[A-Za-z0-9_-]+", value[key]):
                raise ValueError("Invalid private broker binding")
    if bindings["profiles"]["stage"]["flow_id"] == bindings["profiles"]["prod"]["flow_id"]:
        raise ValueError("Stage and Prod require distinct broker flows")
    if bindings["profiles"]["stage"]["broker_connection"] == bindings["profiles"]["prod"]["broker_connection"]:
        raise ValueError("Stage and Prod require distinct broker connections")
    if bindings["shared_connections"]["invoker"]["logical_name"] == bindings["shared_connections"]["directory"]["logical_name"]:
        raise ValueError("Invoker and directory must be separate connection references")
    if bindings["profiles"]["stage"]["broker_reference"] == bindings["profiles"]["prod"]["broker_reference"]:
        raise ValueError("Stage and Prod require distinct broker connection references")


def source_manifest(flows, bindings=None):
    bound = bindings is not None
    bindings = bindings or default_bindings()
    return {
        "version": 1, "status": "BOUND_REQUIRES_TENANT_ACCEPTANCE" if bound else "SOURCE_DRAFT_REQUIRES_BINDINGS",
        "generator": "scripts/build_broker_flows.py", "solution": "MILSTRIP",
        "deployment": {"category": 5, "type": 1, "primaryentity": "none", "initial_state": "Draft / Off",
                       "clientdata": "Serialize the entire generated JSON object as the workflow clientdata string"},
        "flows": {profile: {"name": f"MILSTRIP{profile.title()}Broker", "app_id": APP_IDS[profile],
            "flow_id": bindings["profiles"][profile]["flow_id"],
            "source": f"MILSTRIP-{profile.title()}-Broker.json",
            "sha256": hashlib.sha256((json.dumps(value, indent=2, sort_keys=True) + "\n").encode()).hexdigest()}
            for profile, value in flows.items()},
        "requires": ["Distinct private Stage/Prod broker credentials and connection references",
                     "Invoker-owned Office 365 Users connection; private fixed-tenant directory/management connections",
                     "Live caller identity, write-only history, sharing readback and failure-path acceptance",
                     "Server broker-only cutover before exposing either app"],
    }


def build(bindings=None):
    bindings = default_bindings() if bindings is None else deepcopy(bindings)
    flows = {profile: Builder(profile, bindings).build() for profile in ("stage", "prod")}
    return flows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bindings", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bindings = None
    if args.bindings:
        bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
        validate_bindings(bindings)
        if args.output is None:
            parser.error("Bound files require an explicit --output directory")
    output = args.output or OUT
    if not args.check:
        output.mkdir(parents=True, exist_ok=True)
    flows = build(bindings)
    files = {f"MILSTRIP-{profile.title()}-Broker.json": value for profile, value in flows.items()}
    files["deployment-manifest.json"] = source_manifest(flows, bindings=bindings)
    for filename, value in files.items():
        content = json.dumps(value, indent=2, sort_keys=True) + "\n"
        path = output / filename
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Flow source differs: {path.name}")
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    print("Broker source matches" if args.check else "Built broker flow source; no deployment performed")


if __name__ == "__main__":
    main()
