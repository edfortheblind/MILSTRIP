"""Compare the Python parser with the PostgreSQL parser function locally."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg

from milstrip.parsing.parser import parse_fields
from tests.fixtures.contract_cases import PARITY_CASES, SQL_FIELD_ALIASES


def main() -> None:
    database_url = os.getenv(
        "MILSTRIP_DATABASE_URL",
        "postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage",
    )
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        connection.read_only = True
        with connection.transaction():
            with connection.cursor() as cursor:
                for index, line in enumerate(PARITY_CASES, start=1):
                    python_fields = parse_fields(line)
                    cursor.execute("SELECT * FROM milstrip_app.parse_legacy_mils(%s)", (line,))
                    actual = dict(zip((column.name for column in cursor.description), cursor.fetchone()))
                    expected = {name: getattr(python_fields, SQL_FIELD_ALIASES.get(name, name)) for name in actual}
                    if len(actual) != 14 or actual != expected:
                        raise AssertionError(f"Parser parity failed at case {index}; apply migration 004 and rerun")
    print(f"Python/PostgreSQL parser parity passed: {len(PARITY_CASES)} cases, 14 fields each")


if __name__ == "__main__":
    main()
