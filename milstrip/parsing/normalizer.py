from __future__ import annotations

import re

from milstrip.domain import Issue


def normalize_candidate(line: str) -> tuple[str, Issue | None]:
    if "." not in line and "\u2026" not in line:
        return line, None
    if line.count(".") != 3 or line.count("\u2026") != 2:
        return line, Issue("MIL-NORM-002", "ERROR", "Ambiguous punctuation contamination")
    repaired = line.replace("..", "  ").replace(".", " ")
    repaired = repaired.replace("\u2026", "   ", 1).replace("\u2026", "  ", 1)
    if "\u2026" in repaired or "." in repaired:
        return line, Issue("MIL-NORM-002", "ERROR", "Ambiguous punctuation contamination")
    stock = repaired[7:22].replace(" ", "")
    if len(stock) != 13 or not stock.isdigit():
        return repaired, Issue("MIL-NORM-002", "ERROR", "Invalid stock identifier cannot be repaired")
    return repaired, Issue("MIL-NORM-001", "WARNING", "Unique punctuation expansion requires review")