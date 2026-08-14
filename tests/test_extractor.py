from milstrip.intake.extractor import extract_candidates
from tests.fixtures.real_examples import REAL_EXAMPLES


def test_extracts_every_real_example_from_a_plain_batch():
    text = "\n".join(case["line"] for case in REAL_EXAMPLES)
    candidates = extract_candidates(text)
    assert len(candidates) == len(REAL_EXAMPLES)


def test_strips_html_contamination():
    text = f"<p>{REAL_EXAMPLES[0]['line']}</p><br/>"
    candidates = extract_candidates(text)
    assert len(candidates) == 1
    _, cleaned = candidates[0]
    assert "<" not in cleaned and ">" not in cleaned


def test_html_block_boundaries_preserve_multiple_records():
    text = f"<p>{REAL_EXAMPLES[0]['line']}</p><p>{REAL_EXAMPLES[1]['line']}</p>"
    candidates = extract_candidates(text)
    assert len(candidates) == 2


def test_html_br_preserves_multiple_records():
    text = f"{REAL_EXAMPLES[0]['line']}<br>{REAL_EXAMPLES[1]['line']}"
    candidates = extract_candidates(text)
    assert len(candidates) == 2


def test_bom_lowercase_and_leading_spaces_are_transport_cleanup():
    text = "\ufeff   " + REAL_EXAMPLES[0]["line"].lower()
    candidates = extract_candidates(text)
    assert len(candidates) == 1
    assert candidates[0][1].startswith("a2a")


def test_ignores_non_milstrip_lines():
    text = "Hi Shawn, please process these urgent orders:\n" + REAL_EXAMPLES[0]["line"] + \
           "\nThanks,\nOperations"
    candidates = extract_candidates(text)
    assert len(candidates) == 1


def test_normalizes_tabs_and_nbsp():
    dirty = REAL_EXAMPLES[0]["line"].replace(" ", "\xa0", 1)
    candidates = extract_candidates(dirty)
    assert len(candidates) == 1
    _, cleaned = candidates[0]
    assert "\xa0" not in cleaned
