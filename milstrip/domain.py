"""Canonical MILSTRIP domain model.

Field positions and semantics are reverse-engineered from the production
prototype in the local-only ``local-discovery/Initial Idea/`` folder and
cross-checked against every real example record it contains. See
docs/MILSTRIP_SPEC.md for the full field-by-field evidence and confidence
levels. Do not change a position here without updating that document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Optional


RECORD_LENGTH = 80

KNOWN_FAMILY_PREFIXES = ("A2", "A5")
KNOWN_EXACT_FAMILIES = ("AF6",)
OBSERVED_DICS = ("A2A", "A5A", "A5E")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    start: int  # 1-indexed, inclusive — matches the SQL SUBSTRING() convention on purpose
    length: int
    confidence: str  # KNOWN | INFERRED | UNKNOWN
    note: str = ""

    @property
    def end(self) -> int:
        return self.start + self.length - 1


# Order matches byte order in the 80-character record. Confidence levels:
#   KNOWN     — directly read by the existing SQL prototype into a named column
#   FAMILY    — meaning depends on the DIC layout; preserved without loss
FIELD_SPECS = [
    FieldSpec("dic", 1, 3, "KNOWN", "Document Identifier Code. DLM layouts cover A2_, A5_, and AF6."),
    FieldSpec("ric", 4, 3, "KNOWN", "Routing Identifier Code. All evidence shows 'STZ'."),
    FieldSpec("media_status_cd", 7, 1, "KNOWN", "Media/status code."),
    FieldSpec("stock_or_part_number", 8, 15, "KNOWN", "DLM Stock or Part Number field. Numeric NSNs "
              "observed by Travis use 13 digits followed by two blanks; position 21 can carry type "
              "of pack for subsistence."),
    FieldSpec("ui", 23, 2, "KNOWN", "Unit of issue as sent. NOT what ends up in download_ship940 — "
              "the existing SQL overwrites this with ItemMaster.UM1 at insert time. Kept here only "
              "as a soft cross-check candidate for Phase 2."),
    FieldSpec("order_qty", 25, 5, "KNOWN", "Five digits, or four digits plus DLM ammunition 'M'."),
    FieldSpec("requisition", 30, 14, "KNOWN", "Document/requisition number (ERP_ORDER base)."),
    FieldSpec("suffix", 44, 1, "KNOWN", "Optional 15th requisition character, appended to ERP_ORDER."),
    FieldSpec("supp_addr", 45, 6, "KNOWN", "Supplementary address / candidate ship-to DODAAC."),
    FieldSpec("signal_cd", 51, 1, "KNOWN", "Determines which field is the effective ship-to DODAAC "
              "(see effective_dodaac below) and, for A5, BILLTODODAAC."),
    FieldSpec("fund_cd", 52, 2, "KNOWN", "Fund code."),
    FieldSpec("dist_cd", 54, 3, "KNOWN", "Distribution code."),
    FieldSpec("project_code", 57, 3, "KNOWN", "Project code."),
    FieldSpec("priority_cd", 60, 2, "KNOWN", "Priority. Must be numeric 01-15 per Shawn Hinkle "
              "(2026-08-12 call)."),
    FieldSpec("rdd", 62, 3, "KNOWN", "Required Delivery Date code."),
    FieldSpec("advice_cd", 65, 2, "KNOWN", "Advice code."),
    FieldSpec("tail_67_69", 67, 3, "FAMILY", "A2: date of receipt; A5_/AF6: originating RIC. "
              "Travis legacy A2 evidence instead carries SMS here; preserve and flag that variant."),
    FieldSpec("ownership_cd", 70, 1, "KNOWN", "Ownership code."),
    FieldSpec("cond_cd", 71, 1, "KNOWN", "Condition code (inventory status). Called out by Shawn as "
              "\"extremely important\"."),
    FieldSpec("tail_72_73", 72, 2, "FAMILY", "A2: system management; A5_/AF6: management and "
              "intra-Service/Agency positions."),
    FieldSpec("tail_74_80", 74, 7, "FAMILY", "A2: RIC From plus inventory control data; "
              "A5_/AF6: unit price."),
]

FIELD_BY_NAME = {f.name: f for f in FIELD_SPECS}


@dataclass
class MilstripFields:
    """One record's worth of parsed, still-untrusted field values (raw strings)."""

    source_line: str = ""
    dic: str = ""
    ric: str = ""
    media_status_cd: str = ""
    stock_or_part_number: str = ""
    ui: str = ""
    order_qty_raw: str = ""
    requisition: str = ""
    suffix: str = ""
    supp_addr: str = ""
    signal_cd: str = ""
    fund_cd: str = ""
    dist_cd: str = ""
    project_code: str = ""
    priority_cd: str = ""
    rdd: str = ""
    advice_cd: str = ""
    tail_67_69: str = ""
    ownership_cd: str = ""
    cond_cd: str = ""
    tail_72_73: str = ""
    tail_74_80: str = ""

    @property
    def family(self) -> str:
        return self.dic

    @property
    def family_group(self) -> str:
        if re.fullmatch(r"A2[A-Z0-9]", self.dic):
            return "A2"
        if re.fullmatch(r"A5[A-Z0-9]", self.dic) or self.dic == "AF6":
            return "A5_AF6"
        return "UNKNOWN"

    @property
    def nsn(self) -> str:
        """Return a numeric 13-digit NSN when the 15-position stock field has one."""
        value = self.stock_or_part_number.rstrip()
        return value if len(value) == 13 and value.isascii() and value.isdigit() else ""

    @property
    def routing_cd(self) -> str:
        """Compatibility view of positions 67-69; semantics are family-dependent."""
        return self.tail_67_69

    @property
    def op_cd(self) -> str:
        """Deprecated compatibility name; DLM identifies position 70 as Ownership."""
        return self.ownership_cd

    @property
    def price_tail(self) -> str:
        """Compatibility view; positions 74-80 are unit price only for A5_/AF6."""
        return self.tail_74_80

    @property
    def is_a5e(self) -> bool:
        return self.dic == "A5E"

    @property
    def erp_order(self) -> str:
        suffix = self.suffix if self.suffix.strip() else ""
        return (self.requisition + suffix).rstrip()

    @property
    def effective_dodaac(self) -> str:
        """Mirrors the existing SQL's @dodaac derivation exactly (see the prototype script)."""
        first6 = self.requisition[:6]
        if self.signal_cd and self.signal_cd < "J":
            return first6
        return self.supp_addr


@dataclass
class ProcessingIssue:
    code: str
    message: str
    severity: str  # ERROR | WARNING | INFO


@dataclass
class MilstripRecord:
    raw_line: str
    cleaned_line: str
    fields: Optional[MilstripFields] = None
    issues: list[ProcessingIssue] = field(default_factory=list)
    canonical: Optional[str] = None

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)

    @property
    def status(self) -> str:
        if self.has_errors:
            return "REJECTED"
        if any(i.severity == "WARNING" for i in self.issues):
            return "REQUIRES_REVIEW"
        return "VALID"
