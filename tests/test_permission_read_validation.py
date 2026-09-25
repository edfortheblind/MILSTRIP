"""Read-only permission qualification against synthetic control state and pages."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from api import app as api
from api import permission_read as reader
from api.authorization import AuthorizationError, save_user_access
from api.broker_models import ValidateAppPermissionRead
from api.control import principal_key
from tests.test_control_broker import access_command, context, control, envelope, complete


NOW = datetime(2026, 9, 25, 18, 0, tzinfo=timezone.utc)
RESULT_FIELDS = {"schema_version", "plan_id", "revision", "resource_environment", "app_id", "tenant_id",
                 "target_object_id", "phase", "observation_started_at", "expires_at", "disposition", "reason",
                 "page_count", "row_count", "next_url", "matching_assignments"}


@pytest.fixture
def scope(control, monkeypatch):
    store, manifest = control
    caller = context(control)
    command = access_command(control)
    saved = save_user_access(caller, command, store)
    plan = saved["sharing_plan"]
    app_id = manifest["resources"]["stage"]["app_id"]
    tenant = manifest["tenant_id"]
    route = f"https://api.powerapps.com/providers/Microsoft.PowerApps/apps/{app_id}/permissions?api-version=2017-06-01&%24filter="
    monkeypatch.setattr(reader, "utc_now", lambda: NOW)
    return SimpleNamespace(control=control, store=store, caller=caller, target=command.target, saved=saved,
        binding=store.read()["security"]["brokers"]["stage"], app_id=app_id, tenant=tenant,
        target_id=plan["target"]["object_id"], initial=route+f"environment%20eq%20%27Default-{tenant}%27",
        cursor=route+f"environment+eq+%27Default-{tenant}%27&%24skiptoken=",
        payload={"plan_id":plan["plan_id"], "revision":plan["revision"], "resource_environment":"stage",
                 "phase":"before", "observation_started_at":NOW.isoformat(), "pages":[]})


def row(scope, number=0, principal=None):
    name = f"assignment-{number}"
    return {"id":f"/providers/Microsoft.PowerApps/apps/{scope.app_id}/permissions/{name}", "name":name,
            "properties":{"roleName":"CanView", "principal":{"id":principal or scope.target_id,
                "type":"User", "tenantId":scope.tenant}}}


def page(scope, body, url=None):
    return {"request_url":scope.initial if url is None else url, "response_json":json.dumps(body, ensure_ascii=False)}


def chain(scope, bodies, terminal=True):
    pages = []
    for index, body in enumerate(bodies):
        body = deepcopy(body)
        if index < len(bodies)-1 or not terminal:
            body["nextLink"] = scope.cursor + f"page-{index+2}"
        url = scope.initial if index == 0 else scope.cursor + f"page-{index+1}"
        pages.append(page(scope, body, url))
    return pages


def command(scope, pages=None, **updates):
    payload = {**scope.payload, "pages":pages if pages is not None else [page(scope, {"value":[]})], **updates}
    return ValidateAppPermissionRead.model_validate(payload)


def validate(scope, pages=None, **updates):
    return reader.validate_app_permission_read(scope.binding, scope.caller, command(scope, pages, **updates), scope.store)


@pytest.mark.parametrize("count", [1, 2, 3])
def test_complete_prefix_preserves_bindings_and_projects_only_target(scope, count):
    bodies = [{"value":[]} for _ in range(count)]
    target = row(scope)
    target["properties"]["principal"]["displayName"] = "PRIVATE_SENTINEL"
    target["irrelevant"] = {"raw":"PRIVATE_SENTINEL"}
    bodies[-1]["value"] = [target, row(scope, 1, str(uuid4()))]
    result = validate(scope, chain(scope, bodies))
    assert set(result) == RESULT_FIELDS
    assert result["disposition"] == "COMPLETE" and result["reason"] is None
    assert result["page_count"] == count and result["row_count"] == 2
    assert result["next_url"] is None and result["matching_assignments"] == [row(scope)]
    assert result["app_id"] == scope.app_id and result["tenant_id"] == scope.tenant
    assert result["target_object_id"] == scope.target_id and "PRIVATE_SENTINEL" not in json.dumps(result)


@pytest.mark.parametrize("count", [1, 2])
def test_continue_exposes_validated_next_route_without_assignments(scope, count):
    pages = chain(scope, [{"value":[row(scope)]}] + [{"value":[]}] * (count-1), terminal=False)
    result = validate(scope, pages)
    assert result["disposition"] == "CONTINUE" and result["reason"] is None
    assert result["next_url"] == scope.cursor + f"page-{count+1}"
    assert result["matching_assignments"] == []


def test_page_three_with_continuation_is_incomplete(scope):
    result = validate(scope, chain(scope, [{"value":[]}] * 3, terminal=False))
    assert result["disposition"] == "INCOMPLETE" and result["reason"] == "PAGE_LIMIT"
    assert result["next_url"] is None and result["matching_assignments"] == []


@pytest.mark.parametrize("body", [None, [], {}, {"value":None}, {"value":{}}, {"value":[None]},
    {"value":[{}]}, {"value":[], "error":None}, {"value":[], "error":{"private":"PRIVATE_SENTINEL"}}])
def test_malformed_page_never_becomes_verified_absence(scope, body):
    result = validate(scope, [page(scope, body)])
    assert result["disposition"] == "INCOMPLETE" and result["reason"] == "INVALID_PAGE"
    assert result["matching_assignments"] == [] and result["next_url"] is None


@pytest.mark.parametrize("text", ['{"value":[],"value":[]}', '{"value":[],"native":{"a":1,"a":2}}',
    '{"value":[],"native":NaN}', '{"value":[],"native":Infinity}', '{broken'])
def test_duplicate_keys_and_non_json_numbers_fail_safely(scope, text):
    result = validate(scope, [{"request_url":scope.initial, "response_json":text}])
    assert result["reason"] == "INVALID_PAGE" and result["matching_assignments"] == []


def test_json_recursion_failure_is_sanitized(scope, monkeypatch):
    cmd = command(scope)
    def exhausted(*args, **kwargs):
        raise RecursionError("PRIVATE_SENTINEL")
    monkeypatch.setattr(scope.store, "read", lambda: {})
    monkeypatch.setattr(reader, "_scope", lambda *args: (scope.app_id, scope.tenant, scope.target_id))
    monkeypatch.setattr(reader.json, "loads", exhausted)
    result = reader.validate_app_permission_read(scope.binding, scope.caller, cmd, scope.store)
    assert result["reason"] == "INVALID_PAGE" and result["matching_assignments"] == []
    assert "PRIVATE_SENTINEL" not in json.dumps(result)


def test_utf8_encoding_failure_is_sanitized_even_when_model_is_bypassed(scope):
    cmd = command(scope)
    cmd.pages[0].response_json = '{"value":[],"native":"\ud800"}'
    result = reader.validate_app_permission_read(scope.binding, scope.caller, cmd, scope.store)
    assert result["reason"] == "INVALID_PAGE" and result["matching_assignments"] == []


@pytest.mark.parametrize("name", [".", "..", "a..b", "a:b", "a/b", "%2e", "a"*129, "name\n"])
def test_unsafe_assignment_path_is_rejected(scope, name):
    item = row(scope)
    item.update(name=name, id=f"/providers/Microsoft.PowerApps/apps/{scope.app_id}/permissions/{name}")
    assert validate(scope, [page(scope, {"value":[item]})])["reason"] == "INVALID_PAGE"


@pytest.mark.parametrize("field,value", [("id", "invalid"), ("type", "Other"), ("tenantId", str(uuid4())),
                                         ("id", "00000000-0000-0000-0000-000000000000\n"),
                                         ("tenantId", "00000000-0000-0000-0000-000000000000\n")])
def test_bad_principal_guid_type_or_tenant_is_rejected(scope, field, value):
    item = row(scope)
    item["properties"]["principal"][field] = value
    assert validate(scope, [page(scope, {"value":[item]})])["reason"] == "INVALID_PAGE"


@pytest.mark.parametrize("kind", ["identical", "id_changed_fields", "principal_case"])
def test_duplicate_identity_across_pages_is_not_deduplicated_into_success(scope, kind):
    first = row(scope)
    other = deepcopy(first)
    if kind == "id_changed_fields":
        other["properties"]["principal"]["id"] = str(uuid4())
        other["properties"]["roleName"] = "CanEdit"
        other["name"] = first["name"].upper()
        other["id"] = first["id"].rsplit("/", 1)[0] + "/" + other["name"]
    elif kind == "principal_case":
        other = row(scope, 1, scope.target_id.upper())
    result = validate(scope, chain(scope, [{"value":[first]}, {"value":[other]}]))
    assert result["reason"] == "DUPLICATE_ASSIGNMENT" and result["row_count"] == 2
    assert result["matching_assignments"] == []


@pytest.mark.parametrize("role,principal_type", [("Owner", "User"), ("CanEdit", "User"), ("CanView", "Group")])
def test_elevated_or_non_user_target_is_preserved_for_flow_role_guard(scope, role, principal_type):
    item = row(scope)
    item["properties"].update(roleName=role)
    item["properties"]["principal"].update(type=principal_type, id=scope.target_id.upper(), tenantId=scope.tenant.upper())
    result = validate(scope, [page(scope, {"value":[item]})])
    assert result["disposition"] == "COMPLETE" and len(result["matching_assignments"]) == 1
    found = result["matching_assignments"][0]["properties"]
    assert found["roleName"] == role and found["principal"]["type"] == principal_type
    assert found["principal"]["id"] == scope.target_id and found["principal"]["tenantId"] == scope.tenant


@pytest.mark.parametrize("count,reason", [(999, None), (1000, "ROW_LIMIT")])
def test_cumulative_raw_row_boundary(scope, count, reason):
    rows = [row(scope, index, str(UUID(int=index+1))) for index in range(count)]
    result = validate(scope, chain(scope, [{"value":rows[:500]}, {"value":rows[500:]}]))
    assert result["reason"] == reason and result["row_count"] == count
    assert result["disposition"] == ("COMPLETE" if reason is None else "INCOMPLETE")


@pytest.mark.parametrize("field", ["nextLink", "@odata.nextLink"])
@pytest.mark.parametrize("value", [False, 0, [], {}])
def test_cursor_wrong_types_fail_closed(scope, field, value):
    assert validate(scope, [page(scope, {"value":[], field:value})])["reason"] == "INVALID_CURSOR"


@pytest.mark.parametrize("token", ["opaque-._~", "opaque%2B%2F%3D", "%FF%80", "%252F"])
def test_cursor_canonical_opaque_bytes_are_preserved(scope, token):
    url = scope.cursor + token
    result = validate(scope, [page(scope, {"value":[], "nextLink":url, "@odata.nextLink":url})])
    assert result["disposition"] == "CONTINUE" and result["next_url"] == url


@pytest.mark.parametrize("token", ["", "a"*2049, "a+b", "a/b", "%2f", "%41", "%7E", "%", "%GG",
                                   "%00", "%1F", "%7F", "a&extra=1", "a#fragment", "a\\b", "a\n"])
def test_cursor_suffix_requires_exact_canonical_serialization(scope, token):
    result = validate(scope, [page(scope, {"value":[], "nextLink":scope.cursor+token})])
    assert result["reason"] == "INVALID_CURSOR" and result["next_url"] is None


@pytest.mark.parametrize("change", ["host", "scheme", "port", "app", "tenant", "version", "spaces", "duplicate", "order"])
def test_cursor_scope_and_query_serialization_cannot_change(scope, change):
    url = scope.cursor + "next"
    changes = {
        "host":("api.powerapps.com", "example.invalid"), "scheme":("https://", "http://"),
        "port":("api.powerapps.com/", "api.powerapps.com:443/"), "app":(scope.app_id, str(uuid4())),
        "tenant":(scope.tenant, str(uuid4())), "version":("2017-06-01", "2016-11-01"),
        "spaces":("environment+eq+", "environment%20eq%20"),
        "duplicate":("&%24skiptoken=", "&api-version=2017-06-01&%24skiptoken="),
        "order":("?api-version=2017-06-01&%24filter=", "?%24filter=2017-06-01&api-version="),
    }
    result = validate(scope, [page(scope, {"value":[], "nextLink":url.replace(*changes[change])})])
    assert result["reason"] == "INVALID_CURSOR"


def test_cursor_chain_rejects_conflicts_repeats_mismatches_and_trailing_pages(scope):
    cases = [
        [page(scope, {"value":[], "nextLink":scope.cursor+"a", "@odata.nextLink":scope.cursor+"b"})],
        [page(scope, {"value":[]}), page(scope, {"value":[]}, scope.cursor+"a")],
        [page(scope, {"value":[], "nextLink":scope.cursor+"a"}), page(scope, {"value":[]}, scope.cursor+"b")],
        [page(scope, {"value":[], "nextLink":scope.cursor+"a"}),
         page(scope, {"value":[], "nextLink":scope.cursor+"a"}, scope.cursor+"a")],
        [page(scope, {"value":[]}, scope.initial+"&unexpected=1")],
    ]
    assert all(validate(scope, pages)["reason"] == "INVALID_CURSOR" for pages in cases)


@pytest.mark.parametrize("offset,reason", [(-90, "DEADLINE_EXPIRED"), (-91, "DEADLINE_EXPIRED"),
    (-89.999, None), (5, None), (5.001, "DEADLINE_EXPIRED")])
def test_deadline_and_future_skew_boundaries(scope, offset, reason):
    started = (NOW + timedelta(seconds=offset)).isoformat()
    assert validate(scope, observation_started_at=started)["reason"] == reason


def test_native_seven_digit_timestamp_is_echoed_without_truncation(scope):
    timestamp = "2026-09-25T17:59:59.1234567Z"
    result = validate(scope, observation_started_at=timestamp)
    assert result["observation_started_at"] == timestamp
    assert datetime.fromisoformat(result["expires_at"]) == datetime(2026, 9, 25, 18, 1, 29, 123456, timezone.utc)


def test_budget_is_rechecked_after_page_validation(scope, monkeypatch):
    times = iter([NOW, NOW+timedelta(seconds=90)])
    monkeypatch.setattr(reader, "utc_now", lambda: next(times))
    assert validate(scope)["reason"] == "DEADLINE_EXPIRED"


def test_utf8_budget_precedes_parsing_every_page(scope, monkeypatch):
    pages = chain(scope, [{"value":[]}, {"value":[], "padding":"é"*125_000}])
    def forbidden(*args, **kwargs):
        pytest.fail("No page may be parsed before cumulative UTF-8 sizing succeeds")
    monkeypatch.setattr(reader, "strict_json_loads", forbidden)
    assert validate(scope, pages)["reason"] == "INVALID_PAGE"


def test_exact_three_page_utf8_budget_is_accepted(scope):
    pages = chain(scope, [{"value":[], "padding":""}] * 3)
    for item in pages:
        item["response_json"] = item["response_json"].replace('"padding": ""', '"padding": "' +
            "x" * (250_000-len(item["response_json"].encode("utf-8"))) + '"')
        assert len(item["response_json"].encode("utf-8")) == 250_000
    assert validate(scope, pages)["disposition"] == "COMPLETE"


@pytest.mark.parametrize("update", [{"phase":True}, {"observation_started_at":True},
    {"observation_started_at":NOW.timestamp()}, {"observation_started_at":"2026-09-25T18:00:00"},
    {"observation_started_at":"2026-09-25T18:00:00+01:00"}, {"observation_started_at":"2026-02-30T18:00:00Z"},
    {"observation_started_at":"9999-12-31T23:59:59Z"},
    {"resource_environment":"other"}, {"lease_id":str(uuid4())}, {"native_run":{}}, {"pages":[]}])
def test_payload_does_not_coerce_or_accept_authority_fields(scope, update):
    with pytest.raises(ValidationError):
        command(scope, **update)


def test_original_actor_profile_and_current_binding_are_required(scope):
    cmd = command(scope)
    other = context(scope.control, "Kristen Fleming")
    with pytest.raises(AuthorizationError) as error:
        reader.validate_app_permission_read(scope.binding, other, cmd, scope.store)
    assert error.value.status_code == 403
    prod = context(scope.control, profile="prod")
    with pytest.raises(AuthorizationError):
        reader.validate_app_permission_read(scope.store.read()["security"]["brokers"]["prod"], prod, cmd, scope.store)
    with pytest.raises(AuthorizationError):
        reader.validate_app_permission_read({**scope.binding, "broker_id":"other"}, scope.caller, cmd, scope.store)
    with pytest.raises(AuthorizationError):
        reader.validate_app_permission_read(scope.binding, replace(scope.caller, broker_id="other"), cmd, scope.store)


def test_revoked_capability_invalidates_previously_authorized_context(scope):
    key = principal_key(scope.caller.tenant_id, scope.caller.object_id)
    scope.store.mutate(lambda state: state["users"][key].update(role="OPERATOR"))
    with pytest.raises(AuthorizationError) as error:
        validate(scope)
    assert error.value.status_code == 403


def test_missing_changed_completed_and_superseded_plan_are_rejected(scope):
    with pytest.raises(AuthorizationError) as missing:
        validate(scope, plan_id=str(uuid4()))
    assert missing.value.status_code == 404
    with pytest.raises(AuthorizationError) as changed:
        validate(scope, revision=str(uuid4()))
    assert changed.value.status_code == 409
    save_user_access(scope.caller, access_command(scope.control, person=scope.target, role="ADMIN"), scope.store)
    with pytest.raises(AuthorizationError) as stale:
        validate(scope)
    assert stale.value.status_code == 409


def test_completed_plan_is_rejected(scope):
    complete(scope.control, scope.saved)
    with pytest.raises(AuthorizationError) as error:
        validate(scope)
    assert error.value.status_code == 409


@pytest.mark.parametrize("change", ["duplicate", "permission", "resource"])
def test_plan_must_select_exactly_one_current_app_resource(scope, change):
    def mutate(state):
        resources = state["sharing_plans"][scope.payload["plan_id"]]["resources"]
        item = next(r for r in resources if r["kind"] == "app" and r["environment"] == "stage")
        if change == "duplicate":
            resources.append(dict(item))
        elif change == "permission":
            item["permission"] = "run-only"
        else:
            item["resource_id"] = str(uuid4())
    scope.store.mutate(mutate)
    with pytest.raises(AuthorizationError) as error:
        validate(scope)
    assert error.value.status_code == 409


def test_validation_reads_one_fresh_snapshot_without_writes_network_or_secret_outputs(scope, monkeypatch, capsys, caplog):
    before = scope.store.path.read_bytes()
    reads = []
    original = scope.store.read
    def observed():
        reads.append(True)
        return original()
    def forbidden(*args, **kwargs):
        pytest.fail("Permission qualification must be read-only and offline")
    monkeypatch.setattr(scope.store, "read", observed)
    monkeypatch.setattr(scope.store, "mutate", forbidden)
    monkeypatch.setattr(scope.store, "_write", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("api.runtime.open_repository", forbidden)
    result = validate(scope, [page(scope, {"value":[], "error":"PRIVATE_SENTINEL"})])
    assert reads == [True] and scope.store.path.read_bytes() == before
    assert "PRIVATE_SENTINEL" not in json.dumps(result) + caplog.text + capsys.readouterr().out


def test_readonly_operation_uses_existing_broker_and_keeps_state_unchanged(scope, monkeypatch):
    payload = command(scope).model_dump(mode="json")
    before = scope.store.path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Business database must not be used")
    monkeypatch.setattr("api.runtime.open_repository", forbidden)
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke", auth=("synthetic-stage-broker", "synthetic-broker-password"),
            json=envelope(scope.control, "ValidateAppPermissionRead", payload))
    assert response.status_code == 200
    assert json.loads(response.json()["result_json"])["disposition"] == "COMPLETE"
    assert scope.store.path.read_bytes() == before


@pytest.mark.parametrize("kind", ["extra", "duplicate", "wrong_type", "four_pages", "envelope_limit", "surrogate", "timestamp_overflow"])
def test_broker_payload_errors_are_fixed_and_do_not_echo_private_content(scope, kind):
    payload = command(scope).model_dump(mode="json")
    if kind == "extra":
        payload["PRIVATE_SENTINEL"] = "PRIVATE_SENTINEL"
    elif kind == "wrong_type":
        payload["pages"][0]["response_json"] = {"PRIVATE_SENTINEL":True}
    elif kind == "four_pages":
        payload["pages"] *= 4
    elif kind == "surrogate":
        payload["pages"][0]["response_json"] = '{"value":[],"native":"\ud800PRIVATE_SENTINEL"}'
    elif kind == "timestamp_overflow":
        payload["observation_started_at"] = "9999-12-31T23:59:59Z"
    body = envelope(scope.control, "ValidateAppPermissionRead", payload)
    if kind == "duplicate":
        body["payload_json"] = body["payload_json"][:-1] + ',"phase":"PRIVATE_SENTINEL"}'
    elif kind == "envelope_limit":
        body["payload_json"] = "PRIVATE_SENTINEL" + "x"*1_100_000
    before = scope.store.path.read_bytes()
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke", auth=("synthetic-stage-broker", "synthetic-broker-password"), json=body)
    assert response.status_code == 422 and response.json()["code"] == "INVALID_REQUEST"
    assert "PRIVATE_SENTINEL" not in response.text and scope.store.path.read_bytes() == before
