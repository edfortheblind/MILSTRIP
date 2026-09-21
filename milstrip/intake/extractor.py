from __future__ import annotations

import re


def extract_candidates(text: str) -> list[tuple[int, str]]:
    cleaned = text.replace("\ufeff", "").replace("\xa0", " ")
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</p\s*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    candidates: list[tuple[int, str]] = []
    for line_number, line in enumerate(cleaned.splitlines(), start=1):
        value = line.strip()
        if value.upper().startswith(("A2", "A5", "AF6")):
            candidates.append((line_number, value))
    return candidates