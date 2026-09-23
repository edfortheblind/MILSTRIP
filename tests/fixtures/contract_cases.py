"""Parser parity cases, including branches absent from the original smoke test."""
from tests.fixtures.real_examples import REAL_EXAMPLES

BASE = REAL_EXAMPLES[0]["line"].ljust(80)
PARITY_CASES = [case["line"] for case in REAL_EXAMPLES] + [
    "AF6" + BASE[3:], BASE.lower(), BASE[:43] + "A" + BASE[44:],
    BASE[:7] + "ABCDEFGHIJKLMNO" + BASE[22:],
    BASE[:50] + "A" + BASE[51:], BASE[:50] + "J" + BASE[51:],
    BASE[:24] + "1950M" + BASE[29:], BASE[:71],
]
SQL_FIELD_ALIASES = {"prioritycode": "priority_cd", "advicecode": "advice_cd"}
