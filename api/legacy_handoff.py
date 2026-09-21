from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from milstrip.domain import Fields


def build_legacy_download_ship940_row(
    fields: Fields,
    *,
    dodaac_lookup: dict[str, Any],
    item_lookup: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Build the owner-run SQL row without performing a database write."""
    return {
        "bornondate": now,
        "interfaceid": None,
        "dic": fields.dic,
        "advicecode": fields.advice_cd,
        "billtododaac": fields.supp_addr if fields.dic.startswith("A5") else None,
        "cond_cd": fields.cond_cd,
        "dist_cd": fields.dist_cd,
        "datecreated": now,
        "fund_cd": fields.fund_cd,
        "media_stat_cd": fields.media_status_cd,
        "nsn": fields.nsn,
        "op_cd": fields.ownership_cd,
        "orderqty": int(fields.order_qty_raw),
        "prioritycode": fields.priority_cd,
        "projectcode": fields.project_code,
        "rdd": fields.rdd,
        "ric": fields.ric,
        "requisition": fields.requisition,
        "signal_cd": fields.signal_cd,
        "std_up": Decimal(str(item_lookup["list_price"])),
        "supp_addr": fields.supp_addr,
        "shiptocity": dodaac_lookup.get("city"),
        "shiptododaac": fields.effective_dodaac,
        "shiptoline1": dodaac_lookup.get("add1"),
        "shiptoline2": dodaac_lookup.get("add2"),
        "shiptoline3": dodaac_lookup.get("add3"),
        "shiptoline4": dodaac_lookup.get("add4"),
        "shiptostate": dodaac_lookup.get("state"),
        "shiptocountry": dodaac_lookup.get("cntrycd"),
        "shiptozip": dodaac_lookup.get("zip"),
        "statustododaac": fields.effective_dodaac,
        "suffix": fields.suffix.strip() or None,
        "supplycenterric": "SMS",
        "ui": item_lookup["um1"],
        "erp_order": fields.erp_order,
        "ordersourcetype": 2,
        "calendardate3pl": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "note3pl": now.strftime("%Y%m%d") + "_milstrip",
    }