from __future__ import annotations

from dataclasses import dataclass

RECORD_LENGTH = 80


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
