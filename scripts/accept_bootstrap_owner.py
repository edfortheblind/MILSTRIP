"""Preview or accept one protected Owner from reviewed native permission captures."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.bootstrap_owner_acceptance import OWNER_FILES, accept_bootstrap_owner, owner_capture_spec
from api.control import ControlError, ControlStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", choices=list(OWNER_FILES), required=True)
    parser.add_argument("--control-file", type=Path)
    parser.add_argument("--expected-revision")
    parser.add_argument("--capture-spec", action="store_true", help="Print validated fixed resources for the read-only native capture script")
    parser.add_argument("--accept-owner", action="store_true", help="Apply only this initial protected Owner membership; omitted means preview")
    args = parser.parse_args(argv)
    try:
        store = ControlStore(args.control_file)
        if args.capture_spec:
            if args.accept_owner or args.expected_revision:
                raise ControlError(422, "Capture specification is a separate read-only operation")
            result = owner_capture_spec(store, args.owner)
        else:
            if not args.expected_revision:
                raise ControlError(422, "Preview and acceptance require the reviewed current control revision")
            result = accept_bootstrap_owner(store, args.expected_revision, args.owner, apply=args.accept_owner)
    except ControlError as error:
        print(error.message, file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
