from __future__ import annotations

from milstrip.domain import Fields


def parse_fields(line: str) -> Fields:
    padded = line[:80].ljust(80)
    return Fields(
        source=line,
        family=padded[:3].upper(),
        dic=padded[:3].upper(),
        ric=padded[3:6].upper(),
        media_status_cd=padded[6:7].upper(),
        nsn=padded[7:22].strip().upper(),
        ui=padded[22:24].upper(),
        order_qty_raw=padded[24:29].upper(),
        requisition=padded[29:43].upper(),
        suffix=padded[43:44].upper(),
        supp_addr=padded[44:50].upper(),
        signal_cd=padded[50:51].upper(),
        fund_cd=padded[51:53].upper(),
        dist_cd=padded[53:56].upper(),
        project_code=padded[56:59].upper(),
        priority_cd=padded[59:61].upper(),
        rdd=padded[61:64].upper(),
        advice_cd=padded[64:66].upper(),
        ownership_cd=padded[69:70].upper(),
        cond_cd=padded[70:71].upper(),
        tail_67_69=padded[66:69].upper(),
    )