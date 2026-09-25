"""Slow grants cannot race a completed access removal across Stage/Prod flows."""
from copy import deepcopy
from uuid import uuid4

import pytest

from api.authorization import (AuthorizationError, acquire_sharing_lease, authorize_person,
                               record_sharing_result, save_user_access)
from api.broker_models import AcquireSharingLease, SharingResult
from api.control import ControlError, ControlStore, principal_key
from tests.test_control_broker import access_command, context, control


def claim(store, plan, profile='stage', execution_id=None):
    binding = store.read()['security']['brokers'][profile]
    command = AcquireSharingLease(plan_id=plan['plan_id'], revision=plan['revision'], execution_id=execution_id or uuid4())
    return acquire_sharing_lease(binding, command, store), command


def test_native_run_binding_is_exact_immutable_and_retry_safe(control):
    store, _ = control
    plan = save_user_access(context(control), access_command(control), store)['sharing_plan']
    state = store.read()
    binding = state['security']['brokers']['stage']
    native = dict(environment_name='Default-' + binding['tenant_id'],
                  flow_id=state['resources']['stage']['flow_id'], run_id='synthetic-run-01')
    command = AcquireSharingLease(plan_id=plan['plan_id'], revision=plan['revision'],
                                  execution_id=uuid4(), native_run=native)
    receipt = acquire_sharing_lease(binding, command, store)
    assert acquire_sharing_lease(binding, command, store) == receipt
    changed = command.model_copy(update={'native_run': command.native_run.model_copy(update={'run_id': 'other-run'})})
    with pytest.raises(AuthorizationError, match='cannot restart'):
        acquire_sharing_lease(binding, changed, store)
    # A bound execution cannot become a legacy execution on retry.
    with pytest.raises(AuthorizationError, match='cannot restart'):
        acquire_sharing_lease(binding, command.model_copy(update={'native_run': None}), store)
    def rewrite(state):
        execution = state['sharing_plans'][plan['plan_id']]['executions'][str(command.execution_id)]
        execution['native_run']['run_id'] = 'rewritten'
        key = principal_key(plan['target']['tenant_id'], plan['target']['object_id'])
        state['sharing_leases'][key]['native_run']['run_id'] = 'rewritten'
    with pytest.raises(ControlError):
        store.mutate(rewrite)
    finish(store, plan, receipt)
    saved = store.read()['sharing_plans'][plan['plan_id']]['executions'][str(command.execution_id)]
    assert saved['native_run'] == native


@pytest.mark.parametrize('field,value', [('flow_id', str(uuid4())), ('environment_name', 'Default-wrong')])
def test_native_run_cannot_claim_another_bound_resource(control, field, value):
    store, _ = control
    plan = save_user_access(context(control), access_command(control), store)['sharing_plan']
    state = store.read()
    binding = state['security']['brokers']['stage']
    native = dict(environment_name='Default-' + binding['tenant_id'],
                  flow_id=state['resources']['stage']['flow_id'], run_id='synthetic-run-02')
    native[field] = value
    command = AcquireSharingLease(plan_id=plan['plan_id'], revision=plan['revision'],
                                  execution_id=uuid4(), native_run=native)
    before = store.read()
    with pytest.raises(AuthorizationError, match='does not match'):
        acquire_sharing_lease(binding, command, store)
    assert store.read() == before


def finish(store, plan, lease, *, profile='stage', known=True, observations=None):
    if observations is None:
        observations = [{k: item[k] for k in ('kind', 'resource_id', 'permission', 'present')} | {'verified': True}
                        for item in plan['resources']]
    command = SharingResult(plan_id=plan['plan_id'], revision=plan['revision'], lease_id=lease['lease_id'],
                            execution_id=lease['execution_id'], external_calls_complete=known, observations=observations)
    return record_sharing_result(store.read()['security']['brokers'][profile], command, store), command


def test_old_add_holds_cross_flow_removal_pending_until_external_execution_finishes(control):
    store, _ = control
    admin = context(control)
    request = access_command(control)
    add = save_user_access(admin, request, store)['sharing_plan']
    older, _ = claim(store, add)
    remove = save_user_access(admin, access_command(control, active=False, upn=request.target.upn), store)['sharing_plan']
    with pytest.raises(AuthorizationError, match='earlier sharing execution'):
        claim(store, remove, 'prod')
    with pytest.raises(AuthorizationError):
        authorize_person(store.read()['security']['brokers']['stage'], request.target, uuid4(), store)
    assert store.read()['sharing_plans'][remove['plan_id']]['status'] == 'pending'
    stale, old_callback = finish(store, add, older)
    assert stale['sharing_plan']['status'] == 'superseded'
    assert stale['latest_sharing_plan']['plan_id'] == remove['plan_id']
    assert stale['membership']['access_state'] == 'denied'
    newer, _ = claim(store, remove, 'prod')
    # Retried old callback cannot release the newer flow's lease.
    record_sharing_result(store.read()['security']['brokers']['stage'], old_callback, store)
    key = principal_key(add['target']['tenant_id'], add['target']['object_id'])
    assert store.read()['sharing_leases'][key]['lease_id'] == newer['lease_id']
    done, _ = finish(store, remove, newer, profile='prod')
    assert done['sharing_plan']['status'] == 'completed' and done['membership']['access_state'] == 'denied'


