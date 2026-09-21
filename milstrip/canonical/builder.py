from milstrip.domain import Fields, RECORD_LENGTH


def build_canonical(fields: Fields) -> str:
    return fields.source[:RECORD_LENGTH].ljust(RECORD_LENGTH)