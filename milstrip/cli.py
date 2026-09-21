from __future__ import annotations

import json
import sys
from pathlib import Path

from milstrip.service import process_text

MAX_INPUT_CHARS = 1_000_000


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    json_mode = "--json" in args
    paths = [arg for arg in args if arg != "--json"]
    try:
        if paths:
            text = Path(paths[0]).read_text(encoding="utf-8-sig")
        else:
            text = sys.stdin.read()
        if not text:
            print("MIL-INTAKE-001: empty input", file=sys.stderr)
            return 2
        if len(text) > MAX_INPUT_CHARS:
            print("MIL-INTAKE-003: input too large", file=sys.stderr)
            return 2
    except FileNotFoundError:
        print("MIL-INTAKE-002: input file not found", file=sys.stderr)
        return 2
    records = process_text(text)
    if json_mode:
        print(json.dumps({"records": [{"status": r.status, "nsn": r.fields.nsn, "canonical": r.canonical} for r in records]}))
    else:
        print("DATABASE CHANGES: NONE")
        print(f"Records detected:   {len(records)}")
        print(f"Valid:              {sum(r.status == 'VALID' for r in records)}")
        print(f"Requires review:    {sum(r.status == 'REQUIRES_REVIEW' for r in records)}")
        print(f"Rejected:           {sum(r.status == 'REJECTED' for r in records)}")
    return 1 if any(record.status == "REJECTED" for record in records) else 0