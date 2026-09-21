"""Sanitized MILSTRIP examples derived from the local-only SQL prototype.

These are formatted golden cases from the original SQL corpus. Separate
synthetic-but-structurally-equivalent fixtures in tests/test_service.py cover
the punctuation-compressed email evidence added on 2026-08-14. Generic shift
repair still requires additional real evidence; see docs/OPEN_QUESTIONS.md.

REAL_INCOMPLETE_EXAMPLE is also verbatim from that file, but is explicitly
labeled there "--original from 2026-06-18" — i.e. it is the raw, unprocessed
input as DLA sent it, before Shawn's manual correction, not a valid record.
It stops right after RDD (64 characters) with no advice/routing/op/condition
code section at all. Kept separate and used to test that Phase 1 correctly
rejects a truncated real-world record rather than guessing the missing tail.
"""

REAL_EXAMPLES = [
    {
        "line": "A2ASTZ08405015308058  EA00140SL470151000BAJ SC0140MKK      03103  SMSAA  0001657",
        "erp_order": "SL470151000BAJ",
        "nsn": "8405015308058",
        "qty": "00140",
        "priority": "03",
    },
    {
        "line": "A2ASTZ08405015308058  EA00340SL470151000BCG SC1143MKK      03103  SMSAA  0001657",
        "erp_order": "SL470151000BCG",
        "nsn": "8405015308058",
        "qty": "00340",
        "priority": "03",
    },
    {
        "line": "A2ASTZ08405015308034  EA00050SL470151000BDC SC1143MKK      03103  SMSAA",
        "erp_order": "SL470151000BDC",
        "nsn": "8405015308034",
        "qty": "00050",
        "priority": "03",
    },
    {
        "line": "A5ASTZS8405012795607  EA00084SL470150160BYS SC1143MKK   RDO03999  SMSAA  0016489",
        "erp_order": "SL470150160BYS",
        "nsn": "8405012795607",
        "qty": "00084",
        "priority": "03",
    },
    {
        "line": "A5ESTZS7210001195335  EA01500SC010050162200 SC0101M00   HSI06035  SMSAA  0000465",
        "erp_order": "SC010050162200",
        "nsn": "7210001195335",
        "qty": "01500",
        "priority": "06",
    },
    {
        "line": "A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA      ",
        "erp_order": "SL470162240DCV",
        "nsn": "8405016819440",
        "qty": "00520",
        "priority": "15",
    },
    {
        "line": "A2ASTZ08405016819460  EA00420SL470162240DDL SC0141MKK      15     SMSAA      ",
        "erp_order": "SL470162240DDL",
        "nsn": "8405016819460",
        "qty": "00420",
        "priority": "15",
    },
    {
        "line": "A2ASTZ08405016819468  EA00300SL470162240DDQ SC0141MKK      15     SMSAA      ",
        "erp_order": "SL470162240DDQ",
        "nsn": "8405016819468",
        "qty": "00300",
        "priority": "15",
    },
    {
        "line": "A2ASTZ08405016819531  EA00140SL470162240DDT SC0141MKK      15     SMSAA      ",
        "erp_order": "SL470162240DDT",
        "nsn": "8405016819531",
        "qty": "00140",
        "priority": "15",
    },
    {
        "line": "A5ASTZS7210014980306  EA00001V216876209S111 YNSS01ASE 9BEP502999  SMSAA",
        "erp_order": "V216876209S111",
        "nsn": "7210014980306",
        "qty": "00001",
        "priority": "02",
    },
]

REAL_INCOMPLETE_EXAMPLE = {
    "line": "A5ASTZS7210014980279  EA00007N6278661680738 N50408JMQ 9BMP903999",
    "erp_order": "N6278661680738",
    "nsn": "7210014980279",
    "qty": "00007",
}