def test_unknown_external_call_never_expires_or_allows_takeover_after_restart(control):
    store, _ = control
    admin = context(control)
    request = access_command(control)
    add = save_user_access(admin, request, store)['sharing_plan']
    older, old_claim = claim(store, add)
    pending, _ = finish(store, add, older, known=False)
    assert pending['sharing_plan']['error_code'] == 'PLATFORM_OUTCOME_UNKNOWN'
    remove = save_user_access(admin, access_command(control, active=False, upn=request.target.upn), store)['sharing_plan']
    restarted = ControlStore(store.path)
    with pytest.raises(AuthorizationError, match='earlier sharing execution'):
        claim(restarted, remove, 'prod')
    with pytest.raises(AuthorizationError):
        acquire_sharing_lease(restarted.read()['security']['brokers']['stage'], old_claim, restarted)
    assert restarted.read()['sharing_plans'][remove['plan_id']]['status'] == 'pending'
    # Only trusted evidence that the original external execution is finished
    # closes its lease; no clock-based expiry or new run can take ownership.
    finish(restarted, add, older, known=True)
    newer, _ = claim(restarted, remove, 'prod')
    assert finish(restarted, remove, newer, profile='prod')[0]['sharing_plan']['status'] == 'completed'


def test_same_execution_claim_is_idempotent_but_cannot_restart_after_close(control):
    store, _ = control
    add = save_user_access(context(control), access_command(control), store)['sharing_plan']
    lease, command = claim(store, add)
    binding = store.read()['security']['brokers']['stage']
    assert acquire_sharing_lease(binding, command, store) == lease
    finish(store, add, lease, observations=[])
    with pytest.raises(AuthorizationError, match='cannot restart'):
        acquire_sharing_lease(binding, command, store)
    new_lease, _ = claim(store, add)
    assert new_lease['lease_id'] != lease['lease_id']


def test_old_command_retry_returns_current_desired_plan_without_regranting(control):
    store, _ = control
    admin = context(control)
    request = access_command(control)
    add = save_user_access(admin, request, store)['sharing_plan']
    remove = save_user_access(admin, access_command(control, active=False, upn=request.target.upn), store)['sharing_plan']
    replay = save_user_access(admin, request, store)
    assert replay['superseded'] is True and replay['sharing_plan']['plan_id'] == remove['plan_id']
    assert all(item['present'] is False for item in replay['sharing_plan']['resources'])
    with pytest.raises(AuthorizationError, match='superseded'):
        claim(store, add)


def test_callback_requires_exact_lease_execution_and_owning_broker(control):
    store, _ = control
    plan = save_user_access(context(control), access_command(control), store)['sharing_plan']
    lease, _ = claim(store, plan)
    for changes, profile in [({'lease_id': str(uuid4())}, 'stage'),
                             ({'execution_id': str(uuid4())}, 'stage'), ({}, 'prod')]:
        with pytest.raises(AuthorizationError, match='own the execution lease'):
            finish(store, plan, {**lease, **changes}, profile=profile)
    assert finish(store, plan, lease)[0]['sharing_plan']['status'] == 'completed'


def test_generic_state_update_cannot_drop_an_open_external_execution(control):
    store, _ = control
    plan = save_user_access(context(control), access_command(control), store)['sharing_plan']
    claim(store, plan)
    with pytest.raises(ControlError):
        store.mutate(lambda state: state['sharing_leases'].clear())
    assert len(store.read()['sharing_leases']) == 1


def test_unrelated_users_do_not_share_a_lease(control):
    store, _ = control
    admin = context(control)
    first = access_command(control)
    one = save_user_access(admin, first, store)['sharing_plan']
    claim(store, one)
    second = access_command(control)
    second.target = second.target.model_copy(update={'upn': 'another.operator@austinlighthouse.org'})
    two = save_user_access(admin, second, store)['sharing_plan']
    claim(store, two, 'prod')
    assert len(store.read()['sharing_leases']) == 2
