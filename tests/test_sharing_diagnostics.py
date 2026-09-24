"""Fixed readback diagnostics preserve lease ownership and completion rules."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api import app as api
from api.authorization import AuthorizationError, record_sharing_result, save_user_access
from api.broker_models import SharingResult
from tests.test_control_broker import access_command, context, control, envelope
from tests.test_sharing_leases import claim


def result_payload():
    return dict(plan_id=uuid4(), revision=uuid4(), lease_id=uuid4(),
                execution_id=uuid4(), external_calls_complete=True, observations=[])


def test_diagnostics_schema_is_closed_and_retains_legacy_codes_and_null():
    reasons = ("PLAN_MISMATCH", "CALL_FAILED", "FILTER_FAILED", "PAGINATED",
               "ROW_LIMIT", "PERMISSION_MISMATCH")
    expected = {f"READBACK_{reason}_{profile}_{kind}"
                for reason in reasons for profile in ("STAGE", "PROD") for kind in ("APP", "FLOW")}
    expected.update(("PLATFORM_FAILED", "READBACK_FAILED"))
    schema = SharingResult.model_json_schema()["properties"]["error_code"]
    assert set(schema["anyOf"][0]["enum"]) == expected
    for code in (*expected, None):
        assert SharingResult(**result_payload(), error_code=code).error_code == code
    assert SharingResult(**result_payload()).error_code is None


@pytest.mark.parametrize("code", [
    "native response text", "synthetic.user@example.invalid",
    "https://example.invalid/next?token=synthetic", "READBACK_PAGINATED_OTHER_APP",
    "READBACK_CALL_FAILED_STAGE_APP\n", {"error": "synthetic"}, 429,
])
def test_arbitrary_response_data_is_not_a_diagnostic(code):
    with pytest.raises(ValidationError):
        SharingResult(**result_payload(), error_code=code)


def prepared_result(control, *, verified, complete=True):
    store, _ = control
    plan = save_user_access(context(control), access_command(control), store)["sharing_plan"]
    lease, _ = claim(store, plan)
    observations = [{key: item[key] for key in ("kind", "resource_id", "permission", "present")}
                    | {"verified": verified} for item in plan["resources"]]
    command = SharingResult(plan_id=plan["plan_id"], revision=plan["revision"],
                            lease_id=lease["lease_id"], execution_id=lease["execution_id"],
                            external_calls_complete=complete, observations=observations,
                            error_code="READBACK_PAGINATED_STAGE_APP")
    return store, store.read()["security"]["brokers"]["stage"], command


def test_failed_readback_persists_fixed_reason_without_activating_membership(control):
    store, binding, command = prepared_result(control, verified=False)
    response = record_sharing_result(binding, command, store)
    assert response["sharing_plan"]["status"] == "pending"
    assert response["sharing_plan"]["error_code"] == "READBACK_PAGINATED_STAGE_APP"
    assert response["membership"]["access_state"] == "pending"
    assert store.read()["sharing_plans"][str(command.plan_id)]["error_code"] == command.error_code


def test_verified_completion_clears_diagnostic_and_unknown_outcome_takes_precedence(control):
    store, binding, command = prepared_result(control, verified=True, complete=False)
    response = record_sharing_result(binding, command, store)
    assert response["sharing_plan"]["status"] == "pending"
    assert response["sharing_plan"]["error_code"] == "PLATFORM_OUTCOME_UNKNOWN"
    assert response["membership"]["access_state"] == "pending"
    assert store.read()["sharing_leases"]
    response = record_sharing_result(binding, command.model_copy(update={"external_calls_complete": True}), store)
    assert response["sharing_plan"]["status"] == "completed"
    assert response["sharing_plan"]["error_code"] is None
    assert response["membership"]["access_state"] == "active"


def test_diagnostic_does_not_bypass_callback_lease_ownership(control):
    store, binding, command = prepared_result(control, verified=False)
    before = store.path.read_bytes()
    forged = command.model_copy(update={"lease_id": uuid4()})
    with pytest.raises(AuthorizationError, match="does not own"):
        record_sharing_result(binding, forged, store)
    assert store.path.read_bytes() == before


def test_http_validation_does_not_echo_unapproved_diagnostic_data(control):
    store, _, command = prepared_result(control, verified=False)
    before = store.path.read_bytes()
    payload = command.model_dump(mode="json")
    payload["error_code"] = "PRIVATE_RESPONSE_SENTINEL https://example.invalid/?token=synthetic"
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke",
                               auth=("synthetic-stage-broker", "synthetic-broker-password"),
                               json=envelope(control, "RecordSharingResult", payload))
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"
    assert "PRIVATE_RESPONSE_SENTINEL" not in response.text
    assert "example.invalid" not in response.text
    assert store.path.read_bytes() == before
