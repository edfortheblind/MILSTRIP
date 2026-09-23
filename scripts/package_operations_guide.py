"""Package the public, offline operating guide using an explicit file allowlist.

Run after build_operations_guide.py. This command neither publishes a release
nor reads credentials. Choose a dedicated output directory outside this repo.
Only Python's standard library is needed.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "operations-guide"
VERSION = "1.1.0"
ARCHIVE_NAME = f"MILSTRIP-guide-v{VERSION}.zip"
PDF_NAME = "MILSTRIP-current-and-phase2.pdf"
OPTIONAL_PDF_NAME = "MILSTRIP-quick-sop.pdf"
DIAGRAM_NAMES = (
    "01-current-functional.svg",
    "02-current-architecture.svg",
    "03-current-user-sop.svg",
    "04-phase2-azure-sql.svg",
    "05-phase2-functional.svg",
    "06-phase2-postgresql.svg",
    "07-phase2-transition.svg",
)
# Public architecture describes component roles, not identifiable infrastructure.
# This is a focused release guard, not a general-purpose secret scanner.
PRIVATE_MARKERS = (
    "trav3pl-sql-eastus",
    "trav3pl-sqldb-eastus-prod",
    "trav3pl-psqldb-stage",
    "7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82",
    "milstrip-dev-laptop",
    "travis association for the blind",
    "ed.lopez",
    ".cred",
    "engineering-notes",
    "verification.md",
    "guide.md",
)
PRIVATE_SOURCE_RE = re.compile(
    r"github\.com/edfortheblind/milstrip(?:[/?#\s\"'<]|$)", re.IGNORECASE
)
FIXED_ZIP_TIME = (2026, 9, 23, 0, 0, 0)
README = f"""MILSTRIP operating guide - documentation release {VERSION}
Evidence date: September 23, 2026

START HERE
Download index.html and open it in your browser. It works locally and offline.
No login is needed to read the guide. External reference links need internet.
If your browser previews the file as source, save it first and then open it.

The app remains unpublished DEV. This is a documentation release only.
Reading or downloading these files does not publish or grant access to the app.
Current behavior is distinguished from proposed production work in the guide.

CONTENTS
index.html                     Complete standalone visual guide
{PDF_NAME}   Printable guide
{OPTIONAL_PDF_NAME}            Short operator reference, when included
diagrams/                      Seven scalable SVG charts

