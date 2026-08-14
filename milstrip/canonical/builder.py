"""Rebuild the exact 80-character canonical MILSTRIP from parsed fields.

Used two ways: (1) as the artifact a later phase would hand to the existing
staging table, and (2) right now, as a round-trip correctness check — if
re-slicing the rebuilt string doesn't reproduce the same fields we started
with, the parser and builder have drifted out of sync with each other.
"""

from __future__ import annotations

from milstrip.domain import MilstripFields, RECORD_LENGTH


def build_canonical(fields: MilstripFields) -> str:
    """Right-pad a validated source record without truncating or rewriting bytes."""
    source = fields.source_line
    if len(source) > RECORD_LENGTH:
        raise ValueError(f"Cannot canonicalize {len(source)} characters into an 80-character record")
    if any(not 0x20 <= ord(ch) <= 0x7E for ch in source):
        raise ValueError("Canonical MILSTRIP must contain printable ASCII only")
    return source.ljust(RECORD_LENGTH)
