"""Synthetic host recovery tests; no native services or real control files."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.authorization import (AuthorizationError, acquire_sharing_lease, authorize_person,
                               record_sharing_result, save_user_access)
from api.broker_models import AcquireSharingLease, DirectoryPerson, SaveUserAccess, SharingResult
from api.control import ControlError, ControlStore, principal_key
from api.control_bootstrap import bootstrap_state
from api.sharing_recovery import (BROKER_API, HISTORICAL, REASON, NativeRecoveryCollector,
                                 RecoveryRequest, RecoveryService, preview_captured_evidence)
from tests.test_control_broker import synthetic_manifest


NOW = datetime(2026, 9, 25, 15, 0, tzinfo=timezone.utc)


class SyntheticCollector(NativeRecoveryCollector):
    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = 0

    def collect(self):
        self.calls += 1
        return deepcopy(self.evidence)


def native_evidence(actor_id):
    """Synthesize the reviewed action classes without copying native payloads."""
    inventory, actions = [], []
    started = NOW - timedelta(minutes=10)

    def add(name, connection=None, operation=None, broker_operation=None, status='Skipped', offset=None):
        apis = {'broker': BROKER_API, 'makers': 'shared_powerappsforappmakers',
                'management': 'shared_flowmanagement', 'invoker': 'shared_office365users'}
        inventory.append(dict(name=name, type='OpenApiConnection' if connection else 'Compose',
            connection=connection, operation=operation, broker_operation=broker_operation,
            api_name=apis.get(connection), ancestors=[], ancestor_branches=[]))
        start = started + timedelta(seconds=offset) if offset is not None else None
        actions.append(dict(name=name, status=status, code=None,
                            start_time=start.isoformat() if start else None,
                            end_time=(start + timedelta(seconds=1)).isoformat() if start else None))

    add('Save_membership_add', 'broker', 'InvokeBroker', 'SaveUserAccess', 'Succeeded', 1)
    add('Acquire_lease_add', 'broker', 'InvokeBroker', 'AcquireSharingLease', 'Succeeded', 3)
    for mode in ('add', 'remove'):
        for profile in ('stage', 'prod'):
            for phase in ('Before', 'Add', 'Remove', 'Readback'):
                name = f'{phase}_{mode}_{profile}_flow'
                add(name, 'management', 'ListFlowUsers' if phase in ('Before', 'Readback') else 'ModifyRunOnlyUsers')
                add('Reserve_' + name, 'broker', 'InvokeBroker', 'ReserveManagementCall')
                add('Record_permit_' + name, 'broker', 'InvokeBroker', 'RecordManagementCall')
                app_name = f'{phase}_{mode}_{profile}_app'
                first = app_name == 'Before_add_stage_app'
                add(app_name, 'makers', 'Get-AppRoleAssignment' if phase in ('Before', 'Readback') else 'Edit-AppRoleAssignment',
                    status='Cancelled' if first else 'Skipped', offset=5 if first else None)
    add('Invoke_operation', 'broker', 'InvokeBroker')  # Dynamic branch must remain skipped.
    add('Read_invoker', 'invoker', 'MyProfile_V2', status='Succeeded', offset=0)
    while len(inventory) < 225:
        add('Compose_' + str(len(inventory)))
    environment = 'Default-' + HISTORICAL['tenant_id']
    attached = '/providers/Microsoft.ProcessSimple/environments/' + environment + '/flows/' + HISTORICAL['attached_flow_name']
    return dict(source='native-sharing-recovery-metadata', schema_version=1, collected_at=(NOW-timedelta(seconds=1)).isoformat(),
        tenant_id=HISTORICAL['tenant_id'], environment=environment, actor_object_id=actor_id,
        flow_id=HISTORICAL['flow_id'], run_id=HISTORICAL['run_id'],
        run=dict(status='Cancelled', start_time=started.isoformat(), end_time=(started+timedelta(minutes=1)).isoformat(),
                 workflow_id=attached, workflow_name=HISTORICAL['attached_flow_name'], workflow_version=None),
        actions=actions, definition=dict(attached_flow_name=HISTORICAL['attached_flow_name'], attached_flow_id=attached,
            snapshot_identity_source='run.properties.flow.name', sha256=HISTORICAL['definition_sha256'],
            hash_serialization='powershell-converttojson-depth100-compress-utf8-no-bom',
            logical_flow_id=HISTORICAL['flow_id'], metadata_logical_flow_id=HISTORICAL['flow_id'],
            content_version='1.0.0.0', actions=inventory), completeness=dict(run=True, actions=True, definition=True))


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    manifest = synthetic_manifest()
    manifest['tenant_id'] = HISTORICAL['tenant_id']
    manifest['resources']['stage']['flow_id'] = HISTORICAL['flow_id']
    for member in manifest['members']:
        member['verified_tenant_id'] = HISTORICAL['tenant_id']
    state = bootstrap_state(manifest, ['synthetic-legacy'])
    for member in state['users'].values():
        member['access_state'] = 'active'
    private = tmp_path / '.cred'
    private.mkdir()
    store = ControlStore(private / 'control.json')
    store.create(state)
    person = next(m['directory'] for m in manifest['members'] if m['seed_name'] == 'Ed Lopez')
    binding = state['security']['brokers']['stage']
    context = authorize_person(binding, DirectoryPerson.model_validate(person), uuid4(), store)
    command = SaveUserAccess(command_id=UUID(HISTORICAL['command_id']), expected_revision=state['acl_revision'],
        target=DirectoryPerson(object_id=uuid4(), upn='synthetic.operator@austinlighthouse.org',
            display_name='Synthetic Operator', account_enabled=True, user_type='Member'), role='OPERATOR', active=True)
    original = save_user_access(context, command, store)['sharing_plan']

    def pin_fixture(current):
        plan = current['sharing_plans'].pop(original['plan_id'])
        plan['plan_id'] = HISTORICAL['plan_id']
        current['sharing_plans'][plan['plan_id']] = plan
        operation = current['operations'][HISTORICAL['command_id']]
        operation['plan_id'] = plan['plan_id']
        operation['result']['sharing_plan']['plan_id'] = plan['plan_id']

    store.mutate(pin_fixture)
    request = RecoveryRequest(command_id=HISTORICAL['command_id'], plan_id=HISTORICAL['plan_id'],
        revision=original['revision'], execution_id=HISTORICAL['execution_id'], lease_id=HISTORICAL['lease_id'], intent=REASON)
    with monkeypatch.context() as patch:
        patch.setattr('api.authorization.uuid4', lambda: UUID(HISTORICAL['lease_id']))
        acquire_sharing_lease(binding, AcquireSharingLease(plan_id=request.plan_id, revision=request.revision,
                                                         execution_id=request.execution_id), store)
    store.mutate(lambda current: current['sharing_plans'][str(request.plan_id)]['observations'].update(
        {'retained-partial-grant': {'present': True, 'verified': False}}))
    collector = SyntheticCollector(native_evidence(person['object_id']))
    service = RecoveryService(store, collector, clock=lambda: NOW)
    return store, request, collector, service


def apply_preview(recovery):
    store, request, collector, service = recovery
    preview = service.preview(request)
    result = service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest'])
    return preview, result


def test_only_execution_and_lease_change_with_one_safe_audit_and_no_activation(recovery):
    store, request, collector, service = recovery
    before = store.read()
    preview, result = apply_preview(recovery)
    after = store.read()
    assert collector.calls == 2 and preview['changed'] is False
    assert result['status'] == 'CLOSED' and result['plan_status'] == result['membership_state'] == 'pending'
    assert after['users'] == before['users'] and after['operations'] == before['operations']
    assert after['acl_revision'] == before['acl_revision'] and after['security'] == before['security']
    assert after['runtime'] == before['runtime'] and not after['sharing_leases']
    old_plan, new_plan = before['sharing_plans'][str(request.plan_id)], after['sharing_plans'][str(request.plan_id)]
    assert old_plan['observations']['retained-partial-grant']['present'] is True
    assert {k: v for k, v in old_plan.items() if k != 'executions'} == {k: v for k, v in new_plan.items() if k != 'executions'}
    assert len(after['audit']) == len(before['audit']) + 1
    assert after['audit'][-1]['event_type'] == 'SHARING_EXECUTION_HOST_RECOVERED'
    execution = new_plan['executions'][str(request.execution_id)]
    assert execution['recovery']['evidence_digest'] == preview['evidence_digest']
    assert 'native_run' not in execution  # Historical evidence never fabricates acquisition-time binding.


def test_fresh_collection_keeps_semantic_digest_and_replay_is_read_only(recovery):
    store, request, collector, service = recovery
    preview = service.preview(request)
    collector.evidence['collected_at'] = NOW.isoformat()
    first = service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest'])
    saved = store.path.read_bytes()
    assert service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest']) == first
    assert store.path.read_bytes() == saved and collector.calls == 3


def test_late_callback_cannot_replace_recovered_outcome(recovery):
    store, request, _, _ = recovery
    apply_preview(recovery)
    saved = store.path.read_bytes()
    callback = SharingResult(plan_id=request.plan_id, revision=request.revision, execution_id=request.execution_id,
                             lease_id=request.lease_id, external_calls_complete=True, observations=[])
    with pytest.raises(AuthorizationError, match='different outcome'):
        record_sharing_result(store.read()['security']['brokers']['stage'], callback, store)
    assert store.path.read_bytes() == saved


@pytest.mark.parametrize('fault', ['source', 'stale', 'future', 'not-canceled', 'unknown-definition', 'wrong-flow',
    'wrong-run', 'missing-action', 'duplicate-action', 'missing-inventory', 'unknown-external', 'dynamic-started',
    'management-started', 'reservation-started', 'missing-acquisition', 'wrong-first-read', 'incomplete', 'bad-time'])
def test_incomplete_or_unsafe_native_evidence_never_changes_state(recovery, fault):
    store, request, collector, service = recovery
    evidence = collector.evidence
    actions = {a['name']: a for a in evidence['actions']}
    if fault == 'source': evidence['source'] = 'offline-sharing-recovery-metadata'
    elif fault == 'stale': evidence['collected_at'] = (NOW - timedelta(minutes=6)).isoformat()
    elif fault == 'future': evidence['collected_at'] = (NOW + timedelta(seconds=1)).isoformat()
    elif fault == 'not-canceled': evidence['run']['status'] = 'Succeeded'
    elif fault == 'unknown-definition': evidence['definition']['sha256'] = '0' * 64
    elif fault == 'wrong-flow': evidence['definition']['metadata_logical_flow_id'] = str(uuid4())
    elif fault == 'wrong-run': evidence['run_id'] = 'unrelated-native-run'
    elif fault == 'missing-action': evidence['actions'].pop()
    elif fault == 'duplicate-action': evidence['actions'][-1] = deepcopy(evidence['actions'][0])
    elif fault == 'missing-inventory': evidence['definition']['actions'].pop()
    elif fault == 'unknown-external': evidence['definition']['actions'][-1]['type'] = 'Http'
    elif fault == 'dynamic-started': actions['Invoke_operation']['status'] = 'Succeeded'
    elif fault == 'management-started': actions['Before_add_stage_flow']['status'] = 'Failed'
    elif fault == 'reservation-started': actions['Reserve_Before_add_stage_flow']['status'] = 'Succeeded'
    elif fault == 'missing-acquisition': actions['Acquire_lease_add']['status'] = 'Skipped'
    elif fault == 'wrong-first-read': actions['Before_add_stage_app']['status'] = 'TimedOut'
    elif fault == 'incomplete': evidence['completeness']['actions'] = False
    elif fault == 'bad-time': actions['Acquire_lease_add']['end_time'] = 'not-a-time'
    before = store.path.read_bytes()
    with pytest.raises(ControlError):
        service.preview(request)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize('status', ['Succeeded', 'Failed', 'Running', 'TimedOut', 'Cancelled', 'Waiting'])
def test_any_potentially_started_permission_mutation_blocks_recovery(recovery, status):
    store, request, collector, service = recovery
    next(a for a in collector.evidence['actions'] if a['name'] == 'Add_add_stage_app')['status'] = status
    with pytest.raises(ControlError, match='permission mutation'):
        service.preview(request)


@pytest.mark.parametrize('field', ['command_id', 'plan_id', 'execution_id', 'lease_id', 'revision'])
def test_wrong_current_control_binding_is_rejected(recovery, field):
    store, request, _, service = recovery
    request = request.model_copy(update={field: uuid4()})
    with pytest.raises(ControlError):
        service.preview(request)


def test_active_actor_is_rechecked_and_operator_or_revoked_admin_cannot_apply(recovery):
    store, request, collector, service = recovery
    preview = service.preview(request)
    key = principal_key(HISTORICAL['tenant_id'], collector.evidence['actor_object_id'])
    store.mutate(lambda state: state['users'][key].update(role='OPERATOR'))
    before = store.path.read_bytes()
    with pytest.raises(ControlError) as error:
        service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest'])
    assert error.value.status_code == 403 and store.path.read_bytes() == before


def test_changed_state_or_changed_semantics_requires_new_preview(recovery):
    store, request, collector, service = recovery
    preview = service.preview(request)
    store.mutate(lambda state: state['runtime'].update(synthetic_marker=True))
    before = store.path.read_bytes()
    with pytest.raises(ControlError, match='revision changed'):
        service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest'])
    assert store.path.read_bytes() == before
    fresh = service.preview(request)
    collector.evidence['actions'][-1]['code'] = 'ChangedCode'
    with pytest.raises(ControlError, match='evidence changed'):
        service.apply(request, expected_revision=fresh['control_revision'], evidence_digest=fresh['evidence_digest'])
    assert store.path.read_bytes() == before


def test_stale_or_superseded_plan_cannot_be_recovered(recovery):
    store, request, _, service = recovery
    def supersede(state):
        plan = state['sharing_plans'][str(request.plan_id)]
        key = principal_key(plan['target']['tenant_id'], plan['target']['object_id'])
        state['users'][key]['access_revision'] = str(uuid4())
    store.mutate(supersede)
    with pytest.raises(ControlError, match='superseded'):
        service.preview(request)


@pytest.mark.parametrize('closed', [False, True])
def test_any_management_reservation_for_this_lease_contradicts_evidence(recovery, closed):
    from api.broker_models import ReserveManagementCall, RecordManagementCall
    from api.management_pacing import reserve_management_call, record_management_call
    store, request, _, service = recovery
    binding = store.read()['security']['brokers']['stage']
    payload = request.model_dump(exclude={'intent'})
    payload.pop('command_id')
    payload['step'] = 'Before_add_stage_flow'
    reservation = reserve_management_call(binding, ReserveManagementCall(**payload), store)
    if closed:
        record_management_call(binding, RecordManagementCall(**payload,
            reservation_id=reservation['reservation_id'], outcome_known=True), store)
    before = store.path.read_bytes()
    with pytest.raises(ControlError, match='Management'):
        service.preview(request)
    assert store.path.read_bytes() == before


def test_atomic_persistence_failure_preserves_prior_state(recovery, monkeypatch):
    store, request, _, service = recovery
    preview = service.preview(request)
    before = store.path.read_bytes()
    def fail(*args):
        raise OSError('PRIVATE_WRITE_SENTINEL')
    monkeypatch.setattr('api.control.os.replace', fail)
    with pytest.raises(ControlError) as error:
        service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest'])
    assert 'PRIVATE_WRITE_SENTINEL' not in str(error.value)
    assert store.path.read_bytes() == before and not list(store.path.parent.glob('control-*.tmp'))


def test_offline_preview_cannot_be_used_as_apply_collector(recovery):
    store, request, collector, service = recovery
    evidence = deepcopy(collector.evidence)
    evidence['source'] = 'offline-sharing-recovery-metadata'
    before = store.path.read_bytes()
    preview = preview_captured_evidence(store.read(), request, evidence, now=NOW)
    assert preview['trusted_live_collection'] is False and preview['changed'] is False
    collector.evidence = evidence
    with pytest.raises(ControlError, match='Offline evidence'):
        service.apply(request, expected_revision=preview['control_revision'], evidence_digest=preview['evidence_digest'])
    with pytest.raises(TypeError):
        RecoveryService(store, evidence)
    assert store.path.read_bytes() == before


def test_collector_failure_is_sanitized_and_performs_no_mutation(recovery, monkeypatch):
    store, request, collector, service = recovery
    def fail():
        raise RuntimeError('PRIVATE_COLLECTOR_SENTINEL')
    monkeypatch.setattr(collector, 'collect', fail)
    before = store.path.read_bytes()
    with pytest.raises(ControlError) as error:
        service.preview(request)
    assert error.value.status_code == 503 and 'PRIVATE_COLLECTOR_SENTINEL' not in str(error.value)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize('revision', [None, '', 'invalid', 0])
def test_apply_cannot_disable_compare_and_swap_with_missing_or_invalid_revision(recovery, revision):
    store, request, collector, service = recovery
    preview = service.preview(request)
    before = store.path.read_bytes()
    with pytest.raises(ControlError) as error:
        service.apply(request, expected_revision=revision, evidence_digest=preview['evidence_digest'])
    assert error.value.status_code == 422 and collector.calls == 1
    assert store.path.read_bytes() == before


def test_cli_cannot_apply_offline_capture_or_skip_approval_values(monkeypatch):
    from scripts import recover_sharing
    monkeypatch.setattr(recover_sharing, 'ControlStore', lambda *_: pytest.fail('CLI must reject before reading state'))
    for args in (['--apply', '--offline-evidence', 'captured.json'], ['--apply'],
                 ['--apply', '--evidence-digest', '0' * 64]):
        with pytest.raises(SystemExit) as error:
            recover_sharing.main(args)
        assert error.value.code == 2


def test_cli_live_collector_has_no_offline_input_and_never_echoes_native_diagnostics(monkeypatch):
    from scripts import recover_sharing
    from types import SimpleNamespace
    calls = []
    monkeypatch.setattr(recover_sharing.shutil, 'which', lambda _: 'synthetic-powershell')
    def execute(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return SimpleNamespace(returncode=1, stdout='PRIVATE_NATIVE_SENTINEL', stderr='PRIVATE_NATIVE_SENTINEL')
    monkeypatch.setattr(recover_sharing.subprocess, 'run', execute)
    with pytest.raises(ControlError) as error:
        recover_sharing.PowerShellRecoveryCollector().collect()
    assert 'PRIVATE_NATIVE_SENTINEL' not in str(error.value)
    arguments, options = calls[0]
    assert '-OfflineDirectory' not in arguments and '-OutputFile' in arguments
    assert options['timeout'] == 180 and options['capture_output']


def test_recovery_preserves_unrelated_lease_and_completed_management_reservation(recovery):
    from api.broker_models import ReserveManagementCall, RecordManagementCall
    from api.management_pacing import reserve_management_call, record_management_call
    store, request, collector, service = recovery
    state = store.read()
    actor = state['users'][principal_key(HISTORICAL['tenant_id'], collector.evidence['actor_object_id'])]
    binding = state['security']['brokers']['stage']
    person = DirectoryPerson(object_id=actor['object_id'], upn=actor['upn'], display_name=actor['display_name'],
                             account_enabled=True, user_type='Member')
    context = authorize_person(binding, person, uuid4(), store)
    command = SaveUserAccess(command_id=uuid4(), expected_revision=state['acl_revision'],
        target=DirectoryPerson(object_id=uuid4(), upn='other.synthetic@austinlighthouse.org', display_name='Other Synthetic',
                               account_enabled=True, user_type='Member'), role='OPERATOR', active=True)
    other = save_user_access(context, command, store)['sharing_plan']
    claim = AcquireSharingLease(plan_id=other['plan_id'], revision=other['revision'], execution_id=uuid4())
    lease = acquire_sharing_lease(binding, claim, store)
    payload = claim.model_dump(exclude={'native_run'}) | {'lease_id': lease['lease_id'], 'step': 'Before_add_stage_flow'}
    reservation = reserve_management_call(binding, ReserveManagementCall(**payload), store)
    record_management_call(binding, RecordManagementCall(**payload, reservation_id=reservation['reservation_id'], outcome_known=True), store)
    before = store.read()
    apply_preview(recovery)
    after = store.read()
    other_key = principal_key(other['target']['tenant_id'], other['target']['object_id'])
    assert after['sharing_leases'] == {other_key: before['sharing_leases'][other_key]}
    assert after['management_pacing'] == before['management_pacing']
    assert after['sharing_plans'][other['plan_id']] == before['sharing_plans'][other['plan_id']]
