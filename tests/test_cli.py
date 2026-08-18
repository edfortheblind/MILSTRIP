import json

from milstrip.cli import MAX_INPUT_CHARS, main
from tests.fixtures.real_examples import REAL_EXAMPLES


def _write_batch(tmp_path):
    text = "\n".join(case["line"] for case in REAL_EXAMPLES)
    path = tmp_path / "batch.txt"
    path.write_text(text, encoding="utf-8")
    return path


def test_cli_exits_zero_when_all_valid(tmp_path, capsys):
    path = _write_batch(tmp_path)
    exit_code = main([str(path)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "DATABASE CHANGES: NONE" in out
    assert f"Records detected:   {len(REAL_EXAMPLES)}" in out


def test_cli_json_output_is_valid_json(tmp_path, capsys):
    path = _write_batch(tmp_path)
    main([str(path), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert len(payload["records"]) == len(REAL_EXAMPLES)
    # The A5E example legitimately carries a WARNING (needs a manually
    # supplied address), so REQUIRES_REVIEW is expected there, not VALID.
    assert all(r["status"] in ("VALID", "REQUIRES_REVIEW") for r in payload["records"])
    assert all(r["status"] == "VALID" for r in payload["records"] if r["nsn"] != "7210001195335")


def test_cli_nonzero_exit_when_a_record_is_rejected(tmp_path):
    bad_line = "A2ASTZ084050"  # starts with a known family prefix but is truncated
    path = tmp_path / "bad.txt"
    path.write_text(bad_line, encoding="utf-8")
    exit_code = main([str(path)])
    assert exit_code == 1


def test_cli_returns_intake_error_for_empty_input(tmp_path, capsys):
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    assert main([str(path)]) == 2
    assert "MIL-INTAKE-001" in capsys.readouterr().err


def test_cli_rejects_non_milstrip_text_before_positional_parsing(tmp_path, capsys):
    path = tmp_path / "not-a-milstrip.txt"
    path.write_text("AE2245\n", encoding="utf-8")

    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    assert "MIL-INTAKE-001" in captured.err
    assert "contact the requester/customer" in captured.err


def test_cli_json_exposes_actionable_preparse_rejection(tmp_path, capsys):
    path = tmp_path / "not-a-milstrip.txt"
    path.write_text("AE2245\n", encoding="utf-8")

    assert main([str(path), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["records"] == []
    assert payload["errors"][0]["code"] == "MIL-INTAKE-001"
    assert "corrected MILSTRIP record" in payload["errors"][0]["message"]


def test_cli_returns_controlled_error_for_missing_file(capsys):
    assert main(["/definitely/not/present.txt"]) == 2
    captured = capsys.readouterr()
    assert "MIL-INTAKE-002" in captured.err
    assert "Traceback" not in captured.err


def test_cli_accepts_utf8_bom(tmp_path):
    path = tmp_path / "bom.txt"
    path.write_text("\ufeff" + REAL_EXAMPLES[0]["line"], encoding="utf-8")
    assert main([str(path)]) == 0


def test_cli_rejects_oversized_input(tmp_path, capsys):
    path = tmp_path / "huge.txt"
    path.write_text("X" * (MAX_INPUT_CHARS + 1), encoding="utf-8")
    assert main([str(path)]) == 2
    assert "MIL-INTAKE-003" in capsys.readouterr().err
