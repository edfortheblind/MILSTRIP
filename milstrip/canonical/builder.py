from milstrip.domain import Fields, RECORD_LENGTH


def build_canonical(fields: Fields) -> str:
    if len(fields.source) > RECORD_LENGTH or any(
        not 32 <= ord(character) <= 126 for character in fields.source
    ):
        raise ValueError("Canonical input must be at most 80 printable ASCII characters")
    return fields.source.ljust(RECORD_LENGTH)
