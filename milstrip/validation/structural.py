from __future__ import annotations

import re

from milstrip.domain import Fields, Issue, RECORD_LENGTH


def validate_record(line: str, fields: Fields) -> list[Issue]:
    if len(line) < 71:
        return [Issue("MIL-STR-002", "ERROR", "Record is shorter than 71 characters")]
    if len(line) > RECORD_LENGTH:
        return [Issue("MIL-STR-005", "ERROR", "Record is longer than 80 characters")]
    issues: list[Issue] = []
    if fields.dic[:2] not in {"A2", "A5", "AF"} or fields.dic == "A2!":
        issues.append(Issue("MIL-STR-001", "ERROR", "Unsupported DIC family"))
    if fields.dic in {"A2A", "A2B", "A2E"} and fields.dic != "A2A":
        issues.append(Issue("MIL-BIZ-005", "WARNING", "Unobserved A2 DIC variant"))
    if fields.dic == "AF6":
        issues.append(Issue("MIL-BIZ-004", "WARNING", "AF6 requires legacy review"))
    if fields.nsn.isdigit() and len(fields.nsn) != 13:
        issues.append(Issue("MIL-STR-003", "ERROR", "Numeric stock number must be 13 digits"))
    quantity = fields.order_qty_raw
    if quantity.endswith("M"):
        if not quantity[:4].isdigit() or int(quantity[:4]) < 1000:
            issues.append(Issue("MIL-SEM-001", "ERROR", "Invalid M quantity"))
        else:
            issues.append(Issue("MIL-BIZ-006", "WARNING", "M quantity requires legacy review"))
    elif not quantity.isascii() or not quantity.isdigit() or int(quantity) == 0:
        issues.append(Issue("MIL-SEM-001", "ERROR", "Quantity must be a positive integer"))
    if not fields.priority_cd.isascii() or not fields.priority_cd.isdigit() or not 1 <= int(fields.priority_cd) <= 15:
        issues.append(Issue("MIL-SEM-002", "ERROR", "Priority must be 01 through 15"))
    if not fields.cond_cd.strip():
        issues.append(Issue("MIL-SEM-003", "ERROR", "Condition code is required"))
    if not fields.requisition.strip():
        issues.append(Issue("MIL-STR-004", "ERROR", "Requisition is required"))
    if not fields.effective_dodaac.strip():
        issues.append(Issue("MIL-SEM-005", "ERROR", "Effective DODAAC is required"))
    if fields.dic.startswith("A2") and fields.tail_67_69.strip() not in {"", "SMS"}:
        issues.append(Issue("MIL-STR-007", "ERROR", "Unexpected A2 tail"))
    if fields.is_a5e and not any(issue.severity == "ERROR" for issue in issues):
        issues.append(Issue("MIL-BIZ-001", "WARNING", "A5E requires ship-to address review"))
    if "\u2026" in line or "." in line:
        issues.append(Issue("MIL-NORM-002", "ERROR", "Contaminated punctuation requires review"))
    return issues