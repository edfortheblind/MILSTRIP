"""Preview or accept Ed's initial app membership from reviewed private readbacks."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.bootstrap_acceptance import APP_CAPTURE, FLOW_CAPTURE, accept_bootstrap_member
from api.control import ControlError, ControlStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--accept-ed", action="store_true", help="Apply the reviewed Ed-only membership change; omitted means preview")
    args = parser.parse_args(argv)
    try:
        store = ControlStore()
        result = accept_bootstrap_member(store, args.expected_revision, store.path.parent / APP_CAPTURE,
                                        store.path.parent / FLOW_CAPTURE, apply=args.accept_ed)
    except ControlError as error:
        print(error.message, file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
