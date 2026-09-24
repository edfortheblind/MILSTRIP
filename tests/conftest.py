import os
from pathlib import Path

import pytest


@pytest.fixture
def api_credentials(tmp_path, monkeypatch):
    import json
    from api.auth import ITERATIONS, password_digest
    from api.profiles import empty_runtime_config, RuntimeProfile, save_runtime_config
    from dataclasses import replace
    username, password = 'synthetic-reviewer', 'synthetic-test-password-only'
    salt = 'ab' * 32
    directory = tmp_path / '.cred'
    directory.mkdir()
    path = directory / 'api-credential.json'
    path.write_text(json.dumps(dict(version=1, iterations=ITERATIONS, username=username,
                                   salt=salt, digest=password_digest(password, salt))), encoding='utf-8')
    (directory / 'api-prod-credential.json').write_text(json.dumps(dict(
        version=1, iterations=ITERATIONS, username='synthetic-prod-reviewer', salt=salt,
        digest=password_digest('synthetic-prod-password-only', salt))), encoding='utf-8')
    config_path = directory / 'runtime.json'
    config = empty_runtime_config(config_path)
    profiles = dict(config.profiles)
    profiles['stage'] = RuntimeProfile('stage', 'postgresql', 'Synthetic Stage',
        os.getenv('MILSTRIP_TEST_DATABASE_URL', 'postgresql://localhost/trav3pl-psqldb-stage'), True)
    save_runtime_config(replace(config, profiles=profiles), config_path)
    monkeypatch.setenv('MILSTRIP_RUNTIME_CONFIG_FILE', str(config_path))
    monkeypatch.setenv('MILSTRIP_CONTROL_FILE', str(directory / 'control.json'))
    return username, password


@pytest.fixture
def portable_database():
    """Independent SQLAlchemy outer transaction; every test write rolls back."""
    from types import SimpleNamespace
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict
    from sqlalchemy import select, text
    from api.persistence import Repository, make_engine
    from api.persistence.schema import environment_identity, metadata, SCHEMA_VERSION

    url = os.getenv('MILSTRIP_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set MILSTRIP_TEST_DATABASE_URL for rollback-only local integration tests')
    config = conninfo_to_dict(url)
    if config.get('host') not in {'localhost', '127.0.0.1', '::1'} or config.get('dbname') != 'trav3pl-psqldb-stage':
        pytest.fail('Integration tests require the approved localhost development database')
    engine = make_engine('postgresql', url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET LOCAL lock_timeout = '5s'"))
                connection.execute(text("SET LOCAL statement_timeout = '15s'"))
                driver = connection.connection.driver_connection
                for migration in sorted((Path(__file__).resolve().parents[1] / 'db/migrations').glob('*.sql')):
                    driver.execute(migration.read_text(encoding='utf-8'))
                metadata.create_all(connection)
                identity = connection.execute(select(environment_identity)).mappings().first()
                if identity is None:
                    connection.execute(environment_identity.insert().values(
                        singleton_id=1, profile_id='stage', schema_version=SCHEMA_VERSION))
                Repository(connection).validate_identity('stage')
                for table, column in [('validation_issue', 'issue_id'), ('review_decision', 'decision_id'), ('audit_event', 'event_id')]:
                    target, identifier = sql.Identifier('milstrip_app', table), sql.Identifier(column)
                    next_id = driver.execute(sql.SQL('SELECT coalesce(max({}), 0) + 1 FROM {}').format(identifier, target)).fetchone()[0]
                    driver.execute(sql.SQL('ALTER TABLE {} ALTER COLUMN {} RESTART WITH {}').format(target, identifier, sql.Literal(next_id)))
                yield SimpleNamespace(connection=connection, driver=driver, repository=Repository(connection))
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def runtime_client(portable_database, api_credentials, monkeypatch):
    from contextlib import contextmanager
    from fastapi.testclient import TestClient
    from api.app import app
    from api import runtime
    from api.persistence import Repository

    @contextmanager
    def open_test_repository(provider, connection_string):
        assert provider == 'postgresql'
        with portable_database.connection.begin_nested():
            yield Repository(portable_database.connection)

    monkeypatch.setattr(runtime, 'open_repository', open_test_repository)
    with TestClient(app, client=('127.0.0.1', 50000)) as client:
        client.auth = api_credentials
        yield client


@pytest.fixture
def database():
    """Opt-in local integration tests; all application DDL/data rolls back."""
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    url = os.getenv("MILSTRIP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set MILSTRIP_TEST_DATABASE_URL for rollback-only local integration tests")
    config = conninfo_to_dict(url)
    if config.get("host") not in {"localhost", "127.0.0.1", "::1"} or config.get("dbname") != "trav3pl-psqldb-stage":
        pytest.fail("Integration tests require the approved localhost development database")
    with psycopg.connect(url, connect_timeout=5) as connection:
        with connection.transaction(force_rollback=True):
            connection.execute("SET LOCAL lock_timeout = '5s'")
            connection.execute("SET LOCAL statement_timeout = '15s'")
            for path in sorted((Path(__file__).resolve().parents[1] / "db/migrations").glob("*.sql")):
                connection.execute(path.read_text(encoding="utf-8"))
            # RESTART is transactional, unlike nextval(). Isolate test identity
            # allocation so even sequence state is restored by the rollback.
            from psycopg import sql
            for table, column in [("validation_issue", "issue_id"), ("review_decision", "decision_id"), ("audit_event", "event_id")]:
                target = sql.Identifier("milstrip_app", table)
                identifier = sql.Identifier(column)
                next_id = connection.execute(sql.SQL("SELECT coalesce(max({}), 0) + 1 FROM {}").format(identifier, target)).fetchone()[0]
                connection.execute(sql.SQL("ALTER TABLE {} ALTER COLUMN {} RESTART WITH {}").format(target, identifier, sql.Literal(next_id)))
            yield connection