The ZIP contains only the files above and this README. No credentials, tenant
configuration, private engineering notes, runtime sources, or sample orders
are included. SHA256SUMS.txt is a separate release asset for download checking.
"""


class PackageError(ValueError):
    """A release prerequisite is not satisfied."""


def validate_public_text(text: str, name: str) -> None:
    """Reject known private identifiers without copying their values to logs."""
    normalized = unquote(text).casefold()
    for marker in PRIVATE_MARKERS:
        if marker in normalized:
            raise PackageError(f"{name}: contains a private identifier or source reference")
    if PRIVATE_SOURCE_RE.search(normalized):
        raise PackageError(f"{name}: links to the private source repository")
    if re.search(r"file\s*:|[a-z]:[\\/]users[\\/]|/users/|/home/", normalized):
        raise PackageError(f"{name}: contains a local file URL or user path")


def validate_url(value: str, name: str, *, resource: bool = False) -> None:
    value = value.strip()
    if value.startswith("#"):
        return
    scheme = urlsplit(value).scheme.casefold()
    if scheme == "data":
        return
    if scheme in {"http", "https"} and not resource:
        return
    label = "resource dependency" if resource else "relative or unsupported link"
    raise PackageError(f"{name}: has an offline-incompatible {label}")


def validate_css(css: str, name: str) -> None:
    if re.search(r"@import\b", css, re.IGNORECASE):
        raise PackageError(f"{name}: CSS imports are not standalone")
    for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css, re.IGNORECASE):
        validate_url(match.group(2), name, resource=True)


class StandaloneHTML(HTMLParser):
    def __init__(self, name: str):
        super().__init__(convert_charrefs=True)
        self.name = name
        self.ids: set[str] = set()
        self.fragments: set[str] = set()
        self.text: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "base":
            raise PackageError(f"{self.name}: a base URL changes offline navigation")
        for key, value in attrs:
            if value is None:
                continue
            if key in {"href", "xlink:href", "src", "poster", "action", "formaction"}:
                resource = key in {"src", "poster"} or tag not in {"a", "area"}
                validate_url(value, self.name, resource=resource)
                if value.startswith("#") and len(value) > 1:
                    self.fragments.add(unquote(value[1:]))
            if key == "srcset":
                raise PackageError(f"{self.name}: use embedded src instead of srcset")
            if key == "style":
                validate_css(value, self.name)
            if key == "id":
                if value in self.ids:
                    raise PackageError(f"{self.name}: contains duplicate element IDs")
                self.ids.add(value)
        if tag == "meta" and values.get("http-equiv", "").casefold() == "refresh":
            raise PackageError(f"{self.name}: redirecting metadata is not standalone")
        if tag in {"style", "script"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.text.append(data)


def validate_html(payload: bytes) -> None:
    text = payload.decode("utf-8")
    validate_public_text(text, "index.html")
    validate_css(text, "index.html")
    parser = StandaloneHTML("index.html")
    parser.feed(text)
    parser.close()
    if parser.fragments - parser.ids:
        raise PackageError("index.html: contains an unresolved fragment link")
    visible = " ".join(parser.text).casefold()
    if not re.search(r"\bunpublished\b|\bnot published\b", visible):
        raise PackageError("index.html: must state that the app is unpublished")
    if not re.search(r"\bdev\b|\bdevelopment\b", visible):
        raise PackageError("index.html: must identify the current development status")
    if not re.search(r"september\s+23,?\s+2026|2026-09-23", visible):
        raise PackageError("index.html: must identify the September 23, 2026 evidence date")


def validate_svg(payload: bytes, name: str) -> None:
    text = payload.decode("utf-8")
    validate_public_text(text, name)
    validate_css(text, name)
    element = ET.fromstring(text)
    if element.tag.rsplit("}", 1)[-1] != "svg":
        raise PackageError(f"{name}: is not an SVG document")
    for node in element.iter():
        for key, value in node.attrib.items():
            if key.rsplit("}", 1)[-1] in {"href", "src"}:
                validate_url(value, name, resource=True)


def read_asset(source: Path, relative: str) -> bytes:
    path = source / relative
    if any(part.is_symlink() for part in [path, *path.parents]):
        raise PackageError(f"{relative}: symlinked sources are not allowed")
    if not path.is_file() or not path.stat().st_size:
        raise PackageError(f"Missing or empty release asset: {relative}")
    payload = path.read_bytes()
    if path.suffix == ".pdf":
        if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload[-1024:]:
            raise PackageError(f"{relative}: invalid PDF envelope")
        validate_public_text(payload.decode("latin-1"), relative)
    return payload


def collect_assets(source: Path) -> dict[str, bytes]:
    diagram_dir = source / "diagrams"
    actual = {path.name for path in diagram_dir.glob("*.svg")}
    if actual != set(DIAGRAM_NAMES):
        raise PackageError("Expected exactly the seven approved SVG chart filenames")
    assets = {"index.html": read_asset(source, "index.html"), PDF_NAME: read_asset(source, PDF_NAME)}
    validate_html(assets["index.html"])
    optional = source / OPTIONAL_PDF_NAME
    if optional.exists():
        assets[OPTIONAL_PDF_NAME] = read_asset(source, OPTIONAL_PDF_NAME)
    for name in DIAGRAM_NAMES:
        relative = f"diagrams/{name}"
        assets[relative] = read_asset(source, relative)
        validate_svg(assets[relative], relative)
    assets["README.txt"] = README.encode("utf-8")
    return assets


def zip_assets(assets: dict[str, bytes]) -> bytes:
    archive = BytesIO()
    # Stored entries avoid compression-library variation between machines.
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        for name, payload in sorted(assets.items()):
            entry = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, payload)
    return archive.getvalue()


def build_package(source: Path, output: Path) -> dict[str, str]:
    source, output = source.resolve(), output.resolve()
    if output == source or output in source.parents or source in output.parents:
        raise PackageError("Output must be separate from the source guide directory")
    if output == ROOT or output in ROOT.parents:
        raise PackageError("Use a dedicated output directory, not the repository or its parent")
    assets = collect_assets(source)
    release_assets = {name: payload for name, payload in assets.items() if "/" not in name}
    release_assets[ARCHIVE_NAME] = zip_assets(assets)
    digests = {name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(release_assets.items())}
    manifest = "".join(f"{digest}  {name}\n" for name, digest in digests.items())
    release_assets["SHA256SUMS.txt"] = manifest.encode("ascii")
    if output.exists():
        if not output.is_dir():
            raise PackageError("Output exists and is not a directory")
        if any(path.name not in release_assets or not path.is_file() or path.is_symlink()
               for path in output.iterdir()):
            raise PackageError("Output contains unrelated files; use a dedicated empty directory")
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in sorted(release_assets.items()):
        (output / name).write_bytes(payload)
    return digests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Dedicated release staging directory; outside the repo is preferred")
    args = parser.parse_args()
    try:
        digests = build_package(args.source_dir, args.output_dir)
    except (PackageError, OSError, UnicodeError, ET.ParseError, ValueError) as exc:
        print(f"Release package refused: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {len(DIAGRAM_NAMES)} standalone diagrams; public links and status checked.")
    print(f"PASS: {len(digests)} release assets plus SHA256SUMS.txt; deterministic ZIP created.")
    print("PDF text and metadata must also pass the document release review; this tool checks PDF structure only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
