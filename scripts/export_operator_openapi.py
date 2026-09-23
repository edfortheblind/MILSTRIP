"""Export or check the deterministic local API schema without connecting to a DB."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.app import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "docs/operator-api.openapi.json"
    content = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            print("OpenAPI artifact differs; run scripts/export_operator_openapi.py")
            return 1
        print("OpenAPI artifact matches runtime schema")
    else:
        target.write_text(content, encoding="utf-8", newline="\n")
        print("Exported docs/operator-api.openapi.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
