from __future__ import annotations

from milstrip.domain import FIELD_SPECS, Fields


def parse_fields(line: str) -> Fields:
    padded = line.ljust(80)
    values = {
        name: padded[start - 1:end].upper()
        for name, (start, end) in FIELD_SPECS.items()
    }
    values["nsn"] = values["nsn"].strip()
    return Fields(source=line, family=values["dic"], **values)
