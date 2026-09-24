"""An immutable startup configuration; no request can choose its database."""
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass

import psycopg
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from api.auth import CredentialVerifier, load_verifier
from api.persistence import open_repository, ProviderMismatch, RepositoryConflict, RepositoryNotFound
from api.profiles import ConfigurationError, RuntimeConfig, load_runtime_config


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
    try:
        app.state.runtime = load_runtime()
    except (ConfigurationError, ValueError):
        pass  # Fail closed without exposing private configuration.
    yield
    app.state.runtime = None


def snapshot_for(request):
    snapshot = getattr(request.app.state, "runtime", None)
    if snapshot is None:
        raise HTTPException(503, "API runtime is not configured; contact the administrator")
    return snapshot


def profile_for(request):
    snapshot = snapshot_for(request)
    context = getattr(request.state, "context", None)
    if context is None or context.revision != snapshot.config.revision:
        raise HTTPException(503, "API configuration changed; reconnect")
    return snapshot.config.profiles[context.profile_id]


@contextmanager
def repository(request):
    profile = profile_for(request)
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
