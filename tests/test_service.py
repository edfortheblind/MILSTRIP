from milstrip.service import process_text
from tests.fixtures.real_examples import REAL_EXAMPLES


# Sanitized to the MILSTRIP payloads only; names, email addresses, and phone
# numbers from the source PDF are intentionally excluded.
INVALID_14_DIGIT_SAMPLE = (
    "A2ASTZS84050123456789..EA00004AA000000000001.ZZ9999MKK…RDO03999…SMSAA "
)
REPAIRABLE_DOT_SAMPLE = (
    "A2ASTZS8405012345678..EA00010AA000000000002.ZZ9999MKK…RDO03999…SMSAA "
)


def test_real_14_digit_sample_is_never_auto_corrected():
    record = process_text(INVALID_14_DIGIT_SAMPLE)[0]
    assert record.status == "REJECTED"
    assert record.canonical is None
    assert any(issue.code == "MIL-NORM-002" for issue in record.issues)


def test_plain_14_digit_nsn_requires_customer_correction():
    # Structurally aligned synthetic record isolates the field validator from
    # the punctuation-repair path observed in the real email.
    record = process_text(
        "A2ASTZS84050123456789 EA00004AA000000000001 ZZ9999MKK   030399 SMSAA       "
    )[0]
    assert record.status == "REJECTED"
    issue = next(issue for issue in record.issues if issue.code == "MIL-STR-003")
    assert "contact the requester/customer" in issue.message
    assert record.canonical is None


def test_real_dot_sample_has_one_auditable_repair():
    record = process_text(REPAIRABLE_DOT_SAMPLE)[0]
    assert record.status == "REQUIRES_REVIEW"
    assert record.fields.nsn == "8405012345678"
    assert record.fields.order_qty_raw == "00010"
    assert record.fields.erp_order == "AA000000000002"
    assert record.fields.priority_cd == "03"
    assert record.fields.tail_67_69 == "SMS"
    assert record.canonical is not None
    assert len(record.canonical) == 80
    assert len(record.canonical.encode("ascii")) == 80
    assert any(issue.code == "MIL-NORM-001" for issue in record.issues)


def test_punctuation_is_not_repaired_when_multiple_interpretations_remain():
    record = process_text("A2A…")[0]
    assert record.status == "REJECTED"
    assert record.canonical is None


def test_single_period_never_triggers_email_shape_repair():
    base = REAL_EXAMPLES[0]["line"]
    for position in (3, 30, 45, 52, 67):
        contaminated = base[:position - 1] + "." + base[position:]
        record = process_text(contaminated)[0]
        assert record.status == "REJECTED"
        assert record.canonical is None
        assert not any(issue.code == "MIL-NORM-001" for issue in record.issues)
