import pytest

from milstrip.service import process_text
from tests.fixtures.real_examples import REAL_EXAMPLES


BASE = REAL_EXAMPLES[0]["line"].ljust(80)


@pytest.mark.parametrize("dic", ["A2?", "A5!", "A2Z", "A5Z"])
def test_unverified_dic_never_becomes_valid(dic):
    record = process_text(dic + BASE[3:])[0]
    assert record.status != "VALID"


@pytest.mark.parametrize("character", ["\x01", "\t", "\x0b", "\x1e", "\u00e9", "\u2028"])
def test_non_printable_ascii_is_rejected_in_received_positions(character):
    record = process_text(BASE[:79] + character)[0]
    assert record.status == "REJECTED"
    assert record.canonical is None


def test_blank_stock_is_rejected():
    record = process_text(BASE[:7] + " " * 15 + BASE[22:])[0]
    assert record.status == "REJECTED"


def test_overlength_trailing_spaces_are_not_removed_before_validation():
    record = process_text(BASE + " ")[0]
    assert record.status == "REJECTED"


def test_html_like_text_inside_record_is_not_silently_deleted():
    record = process_text(BASE[:74] + "<b>" + BASE[74:])[0]
    assert record.status == "REJECTED"
