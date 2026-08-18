"""Phase 1 point validators — structural and semantic only.

No database access: NSN existence (ItemMaster), DODAAC existence, and
duplicate/ERP_ORDER checks all require a reference database and are Phase 2
(Validator) work — see docs/ROADMAP.md. Every validator here is a small,
independently testable function returning zero or more ProcessingIssue
records; nothing here mutates state or touches the network.
"""

from __future__ import annotations

import re

from milstrip.domain import MilstripFields, OBSERVED_DICS, ProcessingIssue, RECORD_LENGTH

MIN_STRUCTURAL_LENGTH = 71  # through cond_cd (position 71) — everything KNOWN-confidence


def validate_family(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.family_group == "UNKNOWN":
        return [ProcessingIssue(
            code="MIL-STR-001",
            message=f"Unrecognized record family {fields.dic!r}. DLM layouts supported: A2_, A5_, AF6.",
            severity="ERROR",
        )]
    return []


def validate_length(cleaned_line: str) -> list[ProcessingIssue]:
    if len(cleaned_line) < MIN_STRUCTURAL_LENGTH:
        return [ProcessingIssue(
            code="MIL-STR-002",
            message=(
                f"Record is {len(cleaned_line)} characters; at least "
                f"{MIN_STRUCTURAL_LENGTH} are required to contain every known field "
                "up to and including the condition code. Likely truncated during copy/paste; "
                "do not submit it. Contact the requester/customer for the complete record."
            ),
            severity="ERROR",
        )]
    if len(cleaned_line) > RECORD_LENGTH:
        return [ProcessingIssue(
            code="MIL-STR-005",
            message=f"Record is {len(cleaned_line)} characters; maximum is {RECORD_LENGTH}. "
                    "Extra characters will not be truncated.",
            severity="ERROR",
        )]
    return []


def validate_ascii(cleaned_line: str) -> list[ProcessingIssue]:
    if any(not 0x20 <= ord(ch) <= 0x7E for ch in cleaned_line):
        return [ProcessingIssue(
            code="MIL-STR-006",
            message="Record contains non-ASCII or non-printable characters after transport cleanup.",
            severity="ERROR",
        )]
    return []


def validate_stock_or_part_number(fields: MilstripFields) -> list[ProcessingIssue]:
    value = fields.stock_or_part_number.rstrip()
    if not value:
        return [ProcessingIssue(
            code="MIL-STR-003",
            message="Stock or Part Number (positions 8-22) is blank.",
            severity="ERROR",
        )]
    if value.isascii() and value.isdigit() and len(value) != 13:
        return [ProcessingIssue(
            code="MIL-STR-003",
            message=f"A numeric NSN must be exactly 13 digits; received {len(value)}. "
                    "Do not guess or remove a digit—contact the requester/customer and obtain "
                    "the corrected NSN from DLA.",
            severity="ERROR",
        )]
    if not re.fullmatch(r"[A-Z0-9 -]{1,15}", value):
        return [ProcessingIssue(
            code="MIL-STR-003",
            message=f"Stock or Part Number contains unsupported characters: {value!r}.",
            severity="ERROR",
        )]
    return []


def validate_requisition(fields: MilstripFields) -> list[ProcessingIssue]:
    if not fields.requisition.strip():
        return [ProcessingIssue(
            code="MIL-STR-004",
            message="Requisition/document number is blank.",
            severity="ERROR",
        )]
    return []


def validate_quantity(fields: MilstripFields) -> list[ProcessingIssue]:
    raw = fields.order_qty_raw
    if re.fullmatch(r"[0-9]{5}", raw):
        if int(raw) <= 0:
            return [ProcessingIssue(
                code="MIL-SEM-001",
                message="Quantity must be greater than zero.",
                severity="ERROR",
            )]
        return []

    if re.fullmatch(r"[0-9]{4}M", raw):
        stock = fields.stock_or_part_number.strip()
        fsc = stock[:4]
        ammunition = stock.startswith("13") or fsc in {
            "1410", "1420", "1427", "1440", "5330", "5865", "6810", "8140",
        }
        if ammunition and int(raw[:4]) >= 100:
            return []
        return [ProcessingIssue(
            code="MIL-SEM-001",
            message="Quantity suffix 'M' is allowed only for the ammunition/FSC categories "
                    "listed by DLM AP8.12/AP8.25.",
            severity="ERROR",
        )]
    return [ProcessingIssue(
        code="MIL-SEM-001",
        message=f"Quantity must be five ASCII digits, or four digits plus an allowed 'M'. Received {raw!r}.",
        severity="ERROR",
    )]


def validate_priority(fields: MilstripFields) -> list[ProcessingIssue]:
    raw = fields.priority_cd
    if not re.fullmatch(r"[0-9]{2}", raw):
        return [ProcessingIssue(
            code="MIL-SEM-002",
            message=f"Priority must be numeric. Received {raw!r}.",
            severity="ERROR",
        )]
    value = int(raw)
    if not 1 <= value <= 15:
        return [ProcessingIssue(
            code="MIL-SEM-002",
            message=f"Priority must be between 01 and 15. Received {raw!r}.",
            severity="ERROR",
        )]
    return []


def validate_condition_code(fields: MilstripFields) -> list[ProcessingIssue]:
    if not fields.cond_cd.strip():
        return [ProcessingIssue(
            code="MIL-SEM-003",
            message="Condition code is blank — Shawn Hinkle flagged this field as critical "
                    "(maps to inventory status).",
            severity="ERROR",
        )]
    return []


def validate_family_tail_alignment(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.family_group == "A2":
        value = fields.tail_67_69
        if value.strip() and value != "SMS" and not re.fullmatch(r"[0-9]{3}", value):
            return [ProcessingIssue(
                code="MIL-STR-007",
                message=f"A2 positions 67-69 are misaligned or unsupported: {value!r}. "
                        "Expected blank/date-of-receipt per DLM or the observed Travis 'SMS' variant.",
                severity="ERROR",
            )]
    return []


def validate_signal_code(fields: MilstripFields) -> list[ProcessingIssue]:
    if not fields.signal_cd.strip():
        return [ProcessingIssue(
            code="MIL-SEM-004",
            message="Signal code is blank — this field determines the effective ship-to DODAAC "
                    "and cannot be inferred.",
            severity="ERROR",
        )]
    return []


def validate_effective_dodaac(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.signal_cd.strip() and not fields.effective_dodaac.strip():
        return [ProcessingIssue(
            code="MIL-SEM-005",
            message="Signal code selects an empty effective DODAAC; the destination cannot be inferred.",
            severity="ERROR",
        )]
    return []


def check_a5e_address(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.is_a5e:
        return [ProcessingIssue(
            code="MIL-BIZ-001",
            message="A5E record — a ship-to address must be supplied out-of-band before "
                    "submission (cannot be derived from the MILSTRIP text). Confirmed by "
                    "Shawn Hinkle on the 2026-08-12 call.",
            severity="WARNING",
        )]
    return []


def check_tail_layout(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.family_group == "A2" and fields.tail_67_69 == "SMS":
        return [ProcessingIssue(
            code="MIL-BIZ-002",
            message="Legacy Travis A2 variant carries 'SMS' at positions 67-69, while DLM AP8.25 "
                    "defines those positions as date of receipt. Preserved without reinterpretation.",
            severity="INFO",
        )]
    return []


def check_family_tail(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.tail_74_80.strip():
        meaning = "unit price" if fields.family_group == "A5_AF6" else "RIC From/inventory control"
        return [ProcessingIssue(
            code="MIL-BIZ-003",
            message=f"Positions 74-80 carry {fields.tail_74_80!r} ({meaning} under the applicable "
                    "DLM layout). Preserved; the current legacy SQL does not consume it directly.",
            severity="INFO",
        )]
    return []


def check_af6_legacy_boundary(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.dic == "AF6":
        return [ProcessingIssue(
            code="MIL-BIZ-004",
            message="AF6 is recognized by DLM AP8.12, but its behavior through the current Travis "
                    "SQL prototype has not been verified; submission support requires a decision.",
            severity="WARNING",
        )]
    return []


def check_unconfirmed_dic(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.family_group != "UNKNOWN" and fields.dic not in OBSERVED_DICS and fields.dic != "AF6":
        return [ProcessingIssue(
            code="MIL-BIZ-005",
            message=f"DIC {fields.dic!r} matches a DLM layout group but has not been observed in "
                    "Travis production evidence; confirm before submission.",
            severity="WARNING",
        )]
    return []


def check_m_quantity_legacy_boundary(fields: MilstripFields) -> list[ProcessingIssue]:
    if fields.order_qty_raw.endswith("M"):
        return [ProcessingIssue(
            code="MIL-BIZ-006",
            message="The DLM 'M' quantity form is structurally valid, but the current Travis SQL "
                    "casts positions 25-29 to INT and cannot consume it unchanged.",
            severity="WARNING",
        )]
    return []


STRUCTURAL_VALIDATORS = (validate_length, validate_ascii)
FIELD_VALIDATORS = (
    validate_family,
    validate_stock_or_part_number,
    validate_requisition,
    validate_quantity,
    validate_priority,
    validate_condition_code,
    validate_family_tail_alignment,
    validate_signal_code,
    validate_effective_dodaac,
    check_a5e_address,
    check_tail_layout,
    check_family_tail,
    check_af6_legacy_boundary,
    check_unconfirmed_dic,
    check_m_quantity_legacy_boundary,
)


def validate_record(cleaned_line: str, fields: MilstripFields) -> list[ProcessingIssue]:
    issues: list[ProcessingIssue] = []
    for structural_validator in STRUCTURAL_VALIDATORS:
        issues.extend(structural_validator(cleaned_line))
    if any(issue.severity == "ERROR" for issue in issues):
        return issues
    for field_validator in FIELD_VALIDATORS:
        issues.extend(field_validator(fields))
    return issues
