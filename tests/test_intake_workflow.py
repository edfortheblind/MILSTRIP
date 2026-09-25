"""Real transaction workflow checks; local database fixture rolls back all rows."""
from datetime import timedelta
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import mssql, postgresql

from api.operator_models import ReviewCommand
from api.persistence import RepositoryConflict
from api.persistence.repository import intake_fingerprint, workflow_lock_statement
from api.persistence.schema import intake_workflow, audit_event, utc_now
from milstrip.service import process_text
from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD


def submit(repo, actor, source=SYNTHETIC_RECORD, reason=None):
    return repo.create_intake(str(uuid4()), 'PASTE', str(uuid4()), source,
        hashlib.sha256(source.encode()).hexdigest(), actor, process_text(source),
        enforce_workflow=True, duplicate_override_reason=reason)


def finish(repo, receipt):
    for record in repo.list_records(receipt['request_id']).items:
        repo.review_record(record['record_id'], ReviewCommand(decision='REJECTED',
            reason='Synthetic workflow test', expected_version=0, command_id=uuid4()), 'synthetic-reviewer')


def test_fingerprint_uses_normalized_records_and_preserves_significant_positions():
    source = SYNTHETIC_RECORD
    assert intake_fingerprint(process_text(source), source) == intake_fingerprint(process_text(source+'\r\n'), source+'\r\n')
    changed = source[:29] + ('9' if source[29] != '9' else '8') + source[30:]
    assert intake_fingerprint(process_text(source),source) != intake_fingerprint(process_text(changed),changed)


def test_workflow_mutex_has_both_database_dialects():
    assert 'FOR UPDATE' in str(workflow_lock_statement().compile(dialect=postgresql.dialect()))
    assert 'UPDLOCK, HOLDLOCK, ROWLOCK' in str(workflow_lock_statement().compile(dialect=mssql.dialect()))


def test_every_record_requires_review_even_with_admin_override(portable_database):
    repo = portable_database.repository
    actor = 'workflow-' + str(uuid4())
    first = submit(repo, actor, SYNTHETIC_RECORD+'\nA2A')
    assert repo.workflow_status(actor)['active_request_id'] == first['request_id']
    with pytest.raises(RepositoryConflict, match='Finish every record'):
        submit(repo,actor,reason='Administrator override cannot skip reviews')
    repo.review_record(first['request_id']+':1', ReviewCommand(decision='APPROVED',
        reason='Synthetic review',expected_version=0,command_id=uuid4()), actor)
    assert not repo.workflow_status(actor)['can_start']
    repo.review_record(first['request_id']+':2', ReviewCommand(decision='REJECTED',
        reason='Invalid record',expected_version=0,command_id=uuid4()), actor)
    assert repo.workflow_status(actor)['can_start']


def test_duplicate_window_is_cross_user_and_override_is_audited(portable_database):
    repo = portable_database.repository
    first = submit(repo,'workflow-'+str(uuid4()))
    with pytest.raises(RepositoryConflict, match='last 2 hours'):
        submit(repo,'workflow-'+str(uuid4()),SYNTHETIC_RECORD+'\r\n')
    second = submit(repo,'workflow-'+str(uuid4()),reason='Authorized synthetic resubmission')
    event = repo.connection.execute(select(audit_event.c.event_data).where(
        audit_event.c.aggregate_id == second['request_id'],audit_event.c.event_type=='DUPLICATE_OVERRIDE')).scalar_one()
    assert event['duplicate_request_id'] == first['request_id']
    assert event['reason'] == 'Authorized synthetic resubmission'
    assert event['window_hours'] == 2


def test_two_hour_boundary_and_zero_candidate_release(portable_database):
    repo = portable_database.repository
    actor = 'workflow-'+str(uuid4())
    first = submit(repo,actor)
    finish(repo,first)
    now = repo.connection.scalar(select(utc_now()))
    repo.connection.execute(intake_workflow.update().where(intake_workflow.c.request_id==first['request_id']).values(created_at=now-timedelta(hours=2)+timedelta(seconds=1)))
    with pytest.raises(RepositoryConflict,match='last 2 hours'):
        submit(repo,actor)
    repo.connection.execute(intake_workflow.update().where(intake_workflow.c.request_id==first['request_id']).values(created_at=now-timedelta(hours=2)))
    second=submit(repo,actor)
    finish(repo,second)
    empty=submit(repo,actor,'No MILSTRIP candidates in this synthetic message')
    assert empty['records']==0 and repo.workflow_status(actor)['can_start']


@pytest.mark.parametrize('same_actor', [True, False])
def test_concurrent_submissions_have_one_winner(same_actor):
    import os
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from psycopg.conninfo import conninfo_to_dict
    from api.persistence import open_repository
    from api.persistence.schema import intake_request, milstrip_record, validation_issue
    url=os.getenv('MILSTRIP_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Requires approved local PostgreSQL')
    options=conninfo_to_dict(url)
    assert options.get('host') in {'localhost','127.0.0.1','::1'}
    assert options.get('dbname')=='trav3pl-psqldb-stage'
    marker=str(uuid4())
    ids=[str(uuid4()),str(uuid4())]
    source=SYNTHETIC_RECORD[:30]+marker[:10]+SYNTHETIC_RECORD[40:]
    barrier=Barrier(2)
    def attempt(index):
        actor=marker if same_actor else marker+str(index)
        value=source if not same_actor else source+('\nA2A' if index else '')
        barrier.wait(timeout=5)
        try:
            with open_repository('postgresql',url) as repo:
                repo.validate_identity('stage')
                repo.create_intake(ids[index],'PASTE',marker,value,hashlib.sha256(value.encode()).hexdigest(),
                                   actor,process_text(value),enforce_workflow=True)
            return 'saved'
        except RepositoryConflict:
            return 'blocked'
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(attempt,range(2)))==['blocked','saved']
    finally:
        # Only this test's preallocated synthetic IDs are removed.
        with open_repository('postgresql',url) as repo:
            conn=repo.connection
            record_ids=select(milstrip_record.c.record_id).where(milstrip_record.c.request_id.in_(ids))
            conn.execute(validation_issue.delete().where(validation_issue.c.record_id.in_(record_ids)))
            conn.execute(audit_event.delete().where(audit_event.c.correlation_id.in_(ids)))
            conn.execute(intake_workflow.delete().where(intake_workflow.c.request_id.in_(ids)))
            conn.execute(milstrip_record.delete().where(milstrip_record.c.request_id.in_(ids)))
            conn.execute(intake_request.delete().where(intake_request.c.request_id.in_(ids)))
