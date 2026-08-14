from milstrip.parsing.parser import parse_fields
from tests.fixtures.real_examples import REAL_EXAMPLES, REAL_INCOMPLETE_EXAMPLE


def test_all_real_examples_parse_to_expected_values():
    for case in REAL_EXAMPLES:
        fields = parse_fields(case["line"])
        assert fields.erp_order == case["erp_order"], case["line"]
        assert fields.nsn == case["nsn"], case["line"]
        assert fields.order_qty_raw == case["qty"], case["line"]
        assert fields.priority_cd == case["priority"], case["line"]


def test_family_detected_correctly():
    a2 = parse_fields(REAL_EXAMPLES[0]["line"])
    a5e = parse_fields(REAL_EXAMPLES[4]["line"])
    assert a2.family == "A2A"
    assert a2.is_a5e is False
    assert a5e.family == "A5E"
    assert a5e.is_a5e is True


def test_effective_dodaac_matches_sql_signal_code_rule():
    # Signal code 'M' (>= 'J') -> effective DODAAC comes from supp_addr (position 45-50).
    fields = parse_fields(REAL_EXAMPLES[0]["line"])
    assert fields.signal_cd == "M"
    assert fields.effective_dodaac == fields.supp_addr == "SC0140"

    # Signal code 'J' (>= 'J') -> also supp_addr, per the SQL's `< 'J'` boundary.
    # (REAL_INCOMPLETE_EXAMPLE is too short to pass full validation, but its
    # first 64 characters — including signal_cd at position 51 — are real.)
    fields = parse_fields(REAL_INCOMPLETE_EXAMPLE["line"])
    assert fields.signal_cd == "J"
    assert fields.effective_dodaac == fields.supp_addr == "N50408"
