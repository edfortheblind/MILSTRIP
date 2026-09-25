"""Execute generated permission predicates offline; native connector acceptance is separate."""
from copy import deepcopy
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


def evaluate(value, state, item=None):
    if isinstance(value, dict):
        return {key: evaluate(child, state, item) for key, child in value.items()}
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
        "less": lambda a, b: a < b, "greater": lambda a, b: a > b,
        "length": len, "empty": lambda arg: arg is None or len(arg) == 0,
        "coalesce": lambda *args: next((arg for arg in args if arg is not None), None),
        "toLower": str.lower, "concat": lambda *args: "".join(args),
        "json": json.loads, "string": string, "union": union, "createArray": lambda *args: list(args),
        "first": lambda arg: arg[0], "item": lambda: item,
        "body": lambda name: state.get(name, {}).get("body"),
        "outputs": lambda name: state.get(name, {}).get("body"),
        "actions": lambda name: state.get(name, {}),
    }

    def visit(node):
        if node[0] == "literal":
            return node[1]
        if node[0] == "get":
            parent = visit(node[1])
            return parent.get(visit(node[2])) if parent is not None else None
        assert node[1] in functions, f"Unsupported WDL function: {node[1]}"
        return functions[node[1]](*(visit(arg) for arg in node[2]))

    return visit(expression_tree(value))


def execute(actions, state, failures=None):
    """Honor generated runAfter gates and evaluate the actual action inputs."""
    for name, action in actions.items():
        if any(state.get(parent, {}).get("status") not in statuses
               for parent, statuses in action["runAfter"].items()):
            state[name] = {"status": "Skipped"}
            continue
        if name in (failures or {}):
            state[name] = {"status": failures[name]}
            continue
        inputs, kind = action["inputs"], action["type"]
        try:
            if kind == "ParseJson":
                result = evaluate(inputs["content"], state)
                if isinstance(result, str):
                    result = json.loads(result)
                jsonschema.Draft4Validator(inputs["schema"]).validate(result)
            elif kind in {"Query", "Select"}:
                rows = evaluate(inputs["from"], state)
                result = ([row for row in rows if evaluate(inputs["where"], state, row)]
                          if kind == "Query" else [evaluate(inputs["select"], state, row) for row in rows])
            else:
                assert kind == "Compose", f"Unsupported action: {kind}"
                result = evaluate(inputs, state)
            state[name] = {"status": "Succeeded", "body": result}
        except (jsonschema.ValidationError, ValueError, TypeError, KeyError):
            state[name] = {"status": "Failed"}
    return state


@pytest.fixture
def builder():
    bindings = default_bindings()
    bindings.update(tenant_id=TENANT, deployed_owner_object_id="22222222-2222-2222-2222-222222222222")
    return Builder("stage", bindings)


def assignment(number=0, principal=TARGET):
    name = f"assignment-{number}"
    return {"id": f"/providers/Microsoft.PowerApps/apps/{APP_IDS['stage']}/permissions/{name}",
            "name": name, "properties": {"roleName": "CanView",
            "principal": {"id": principal, "type": "User", "tenantId": TENANT}}}


def pipeline(builder, payload, read="Before_add_stage_app", failure=None, failure_status="Failed"):
    # Explicit content isolates response qualification from the unaccepted native wrapper.
    actions, parsed, validated = builder.permission_page(read, APP_IDS["stage"], f"@body('{read}')")
    state = {read: {"status": "Succeeded", "body": deepcopy(payload)}}
    if failure == "connector":
        state[read] = {"status": failure_status}
    failures = {f"{failure}_{read}": failure_status} if failure and failure != "connector" else {}
    execute(actions, state, failures)
    return state, parsed, validated


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


@pytest.mark.parametrize("failure", ["connector", "Parsed", "Invalid", "Ids", "Principals"])
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
    state, parsed, validated = pipeline(builder, {"value": rows})
    assert state[validated].get("body") is True
    assert evaluate("@and(" + permission_page_complete(parsed, validated) + ")", state) is complete


def decisions(builder, payload, target=TARGET, desired=False, failure=None,
              failure_status="Failed", failure_phase=None, readback_payload=...):
    """Run the actual generated app-read chains; replace only connector results."""
    suffix = "add" if desired else "remove"
    key = suffix + "_stage_app"
    generated = builder.reconcile(suffix)["Sharing_needed_" + suffix]["actions"]
    state = {"Leased_" + suffix: {"status": "Succeeded", "body": {"sharing_plan": {
        "target": {"object_id": target, "tenant_id": TENANT}}}}}
    state["Plan_" + key] = {"status": "Succeeded", "body": [{"present": desired}]}
    for phase, filtered in (("Before", "Matched"), ("Readback", "Found")):
        read = phase + "_" + key
        content = readback_payload if phase == "Readback" and readback_payload is not ... else payload
        state[read] = {"status": "Succeeded", "body": deepcopy(content)}
        inject = failure if failure_phase in (None, phase) else None
        if inject == "connector":
            state[read] = {"status": failure_status}
        failures = {f"{inject}_{read}": failure_status} if inject and inject != "connector" else {}
        names = [prefix + "_" + read for prefix in ("Parsed", "Invalid", "Ids", "Principals", "Validated")]
        execute({name: generated[name] for name in names}, state, failures)
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
    mutate, observation = decisions(builder, {"value": rows}, desired=True)
    assert mutate is complete
    assert observation["verified"] is complete and observation["present"] is False


@pytest.mark.parametrize("desired", [False, True])
@pytest.mark.parametrize("phase", ["Before", "Readback"])
@pytest.mark.parametrize("status", ["Failed", "Skipped", "TimedOut"])
@pytest.mark.parametrize("failure", ["connector", "Parsed", "Invalid", "Ids", "Principals"])
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
