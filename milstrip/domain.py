from __future__ import annotations

from dataclasses import dataclass

RECORD_LENGTH = 80

# Inclusive, one-based MILSTRIP positions. The untouched tail stays in source.
FIELD_SPECS = {
    "dic": (1, 3), "ric": (4, 6), "media_status_cd": (7, 7),
    "nsn": (8, 22), "ui": (23, 24), "order_qty_raw": (25, 29),
    "requisition": (30, 43), "suffix": (44, 44), "supp_addr": (45, 50),
    "signal_cd": (51, 51), "fund_cd": (52, 53), "dist_cd": (54, 56),
    "project_code": (57, 59), "priority_cd": (60, 61), "rdd": (62, 64),
    "advice_cd": (65, 66), "tail_67_69": (67, 69),
    "ownership_cd": (70, 70), "cond_cd": (71, 71),
}


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    field_name: str | None = None


@dataclass(frozen=True)
class Fields:
    source: str
    family: str
    dic: str
    ric: str
    media_status_cd: str
    nsn: str
    ui: str
    order_qty_raw: str
    requisition: str
    suffix: str
    supp_addr: str
    signal_cd: str
    fund_cd: str
    dist_cd: str
    project_code: str
    priority_cd: str
    rdd: str
    advice_cd: str
    ownership_cd: str
    cond_cd: str
    tail_67_69: str

    @property
    def is_a5e(self) -> bool:
        return self.family == "A5E"

    @property
    def effective_dodaac(self) -> str:
        return self.requisition[:6] if self.signal_cd < "J" else self.supp_addr

    @property
    def erp_order(self) -> str:
        return (self.requisition + self.suffix).rstrip()


@dataclass(frozen=True)
class Record:
    status: str
    fields: Fields
    issues: tuple[Issue, ...]
    canonical: str | None
    raw_candidate: str | None = None
