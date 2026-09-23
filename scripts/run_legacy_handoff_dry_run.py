from __future__ import annotations

from datetime import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg

from api.legacy_handoff import build_legacy_download_ship940_row, legacy_order_exists
from milstrip.parsing.parser import parse_fields


SAMPLE = "A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA"


def main() -> None:
    connection_string = os.getenv(
        "MILSTRIP_DATABASE_URL",
        "postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage",
    )
    fields = parse_fields(SAMPLE)
    with psycopg.connect(connection_string, connect_timeout=5) as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT city, add1, add2, add3, add4, state, cntrycd, zip "
                "FROM dbo.cfg_dodaac_active WHERE dodaac = %s",
                (fields.effective_dodaac,),
            )
            dodaac_row = cursor.fetchone()
            if dodaac_row is None:
                raise RuntimeError(f"No active DODAAC: {fields.effective_dodaac}")
            dodaac = dict(zip(("city", "add1", "add2", "add3", "add4", "state", "cntrycd", "zip"), dodaac_row))

            cursor.execute(
                "SELECT um1, list_price FROM dbo.itemmaster WHERE item = %s",
                (fields.nsn,),
            )
            item_row = cursor.fetchone()
            if item_row is None:
                raise RuntimeError(f"No ItemMaster row: {fields.nsn}")
            item = dict(zip(("um1", "list_price"), item_row))

            row = build_legacy_download_ship940_row(
                fields,
                dodaac_lookup=dodaac,
                item_lookup=item,
                now=datetime(2026, 9, 21, 12, 0),
            )
            duplicate = legacy_order_exists(cursor, row["erp_order"])

    print({
        "status": "DUPLICATE" if duplicate else "DRY_RUN_READY",
        "erp_order": row["erp_order"],
        "nsn": row["nsn"],
        "dodaac": row["shiptododaac"],
        "ui": row["ui"],
        "orderqty": row["orderqty"],
        "legacy_write": False,
    })


if __name__ == "__main__":
    main()
