"""An immutable startup configuration; no request can choose its database."""
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, replace

import psycopg
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from api.auth import CredentialVerifier, load_verifier
from api.persistence import open_repository, ProviderMismatch, RepositoryConflict, RepositoryNotFound
from api.profiles import ConfigurationError, CredentialBinding, RuntimeConfig, load_runtime_config
from api.profile_manager import ProfileBusy, ProfileManager, SingleWorkerLease


@dataclass(frozen=True)
class RequestContext:
    actor: str
    profile_id: str
    revision: str


@dataclass(frozen=True)
class RuntimeSnapshot:
    config: RuntimeConfig
    verifiers: tuple[CredentialVerifier, ...]


def load_runtime():
    config = load_runtime_config()
    verifiers = tuple(load_verifier(binding.credential_file, binding.profile_id) for binding in config.bindings)
    if len({v.username for v in verifiers}) != len(verifiers):
        raise ConfigurationError("Stage and Prod require different API usernames")
    return RuntimeSnapshot(config, verifiers)


@asynccontextmanager
async def lifespan(app):
    app.state.runtime = None
    app.state.profile_manager = None
    app.state.control_active = False
    instance_lock = None
    try:
        from api.control import ControlStore
        from api.administration import validate_control_profiles
        store = ControlStore()
        state = store.read() if store.exists() else None
        if state is not None and state["runtime"].get("active"):
            if not state["security"].get("enforced"):
                raise RuntimeError("Active control profiles require explicit security enforcement")
            instance_lock = SingleWorkerLease(store.path)
            instance_lock.__enter__()
            state = store.read()
            if not state["runtime"].get("active") or not state["security"].get("enforced"):
                raise RuntimeError("Control activation changed during API startup")
            # Control profiles are the sole database authority after cutover.
            # Legacy runtime.json and its direct-call verifiers are not read.
            profiles = validate_control_profiles(state["runtime"]["profiles"], require_revisions=True)
            revisions = {key: record["revision"] for key, record in state["runtime"]["profiles"].items()}
            bindings = tuple(CredentialBinding(key, store.path.parent / binding["credential_file"])
                             for key, binding in state["security"]["brokers"].items())
            config = RuntimeConfig(1, state["revision"], profiles, bindings)
            app.state.runtime = RuntimeSnapshot(config, ())
            app.state.profile_manager = ProfileManager(profiles, revisions, control_path=store.path)
            app.state.control_active = True
        else:
            try:
                app.state.runtime = load_runtime()
            except (ConfigurationError, ValueError):
                pass  # Fail closed without exposing private configuration.
            if app.state.runtime is not None:
                config = app.state.runtime.config
                app.state.profile_manager = ProfileManager(config.profiles,
                    {key: config.revision for key in config.profiles})
        yield
    finally:
        app.state.runtime = None
        app.state.profile_manager = None
        app.state.control_active = False
        if instance_lock:
            instance_lock.__exit__(None, None, None)


def snapshot_for(request):
    pinned = getattr(request.state, "runtime_snapshot", None)
    if pinned is not None:
        return pinned
    snapshot = getattr(request.app.state, "runtime", None)
    if snapshot is None:
        raise HTTPException(503, "API runtime is not configured; contact the administrator")
    return snapshot


def profile_for(request):
    pinned = getattr(request.state, "profile_lease", None)
    if pinned is not None:
        return pinned.profile
    snapshot = snapshot_for(request)
    context = getattr(request.state, "context", None)
    if context is None or context.revision != snapshot.config.revision:
        raise HTTPException(503, "API configuration changed; reconnect")
    return snapshot.config.profiles[context.profile_id]


@contextmanager
def business_scope(request, profile_id):
    """Pin the environment before dispatch, including its commit/rollback."""
    manager = getattr(request.app.state, "profile_manager", None)
    if manager is None:
        raise HTTPException(503, "API runtime is not configured")
    previous_lease = getattr(request.state, "profile_lease", None)
    previous_snapshot = getattr(request.state, "runtime_snapshot", None)
    if previous_lease is not None:
        if previous_lease.profile.profile_id != profile_id:
            raise HTTPException(403, "Request environment cannot change")
        yield previous_lease
        return
    try:
        with manager.lease(profile_id) as pinned:
            base = request.app.state.runtime
            profiles = dict(base.config.profiles)
            profiles[profile_id] = pinned.profile
            request.state.profile_lease = pinned
            request.state.runtime_snapshot = replace(base, config=replace(
                base.config, revision=pinned.revision, profiles=profiles))
            try:
                yield pinned
            finally:
                request.state.profile_lease = previous_lease
                request.state.runtime_snapshot = previous_snapshot
    except ProfileBusy:
        raise HTTPException(503, "Environment is changing or requires recovery", headers={"Retry-After": "5"}) from None


@contextmanager
def repository(request):
    broker = getattr(request.state, "broker_context", None)
    context = broker or getattr(request.state, "context", None)
    if context is None:
        raise HTTPException(503, "Authenticated environment is unavailable")
    with business_scope(request, context.profile_id) as pinned:
        profile = pinned.profile
        if not profile.enabled:
            raise HTTPException(503, "This environment is disabled; contact the administrator")
        try:
            with open_repository(profile.provider, profile.connection_string) as value:
                value.validate_identity(profile.profile_id)
                yield value
        except RepositoryNotFound as error:
            raise HTTPException(404, str(error)) from None
        except RepositoryConflict as error:
            raise HTTPException(409, str(error)) from None
        except ProviderMismatch:
            raise HTTPException(503, "Database environment or schema does not match the configured profile") from None
        except (SQLAlchemyError, psycopg.Error):
            raise HTTPException(503, "Database unavailable") from None
