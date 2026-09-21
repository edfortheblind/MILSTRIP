from datetime import datetime
from decimal import Decimal

from api.legacy_handoff import build_legacy_download_ship940_row
from milstrip.parsing.parser import parse_fields
from tests.fixtures.real_examples import REAL_EXAMPLES


def test_owner_run_mapping_targets_download_ship940_contract():
    fields = parse_fields(REAL_EXAMPLES[5]["line"])
    row = build_legacy_download_ship940_row(
        fields,
        dodaac_lookup={"city": "Test City", "add1": "Test Address", "state": "TX", "cntrycd": "US", "zip": "78701"},
        item_lookup={"um1": "EA", "list_price": Decimal("35.6100")},
        now=datetime(2026, 9, 21, 10, 30),
    )

    assert row["nsn"] == "8405016819440"
    assert row["orderqty"] == 520
    assert row["shiptododaac"] == "SC0141"
    assert row["ui"] == "EA"
    assert row["ordersourcetype"] == 2
    assert row["supplycenterric"] == "SMS"
    assert row["erp_order"] == "SL470162240DCV"