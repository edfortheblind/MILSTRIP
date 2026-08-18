"""Phase 1 CLI — parse and structurally validate MILSTRIP requests.

    python -m milstrip.cli request.txt
    python -m milstrip.cli request.txt --json
    type request.txt | python -m milstrip.cli
    python -m milstrip.cli --label "Ticket 28108" request.txt

This Phase 1 CLI never connects to a database and never writes anything
anywhere — every run is effectively a dry run. Its JSON is diagnostic, not the
Rainbow deliverable. Rainbow CSV creation/FTP delivery is Phase 2; the
application database is Phase 3. See docs/ROADMAP.md.
"""

from __future__ import annotations

import argparse
import json
import sys

from milstrip.domain import MilstripRecord
from milstrip.service import process_text

MAX_INPUT_CHARS = 5_000_000


def _safe_display(value: str) -> str:
    """Render untrusted text without emitting terminal control sequences."""
    return value.encode("unicode_escape", errors="backslashreplace").decode("ascii")


def _print_intake_error(code: str, message: str, *, as_json: bool, label: str | None) -> None:
    if as_json:
        print(json.dumps({"label": label, "records": [], "errors": [
            {"code": code, "message": message},
        ]}, indent=2))
    else:
        print(f"ERROR {code}: {_safe_display(message)}", file=sys.stderr)


def _record_to_dict(record: MilstripRecord) -> dict:
    return {
        "raw_line": record.raw_line,
        "cleaned_line": record.cleaned_line,
        "status": record.status,
        "erp_order": record.fields.erp_order if record.fields else None,
        "stock_or_part_number": record.fields.stock_or_part_number.rstrip() if record.fields else None,
        "nsn": (record.fields.nsn or None) if record.fields else None,
        "quantity": record.fields.order_qty_raw if record.fields else None,
        "priority": record.fields.priority_cd if record.fields else None,
        "effective_dodaac": record.fields.effective_dodaac if record.fields else None,
        "canonical": record.canonical,
        "issues": [
            {"code": i.code, "severity": i.severity, "message": i.message}
            for i in record.issues
        ],
    }


def _print_human_report(label: str | None, records: list[MilstripRecord]) -> None:
    if label:
        print(_safe_display(label))
    print("-" * 40)
    print(f"Records detected:   {len(records)}")
    valid = [r for r in records if r.status == "VALID"]
    review = [r for r in records if r.status == "REQUIRES_REVIEW"]
    rejected = [r for r in records if r.status == "REJECTED"]
    print(f"Valid:              {len(valid)}")
    print(f"Requires review:    {len(review)}")
    print(f"Rejected:           {len(rejected)}")
    print()

    for idx, record in enumerate(records, start=1):
        mark = {"VALID": "OK", "REQUIRES_REVIEW": "REVIEW", "REJECTED": "ERROR"}[record.status]
        print(f"[{idx}] {mark}")
        print(f"  Received:  {_safe_display(record.raw_line.strip())}")
        if record.fields is not None:
            f = record.fields
            print(f"  ERP order: {_safe_display(f.erp_order)}")
            print(f"  Stock/part: {_safe_display(f.stock_or_part_number.rstrip())}")
            if f.nsn:
                print(f"  NSN:       {_safe_display(f.nsn)}")
            print(f"  Qty:       {_safe_display(f.order_qty_raw)}")
            print(f"  Priority:  {_safe_display(f.priority_cd)}")
            print(f"  DODAAC:    {_safe_display(f.effective_dodaac)}")
        for issue in record.issues:
            print(f"    {issue.severity} {issue.code}: {_safe_display(issue.message)}")
        if record.canonical:
            print(f"  Canonical: {_safe_display(record.canonical)}")
        print()

    print(f"{len(valid)} VALID, {len(review)} REQUIRES REVIEW, {len(rejected)} REJECTED")
    print("DATABASE CHANGES: NONE (Phase 1 — parsing only, see docs/ROADMAP.md)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("file", nargs="?", help="Path to a text file with the raw request. "
                         "Omit to read from stdin.")
    parser.add_argument("--json", action="store_true", help="Emit a diagnostic JSON report "
                        "instead of text. This is not the Rainbow deliverable.")
    parser.add_argument("--label", default=None, help="Optional free-text label for the report "
                         "(e.g. a ticket number). Not persisted anywhere.")
    args = parser.parse_args(argv)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8-sig", errors="strict") as fh:
                raw_text = fh.read(MAX_INPUT_CHARS + 1)
        except (OSError, UnicodeError) as exc:
            message = f"Unable to read input file: {exc}"
            _print_intake_error("MIL-INTAKE-002", message, as_json=args.json, label=args.label)
            return 2
    else:
        try:
            raw_text = sys.stdin.read(MAX_INPUT_CHARS + 1)
        except (OSError, UnicodeError) as exc:
            _print_intake_error(
                "MIL-INTAKE-002", f"Unable to read stdin: {exc}",
                as_json=args.json, label=args.label,
            )
            return 2

    if len(raw_text) > MAX_INPUT_CHARS:
        _print_intake_error(
            "MIL-INTAKE-003",
            f"Input exceeds the {MAX_INPUT_CHARS}-character safety limit.",
            as_json=args.json,
            label=args.label,
        )
        return 2

    records = process_text(raw_text)
    intake_errors = []
    if not records:
        intake_errors.append({
            "code": "MIL-INTAKE-001",
            "message": (
                "No plausible MILSTRIP records were detected. Expected a record beginning "
                "with an A2_, A5_, or AF6 document identifier and containing the required "
                "fixed-width fields. Do not submit or invent missing values; contact the "
                "requester/customer and ask for a corrected MILSTRIP record."
            ),
        })

    if args.json:
        print(json.dumps({
            "label": args.label,
            "records": [_record_to_dict(r) for r in records],
            "errors": intake_errors,
        }, indent=2))
    else:
        _print_human_report(args.label, records)
        for error in intake_errors:
            print(f"ERROR {error['code']}: {error['message']}", file=sys.stderr)

    if intake_errors:
        return 2
    return 1 if any(r.status == "REJECTED" for r in records) else 0


if __name__ == "__main__":
    sys.exit(main())
