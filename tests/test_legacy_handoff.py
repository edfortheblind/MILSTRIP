from datetime import datetime
from decimal import Decimal

from api.legacy_handoff import build_legacy_download_ship940_row
from milstrip.parsing.parser import parse_fields
from tests.fixtures.real_examples import REAL_EXAMPLES
import pytest


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


@pytest.mark.parametrize("line", [
    "A2?" + REAL_EXAMPLES[0]["line"][3:],
    "A2Z" + REAL_EXAMPLES[0]["line"][3:],
    REAL_EXAMPLES[4]["line"],
    "AF6" + REAL_EXAMPLES[0]["line"][3:],
    REAL_EXAMPLES[0]["line"][:24] + "1950M" + REAL_EXAMPLES[0]["line"][29:],
    REAL_EXAMPLES[0]["line"][:7] + "ABCDEFGHIJKLMNO" + REAL_EXAMPLES[0]["line"][22:],
])
def test_unapproved_or_lossy_handoff_is_blocked(line):
    with pytest.raises(ValueError):
        build_legacy_download_ship940_row(
            parse_fields(line), dodaac_lookup={"city": "Test City"},
            item_lookup={"um1": "EA", "list_price": "1.00"}, now=datetime(2026, 9, 23),
        )


def test_duplicate_protection_includes_different_dic_and_padded_order(database):
    from api.legacy_handoff import legacy_order_exists

    database.execute("CREATE TEMP TABLE milstrip_handoff_test (erp_order text, dic text) ON COMMIT DROP")
    database.execute("INSERT INTO milstrip_handoff_test VALUES ('TEST-ORDER  ', 'A5A')")
    with database.cursor() as cursor:
        assert legacy_order_exists(cursor, "TEST-ORDER", temporary=True)
        assert not legacy_order_exists(cursor, "NEW-ORDER", temporary=True)


def test_complete_synthetic_row_matches_recovered_sql_contract():
    from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD, TEST_TIME

    row = build_legacy_download_ship940_row(
        parse_fields(SYNTHETIC_RECORD),
        dodaac_lookup={"city": "Test City", "add1": "Line 1", "add2": "Line 2", "add3": "Line 3", "add4": "Line 4", "state": "TX", "cntrycd": "US", "zip": "00000"},
        item_lookup={"um1": "BX", "list_price": "12.3400"}, now=TEST_TIME,
    )
    assert row == {
        "bornondate": TEST_TIME, "interfaceid": None, "dic": "A2A", "advicecode": "  ",
        "billtododaac": None, "cond_cd": "A", "dist_cd": "   ", "datecreated": TEST_TIME,
        "fund_cd": "KK", "media_stat_cd": "0", "nsn": "8405016819440", "op_cd": "A",
        "orderqty": 1, "prioritycode": "15", "projectcode": "   ", "rdd": "   ",
        "ric": "STZ", "requisition": "ZZ999926600001", "signal_cd": "M", "std_up": Decimal("12.3400"),
        "supp_addr": "SC0141", "shiptocity": "Test City", "shiptododaac": "SC0141",
        "shiptoline1": "Line 1", "shiptoline2": "Line 2", "shiptoline3": "Line 3", "shiptoline4": "Line 4",
        "shiptostate": "TX", "shiptocountry": "US", "shiptozip": "00000", "statustododaac": "SC0141",
        "suffix": None, "supplycenterric": "SMS", "ui": "BX", "erp_order": "ZZ999926600001",
        "ordersourcetype": 2, "calendardate3pl": datetime(2026, 9, 23), "note3pl": "20260923_milstrip",
    }


@pytest.mark.parametrize("lookups", [(None, None), ({"city": "Test"}, None), (None, {"um1": "EA", "list_price": "1"})])
def test_missing_references_block_handoff(lookups):
    from scripts.run_controlled_handoff_test import SYNTHETIC_RECORD, TEST_TIME

    with pytest.raises(ValueError):
        build_legacy_download_ship940_row(parse_fields(SYNTHETIC_RECORD), dodaac_lookup=lookups[0], item_lookup=lookups[1], now=TEST_TIME)
