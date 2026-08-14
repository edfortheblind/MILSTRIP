"""Turn raw, dirty email/ticket text into candidate MILSTRIP lines.

Deliberately conservative: this module never guesses field values, it only
locates lines that plausibly start a MILSTRIP record and strips the noise
(HTML, tabs, non-breaking spaces) that copy-paste from Outlook/Freshservice
reliably introduces (confirmed on the 2026-08-12 Shawn Hinkle call).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from milstrip.domain import KNOWN_EXACT_FAMILIES, KNOWN_FAMILY_PREFIXES

_WS_CHARS = ("\xa0", "\t", "​")
_BLOCK_TAGS = {"br", "p", "div", "li", "tr", "table", "section", "article"}
_PREFIX_RE = re.compile(r"^(?:A2|A5|AF6)", re.IGNORECASE)


class _TextWithBoundariesParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_html(text: str) -> str:
    parser = _TextWithBoundariesParser()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts)


def clean_line(line: str) -> str:
    for ch in _WS_CHARS:
        line = line.replace(ch, " ")
    return line.lstrip(" ").rstrip("\r\n")


def looks_like_milstrip(line: str) -> bool:
    stripped = line.lstrip(" \ufeff")
    prefix = stripped[:3].upper()
    return bool(_PREFIX_RE.match(stripped)) or prefix in KNOWN_EXACT_FAMILIES or prefix[:2] in KNOWN_FAMILY_PREFIXES


def extract_candidates(raw_text: str) -> list[tuple[str, str]]:
    """Return a list of (raw_line, cleaned_line) pairs for every candidate found.

    ``raw_line`` preserves the extracted logical text line before transport
    cleanup. The complete caller-owned payload remains the authoritative raw
    input because HTML boundaries may not map one-to-one to source lines.
    """

    text = strip_html(raw_text)
    candidates = []
    for line in text.splitlines():
        cleaned = clean_line(line.lstrip("\ufeff"))
        if looks_like_milstrip(cleaned):
            candidates.append((line, cleaned))
    return candidates
