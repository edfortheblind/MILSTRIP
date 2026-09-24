"""Explicit application-only schema setup on a privately configured target."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.persistence import provision_schema
from api.profiles import load_runtime_config, target_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', choices=['stage', 'prod'], required=True)
    parser.add_argument('--provision-application-schema', action='store_true')
    parser.add_argument('--confirm-target')
    args = parser.parse_args()
    try:
        profile = load_runtime_config().profiles[args.environment]
        if not profile.connection_string:
            raise ValueError('No connection string')
        target = target_summary(profile)
        print('Target:', target)
        if not args.provision_application_schema:
            print('Preview only. No database connection or schema change performed.')
            print('Provisioning requires --provision-application-schema and --confirm-target with the exact target above.')
            return
        if args.confirm_target != target:
            raise ValueError('Confirmation does not match')
        provision_schema(profile.provider, profile.connection_string, profile.profile_id)
    except Exception:
        raise SystemExit('Not completed. Verify private configuration, target confirmation, authorization and schema compatibility.') from None
    print('Application schema and environment identity verified. Existing rows preserved. Test in Configure-Runtime before enabling.')


if __name__ == '__main__':
    main()
