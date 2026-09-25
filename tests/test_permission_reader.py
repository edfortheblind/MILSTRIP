"""Execute generated permission predicates offline; native connector acceptance is separate."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import re
from uuid import UUID

import jsonschema
import pytest

from scripts.build_broker_flows import APP_IDS, Builder, default_bindings, permission_page_complete

TENANT = "11111111-1111-1111-1111-111111111111"
TARGET = "33333333-3333-3333-3333-333333333333"
TOKEN = re.compile(r"\s*('(?:''|[^'])*'|[A-Za-z_][A-Za-z_0-9]*|-?[0-9]+|\?\[|[(),\]])")


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SimulatedClock:
    def __init__(self, value="2026-09-25T17:00:00Z"):
        self.now = timestamp(value)

    def value(self):
        return self.now.isoformat().replace("+00:00", "Z")

    def advance(self, seconds):
        assert seconds >= 0, "Mocked elapsed time cannot be negative"
        self.now += timedelta(seconds=seconds)


def ticks(value):
    delta = timestamp(value) - datetime(1, 1, 1, tzinfo=timezone.utc)
    return delta.days * 864000000000 + delta.seconds * 10000000 + delta.microseconds * 10


@lru_cache(maxsize=None)
def expression_tree(expression):
    """Parse the small WDL subset used by these generated expressions."""
    source, tokens, position = expression.removeprefix("@"), [], 0
    while position < len(source):
        match = TOKEN.match(source, position)
        assert match, f"Unsupported WDL syntax at {position}"
        tokens.append(match[1])
        position = match.end()
    index = 0

    def take(expected=None):
        nonlocal index
        token = tokens[index]
        index += 1
        assert expected is None or token == expected
        return token

    def parse():
        token = take()
        if token.startswith("'"):
            node = ("literal", token[1:-1].replace("''", "'"))
        elif token in {"true", "false", "null"}:
            node = ("literal", {"true": True, "false": False, "null": None}[token])
        elif re.fullmatch(r"-?[0-9]+", token):
            node = ("literal", int(token))
        else:
            take("(")
            args = []
            if tokens[index] != ")":
                args.append(parse())
                while tokens[index] == ",":
                    take(",")
                    args.append(parse())
            take(")")
            node = ("call", token, args)
        while index < len(tokens) and tokens[index] == "?[":
            take("?[")
            key = parse()
            take("]")
            node = ("get", node, key)
        return node

    result = parse()
    assert index == len(tokens), "Unconsumed WDL expression"
    return result


def evaluate(value, state, item=None, clock=None):
    clock = clock or SimulatedClock()
    if isinstance(value, dict):
        return {key: evaluate(child, state, item, clock) for key, child in value.items()}
    if isinstance(value, list):
        return [evaluate(child, state, item, clock) for child in value]
    if not isinstance(value, str) or not value.startswith("@"):
        return value

    def union(*arrays):
        result = []
        for array in arrays:
            for entry in array:
                if entry not in result:
                    result.append(entry)
        return result

    def string(arg):
        if arg is None:
            return ""
        return arg if isinstance(arg, str) else json.dumps(arg, ensure_ascii=False, separators=(",", ":"))

    functions = {
        "and": lambda *args: all(args), "or": lambda *args: any(args),
        "not": lambda arg: not arg, "equals": lambda a, b: a == b,
        "contains": lambda container, value: value in container,
        "less": lambda a, b: a < b, "greater": lambda a, b: a > b,
        "lessOrEquals": lambda a, b: a <= b, "add": lambda a, b: a + b,
        "length": len, "empty": lambda arg: arg is None or len(arg) == 0,
        "coalesce": lambda *args: next((arg for arg in args if arg is not None), None),
        "toLower": str.lower, "concat": lambda *args: "".join(args),
        "json": json.loads, "string": string, "union": union, "createArray": lambda *args: list(args),
        "first": lambda arg: arg[0], "item": lambda: item,
        "body": lambda name: state.get(name, {}).get("body"),
        "outputs": lambda name: state.get(name, {}).get("body"),
        "actions": lambda name: state.get(name, {}),
        "utcNow": clock.value, "ticks": ticks,
        "addSeconds": lambda value, seconds: (timestamp(value) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z"),
    }

    def visit(node):
        if node[0] == "literal":
            return node[1]
        if node[0] == "get":
            parent = visit(node[1])
            return parent.get(visit(node[2])) if parent is not None else None
        if node[1] == "if":
            return visit(node[2][1] if visit(node[2][0]) else node[2][2])
        assert node[1] in functions, f"Unsupported WDL function: {node[1]}"
        return functions[node[1]](*(visit(arg) for arg in node[2]))

    return visit(expression_tree(value))


def execute(actions, state, failures=None, *, connectors=None, calls=None, clock=None):
    """Execute an offline action graph; only explicitly mocked HTTP calls exist.

    Container status can be overridden after its children run, allowing proof
    tests to require each child even when a parent reports success. This is a
    bounded test model, not a claim of complete native scheduler emulation.
    """
    failures, connectors = failures or {}, connectors or {}
    calls = [] if calls is None else calls
    clock = clock or SimulatedClock()

    def skip(name, action):
        state[name] = {"status": "Skipped"}
        if action["type"] == "If":
            for group in (action["actions"], action["else"]["actions"]):
                for child, definition in group.items():
                    skip(child, definition)

    pending = dict(actions)
    while pending:
        ready = [name for name, action in pending.items()
                 if all(parent not in pending and parent in state for parent in action["runAfter"])]
        assert ready, "Unresolved or cyclic action dependency in test graph"
        for name in ready:
            action = pending.pop(name)
            if any(state[parent].get("status") not in statuses
                   for parent, statuses in action["runAfter"].items()):
                skip(name, action)
                continue
            kind, inputs = action["type"], action.get("inputs")
            if failures.get(name) == "Skipped":
                skip(name, action)
                continue
            if name in failures and kind not in {"If", "OpenApiConnection"}:
                state[name] = {"status": failures[name]}
                continue
            try:
                if kind == "If":
                    chosen = evaluate(action["expression"], state, clock=clock)
                    if not isinstance(chosen, bool):
                        raise TypeError("Condition result must be boolean")
                    selected = action["actions"] if chosen else action["else"]["actions"]
                    unselected = action["else"]["actions"] if chosen else action["actions"]
                    for child, definition in unselected.items():
                        skip(child, definition)
                    execute(selected, state, failures, connectors=connectors, calls=calls, clock=clock)
                    statuses = [state[child]["status"] for child in selected]
                    status = "TimedOut" if "TimedOut" in statuses else (
                        "Failed" if "Failed" in statuses else "Succeeded")
                    state[name] = {"status": failures.get(name, status)}
                    continue
                if kind == "OpenApiConnection":
                    assert name in connectors or name in failures, "Unexpected connector call: " + name
                    parameters = evaluate(inputs["parameters"], state, clock=clock)
                    configured = connectors.get(name, {})
                    result = configured(parameters, clock) if callable(configured) else deepcopy(configured)
                    status = failures.get(name, result.get("status", "Succeeded"))
                    assert status in {"Succeeded", "Failed", "Skipped", "TimedOut"}
                    if status == "Skipped":
                        skip(name, action)
                        continue
                    started = clock.value()
                    calls.append({"name": name, "parameters": parameters,
                                  "started_at": started})
                    clock.advance(result.pop("elapsed_seconds", 0))
                    result.update(status=status, startTime=started, endTime=clock.value())
                    state[name] = result
                    continue
                if kind == "ParseJson":
                    result = evaluate(inputs["content"], state, clock=clock)
                    if isinstance(result, str):
                        result = json.loads(result)
                    jsonschema.Draft4Validator(inputs["schema"]).validate(result)
                elif kind in {"Query", "Select"}:
                    rows = evaluate(inputs["from"], state, clock=clock)
                    result = ([row for row in rows if evaluate(inputs["where"], state, row, clock)]
                              if kind == "Query" else [evaluate(inputs["select"], state, row, clock) for row in rows])
                else:
                    assert kind == "Compose", f"Unsupported action: {kind}"
                    result = evaluate(inputs, state, clock=clock)
                state[name] = {"status": "Succeeded", "body": result}
            except (jsonschema.ValidationError, ValueError, TypeError, KeyError):
                state[name] = {"status": "Failed"}
                if kind == "If":
                    for group in (action["actions"], action["else"]["actions"]):
                        for child, definition in group.items():
                            if child not in state:
                                skip(child, definition)
    return state


@pytest.fixture
def builder(monkeypatch):
    import api.permission_read as reader
    monkeypatch.setattr(reader, "_scope", lambda state, binding, context, command:
                        (APP_IDS[command.resource_environment], TENANT, context["target"]))
    bindings = default_bindings()
    bindings.update(tenant_id=TENANT, environment_name="Default-" + TENANT,
                    deployed_owner_object_id="22222222-2222-2222-2222-222222222222")
    return Builder("stage", bindings)


def assignment(number=0, principal=TARGET):
    name = f"assignment-{number}"
    return {"id": f"/providers/Microsoft.PowerApps/apps/{APP_IDS['stage']}/permissions/{name}",
            "name": name, "properties": {"roleName": "CanView",
            "principal": {"id": principal, "type": "User", "tenantId": TENANT}}}


def run_reader(builder, payload, *, read="Before_add_stage_app", target=TARGET,
               failure=None, failure_status="Failed", pages=None, overrides=None, clock=None,
               injected_failures=None, reply_transform=None):
    from types import SimpleNamespace
    from api.broker_models import ValidateAppPermissionRead
    from api.permission_read import validate_app_permission_read
    actions, parsed, validated, status = builder.permission_read(read, "stage", "test", "before",
        "Plan", plan_expression="outputs('Plan')")
    state = {"Plan": {"status": "Succeeded", "body": {
        "plan_id": "55555555-5555-5555-5555-555555555555",
        "revision": "66666666-6666-6666-6666-666666666666",
        "target": {"object_id": target, "tenant_id": TENANT}}},
        "Request_id": {"status": "Succeeded", "body": "77777777-7777-7777-7777-777777777777"},
        "Verified_actor": {"status": "Succeeded", "body": {}}}
    def validator(parameters, active_clock):
        command = ValidateAppPermissionRead.model_validate(json.loads(parameters["body/payload_json"]))
        result = validate_app_permission_read({}, {"target": target}, command,
            SimpleNamespace(read=lambda: {}), now=active_clock.now)
        if reply_transform:
            result = reply_transform(command, result, active_clock)
        return {"body": {"result_json": json.dumps(result)}}
    connectors = {}
    for number, content in enumerate(pages or [payload], 1):
        connectors[read if number == 1 else read + f"_P{number}"] = {"body": deepcopy(content)}
    for number in range(1, 4):
        connectors[f"Validate_{read}_P{number}"] = validator
    connectors.update(overrides or {})
    failed = (read if failure == "connector" else f"{failure}_{read}" if failure in {"Terminal", "Effective"}
              else f"{failure}_{read}_P1")
    failures = {failed: failure_status} if failure else {}
    failures.update(injected_failures or {})
    calls = []
    execute(actions, state, failures, connectors=connectors, calls=calls, clock=clock)
    return state, parsed, validated, status, calls


def pipeline(builder, payload, **kwargs):
    return run_reader(builder, payload, **kwargs)[:3]


def paged_rows(rows):
    from api.permission_read import permission_urls
    cursor = permission_urls(APP_IDS["stage"], TENANT)[1]
    pages = [{"value": rows[index:index + 400]} for index in range(0, len(rows), 400)]
    for index, page in enumerate(pages[:-1], 1):
        page["nextLink"] = cursor + "page" + str(index)
    return pages


@pytest.mark.parametrize("payload", [{"value": []}, {"value": [assignment()]}, json.dumps({"value": []})])
def test_complete_well_formed_pages_pass_generated_pipeline(builder, payload):
    state, _, validated = pipeline(builder, payload)
    assert state[validated] == {"status": "Succeeded", "body": True}


@pytest.mark.parametrize("payload", [None, [], {}, {"value": None}, {"value": {}},
    {"error": {"code": "denied"}, "value": []}, {"value": [None]}, {"value": [{}]}, "{broken"])
def test_malformed_or_error_response_cannot_become_empty_page(builder, payload):
    state, parsed, validated = pipeline(builder, payload)
    assert state[parsed]["status"] == "Failed"
    assert state[validated].get("body") is False


@pytest.mark.parametrize("path,replacement", [
    (("properties", "principal"), None), (("properties", "principal", "id"), "invalid"),
    (("properties", "principal", "id"), TARGET + "\n"),
    (("properties", "principal", "type"), "Unknown"),
    (("properties", "principal", "tenantId"), "44444444-4444-4444-4444-444444444444"),
    (("properties", "principal", "tenantId"), TENANT + "\n"),
    (("properties", "roleName"), "Unknown"), (("name",), "different-name"),
    (("id",), f"/providers/Microsoft.PowerApps/apps/{APP_IDS['prod']}/permissions/assignment-0"),
])
def test_bad_assignment_identity_or_principal_is_rejected(builder, path, replacement):
    row = assignment()
    container = row
    for key in path[:-1]:
        container = container[key]
    container[path[-1]] = replacement
    state, _, validated = pipeline(builder, {"value": [row]})
    assert state[validated].get("body") is False


@pytest.mark.parametrize("duplicate", ["id", "principal"])
def test_case_insensitive_duplicate_id_or_principal_is_rejected(builder, duplicate):
    first = assignment(principal="abcdefab-abcd-abcd-abcd-abcdefabcdef")
    second = deepcopy(first)
    if duplicate == "id":
        second["name"] = second["name"].upper()
        second["id"] = second["id"].rsplit("/", 1)[0] + "/" + second["name"]
        second["properties"]["principal"]["id"] = TARGET
        second["properties"]["roleName"] = "CanEdit"
    else:
        second = assignment(1, principal=first["properties"]["principal"]["id"].upper())
    state, _, validated = pipeline(builder, {"value": [first, second]})
    assert state[validated].get("body") is False


@pytest.mark.parametrize("failure", ["connector", "Payload", "Validate", "Reply", "Terminal", "Effective"])
@pytest.mark.parametrize("status", ["Failed", "Skipped", "TimedOut"])
def test_failed_read_parser_or_projection_never_qualifies_absence(builder, failure, status):
    state, _, validated = pipeline(builder, {"value": []}, failure=failure, failure_status=status)
    assert state[validated].get("body") is False


@pytest.mark.parametrize("key", ["nextLink", "@odata.nextLink"])
@pytest.mark.parametrize("cursor,complete", [(None, True), ("", True), ("https://example.invalid/next", False),
                                            (False, False), (0, False), ({"unexpected": "shape"}, False), ([], False)])
def test_both_continuation_keys_must_be_empty_and_well_typed(builder, key, cursor, complete):
    state, parsed, validated = pipeline(builder, {"value": [], key: cursor})
    if cursor is not None and not isinstance(cursor, str):
        assert state[parsed]["status"] == "Failed"
    assert evaluate("@and(" + permission_page_complete(parsed, validated) + ")", state) is complete


@pytest.mark.parametrize("count,complete", [(999, True), (1000, False)])
def test_strict_row_limit_uses_generated_completeness_predicate(builder, count, complete):
    rows = [assignment(index, str(UUID(int=index+1))) for index in range(count)]
    state, parsed, validated = pipeline(builder, None, pages=paged_rows(rows))
    assert state[validated].get("body") is complete
    assert evaluate("@and(" + permission_page_complete(parsed, validated) + ")", state) is complete


def decisions(builder, payload, target=TARGET, desired=False, failure=None,
              failure_status="Failed", failure_phase=None, readback_payload=..., pages=None,
              reply_transform=None, response_phase=None):
    """Execute actual generated read/guard expressions with the real API validator."""
    suffix = "add" if desired else "remove"
    key = suffix + "_stage_app"
    generated = builder.reconcile(suffix)["Sharing_needed_" + suffix]["actions"]
    state = {"Leased_" + suffix: {"status": "Succeeded", "body": {"sharing_plan": {
        "target": {"object_id": target, "tenant_id": TENANT}}}}}
    state["Plan_" + key] = {"status": "Succeeded", "body": [{"present": desired}]}
    for phase, filtered in (("Before", "Matched"), ("Readback", "Found")):
        read = phase + "_" + key
        content = readback_payload if phase == "Readback" and readback_payload is not ... else payload
        inject = failure if failure_phase in (None, phase) else None
        observed, _, _, _, _ = run_reader(builder, content, read=read, target=target,
            failure=inject, failure_status=failure_status, pages=pages,
            reply_transform=reply_transform if response_phase in (None, phase) else None)
        state.update(observed)
        execute({filtered + "_" + key: generated[filtered + "_" + key]}, state)
        if phase == "Before":
            mutation = generated["Mutate_" + key]
            execute({"Mutate_" + key: {"type": "Compose", "inputs": mutation["expression"],
                                      "runAfter": mutation["runAfter"]}}, state)
    execute({"Observed_" + key: generated["Observed_" + key]}, state)
    return state["Mutate_" + key].get("body") is True, state["Observed_" + key].get("body", {})


@pytest.mark.parametrize("role", ["CanEdit", "Owner"])
def test_existing_elevated_target_grant_is_not_verified_absence_on_removal(builder, role):
    row = assignment()
    row["properties"]["roleName"] = role
    mutate, observation = decisions(builder, {"value": [row]})
    assert mutate is False
    assert observation["verified"] is False


@pytest.mark.parametrize("desired", [False, True])
def test_pinned_deployment_owner_is_present_and_never_mutated(builder, desired):
    owner = builder.bindings["deployed_owner_object_id"]
    row = assignment(principal=owner)
    row["properties"]["roleName"] = "Owner"
    mutate, observation = decisions(builder, {"value": [row]}, target=owner, desired=desired)
    assert mutate is False
    assert observation["verified"] is True and observation["present"] is True


@pytest.mark.parametrize("principal_type", ["Group", "Tenant"])
@pytest.mark.parametrize("desired", [False, True])
def test_wrong_principal_type_for_target_never_allows_mutation_or_verification(builder, principal_type, desired):
    row = assignment()
    row["properties"]["principal"]["type"] = principal_type
    mutate, observation = decisions(builder, {"value": [row]}, desired=desired)
    assert mutate is False
    assert observation["verified"] is False


def test_unrelated_well_formed_group_does_not_hide_absent_user(builder):
    row = assignment(principal="44444444-4444-4444-4444-444444444444")
    row["properties"]["principal"]["type"] = "Group"
    mutate, observation = decisions(builder, {"value": [row]}, desired=True)
    assert mutate is True
    assert observation["verified"] is True and observation["present"] is False


@pytest.mark.parametrize("encoded", [False, True])
@pytest.mark.parametrize("present", [False, True])
@pytest.mark.parametrize("desired", [False, True])
def test_generated_read_chains_accept_direct_object_or_json_text(builder, encoded, present, desired):
    payload = {"value": [assignment()] if present else []}
    mutate, observation = decisions(builder, json.dumps(payload) if encoded else payload, desired=desired)
    assert mutate is (desired != present)
    assert observation["verified"] is True and observation["present"] is present


@pytest.mark.parametrize("payload", [None, [], {}, {"value": None}, {"value": {}}, {"value": [{}]},
    {"error": {"code": "denied"}, "value": []}, "{broken", {"body": {"value": []}},
    {"statusCode": 200, "body": json.dumps({"value": []})}])
def test_generated_chains_reject_invalid_pages_and_unexpected_wrappers(builder, payload):
    mutate, observation = decisions(builder, payload, desired=True)
    assert mutate is False
    assert observation.get("verified") is not True


@pytest.mark.parametrize("key", ["nextLink", "@odata.nextLink"])
def test_generated_chains_reject_either_continuation_without_mutation(builder, key):
    mutate, observation = decisions(builder, {"value": [], key: "https://example.invalid/next"}, desired=True)
    assert mutate is False
    assert observation["verified"] is False


@pytest.mark.parametrize("count,complete", [(999, True), (1000, False)])
def test_generated_chains_apply_strict_row_limit(builder, count, complete):
    rows = [assignment(index, str(UUID(int=index+1))) for index in range(count)]
    mutate, observation = decisions(builder, None, desired=True, pages=paged_rows(rows))
    assert mutate is complete
    assert observation["verified"] is complete and observation["present"] is False


@pytest.mark.parametrize("desired", [False, True])
@pytest.mark.parametrize("phase", ["Before", "Readback"])
@pytest.mark.parametrize("status", ["Failed", "Skipped", "TimedOut"])
@pytest.mark.parametrize("failure", ["connector", "Payload", "Validate", "Reply", "Terminal", "Effective"])
def test_generated_chains_never_trust_failed_read_or_validation(builder, desired, phase, status, failure):
    payload = {"value": [] if desired else [assignment()]}
    mutate, observation = decisions(builder, payload, desired=desired, failure=failure,
                                   failure_status=status, failure_phase=phase)
    if phase == "Before":
        assert mutate is False
        assert observation["verified"] is True and observation["present"] is not desired
    else:
        assert mutate is True
        assert observation.get("verified") is not True


@pytest.mark.parametrize("desired", [False, True])
def test_generated_readback_reports_observed_post_mutation_state(builder, desired):
    before = {"value": [] if desired else [assignment()]}
    after = {"value": [assignment()] if desired else []}
    mutate, observation = decisions(builder, before, desired=desired, readback_payload=after)
    assert mutate is True
    assert observation["verified"] is True and observation["present"] is desired


@pytest.mark.parametrize("name", [".", "..", "a..b", "a:b", "a" * 129, "bad\nname", "bad\n",
                                "a/b", "a%b", "%2e", "%2e%2e", "%2f"])
def test_unsafe_assignment_name_never_allows_mutation_or_verified_readback(builder, name):
    row = assignment()
    row.update(name=name, id=f"/providers/Microsoft.PowerApps/apps/{APP_IDS['stage']}/permissions/{name}")
    mutate, observation = decisions(builder, {"value": [row]})
    assert mutate is False
    assert observation.get("verified") is not True


@pytest.mark.parametrize("name", ["a" * 128, "77777777-7777-7777-7777-777777777777"])
def test_maximum_length_assignment_token_and_uuid_remain_accepted(builder, name):
    row = assignment()
    row.update(name=name, id=f"/providers/Microsoft.PowerApps/apps/{APP_IDS['stage']}/permissions/{name}")
    mutate, observation = decisions(builder, {"value": [row]})
    assert mutate is True
    assert observation["verified"] is True and observation["present"] is True


def test_graph_scheduler_waits_for_dependencies_regardless_of_mapping_order():
    from scripts.build_broker_flows import compose

    state = execute({"Consumer": compose("@add(outputs('Producer'), 1)", "Producer"),
                     "Producer": compose(7)}, {})
    assert state["Consumer"] == {"status": "Succeeded", "body": 8}


@pytest.mark.parametrize("cyclic", [False, True])
def test_graph_scheduler_refuses_missing_or_cyclic_dependencies(cyclic):
    from scripts.build_broker_flows import compose

    actions = {"First": compose(1, "Second")}
    if cyclic:
        actions["Second"] = compose(2, "First")
    with pytest.raises(AssertionError, match="dependency"):
        execute(actions, {})


def test_false_condition_recursively_skips_unselected_requests(builder):
    from scripts.build_broker_flows import compose, condition

    nested = condition("@true", {"UnselectedRequest": builder.connection("permissions", "InvokeHttp", {})},
                       {"OtherUnselectedRequest": builder.connection("permissions", "InvokeHttp", {})})
    actions = {"After": compose("@actions('Optional')?['status']", "Optional"),
               "Optional": condition("@false", {"Nested": nested}, {"Selected": compose("selected")})}
    calls = []
    state = execute(actions, {}, calls=calls)
    assert calls == []
    assert state["Optional"]["status"] == "Succeeded"
    assert state["Selected"]["body"] == "selected" and state["After"]["body"] == "Succeeded"
    assert all(state[name]["status"] == "Skipped" for name in
               ("Nested", "UnselectedRequest", "OtherUnselectedRequest"))


@pytest.mark.parametrize("expression", ["@null", "true", 1])
def test_unknown_or_wrong_type_condition_is_failed_not_successful_optional_skip(builder, expression):
    from scripts.build_broker_flows import condition

    actions = {"Guard": condition(expression, {"RequiredRead": builder.connection("permissions", "InvokeHttp", {})})}
    state = execute(actions, {})
    assert state["Guard"]["status"] == "Failed"
    assert state["RequiredRead"]["status"] == "Skipped"


@pytest.mark.parametrize("child_status", ["Failed", "Skipped", "TimedOut"])
def test_successful_container_cannot_substitute_for_required_child_proof(builder, child_status):
    from scripts.build_broker_flows import compose, condition

    actions = {
        "ReadGate": condition("@true", {"RequiredRead": builder.connection("permissions", "InvokeHttp", {})}),
        "Proof": compose("@and(equals(actions('ReadGate')?['status'], 'Succeeded'), "
                         "equals(actions('RequiredRead')?['status'], 'Succeeded'))", "ReadGate"),
        "Mutation": condition("@outputs('Proof')", {"ForbiddenWrite": builder.connection("makers", "Edit-AppRoleAssignment", {})},
                              previous="Proof"),
    }
    calls = []
    state = execute(actions, {}, {"ReadGate": "Succeeded"},
                    connectors={"RequiredRead": {"status": child_status}}, calls=calls)
    assert state["ReadGate"]["status"] == "Succeeded"
    assert state["RequiredRead"]["status"] == child_status
    assert state["Proof"]["body"] is False
    assert state["ForbiddenWrite"]["status"] == "Skipped"
    assert [item["name"] for item in calls] == ([] if child_status == "Skipped" else ["RequiredRead"])


def test_unmocked_connector_call_is_rejected_without_network(builder):
    with pytest.raises(AssertionError, match="Unexpected connector call"):
        execute({"Unmocked": builder.connection("permissions", "InvokeHttp", {})}, {})


@pytest.mark.parametrize("elapsed,within_budget", [(89.999, True), (90, False), (90.001, False)])
def test_clock_measures_budget_after_response_and_blocks_later_work(builder, elapsed, within_budget):
    from scripts.build_broker_flows import compose, condition

    actions = {
        "Started": compose("@utcNow()"),
        "Read": builder.connection("permissions", "InvokeHttp", {"request/method": "GET"}, "Started"),
        "Proof": compose("@less(ticks(utcNow()), ticks(addSeconds(outputs('Started'), 90)))", "Read"),
        "Continue": condition("@outputs('Proof')", {"NextRead": builder.connection("permissions", "InvokeHttp",
                              {"request/url": "@body('Read')?['nextLink']"})}, previous="Proof"),
    }
    clock, calls = SimulatedClock(), []
    state = execute(actions, {}, connectors={
        "Read": {"body": {"nextLink": "https://example.invalid/synthetic-next"}, "elapsed_seconds": elapsed},
        "NextRead": {"body": {"value": []}},
    }, calls=calls, clock=clock)
    assert state["Proof"]["body"] is within_budget
    assert len(calls) == (2 if within_budget else 1)
    assert state["Read"]["startTime"] == state["Started"]["body"]
    assert state["Read"]["endTime"] == clock.value()
    if within_budget:
        assert calls[1]["parameters"] == {"request/url": "https://example.invalid/synthetic-next"}
    else:
        assert state["NextRead"]["status"] == "Skipped"


@pytest.mark.parametrize("count", [1, 2, 3])
def test_terminal_page_stops_reads_and_returns_only_target(builder, count):
    from api.permission_read import permission_urls
    prefix = permission_urls(APP_IDS["stage"], TENANT)[1]
    pages = [{"value": [], "nextLink": prefix + str(index)} for index in range(1, count)]
    pages.append({"value": [assignment()]})
    state, parsed, valid, status, calls = run_reader(builder, None, pages=pages)
    assert state[valid]["body"] is True and state[status]["body"] is None
    assert state[parsed]["body"] == {"value": [assignment()]}
    assert len(calls) == count * 2
    assert [len(json.loads(call["parameters"]["body/payload_json"])["pages"]) for call in calls
            if "body/payload_json" in call["parameters"]] == list(range(1, count + 1))
    for number in range(count + 1, 4):
        assert state[f"Before_add_stage_app_P{number}"]["status"] == "Skipped"


def test_third_continuation_is_incomplete_and_never_issues_fourth_read(builder):
    from api.permission_read import permission_urls
    prefix = permission_urls(APP_IDS["stage"], TENANT)[1]
    pages = [{"value": [], "nextLink": prefix + str(index)} for index in range(1, 4)]
    state, parsed, valid, status, calls = run_reader(builder, None, pages=pages)
    assert state[valid]["body"] is False and state[status]["body"] == "PAGINATED"
    assert state[parsed]["status"] == "Failed" and len(calls) == 6


@pytest.mark.parametrize("number", [2, 3])
@pytest.mark.parametrize("kind", ["request", "Payload", "Validate", "Reply"])
@pytest.mark.parametrize("status", ["Failed", "Skipped", "TimedOut"])
def test_required_page_child_failure_cannot_be_hidden_by_successful_parent(builder, number, kind, status):
    from api.permission_read import permission_urls
    read = "Before_add_stage_app"
    prefix = permission_urls(APP_IDS["stage"], TENANT)[1]
    pages = [{"value": [], "nextLink": prefix + str(index)} for index in (1, 2)] + [{"value": []}]
    child = f"{read}_P{number}" if kind == "request" else f"{kind}_{read}_P{number}"
    state, parsed, valid, _, calls = run_reader(builder, None, pages=pages,
        injected_failures={child: status, f"Page{number}_{read}": "Succeeded"})
    assert state[f"Page{number}_{read}"]["status"] == "Succeeded"
    assert state[valid]["body"] is False and state[parsed]["status"] == "Failed"
    assert len(calls) <= number * 2
    if number == 2:
        assert state[f"{read}_P3"]["status"] == "Skipped"


@pytest.mark.parametrize("field,value", [
    ("schema_version", 2), ("plan_id", "77777777-7777-7777-7777-777777777777"),
    ("revision", "77777777-7777-7777-7777-777777777777"), ("resource_environment", "prod"),
    ("app_id", APP_IDS["prod"]), ("tenant_id", "77777777-7777-7777-7777-777777777777"),
    ("target_object_id", "77777777-7777-7777-7777-777777777777"), ("phase", "after"),
    ("observation_started_at", "2026-09-25T17:00:01Z"), ("page_count", 2),
    ("row_count", True), ("row_count", 1000), ("matching_assignments", None),
    ("next_url", "https://example.invalid"), ("reason", "INVALID_PAGE"),
    ("expires_at", "2026-09-25T17:01:31Z"), ("expires_at", "2026-09-25T17:00:00Z"),
])
def test_changed_validator_binding_or_incoherent_complete_result_is_rejected(builder, field, value):
    def alter(command, result, clock):
        return {**result, field: value}
    state, parsed, valid, _, calls = run_reader(builder, {"value": []}, reply_transform=alter)
    assert state[valid].get("body") is not True and state[parsed]["status"] != "Succeeded"
    assert len(calls) == 2


@pytest.mark.parametrize("elapsed", [90, 91])
@pytest.mark.parametrize("continued", [False, True])
def test_deadline_after_validation_blocks_continuation_and_complete_evidence(builder, elapsed, continued):
    from api.permission_read import permission_urls
    body = {"value": []}
    if continued:
        body["nextLink"] = permission_urls(APP_IDS["stage"], TENANT)[1] + "page2"
    def delay(command, result, clock):
        clock.advance(elapsed)
        return result
    state, _, valid, _, calls = run_reader(builder, body, reply_transform=delay)
    assert state[valid]["body"] is False and len(calls) == 2
    assert state["Before_add_stage_app_P2"]["status"] == "Skipped"


def test_delayed_mutation_guard_rechecks_observation_deadline(builder):
    from scripts.build_broker_flows import permission_page_complete
    clock = SimulatedClock()
    state, parsed, valid, _, _ = run_reader(builder, {"value": []}, clock=clock)
    assert state[valid]["body"] is True
    clock.advance(90)
    assert evaluate("@and(" + permission_page_complete(parsed, valid) + ")", state, clock=clock) is False


@pytest.mark.parametrize("size,expected_calls", [(260000, 2), (1100001, 1)])
def test_page_and_actual_serialized_envelope_budgets_fail_closed(builder, size, expected_calls):
    state, _, valid, _, calls = run_reader(builder, {"value": [], "padding": "x" * size})
    assert state[valid]["body"] is False and len(calls) == expected_calls


def test_repeated_cursor_and_duplicate_across_pages_block_continuation(builder):
    from api.permission_read import permission_urls
    cursor = permission_urls(APP_IDS["stage"], TENANT)[1] + "page2"
    for last in ({"value": [], "nextLink": cursor}, {"value": [assignment()]}):
        pages = [{"value": [assignment()], "nextLink": cursor}, last]
        state, _, valid, _, calls = run_reader(builder, None, pages=pages)
        assert state[valid]["body"] is False and len(calls) == 4
        assert state["Before_add_stage_app_P3"]["status"] == "Skipped"


@pytest.mark.parametrize("kind,expected", [("page_limit", "PAGINATED"), ("row_limit", "ROW_LIMIT"),
    ("malformed", "FILTER_FAILED"), ("transport", "CALL_FAILED")])
def test_generated_readback_diagnostic_preserves_fixed_failure_category(builder, kind, expected):
    from api.permission_read import permission_urls
    from scripts.build_broker_flows import readback_reason
    read, key = "Readback_add_stage_app", "add_stage_app"
    prefix = permission_urls(APP_IDS["stage"], TENANT)[1]
    kwargs = {}
    if kind == "page_limit":
        kwargs["pages"] = [{"value": [], "nextLink": prefix + str(index)} for index in range(3)]
    elif kind == "row_limit":
        kwargs["pages"] = paged_rows([assignment(index, str(UUID(int=index+1))) for index in range(1000)])
    elif kind == "transport":
        kwargs.update(failure="connector", failure_status="TimedOut")
    state, parsed, valid, status, _ = run_reader(builder, {} if kind == "malformed" else {"value": []}, read=read, **kwargs)
    state.update({"Plan_test": {"status": "Succeeded", "body": [{"present": True}]},
        "Found_test": {"status": "Succeeded", "body": []},
        "Observed_test": {"status": "Succeeded", "body": {"present": False, "verified": False}}})
    value = evaluate(readback_reason(key, "Plan_test", read, "Found_test", "Observed_test",
        page=parsed, validated=valid, read_status=status), state)
    assert value == "READBACK_" + expected + "_STAGE_APP"



def test_read_only_diagnostic_reuses_graph_without_fabricating_lease(builder):
    from scripts.build_broker_flows import walk_actions
    actions, _, _, _ = builder.permission_read("Diagnostic_stage", "stage", "unused", "before",
        "Diagnostic_plan", plan_expression="outputs('Diagnostic_plan')")
    serialized = json.dumps(actions)
    assert "Leased_" not in serialized and "lease_id" not in serialized and "native_run" not in serialized
    operations = [(step["inputs"]["host"]["connectionName"], step["inputs"]["host"]["operationId"],
                   step["inputs"]["parameters"].get("body/operation"))
                  for step in walk_actions(actions) if step["type"] == "OpenApiConnection"]
    assert operations.count(("permissions", "InvokeHttp", None)) == 3
    assert operations.count(("broker", "InvokeBroker", "ValidateAppPermissionRead")) == 3
    assert len(operations) == 6


@pytest.mark.parametrize("phase", ["Before", "Readback"])
@pytest.mark.parametrize("desired", [False, True])
@pytest.mark.parametrize("corruption", ["empty_object", "missing_id", "missing_name", "missing_properties",
    "missing_role", "missing_principal", "wrong_target", "wrong_tenant", "wrong_app", "wrong_path_name", "wrong_count"])
def test_corrupt_validator_match_never_becomes_empty_target_evidence(builder, phase, desired, corruption):
    owner = builder.bindings["deployed_owner_object_id"]
    row = assignment(principal=owner)
    row["properties"]["roleName"] = "Owner"
    def corrupt(command, result, clock):
        match = deepcopy(result["matching_assignments"][0])
        if corruption == "empty_object":
            match = {}
        elif corruption in {"missing_id", "missing_name", "missing_properties"}:
            del match[corruption.removeprefix("missing_")]
        elif corruption == "missing_role":
            del match["properties"]["roleName"]
        elif corruption == "missing_principal":
            del match["properties"]["principal"]
        elif corruption in {"wrong_target", "wrong_tenant"}:
            match["properties"]["principal"]["id" if corruption == "wrong_target" else "tenantId"] = "99999999-9999-9999-9999-999999999999"
        elif corruption == "wrong_app":
            match["id"] = match["id"].replace(APP_IDS["stage"], APP_IDS["prod"])
        elif corruption == "wrong_path_name":
            match["name"] = "different"
        result = {**result, "matching_assignments": [match]}
        if corruption == "wrong_count":
            result["row_count"] = 0
        return result
    mutate, observation = decisions(builder, {"value": [row]}, target=owner, desired=desired,
        reply_transform=corrupt, response_phase=phase)
    assert mutate is False
    assert observation["verified"] is (phase == "Before")
    if phase == "Readback":
        assert observation["verified"] is False
