from __future__ import annotations

import re
from html.parser import HTMLParser


class _EmailText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "tr"}:
            self.parts.append("\n")


def extract_candidates(text: str) -> list[tuple[int, str]]:
    cleaned = text.removeprefix("\ufeff")
    if cleaned.lstrip(" \r\n").startswith("<"):
        parser = _EmailText()
        parser.feed(cleaned)
        cleaned = "".join(parser.parts)
    else:
        cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("\xa0", " ").replace("\r\n", "\n")
    candidates: list[tuple[int, str]] = []
    for line_number, line in enumerate(cleaned.split("\n"), start=1):
        value = line.lstrip(" ")
        if value.upper().startswith(("A2", "A5", "AF")):
            candidates.append((line_number, value))
    return candidates
