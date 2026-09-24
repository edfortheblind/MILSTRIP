"""The two broker flows share one quota; delayed/unknown calls cannot bunch."""
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api import app as api
from api import management_pacing as pacing
from api.authorization import AuthorizationError, save_user_access
from api.broker_models import RecordManagementCall, ReserveManagementCall
from api.control import ControlError, ControlStore
from tests.test_control_broker import access_command, context, control, envelope
from tests.test_sharing_leases import claim, finish


@pytest.fixture
def clock(monkeypatch):
    current = [datetime(2026, 9, 24, 18, tzinfo=timezone.utc)]
    monkeypatch.setattr(pacing, "utc_now", lambda: current[0])
    return current


def reserve(store, plan, lease, step="Before_add_stage_flow", profile="stage"):
    command = ReserveManagementCall(plan_id=plan["plan_id"], revision=plan["revision"],
        lease_id=lease["lease_id"], execution_id=lease["execution_id"], step=step)
    result = pacing.reserve_management_call(store.read()["security"]["brokers"][profile], command, store)
    return result, command


def complete(store, reservation, command, *, known=True, profile="stage"):
    body = RecordManagementCall(**command.model_dump(), reservation_id=reservation["reservation_id"], outcome_known=known)
    return pacing.record_management_call(store.read()["security"]["brokers"][profile], body, store), body


def setup_plan(control, profile="stage"):
    store, _ = control
    request = access_command(control)
    plan = save_user_access(context(control, profile=profile), request, store)["sharing_plan"]
    lease, _ = claim(store, plan, profile)
    return plan, lease, request


def test_legacy_version_one_state_gains_optional_pacer_without_cutover(control, clock):
    store, _ = control
    assert "management_pacing" not in store.read()
    plan, lease, _ = setup_plan(control)
    reservation, _ = reserve(store, plan, lease)
    state = store.read()
    assert state["version"] == 1 and not state["security"]["enforced"] and not state["runtime"]["active"]
    assert reservation["not_before"] == "2026-09-24T18:00:00Z"
    assert state["management_pacing"]["active"] is not None


def test_one_inflight_permit_covers_both_flows_and_different_people(control, clock):
    store, _ = control
    one, first, _ = setup_plan(control)
    reservation, command = reserve(store, one, first)
    two, second, _ = setup_plan(control, "prod")
    with pytest.raises(AuthorizationError, match="connection is busy"):
        reserve(store, two, second, profile="prod")
    # Busy reserve issued no external call; the second target can close/retry.
    assert finish(store, two, second, profile="prod", observations=[])[0]["sharing_plan"]["status"] == "pending"
    # A delayed first run still owns the global permit; future reservations do not pile up.
    clock[0] += timedelta(minutes=3)
    with pytest.raises(AuthorizationError, match="finish before"):
        finish(store, one, first)
    complete(store, reservation, command)
    second, _ = claim(store, two, "prod")
    queued, _ = reserve(store, two, second, profile="prod")
    assert queued["not_before"] == "2026-09-24T18:03:13Z"


def test_six_calls_have_at_most_five_starts_in_any_sixty_seconds(control, clock):
    store, _ = control
    plan, lease, _ = setup_plan(control)
    starts = []
    for step in ("Before_add_stage_flow", "Add_add_stage_flow", "Readback_add_stage_flow",
                 "Before_add_prod_flow", "Add_add_prod_flow", "Readback_add_prod_flow"):
        reservation, command = reserve(store, plan, lease, step)
        clock[0] = datetime.fromisoformat(reservation["not_before"].replace("Z", "+00:00"))
        starts.append(clock[0])
        complete(store, reservation, command)
    assert (starts[-1] - starts[0]).total_seconds() == 65
    assert all(sum(start <= other < start + timedelta(seconds=60) for other in starts) <= 5 for start in starts)


def test_reservation_replay_and_completion_are_idempotent_but_action_cannot_restart(control, clock):
    store, _ = control
    plan, lease, _ = setup_plan(control)
    result, command = reserve(store, plan, lease)
    assert reserve(store, plan, lease)[0] == result
    complete(store, result, command)
    saved = store.read()["management_pacing"]["not_before"]
    clock[0] += timedelta(seconds=60)
    assert complete(store, result, command)[0]["status"] == "CLOSED"
    assert store.read()["management_pacing"]["not_before"] == saved
    with pytest.raises(AuthorizationError, match="cannot restart"):
        reserve(store, plan, lease)


