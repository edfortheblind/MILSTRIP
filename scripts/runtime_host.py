"""Host preflight and legacy-editor boundary; no database connection is made."""
import argparse
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.control import ControlError, ControlStore
from api.auth import load_verifier
from api.profiles import ConfigurationError, load_runtime_config, save_runtime_config
from api.runtime import lifespan


def require_legacy_editor(store=None):
    """Reject obsolete host edits after the one-way administration cutover."""
    try:
        store = store or ControlStore()
        if store.exists():
            state = store.read()
            if state['runtime'].get('active') or state['security'].get('enforced'):
                raise ConfigurationError('Host configuration is closed. Use Database configuration in the MILSTRIP app.')
    except ControlError:
        raise ConfigurationError('Administration state is unavailable. Host configuration remains closed.') from None


def save_legacy_configuration(config, path, *, expected_revision=None):
    """Serialize a stale-open editor against explicit control activation."""
    try:
        store = ControlStore()
        descriptor = store._lock()
        try:
            require_legacy_editor(store)
            return save_runtime_config(config, path, expected_revision=expected_revision)
        finally:
            store._unlock(descriptor)
    except ControlError:
        raise ConfigurationError('Administration state is unavailable or busy. Host configuration was not saved.') from None


async def check_startup():
    app = SimpleNamespace(state=SimpleNamespace())
    async with lifespan(app):
        if app.state.runtime is None:
            raise ConfigurationError('Runtime configuration is unavailable')
        store = ControlStore()
        state = store.read() if store.exists() else None
        if state is not None and state['security'].get('enforced') and not app.state.control_active:
            raise ConfigurationError('Control activation is incomplete')
        if app.state.control_active:
            usernames = set(state['security']['legacy_usernames'])
            try:
                for binding in app.state.runtime.config.bindings:
                    verifier = load_verifier(binding.credential_file, binding.profile_id)
                    if verifier.username in usernames:
                        raise ValueError
                    usernames.add(verifier.username)
            except ValueError:
                raise ConfigurationError('Broker authentication is unavailable or uses conflicting identities') from None
        return 'control' if app.state.control_active else 'legacy'


def configured_profile(profile_id):
    """Read the selected authority for explicit host provisioning previews."""
    from api.administration import validate_control_profiles
    store = ControlStore()
    if store.exists():
        state = store.read()
        if state['runtime'].get('active') or state['security'].get('enforced'):
            if not state['runtime'].get('active') or not state['security'].get('enforced'):
                raise ConfigurationError('Control activation is incomplete')
            return validate_control_profiles(state['runtime']['profiles'], require_revisions=True)[profile_id]
    return load_runtime_config().profiles[profile_id]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check-startup', 'check-legacy-editor'])
    args = parser.parse_args(argv)
    try:
        if args.action == 'check-startup':
            authority = asyncio.run(check_startup())
            print('Active control configuration verified.' if authority == 'control' else 'Legacy runtime configuration verified.')
        else:
            require_legacy_editor()
    except Exception:
        print('Host check failed. Verify private configuration and the selected authority; active control settings must be managed in the app.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
