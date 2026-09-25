"""Configuration changes preserve routing, secrets and recoverable outcomes."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from api import administration
from api.administration import AdministrationService, import_runtime_config, validate_control_profiles
from api.authorization import AuthorizationError, BrokerContext, VerifiedPrincipal, ROLE_CAPABILITIES
from api.control import ControlError, ControlStore, principal_key
from api.profile_manager import ProfileBusy, ProfileManager
from api.profiles import CredentialBinding, RuntimeConfig, RuntimeProfile


def identifier():
    return str(uuid4())


@pytest.fixture
def configured_admin(tmp_path, monkeypatch):
    private = tmp_path / '.cred'
    private.mkdir(exist_ok=True)
    store = ControlStore(private / 'control.json')
    monkeypatch.setenv('MILSTRIP_CONTROL_FILE', str(store.path))
    tenant, owner1, owner2, admin_id = [identifier() for _ in range(4)]
    users = {}
    for oid, role, name in [(owner1, 'OWNER', 'Owner One'), (owner2, 'OWNER', 'Owner Two'),
                            (admin_id, 'ADMIN', 'Synthetic Admin')]:
        users[principal_key(tenant, oid)] = {
            'tenant_id': tenant, 'object_id': oid, 'upn': oid + '@austinlighthouse.org',
            'display_name': name, 'role': role, 'desired_active': True,
            'access_state': 'active', 'access_revision': identifier()}
    state = {
        'version': 1, 'revision': identifier(), 'acl_revision': identifier(),
        'security': {'tenant_id': tenant, 'enforced': True, 'allowed_domain': 'austinlighthouse.org',
                     'legacy_usernames': [], 'brokers': {
                         p: {'broker_id': p + '-broker', 'profile_id': p, 'tenant_id': tenant,
                             'credential_file': p + '-broker.json'} for p in ('stage', 'prod')}},
        'resources': {p: {'app_id': identifier(), 'flow_id': identifier()} for p in ('stage', 'prod')},
        'users': users, 'protected_owners': [principal_key(tenant, owner1), principal_key(tenant, owner2)],
        'sharing_plans': {}, 'operations': {}, 'audit': [],
        'runtime': {'active': False, 'profiles': {}, 'drafts': {}, 'tests': {}}}
    store.create(state)
    config = RuntimeConfig(1, identifier(), {
        'stage': RuntimeProfile('stage', 'postgresql', 'Stage',
            'host=localhost dbname=synthetic_stage user=synthetic password=stage-secret', True),
        'prod': RuntimeProfile('prod', 'postgresql', 'Prod', '', False)},
        (CredentialBinding('stage', private / 'stage.json'), CredentialBinding('prod', private / 'prod.json')))
    import_runtime_config(store, config)
    store.mutate(lambda current: current['runtime'].update(active=True))
    records = store.read()['runtime']['profiles']
    manager = ProfileManager(config.profiles, {p: r['revision'] for p, r in records.items()}, control_path=store.path)
    principal = VerifiedPrincipal(tenant, admin_id, users[principal_key(tenant, admin_id)]['upn'],
                                  'Synthetic Admin', 'ADMIN', ROLE_CAPABILITIES['ADMIN'])
    context = BrokerContext(principal, 'stage', 'stage-broker', identifier())
    service = AdministrationService(store, manager, drain_timeout=0.01)
    calls = []

    class Repository:
        def health(self):
            calls.append('health')
            return True

        def validate_identity(self, profile_id):
            calls.append(('identity', profile_id))

        def validate_workflow_tracking(self):
            calls.append('tracking')

    @contextmanager
    def open_repository(provider, dsn):
        calls.append(('connect', provider, dsn))
        yield Repository()

    monkeypatch.setattr(administration, 'open_repository', open_repository)
    return SimpleNamespace(store=store, manager=manager, context=context, service=service, config=config, calls=calls)


def save(env, **changes):
    profile = env.store.read()['runtime']['profiles'][env.context.profile_id]
    payload = {'command_id': identifier(), 'expected_active_revision': profile['revision'],
               'provider': profile['provider'], 'label': profile['label'], 'enabled': profile['enabled'], **changes}
    return env.service.invoke('SaveRuntimeDraft', payload, env.context), payload


def probe(env, draft):
    return env.service.invoke('TestRuntimeDraft', {'command_id': identifier(),
        'draft_id': draft['draft_id'], 'draft_revision': draft['draft_revision']}, env.context)


def apply(env, draft, receipt=None, **changes):
    payload = {'command_id': identifier(), 'draft_id': draft['draft_id'],
               'draft_revision': draft['draft_revision'], 'expected_active_revision': draft['base_revision'],
               'test_id': receipt['test_id'] if receipt else None, **changes}
    return env.service.invoke('ApplyRuntimeDraft', payload, env.context), payload


def test_draft_and_test_leave_routing_unchanged_and_never_return_secret(configured_admin):
    env = configured_admin
    before = env.manager.snapshot('stage')
    draft, payload = save(env, replacement_connection_string=
        'host=localhost dbname=synthetic_stage user=replacement password=private-replacement')
    receipt = probe(env, draft)
    summaries = env.service.invoke('GetRuntimeProfiles', {}, env.context)
    assert receipt['status'] == 'PASSED' and env.manager.snapshot('stage') == before
    assert env.calls[1:] == ['health', ('identity', 'stage'), 'tracking']
    public = json.dumps([draft, receipt, summaries, env.store.read()['audit'], env.store.read()['operations']])
    assert 'private-replacement' not in public and 'stage-secret' not in public and 'user=' not in public
    assert env.service.invoke('SaveRuntimeDraft', payload, env.context) == draft


def test_draft_with_missing_intake_tracking_cannot_get_passed_receipt(configured_admin, monkeypatch):
    env = configured_admin
    draft, _ = save(env)

    class MissingTracking:
        def health(self):
            return True

        def validate_identity(self, profile_id):
            pass

        def validate_workflow_tracking(self):
            raise ValueError('PRIVATE_TRACKING_DETAIL')

    @contextmanager
    def connect(*args):
        yield MissingTracking()

    monkeypatch.setattr(administration, 'open_repository', connect)
    receipt = probe(env, draft)
    assert receipt['status'] == 'FAILED'
    assert 'workflow tracking' in receipt['detail']
    assert 'PRIVATE_TRACKING_DETAIL' not in json.dumps(receipt)
    with pytest.raises(ControlError):
        apply(env, draft, receipt)


def test_apply_changes_only_stage_and_replay_preserves_revision(configured_admin):
    env = configured_admin
    prod = env.manager.snapshot('prod')
    draft, _ = save(env, replacement_connection_string=
        'host=127.0.0.1 dbname=synthetic_stage user=rotated password=rotated-secret')
    result, payload = apply(env, draft, probe(env, draft))
    assert result['status'] == 'APPLIED'
    assert env.manager.snapshot('stage').revision == result['revision'] != draft['base_revision']
    assert env.manager.snapshot('prod') == prod
    assert env.service.invoke('ApplyRuntimeDraft', payload, env.context) == result
    assert len([a for a in env.store.read()['audit'] if a['event_type'] == 'ApplyRuntimeDraft']) == 1


def test_disabled_prod_can_be_configured_without_business_database(configured_admin):
    env = configured_admin
    env.context = replace(env.context, profile_id='prod', broker_id='prod-broker')
    draft, _ = save(env, enabled=True, replacement_connection_string=
        'host=localhost dbname=synthetic_prod user=synthetic password=prod-secret')
    result, _ = apply(env, draft, probe(env, draft))
    assert result['enabled'] and env.manager.snapshot('prod').profile.enabled
    assert env.manager.snapshot('stage').profile == env.config.profiles['stage']


@pytest.mark.parametrize('enabled', [True, False])
def test_target_move_requires_separate_disable_first(configured_admin, enabled):
    env = configured_admin
    draft, _ = save(env, enabled=enabled, replacement_connection_string='host=localhost dbname=other_stage')
    with pytest.raises(ControlError, match='Disable') as error:
        apply(env, draft, probe(env, draft))
    assert error.value.status_code == 409
    assert env.manager.snapshot('stage').profile == env.config.profiles['stage']


def test_disable_then_move_and_enable_is_explicit(configured_admin):
    env = configured_admin
    disabled, _ = save(env, enabled=False)
    apply(env, disabled)
    moved, _ = save(env, enabled=True, replacement_connection_string='host=localhost dbname=other_stage')
    apply(env, moved, probe(env, moved))
    assert env.manager.snapshot('stage').profile.connection_string == 'host=localhost dbname=other_stage'


@pytest.mark.parametrize('case', ['missing', 'failed', 'expired', 'other_draft'])
def test_enabled_apply_requires_exact_successful_unexpired_test(configured_admin, monkeypatch, case):
    env = configured_admin
    draft, _ = save(env)
    if case == 'failed':
        @contextmanager
        def unavailable(*args):
            raise RuntimeError('password=NEVER-RETURN-THIS')
            yield
        monkeypatch.setattr(administration, 'open_repository', unavailable)
    receipt = None if case == 'missing' else probe(env, draft)
    if case == 'failed':
        assert receipt['status'] == 'FAILED' and 'NEVER' not in json.dumps(receipt)
    if case == 'expired':
        env.service.clock = lambda: datetime.now(timezone.utc) + timedelta(minutes=6)
    if case == 'other_draft':
        draft, _ = save(env, label='Another draft')
    with pytest.raises(ControlError) as error:
        apply(env, draft, receipt)
    assert error.value.status_code == 412


def test_stale_draft_and_compare_and_swap_cannot_overwrite(configured_admin):
    env = configured_admin
    stale, stale_payload = save(env, label='Older draft')
    current, _ = save(env, label='New draft', enabled=False)
    apply(env, current)
    with pytest.raises(ControlError, match='active configuration changed'):
        probe(env, stale)
    stale_payload['command_id'] = identifier()
    with pytest.raises(ControlError, match='active configuration changed'):
        env.service.invoke('SaveRuntimeDraft', stale_payload, env.context)
    assert env.manager.snapshot('stage').profile.label == 'New draft'


def test_stale_apply_is_definite_conflict_and_new_draft_can_continue(configured_admin):
    env = configured_admin
    stale, _ = save(env, label='Stale target', enabled=False)
    current, _ = save(env, label='Current target', enabled=False)
    apply(env, current)
    command_id = identifier()
    with pytest.raises(ControlError, match='active configuration changed') as error:
        apply(env, stale, command_id=command_id)
    assert error.value.status_code == 409
    assert command_id not in env.store.read()['operations']
    fresh, _ = save(env, label='Updated target', enabled=False)
    assert apply(env, fresh)[0]['status'] == 'APPLIED'


def test_concurrent_apply_keeps_command_retryable_until_profile_is_available(configured_admin):
    env = configured_admin
    draft, _ = save(env, enabled=False)
    command_id = identifier()
    with env.manager.drain('stage'):
        with pytest.raises(ControlError, match='busy') as error:
            apply(env, draft, command_id=command_id)
        assert error.value.status_code == 503
        assert command_id not in env.store.read()['operations']
    result, payload = apply(env, draft, command_id=command_id)
    assert result['status'] == 'APPLIED'
    assert env.service.invoke('ApplyRuntimeDraft', payload, env.context) == result


def test_receipt_cannot_be_reused_by_another_administrator(configured_admin):
    env = configured_admin
    draft, _ = save(env)
    receipt = probe(env, draft)
    owner = next(user for user in env.store.read()['users'].values() if user['role'] == 'OWNER')
    env.context = replace(env.context, principal=VerifiedPrincipal(
        owner['tenant_id'], owner['object_id'], owner['upn'], owner['display_name'], 'OWNER', ROLE_CAPABILITIES['OWNER']))
    with pytest.raises(ControlError) as error:
        apply(env, draft, receipt)
    assert error.value.status_code == 412
    result, _ = apply(env, draft, probe(env, draft))
    assert result['status'] == 'APPLIED'


def test_command_id_cannot_hide_changed_secret(configured_admin):
    env = configured_admin
    _, payload = save(env, replacement_connection_string='host=localhost dbname=synthetic_stage password=one')
    payload['replacement_connection_string'] = 'host=localhost dbname=synthetic_stage password=two'
    with pytest.raises(ControlError, match='Command ID'):
        env.service.invoke('SaveRuntimeDraft', payload, env.context)


def test_operator_and_revoked_admin_cannot_configure(configured_admin):
    env = configured_admin
    key = principal_key(env.context.tenant_id, env.context.object_id)
    env.store.mutate(lambda state: state['users'][key].update(role='OPERATOR'))
    with pytest.raises(AuthorizationError):
        env.service.invoke('GetRuntimeProfiles', {}, env.context)
    env.store.mutate(lambda state: state['users'][key].update(role='ADMIN', desired_active=False))
    with pytest.raises(AuthorizationError):
        save(env)


def test_role_is_rechecked_inside_atomic_mutation(configured_admin, monkeypatch):
    env = configured_admin
    original = env.store.mutate
    key = principal_key(env.context.tenant_id, env.context.object_id)
    def revoke_before_mutation(callback, **kwargs):
        original(lambda state: state['users'][key].update(desired_active=False))
        return original(callback, **kwargs)
    monkeypatch.setattr(env.store, 'mutate', revoke_before_mutation)
    with pytest.raises(AuthorizationError):
        save(env)
    assert env.store.read()['runtime']['drafts'] == {}


def test_other_environment_draft_is_not_accessible(configured_admin):
    env = configured_admin
    draft, _ = save(env)
    env.context = replace(env.context, profile_id='prod')
    with pytest.raises(ControlError) as error:
        probe(env, draft)
    assert error.value.status_code == 404


@pytest.mark.parametrize('changes', [
    {'replacement_connection_string': 'host=remote.example dbname=private password=SECRET sslmode=disable'},
    {'provider': 'sqlserver'}, {'profile_id': 'prod'},
    {'enabled': 'yes'}, {'replacement_connection_string': {'password': 'SECRET'}},
])
def test_invalid_payloads_never_echo_private_input(configured_admin, changes):
    with pytest.raises(ControlError) as error:
        save(configured_admin, **changes)
    assert error.value.status_code == 422 and 'SECRET' not in str(error.value)


def test_stage_and_prod_cannot_share_normalized_target(configured_admin):
    env = configured_admin
    env.context = replace(env.context, profile_id='prod')
    with pytest.raises(ControlError):
        save(env, replacement_connection_string='postgresql://127.0.0.1:5432/synthetic_stage')


def test_apply_does_not_cut_over_inactive_control_store(configured_admin):
    env = configured_admin
    env.store.mutate(lambda state: state['runtime'].update(active=False))
    draft, _ = save(env, enabled=False)
    with pytest.raises(ControlError, match='explicit security cutover'):
        apply(env, draft)
    assert env.manager.snapshot('stage').profile.enabled


def test_process_started_before_cutover_must_restart_before_hot_apply(configured_admin):
    env = configured_admin
    env.manager.control_path = None
    draft, _ = save(env, enabled=False)
    with pytest.raises(ControlError, match='Restart the API after security cutover'):
        apply(env, draft)
    assert env.manager.snapshot('stage').profile.enabled


def test_apply_timeout_leaves_old_profile_and_durable_revision(configured_admin):
    env = configured_admin
    draft, _ = save(env, enabled=False)
    with env.manager.lease('stage'):
        with pytest.raises(ControlError) as error:
            apply(env, draft)
    assert error.value.status_code == 503
    assert env.manager.status('stage') == 'AVAILABLE'
    assert env.store.read()['runtime']['profiles']['stage']['revision'] == draft['base_revision']


@pytest.mark.parametrize('committed', [False, True])
def test_uncertain_write_blocks_only_if_durable_outcome_changed(configured_admin, monkeypatch, committed):
    env = configured_admin
    draft, _ = save(env, enabled=False)
    write = env.store._write
    def fail(state):
        if committed:
            write(state)
        raise ControlError(503, 'Synthetic persistence failure')
    monkeypatch.setattr(env.store, '_write', fail)
    with pytest.raises(ControlError):
        apply(env, draft)
    assert env.manager.status('stage') == ('BLOCKED' if committed else 'AVAILABLE')
    with env.manager.lease('prod'):
        pass
    if committed:
        with pytest.raises(ProfileBusy):
            with env.manager.lease('stage'):
                pytest.fail('Uncertain routing must stay blocked')
        operations = env.store.read()['operations'].values()
        assert any(o['operation'] == 'ApplyRuntimeDraft' and o['result']['status'] == 'APPLIED' for o in operations)


def test_publish_failure_keeps_durable_result_and_blocks_old_destination(configured_admin, monkeypatch):
    env = configured_admin
    draft, _ = save(env, enabled=False)
    def fail(*args):
        raise RuntimeError('private failure details')
    monkeypatch.setattr(env.manager, 'publish', fail)
    with pytest.raises(ControlError, match='restart for recovery'):
        apply(env, draft)
    assert env.manager.status('stage') == 'BLOCKED'
    assert env.store.read()['runtime']['profiles']['stage']['enabled'] is False


def test_unreadable_store_after_failed_apply_blocks_routing(configured_admin, monkeypatch):
    env = configured_admin
    draft, _ = save(env, enabled=False)
    def unreadable():
        raise ControlError(503, 'Synthetic unreadable state')
    def fail_write(state):
        monkeypatch.setattr(env.store, 'read', unreadable)
        raise ControlError(503, 'Synthetic write outcome unavailable')
    monkeypatch.setattr(env.store, '_write', fail_write)
    with pytest.raises(ControlError):
        apply(env, draft)
    assert env.manager.status('stage') == 'BLOCKED'
    assert env.manager.status('prod') == 'AVAILABLE'


def test_control_summary_remains_accessible_without_business_runtime(configured_admin):
    env = configured_admin
    env.service.manager = None
    result = env.service.invoke('GetRuntimeProfiles', {}, env.context)
    assert {p['runtime_state'] for p in result['profiles']} == {'UNAVAILABLE'}
    assert {p['profile_id'] for p in result['profiles']} == {'stage', 'prod'}


def test_import_is_once_only_and_never_activates(tmp_path):
    # The live fixture already imported a valid config; this case tests the
    # independent bootstrap invariant using a minimal in-memory store.
    class Store:
        state = {'runtime': {'active': False, 'profiles': {}}}
        def mutate(self, callback):
            return callback(self.state)
    store = Store()
    config = RuntimeConfig(1, identifier(), {
        p: RuntimeProfile(p, 'postgresql', p, '', False) for p in ('stage', 'prod')},
        tuple(CredentialBinding(p, tmp_path / '.cred' / (p + '.json')) for p in ('stage', 'prod')))
    assert import_runtime_config(store, config) == {'imported': True, 'active': False}
    with pytest.raises(ControlError):
        import_runtime_config(store, config)


def test_private_profile_revisions_are_validated(configured_admin):
    records = configured_admin.store.read()['runtime']['profiles']
    records['stage']['revision'] = 'bad-revision'
    with pytest.raises(ValueError, match='canonical UUID'):
        validate_control_profiles(records, require_revisions=True)


def test_auto_provider_changes_engine_from_connection_string_only(configured_admin):
    env = configured_admin
    sql = 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:synthetic.example.invalid,1433;Database=stage;Uid=test;Pwd={private};Encrypt=yes;TrustServerCertificate=no;'
    draft, _ = save(env, provider='auto', replacement_connection_string=sql)
    assert env.store.read()['runtime']['drafts'][draft['draft_id']]['candidate']['provider']=='sqlserver'
    draft, _ = save(env, provider='auto', replacement_connection_string='host=localhost dbname=synthetic_stage')
    assert env.store.read()['runtime']['drafts'][draft['draft_id']]['candidate']['provider']=='postgresql'
    with pytest.raises(ControlError):
        save(env, provider='auto', replacement_connection_string='Driver={ODBC Driver 18 for SQL Server};Server=remote;Database=stage;Encrypt=no;')


def test_initialize_from_draft_requires_disabled_profile_and_target_confirmation(configured_admin, monkeypatch):
    env=configured_admin
    calls=[]
    monkeypatch.setattr(administration,'provision_schema',lambda *args: calls.append(args))
    draft,_=save(env)
    def command(d):
        return {'command_id':identifier(),'draft_id':d['draft_id'],'draft_revision':d['draft_revision'],'confirm_target':d['target']}
    with pytest.raises(ControlError,match='Disable'):
        env.service.invoke('InitializeRuntimeDraft',command(draft),env.context)
    disabled,_=save(env,enabled=False)
    apply(env,disabled)
    draft,_=save(env,enabled=True)
    payload=command(draft)
    with pytest.raises(ControlError,match='Confirm'):
        env.service.invoke('InitializeRuntimeDraft',{**payload,'confirm_target':'wrong'},env.context)
    result=env.service.invoke('InitializeRuntimeDraft',payload,env.context)
    assert result['status']=='INITIALIZED'
    assert env.service.invoke('InitializeRuntimeDraft',payload,env.context)==result
    assert len(calls)==1 and not env.manager.snapshot('stage').profile.enabled


def test_initialize_failure_is_sanitized_and_retryable(configured_admin,monkeypatch):
    env=configured_admin
    disabled,_=save(env,enabled=False)
    apply(env,disabled)
    draft,_=save(env)
    def fail(*args):
        raise RuntimeError('password=must-never-escape')
    monkeypatch.setattr(administration,'provision_schema',fail)
    payload={'command_id':identifier(),'draft_id':draft['draft_id'],'draft_revision':draft['draft_revision'],'confirm_target':draft['target']}
    with pytest.raises(ControlError) as error:
        env.service.invoke('InitializeRuntimeDraft',payload,env.context)
    assert 'must-never-escape' not in str(error.value)
    monkeypatch.setattr(administration,'provision_schema',lambda *args: None)
    assert env.service.invoke('InitializeRuntimeDraft',payload,env.context)['status']=='INITIALIZED'


def test_operator_cannot_initialize_database(configured_admin):
    env=configured_admin
    env.store.mutate(lambda state: state['users'][env.context.actor_id.removeprefix('entra:')].update(role='OPERATOR'))
    with pytest.raises(AuthorizationError):
        env.service.invoke('InitializeRuntimeDraft',{},env.context)
