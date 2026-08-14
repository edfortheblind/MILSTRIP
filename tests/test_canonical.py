from milstrip.canonical.builder import build_canonical
from milstrip.domain import RECORD_LENGTH
from milstrip.parsing.parser import parse_fields
from tests.fixtures.real_examples import REAL_EXAMPLES


def test_canonical_is_always_80_characters():
    for case in REAL_EXAMPLES:
        fields = parse_fields(case["line"])
        canonical = build_canonical(fields)
        assert len(canonical) == RECORD_LENGTH


def test_round_trip_reparsing_matches_original_fields():
    for case in REAL_EXAMPLES:
        fields = parse_fields(case["line"])
        canonical = build_canonical(fields)
        reparsed = parse_fields(canonical)
        assert reparsed.nsn == fields.nsn
        assert reparsed.erp_order == fields.erp_order
        assert reparsed.order_qty_raw == fields.order_qty_raw
        assert reparsed.priority_cd == fields.priority_cd
        assert reparsed.cond_cd == fields.cond_cd


def test_family_dependent_positions_are_preserved_byte_for_byte():
    line = REAL_EXAMPLES[0]["line"]
    line = line[:20] + "XY" + line[22:71] + "ZZ" + line[73:]
    canonical = build_canonical(parse_fields(line))
    assert canonical == line.ljust(RECORD_LENGTH)
    assert canonical[20:22] == "XY"
    assert canonical[71:73] == "ZZ"
    assert len(canonical.encode("ascii")) == RECORD_LENGTH
