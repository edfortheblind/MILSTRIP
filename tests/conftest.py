import os
from pathlib import Path

import pytest


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
