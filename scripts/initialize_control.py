"""Host-only bootstrap; requires reviewed private directory evidence."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.auth import load_verifier
from api.control import ControlError, ControlStore
from api.control_bootstrap import bootstrap_state, enforce_security
from api.profiles import load_runtime_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-manifest", type=Path)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--enforce-broker-only", action="store_true")
    parser.add_argument("--expected-revision")
    args = parser.parse_args()
    try:
        store = ControlStore()
        if args.enforce_broker_only:
            if args.initialize or not args.expected_revision:
                raise ControlError(422, "Enforcement requires only the reviewed current revision")
            state = store.read()
            usernames = set(state["security"]["legacy_usernames"])
            for binding in state["security"]["brokers"].values():
                verifier = load_verifier(store.path.parent / binding["credential_file"], binding["profile_id"])
                if verifier.username in usernames:
                    raise ControlError(422, "Broker identities must be distinct from existing shared identities")
                usernames.add(verifier.username)
            result = enforce_security(store, args.expected_revision)
        elif args.initialize and args.verified_manifest:
            manifest_path = args.verified_manifest.absolute()
            if manifest_path.parent != store.path.parent or manifest_path.is_symlink():
                raise ControlError(422, "The reviewed manifest must be in the same private directory")
            config = load_runtime_config()
            legacy = [load_verifier(binding.credential_file, binding.profile_id).username for binding in config.bindings]
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            state = bootstrap_state(manifest, legacy)
            # Build the complete inactive authority before the one atomic
            # create. A failed write must never strand a half-initialized file.
            state["runtime"]["profiles"] = {key: {
                "revision": config.revision, "provider": profile.provider,
                "label": profile.label, "connection_string": profile.connection_string,
                "enabled": profile.enabled,
            } for key, profile in config.profiles.items()}
            store.create(state)
            result = {"initialized": True, "seeded_members": 6, "enforced": False,
                      "next": "Verify broker credentials, flow identity and platform sharing before explicit cutover"}
        else:
            result = {"changed": False, "next": "Provide --initialize --verified-manifest using reviewed private directory evidence"}
    except Exception:
        print("Control setup did not complete. Check reviewed identities, private storage, sharing and revision.")
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
