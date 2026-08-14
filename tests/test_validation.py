from milstrip.parsing.parser import parse_fields
from milstrip.validation.structural import validate_record
from tests.fixtures.real_examples import REAL_EXAMPLES, REAL_INCOMPLETE_EXAMPLE


def _set_field(line: str, start: int, length: int, value: str) -> str:
    """1-indexed, SUBSTRING()-style replacement — keeps every other position
    (and the overall length) exactly as in the source line."""
    end = start - 1 + length
    value = value[:length].ljust(length)
    return line[:start - 1] + value + line[end:]


BASE_LINE = REAL_EXAMPLES[0]["line"]  # 80 chars, everything valid


def test_all_real_examples_pass_or_only_warn():
    for case in REAL_EXAMPLES:
        fields = parse_fields(case["line"])
        issues = validate_record(case["line"], fields)
        errors = [i for i in issues if i.severity == "ERROR"]
        assert errors == [], (case["line"], issues)


def test_a5e_example_gets_address_warning():
    a5e_line = REAL_EXAMPLES[4]["line"]
    fields = parse_fields(a5e_line)
    issues = validate_record(a5e_line, fields)
    codes = [i.code for i in issues]
    assert "MIL-BIZ-001" in codes


def test_real_incomplete_example_is_rejected_as_too_short():
    line = REAL_INCOMPLETE_EXAMPLE["line"]
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert [i.code for i in issues] == ["MIL-STR-002"]


# Everything below mutates a known-good real line at one field position at a
# time, preserving overall length/shape — these specific field VALUES are
# constructed to exercise a validator, not real Shawn Hinkle data.

def test_invalid_nsn_length_rejected():
    line = _set_field(BASE_LINE, 8, 13, "840501530805 ")  # 12 digits + trailing space
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-STR-003" for i in issues)


def test_non_numeric_quantity_rejected():
    line = _set_field(BASE_LINE, 25, 5, "0A140")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-SEM-001" for i in issues)


def test_zero_quantity_rejected():
    line = _set_field(BASE_LINE, 25, 5, "00000")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-SEM-001" for i in issues)


def test_priority_out_of_range_rejected():
    line = _set_field(BASE_LINE, 60, 2, "16")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-SEM-002" for i in issues)


def test_priority_non_numeric_rejected():
    line = _set_field(BASE_LINE, 60, 2, "1A")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-SEM-002" for i in issues)


def test_unknown_family_rejected():
    line = _set_field(BASE_LINE, 1, 3, "ZZA")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-STR-001" for i in issues)


def test_short_line_rejected_without_cascading_field_errors():
    line = "A2ASTZ084050"
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert [i.code for i in issues] == ["MIL-STR-002"]


def test_blank_condition_code_rejected():
    line = _set_field(BASE_LINE, 71, 1, " ")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-SEM-003" for i in issues)


def test_blank_requisition_rejected():
    line = _set_field(BASE_LINE, 30, 14, " " * 14)
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    assert any(i.code == "MIL-STR-004" for i in issues)


def test_misaligned_a2_tail_is_rejected():
    line = _set_field(BASE_LINE, 67, 3, "XYZ")
    fields = parse_fields(line)
    issues = validate_record(line, fields)
    codes_by_severity = {(i.code, i.severity) for i in issues}
    assert ("MIL-STR-007", "ERROR") in codes_by_severity


def test_record_over_80_characters_is_rejected_without_truncation():
    line = BASE_LINE + "EXTRA"
    issues = validate_record(line, parse_fields(line))
    assert any(i.code == "MIL-STR-005" for i in issues)


def test_numeric_stock_number_with_14_digits_is_rejected():
    line = _set_field(BASE_LINE, 8, 15, "12345678901234 ")
    issues = validate_record(line, parse_fields(line))
    assert any(i.code == "MIL-STR-003" for i in issues)


def test_alphanumeric_part_number_is_allowed_by_dlm_layout():
    line = _set_field(BASE_LINE, 8, 15, "PART-12345")
    issues = validate_record(line, parse_fields(line))
    assert not any(i.code == "MIL-STR-003" for i in issues)


def test_ammunition_quantity_m_suffix_is_supported():
    line = _set_field(BASE_LINE, 8, 15, "1300000000000")
    line = _set_field(line, 25, 5, "1950M")
    issues = validate_record(line, parse_fields(line))
    assert not any(i.code == "MIL-SEM-001" for i in issues)
    assert any(i.code == "MIL-BIZ-006" and i.severity == "WARNING" for i in issues)


def test_ammunition_m_quantity_must_exceed_99999():
    line = _set_field(BASE_LINE, 8, 15, "1300000000000")
    line = _set_field(line, 25, 5, "0099M")
    issues = validate_record(line, parse_fields(line))
    assert any(i.code == "MIL-SEM-001" for i in issues)


def test_unicode_digits_are_rejected_without_crashing():
    for value in ("0000²", "００１４０"):
        line = _set_field(BASE_LINE, 25, 5, value)
        issues = validate_record(line, parse_fields(line))
        assert any(i.severity == "ERROR" for i in issues)


def test_blank_effective_dodaac_is_rejected():
    line = _set_field(BASE_LINE, 45, 6, "")
    issues = validate_record(line, parse_fields(line))
    assert any(i.code == "MIL-SEM-005" for i in issues)


def test_af6_is_recognized_but_requires_legacy_review():
    line = _set_field(BASE_LINE, 1, 3, "AF6")
    issues = validate_record(line, parse_fields(line))
    assert not any(i.code == "MIL-STR-001" for i in issues)
    assert any(i.code == "MIL-BIZ-004" and i.severity == "WARNING" for i in issues)


def test_invalid_dic_character_is_rejected_and_unobserved_dic_warns():
    invalid = _set_field(BASE_LINE, 1, 3, "A2!")
    assert any(i.code == "MIL-STR-001" for i in validate_record(invalid, parse_fields(invalid)))

    unobserved = _set_field(BASE_LINE, 1, 3, "A2B")
    issues = validate_record(unobserved, parse_fields(unobserved))
    assert not any(i.code == "MIL-STR-001" for i in issues)
    assert any(i.code == "MIL-BIZ-005" and i.severity == "WARNING" for i in issues)
