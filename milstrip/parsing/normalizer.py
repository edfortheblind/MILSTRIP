"""Deterministic, evidence-backed transport normalization.

Only the exact punctuation-compression shape observed in the 2026-08-14 email
sample is eligible for repair. Generic positional shifts remain rejected.
"""

from __future__ import annotations

import re


_DOT_EMAIL_SHAPE = re.compile(
    r"^(?P<prefix>A2[A-Z0-9][A-Z0-9]{3}[A-Z0-9])"
    r"(?P<stock>[A-Z0-9-]{1,15})\.\."
    r"(?P<ui>[A-Z]{2})(?P<qty>[0-9]{5})(?P<req>[A-Z0-9]{14})\."
    r"(?P<supp>[A-Z0-9]{6})(?P<signal>[A-Z0-9])(?P<fund>[A-Z0-9]{2})…"
    r"(?P<middle>[A-Z0-9]{8})…(?P<tail>SMSAA)\s*$"
)


def normalize_line(cleaned_line: str) -> str:
    # MILSTRIP is an ASCII fixed-width interchange format. Translate ASCII
    # letters only so Unicode case-folding can never change field width.
    return cleaned_line.translate(str.maketrans(
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    ))


def placeholder_expansions(line: str) -> list[str]:
    """Reconstruct only the exact evidence-backed dot-email shape.

    The two separator widths are determined by the DLM field boundaries for
    that collected A2 shape. All other punctuation patterns return no repair.
    The list return type keeps the service contract explicit if a future,
    separately evidenced pattern genuinely has multiple candidates.
    """
    if "." not in line and "…" not in line:
        return []
    match = _DOT_EMAIL_SHAPE.fullmatch(line)
    if match is None:
        # Punctuation outside the collected shape is not evidence of spacing.
        return []

    stock = match.group("stock")
    if len(stock) > 15:
        return []
    candidate = (
        match.group("prefix")
        + stock.ljust(15)
        + match.group("ui")
        + match.group("qty")
        + match.group("req")
        + " "  # suffix
        + match.group("supp")
        + match.group("signal")
        + match.group("fund")
        + " " * 3  # distribution omitted in the collected email
        + match.group("middle")  # project + priority + RDD
        + " " * 2  # advice omitted
        + match.group("tail")
    )
    return [candidate]
