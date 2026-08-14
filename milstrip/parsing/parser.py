"""Fixed-width field extraction — position-based only, per docs/MILSTRIP_SPEC.md.

This module answers "what fields appear to be present" from a cleaned line.
It never validates business rules (see milstrip.validation) and never invents
a value for a position that isn't there.
"""

from __future__ import annotations

from milstrip.domain import FIELD_SPECS, MilstripFields


def _slice(line: str, start: int, length: int) -> str:
    """1-indexed, SQL SUBSTRING()-compatible slice. Missing trailing positions
    (a line shorter than the field's end) yield an empty string rather than
    raising — real records are frequently right-trimmed of trailing spaces."""

    end = start - 1 + length
    return line[start - 1:end] if start - 1 < len(line) else ""


def parse_fields(cleaned_line: str) -> MilstripFields:
    values = {}
    for spec in FIELD_SPECS:
        values[spec.name] = _slice(cleaned_line, spec.start, spec.length)

    return MilstripFields(
        source_line=cleaned_line,
        dic=values["dic"],
        ric=values["ric"],
        media_status_cd=values["media_status_cd"],
        stock_or_part_number=values["stock_or_part_number"],
        ui=values["ui"],
        order_qty_raw=values["order_qty"],
        requisition=values["requisition"],
        suffix=values["suffix"],
        supp_addr=values["supp_addr"],
        signal_cd=values["signal_cd"],
        fund_cd=values["fund_cd"],
        dist_cd=values["dist_cd"],
        project_code=values["project_code"],
        priority_cd=values["priority_cd"],
        rdd=values["rdd"],
        advice_cd=values["advice_cd"],
        tail_67_69=values["tail_67_69"],
        ownership_cd=values["ownership_cd"],
        cond_cd=values["cond_cd"],
        tail_72_73=values["tail_72_73"],
        tail_74_80=values["tail_74_80"],
    )
