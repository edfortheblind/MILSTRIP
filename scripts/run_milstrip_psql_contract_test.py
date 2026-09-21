"""Compare the Python parser with the PostgreSQL parser function locally."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg

from milstrip.parsing.parser import parse_fields


SAMPLE = "A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA"


def main() -> None:
    database_url = os.getenv(
        "MILSTRIP_DATABASE_URL",
        "postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage",
    )
    python_fields = parse_fields(SAMPLE)
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT dic, nsn, ui, order_qty_raw, effective_dodaac, erp_order
                    FROM milstrip_app.parse_legacy_mils(%s)
                    """,
                    (SAMPLE,),
                )
                sql_fields = cursor.fetchone()
                expected = (
                    python_fields.dic,
                    python_fields.nsn,
                    python_fields.ui,
                    python_fields.order_qty_raw,
                    python_fields.effective_dodaac,
                    python_fields.erp_order,
                )
                if sql_fields != expected:
                    raise AssertionError(f"parser mismatch: python={expected!r} sql={sql_fields!r}")
    print("Python/PostgreSQL MILSTRIP contract test passed")


if __name__ == "__main__":
    main()