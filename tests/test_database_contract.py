import pytest

from milstrip.parsing.parser import parse_fields
from milstrip.service import process_text
from tests.fixtures.contract_cases import BASE, PARITY_CASES, SQL_FIELD_ALIASES


@pytest.mark.parametrize("line", PARITY_CASES)
def test_every_exposed_postgresql_field_matches_python(database, line):
    fields = parse_fields(line)
    with database.cursor() as cursor:
        cursor.execute("SELECT * FROM milstrip_app.parse_legacy_mils(%s)", (line,))
        actual = dict(zip((column.name for column in cursor.description), cursor.fetchone()))
    assert len(actual) == 14
    assert actual == {name: getattr(fields, SQL_FIELD_ALIASES.get(name, name)) for name in actual}


@pytest.mark.parametrize("line", [None, "", BASE[:70], BASE + " ", BASE[:79] + "\u00e9", BASE[:79] + "\x01"])
def test_sql_transport_failures(database, line):
    import psycopg

    with pytest.raises(psycopg.errors.InvalidParameterValue):
        with database.transaction():
            database.execute("SELECT * FROM milstrip_app.parse_legacy_mils(%s)", (line,))
    if line is not None and line.startswith("A2"):
        assert process_text(line)[0].status == "REJECTED"


def test_canonical_column_preserves_all_trailing_spaces(database):
    from uuid import uuid4

    request_id = str(uuid4())
    database.execute("INSERT INTO milstrip_app.intake_request(request_id, source_type, source_sha256, source_text) VALUES (%s, 'PASTE', %s, '')", (request_id, "0" * 64))
    canonical = BASE[:71].ljust(80)
    database.execute("INSERT INTO milstrip_app.milstrip_record(record_id, request_id, record_sequence, canonical_record) VALUES (%s, %s, 1, %s)", (request_id, request_id, canonical))
    assert database.execute("SELECT canonical_record FROM milstrip_app.milstrip_record WHERE record_id=%s", (request_id,)).fetchone()[0] == canonical