def test_unknown_call_survives_restart_supersession_and_requires_original_completion(control, clock):
    store, _ = control
    plan, lease, request = setup_plan(control)
    reservation, command = reserve(store, plan, lease)
    assert complete(store, reservation, command, known=False)[0]["status"] == "UNKNOWN"
    finish(store, plan, lease, known=False, observations=[])
    later = save_user_access(context(control), access_command(control, active=False, upn=request.target.upn), store)["sharing_plan"]
    restarted = ControlStore(store.path)
    clock[0] += timedelta(days=2)
    another, another_lease, _ = setup_plan(control, "prod")
    with pytest.raises(AuthorizationError, match="connection is busy"):
        reserve(restarted, another, another_lease, profile="prod")
    assert complete(restarted, reservation, command)[0]["status"] == "CLOSED"
    assert finish(restarted, plan, lease)[0]["sharing_plan"]["status"] == "superseded"
    claim(restarted, later, "prod")


@pytest.mark.parametrize("field", ["lease_id", "execution_id", "reservation_id", "plan_id", "revision"])
def test_completion_rejects_wrong_identity_without_releasing_permit(control, clock, field):
    store, _ = control
    plan, lease, _ = setup_plan(control)
    reservation, command = reserve(store, plan, lease)
    body = command.model_dump() | {"reservation_id": reservation["reservation_id"], "outcome_known": True, field: uuid4()}
    with pytest.raises(AuthorizationError):
        pacing.record_management_call(store.read()["security"]["brokers"]["stage"], RecordManagementCall(**body), store)
    assert store.read()["management_pacing"]["active"] is not None
    with pytest.raises(AuthorizationError):
        complete(store, reservation, command, profile="prod")


def test_superseded_and_unleased_plans_cannot_reserve(control, clock):
    store, _ = control
    plan, lease, request = setup_plan(control)
    save_user_access(context(control), access_command(control, active=False, upn=request.target.upn), store)
    with pytest.raises(AuthorizationError, match="superseded"):
        reserve(store, plan, lease)
    with pytest.raises(AuthorizationError, match="running sharing lease"):
        reserve(store, plan, {**lease, "lease_id": str(uuid4())})


def test_control_mutation_cannot_drop_active_or_reopen_completed_permit(control, clock):
    store, _ = control
    plan, lease, _ = setup_plan(control)
    reservation, command = reserve(store, plan, lease)
    with pytest.raises(ControlError):
        store.mutate(lambda state: state.pop("management_pacing"))
    with pytest.raises(ControlError):
        store.mutate(lambda state: state["management_pacing"].update(active=None))
    complete(store, reservation, command)
    key = next(iter(store.read()["management_pacing"]["reservations"]))
    with pytest.raises(ControlError):
        store.mutate(lambda state: state["management_pacing"]["reservations"][key].update(status="RUNNING"))


def test_only_fixed_management_actions_are_reservable(control):
    plan, lease, _ = setup_plan(control)
    with pytest.raises(ValidationError):
        ReserveManagementCall(plan_id=plan["plan_id"], revision=plan["revision"], lease_id=lease["lease_id"],
                              execution_id=lease["execution_id"], step="Delete_any_flow")


def test_internal_management_operations_use_broker_binding_and_safe_errors(control, clock):
    store, _ = control
    plan, lease, _ = setup_plan(control)
    command = ReserveManagementCall(plan_id=plan["plan_id"], revision=plan["revision"], lease_id=lease["lease_id"],
                                    execution_id=lease["execution_id"], step="Before_add_stage_flow")
    auth = ("synthetic-stage-broker", "synthetic-broker-password")
    with TestClient(api.app, client=("127.0.0.1", 5000)) as client:
        response = client.post("/api/v1/broker/invoke", auth=auth,
            json=envelope(control, "ReserveManagementCall", command.model_dump(mode="json")))
        assert response.status_code == 200
        reserved = json.loads(response.json()["result_json"])
        callback = RecordManagementCall(**command.model_dump(), reservation_id=reserved["reservation_id"], outcome_known=True)
        response = client.post("/api/v1/broker/invoke", auth=auth,
            json=envelope(control, "RecordManagementCall", callback.model_dump(mode="json")))
        assert response.status_code == 200 and json.loads(response.json()["result_json"])["status"] == "CLOSED"
