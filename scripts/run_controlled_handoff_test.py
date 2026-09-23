"""Owner-approved synthetic handoff to a fixed temporary target; never dbo writes."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from api.legacy_handoff import build_legacy_download_ship940_row, legacy_order_exists
from milstrip.parsing.parser import parse_fields


SYNTHETIC_RECORD = "A2ASTZ08405016819440  EA00001ZZ999926600001 SC0141MKK      15     SMSAA".ljust(80)
TEST_TIME = datetime(2026, 9, 23, 12, 0)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def build_test_row(connection):
    fields = parse_fields(SYNTHETIC_RECORD)
    columns = ("city", "add1", "add2", "add3", "add4", "state", "cntrycd", "zip")
    addresses = connection.execute(
        "SELECT city, add1, add2, add3, add4, state, cntrycd, zip FROM dbo.cfg_dodaac_active WHERE dodaac=%s LIMIT 2",
        (fields.effective_dodaac,),
    ).fetchall()
    items = connection.execute(
        "SELECT um1, list_price FROM dbo.itemmaster WHERE item=%s LIMIT 2", (fields.nsn,),
    ).fetchall()
    if len(addresses) != 1 or len(items) != 1:
        raise ValueError("Test requires exactly one matching ItemMaster and DODAAC reference")
    with connection.cursor() as cursor:
        if legacy_order_exists(cursor, fields.erp_order):
            raise ValueError("Synthetic requisition already exists; select and approve a new fixture")
    return build_legacy_download_ship940_row(
        fields, dodaac_lookup=dict(zip(columns, addresses[0])),
        item_lookup=dict(zip(("um1", "list_price"), items[0])), now=TEST_TIME,
    )


def exercise_temporary_handoff(connection, row):
    """Copy column/constraint/index/identity definitions, not rows or triggers."""
    connection.execute("CREATE TEMP TABLE milstrip_handoff_test (LIKE dbo.download_ship940 INCLUDING CONSTRAINTS INCLUDING IDENTITY INCLUDING INDEXES) ON COMMIT DROP")
    target = sql.Identifier("pg_temp", "milstrip_handoff_test")
    columns = sql.SQL(", ").join(map(sql.Identifier, row))
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        target, columns, sql.SQL(", ").join(sql.Placeholder() for _ in row),
    )

    def insert_if_new():
        # Sequential test guard only. This is not a concurrent production writer.
        with connection.cursor() as cursor:
            if legacy_order_exists(cursor, row["erp_order"], temporary=True):
                return False
            cursor.execute(insert, tuple(row.values()))
            return True

    with connection.transaction(force_rollback=True):
        with connection.cursor() as cursor:
            require(insert_if_new(), "Initial insert was blocked")
            cursor.execute(sql.SQL("SELECT {} FROM {}").format(columns, target))
            actual = dict(zip(row, cursor.fetchone()))
            # bpchar columns may be padded by the legacy schema.
            for name, expected in row.items():
                value = actual[name]
                if isinstance(expected, str) and isinstance(value, str):
                    value, expected = value.rstrip(), expected.rstrip()
                if value != expected:
                    raise AssertionError(f"Legacy field mismatch: {name}")
            require(not insert_if_new(), "Duplicate was inserted")
            # A different document type still collides with the same ERP order.
            cursor.execute("UPDATE pg_temp.milstrip_handoff_test SET dic='A5A'")
            require(not insert_if_new(), "Cross-DIC duplicate was inserted")
            require(connection.execute("SELECT count(*) FROM pg_temp.milstrip_handoff_test").fetchone()[0] == 1, "Unexpected duplicate row count")
    require(connection.execute("SELECT count(*) FROM pg_temp.milstrip_handoff_test").fetchone()[0] == 0, "Savepoint rollback left rows")
    # Retry after rollback can insert again; the outer transaction also rolls back.
    require(insert_if_new(), "Retry after rollback was blocked")
    require(connection.execute("SELECT count(*) FROM pg_temp.milstrip_handoff_test").fetchone()[0] == 1, "Unexpected retry row count")
    return {"mapped_fields": len(row), "duplicate": "PASS", "rollback": "PASS", "retry": "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Execute only after owner approves this fixture and temporary target")
    args = parser.parse_args()
    url = os.getenv("MILSTRIP_DATABASE_URL", "postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage")
    config = conninfo_to_dict(url)
    if config.get("host") not in {"localhost", "127.0.0.1", "::1"} or config.get("dbname") != "trav3pl-psqldb-stage":
        parser.error("Only the approved localhost development database is allowed")
    try:
        with psycopg.connect(url, connect_timeout=5) as connection:
            connection.read_only = not args.execute
            with connection.transaction(force_rollback=True):
                connection.execute("SET LOCAL lock_timeout='5s'")
                connection.execute("SET LOCAL statement_timeout='15s'")
                row = build_test_row(connection)
                result = exercise_temporary_handoff(connection, row) if args.execute else {"status": "PREPARATION_PASS"}
            require(connection.execute("SELECT to_regclass('pg_temp.milstrip_handoff_test')").fetchone()[0] is None, "Temporary table survived outer rollback")
        print(json.dumps({**result, "erp_order": row["erp_order"], "target": "pg_temp.milstrip_handoff_test", "legacy_write": False}))
    except (psycopg.Error, ValueError, AssertionError) as error:
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__, "legacy_write": False}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
