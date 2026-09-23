"""Standalone real HTTP checks; --workflow exercises synthetic intake and review."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.auth import ITERATIONS, password_digest
from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def workflow(client, marker):
    def call(method, path, expected=200, **kwargs):
        response = client.request(method, '/api/v1' + path, **kwargs)
        require(response.status_code == expected, f'{method} {path.split("/")[1]} expected HTTP {expected}; received {response.status_code}')
        return response.json()

    body = dict(source_type='PASTE', source_id=marker,
                source_text=SYNTHETIC_RECORD + '\nA2A', submitted_by='untrusted-client')
    ack = call('POST', '/intake/requests', 201, json=body)
    request_id = ack['request_id']
    parent = '/intake/requests/' + request_id
    require(ack['records'] == 2 and ack['rejected'] == 1, 'Unexpected intake classification')
    detail = call('GET', parent)
    require(detail['source_id'] == marker and detail['submitted_by'] == 'synthetic-http-check', 'Intake identity mismatch')
    listing = call('GET', '/intake/requests', params={'limit': 1})
    require(len(listing['items']) <= 1 and 'next_cursor' in listing, 'Request page contract mismatch')
    page = call('GET', parent + '/records', params={'limit': 1})
    valid = page['items'][0]
    require(valid['canonical_record'] == SYNTHETIC_RECORD and len(valid['canonical_record']) == 80, 'Canonical text changed')
    require(bool(page['next_cursor']), 'Second record page missing')
    second = call('GET', parent + '/records', params={'limit': 1, 'cursor': page['next_cursor']})
    rejected = second['items'][0]
    require(rejected['status'] == 'REJECTED' and bool(rejected['issues']), 'Invalid record issues missing')
    require(second['next_cursor'] is None, 'Unexpected extra record page')
    review_path = '/records/' + valid['record_id'] + '/review-decisions'
    command = dict(decision='APPROVED', reason='Standalone synthetic verification', expected_version=0, command_id=str(uuid4()))
    accepted = call('POST', review_path, 201, json=command)
    require(accepted['review_version'] == 1 and accepted['decided_by'] == 'synthetic-http-check', 'Review identity/version mismatch')
    require(call('POST', review_path, json=command) == accepted, 'Retry changed accepted decision')
    call('POST', review_path, 409, json={**command, 'command_id': str(uuid4())})
    call('POST', review_path, 409, json={**command, 'reason': 'Conflicting retry'})
    call('POST', '/records/' + rejected['record_id'] + '/review-decisions', 409, json={**command, 'command_id': str(uuid4())})
    updated = call('GET', parent + '/records', params={'limit': 1})['items'][0]
    require(updated['status'] == 'VALID' and updated['canonical_record'] == SYNTHETIC_RECORD, 'Review altered validation or canonical text')
    require(updated['review_version'] == 1, 'Retry/conflict created an extra version')
    events, cursor = [], None
    for _ in range(5):
        params = {'limit': 1}
        if cursor:
            params['cursor'] = cursor
        history = call('GET', parent + '/audit-events', params=params)
        events.extend(history['items'])
        cursor = history['next_cursor']
        if not cursor:
            break
    require(cursor is None and len(events) == 2, 'Audit count or pagination mismatch')
    require(sum(e['event_type'] == 'REVIEW_DECIDED' for e in events) == 1, 'Duplicate review audit event')
    require(all(e['actor'] == 'synthetic-http-check' for e in events), 'Audit identity mismatch')
    call('GET', parent + '/records', 422, params={'limit': 0})
    print('PASS: seven operations; synthetic intake/results; canonical padding; authenticated actors; pagination; exact retry; conflicts; invalid approval; audit history')


def cleanup(database_url, marker):
    """Delete only this run's UUID-tagged synthetic metadata, including late POSTs."""
    with psycopg.connect(database_url, connect_timeout=5) as db:
        db.execute("SET LOCAL lock_timeout = '5s'")
        db.execute("SET LOCAL statement_timeout = '15s'")
        request_ids = [row[0] for row in db.execute(
            "SELECT request_id FROM milstrip_app.intake_request WHERE source_id=%s AND submitted_by='synthetic-http-check'",
            (marker,)).fetchall()]
        record_ids = [row[0] for row in db.execute(
            'SELECT record_id FROM milstrip_app.milstrip_record WHERE request_id=ANY(%s)', (request_ids,)).fetchall()]
        db.execute("DELETE FROM milstrip_app.audit_event WHERE (aggregate_type='intake_request' AND aggregate_id=ANY(%s)) OR (aggregate_type='milstrip_record' AND aggregate_id=ANY(%s))", (request_ids, record_ids))
        db.execute('DELETE FROM milstrip_app.review_decision WHERE record_id=ANY(%s)', (record_ids,))
        db.execute('DELETE FROM milstrip_app.validation_issue WHERE record_id=ANY(%s)', (record_ids,))
        db.execute('DELETE FROM milstrip_app.milstrip_record WHERE request_id=ANY(%s)', (request_ids,))
        db.execute('DELETE FROM milstrip_app.intake_request WHERE request_id=ANY(%s)', (request_ids,))
    with psycopg.connect(database_url, connect_timeout=5) as db:
        require(db.execute('SELECT count(*) FROM milstrip_app.intake_request WHERE source_id=%s', (marker,)).fetchone()[0] == 0, 'Synthetic cleanup incomplete')
    print('PASS: synthetic application rows removed; no legacy-table writes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow', action='store_true', help='Exercise all seven operations and remove this run\'s synthetic metadata')
    args = parser.parse_args()
    database_url = os.getenv('MILSTRIP_DATABASE_URL', 'postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage')
    config = conninfo_to_dict(database_url)
    require(config.get('host') in {'localhost', '127.0.0.1', '::1'}
            and config.get('hostaddr') in {None, '127.0.0.1', '::1'}
            and config.get('port', '5432') == '5432'
            and config.get('dbname') == 'trav3pl-psqldb-stage'
            and not config.get('service'), 'Only the approved local database is allowed')
    marker = 'standalone-' + str(uuid4())
    with tempfile.TemporaryDirectory(prefix='http-check-', dir=ROOT / '.cred') as directory:
        username, password, salt = 'synthetic-http-check', secrets.token_urlsafe(32), secrets.token_hex(32)
        path = Path(directory) / 'credential.json'
        path.write_text(json.dumps(dict(version=1, iterations=ITERATIONS, username=username,
                                       salt=salt, digest=password_digest(password, salt))))
        environment = dict(os.environ, MILSTRIP_API_CREDENTIAL_FILE=str(path))
        environment.setdefault('MILSTRIP_DATABASE_URL', 'postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-proxy-headers', '--no-access-log'], cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=15, trust_env=False) as client:
                for attempt in range(50):
                    if process.poll() is not None:
                        raise RuntimeError('Smoke-test server stopped before readiness')
                    try:
                        response = client.get('/api/v1/health')
                        break
                    except httpx.ConnectError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Smoke-test server did not start')
                assert response.status_code == 401
                assert client.get('/api/v1/health', auth=(username, 'invalid')).status_code == 401
                response = client.get('/api/v1/health', auth=(username, password))
                assert response.status_code == 200 and response.json()['database'] == 'AVAILABLE'
                assert client.get('/api/v1/intake/requests?limit=1', auth=(username, password)).status_code == 200
                assert client.get('/api/v1/intake/requests/synthetic-missing/records', auth=(username, password)).status_code == 404
                print('Real loopback HTTP passed: missing/invalid 401, authenticated health/list 200, missing records 404')
                if args.workflow:
                    client.auth = (username, password)
                    workflow(client, marker)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if args.workflow:
                cleanup(database_url, marker)


if __name__ == '__main__':
    main()
