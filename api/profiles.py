"""Immutable database destinations loaded once when the API starts.

Connection strings and credential verifiers live only in the access-restricted
``.cred`` directory. Saving this file prepares the next API restart; it never
changes a running request's destination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType
from typing import Mapping
from uuid import UUID, uuid4

from psycopg.conninfo import conninfo_to_dict


PROFILE_IDS = frozenset({"stage", "prod"})
PROVIDERS = frozenset({"postgresql", "sqlserver"})
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", ".", "(local)"})


class ConfigurationError(ValueError):
    """A safe, fixed message suitable for the administrator screen."""


@dataclass(frozen=True)
class RuntimeProfile:
    profile_id: str
    provider: str
    label: str
    connection_string: str = field(repr=False)
    enabled: bool = False


@dataclass(frozen=True)
class CredentialBinding:
    profile_id: str
    credential_file: Path


@dataclass(frozen=True)
class RuntimeConfig:
    version: int
    revision: str
    profiles: Mapping[str, RuntimeProfile]
    bindings: tuple[CredentialBinding, ...]

    def __post_init__(self):
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))
        object.__setattr__(self, "bindings", tuple(self.bindings))


def runtime_config_path() -> Path:
    override = os.getenv("MILSTRIP_RUNTIME_CONFIG_FILE")
    return Path(override) if override else Path(__file__).resolve().parents[1] / ".cred" / "runtime.json"


def _host(value: str) -> str:
    if value.strip().lower() in _LOCAL_HOSTS:
        return "localhost"
    result = value.strip().lower().rstrip(".").strip("[]")
    try:
        if ipaddress.ip_address(result).is_loopback:
            return "localhost"
    except ValueError:
        pass
    return "localhost" if result in _LOCAL_HOSTS else result


def _postgres_target(connection_string: str) -> tuple[str, str, str]:
    try:
        options = conninfo_to_dict(connection_string)
    except Exception:
        raise ConfigurationError("PostgreSQL connection string is invalid.") from None
    if any(key in options for key in ("service", "servicefile", "passfile", "hostaddr", "options")):
        raise ConfigurationError("PostgreSQL service files, override files and session options are not supported.")
    host, database = options.get("host", ""), options.get("dbname", "")
    if (not host or not database or any(c in host for c in ",/\\")
            or any(ord(c) < 32 for c in host + database)):
        raise ConfigurationError("Specify one PostgreSQL host and a database name.")
    try:
        port = int(options.get("port", "5432"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ConfigurationError("PostgreSQL port must be between 1 and 65535.") from None
    normalized_host = _host(host)
    if normalized_host != "localhost" and options.get("sslmode") != "verify-full":
        raise ConfigurationError("Remote PostgreSQL requires sslmode=verify-full and a trusted server certificate.")
    return normalized_host, str(port), database


def _odbc_attributes(connection_string: str) -> dict[str, str]:
    """Parse ODBC braces and escaped closing braces without exposing values."""
    attributes: dict[str, str] = {}
    position = 0
    length = len(connection_string)
    aliases = {"data source": "server", "address": "server", "addr": "server",
               "network address": "server", "initial catalog": "database",
               "user id": "uid", "password": "pwd", "integrated security": "trusted_connection"}
    while position < length:
        while position < length and connection_string[position] in " ;\t":
            position += 1
        if position == length:
            break
        match = re.match(r"([^=;]+)=", connection_string[position:])
        if match is None:
            raise ConfigurationError("SQL Server connection string is invalid.")
        key = match[1].strip().lower()
        key = aliases.get(key, key)
        position += match.end()
        while position < length and connection_string[position] == " ":
            position += 1
        if position < length and connection_string[position] == "{":
            position += 1
            characters: list[str] = []
            while position < length:
                character = connection_string[position]
                position += 1
                if character == "}":
                    if position < length and connection_string[position] == "}":
                        characters.append("}")
                        position += 1
                    else:
                        break
                else:
                    characters.append(character)
            else:
                raise ConfigurationError("SQL Server connection string has an unclosed value.")
            value = "".join(characters)
            while position < length and connection_string[position] == " ":
                position += 1
            if position < length and connection_string[position] != ";":
                raise ConfigurationError("SQL Server connection string is invalid.")
        else:
            end = connection_string.find(";", position)
            if end == -1:
                end = length
            value = connection_string[position:end].strip()
            position = end
        if not key or key in attributes:
            raise ConfigurationError("SQL Server connection string contains a duplicate attribute.")
        attributes[key] = value
        if position < length:
            position += 1
    return attributes


def _sqlserver_target(connection_string: str) -> tuple[str, str, str]:
    options = _odbc_attributes(connection_string)
    allowed = {"driver", "server", "database", "uid", "pwd", "authentication",
               "trusted_connection", "encrypt", "trustservercertificate",
               "connection timeout", "connect timeout", "app", "applicationintent"}
    if set(options) - allowed:
        raise ConfigurationError("SQL Server connection string contains an unsupported attribute.")
    if options.get("driver", "").lower() not in {
        "odbc driver 17 for sql server", "odbc driver 18 for sql server"
    }:
        raise ConfigurationError("Use Microsoft ODBC Driver 17 or 18 for SQL Server.")
    if (options.get("encrypt", "").lower() not in {"yes", "mandatory", "strict"}
            or options.get("trustservercertificate", "").lower() != "no"):
        raise ConfigurationError("SQL Server requires Encrypt=yes and TrustServerCertificate=no.")
    server, database = options.get("server", "").strip(), options.get("database", "").strip()
    if (not server or not database or any(ord(c) < 32 for c in server + database)
            or any(c in server for c in "/;=")):
        raise ConfigurationError("Specify one SQL Server host and a database name.")
    server = server.lower()
    if server.startswith("tcp:"):
        server = server[4:]
    elif ":" in server and not server.startswith("["):
        raise ConfigurationError("Use a SQL Server TCP host or named instance.")
    parts = server.rsplit(",", 1)
    try:
        port = int(parts[1]) if len(parts) == 2 else 1433
        if not 1 <= port <= 65535 or "," in parts[0]:
            raise ValueError
    except ValueError:
        raise ConfigurationError("SQL Server TCP port must be between 1 and 65535.") from None
    return _host(parts[0]), str(port), database.casefold()


def normalized_target(profile: RuntimeProfile) -> tuple[str, str, str, str] | None:
    if profile.provider not in PROVIDERS:
        raise ConfigurationError("Database provider is invalid.")
    if not profile.connection_string:
        return None
    target = (_postgres_target(profile.connection_string) if profile.provider == "postgresql"
              else _sqlserver_target(profile.connection_string))
    return (profile.provider, *target)


def target_summary(profile: RuntimeProfile) -> str:
    """Return host/database only, never an identity, password or complete DSN."""
    target = normalized_target(profile)
    if target is None:
        return "Not configured"
    provider, host, port, database = target
    return f"{provider} | {host}:{port} | {database}"


def validate_runtime_config(config: RuntimeConfig) -> RuntimeConfig:
    if type(config.version) is not int or config.version != 1:
        raise ConfigurationError("Unsupported runtime configuration version.")
    try:
        if str(UUID(config.revision)) != config.revision:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ConfigurationError("Runtime configuration revision must be a canonical UUID.") from None
    if set(config.profiles) != PROFILE_IDS:
        raise ConfigurationError("Configure exactly the Stage and Prod profiles.")
    targets = []
    for profile_id, profile in config.profiles.items():
        if (not isinstance(profile, RuntimeProfile) or profile.profile_id != profile_id
                or profile.provider not in PROVIDERS or type(profile.enabled) is not bool):
            raise ConfigurationError("Profile identity, provider or enabled state is invalid.")
        if (not isinstance(profile.label, str) or not profile.label.strip() or len(profile.label) > 80
                or any(ord(c) < 32 for c in profile.label)):
            raise ConfigurationError("Profile labels must contain 1-80 visible characters.")
        if (not isinstance(profile.connection_string, str) or len(profile.connection_string) > 8192
                or any(ord(c) < 32 for c in profile.connection_string)):
            raise ConfigurationError("Connection strings must be a single line of at most 8192 characters.")
        if profile.enabled and not profile.connection_string:
            raise ConfigurationError("An enabled profile requires a connection string.")
        target = normalized_target(profile)
        if target:
            targets.append(target)
    if len(set(targets)) != len(targets):
        raise ConfigurationError("Stage and Prod must use different databases.")
    if (len(config.bindings) != 2 or {b.profile_id for b in config.bindings} != PROFILE_IDS):
        raise ConfigurationError("Stage and Prod each require one credential binding.")
    paths = []
    for binding in config.bindings:
        path = binding.credential_file
        if (not isinstance(path, Path) or path.suffix.lower() != ".json"
                or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\.json", path.name)
                or (path.is_absolute() and path.parent.name != ".cred")
                or (not path.is_absolute() and path.parent != Path("."))):
            raise ConfigurationError("Credential files must be JSON files directly inside .cred.")
        paths.append(path.name.casefold())
    if len(set(paths)) != len(paths):
        raise ConfigurationError("Stage and Prod must use different credential files.")
    return config


def _storage_path(path: Path) -> Path:
    path = Path(path).absolute()
    if path.parent.name != ".cred" or path.suffix.lower() != ".json":
        raise ConfigurationError("Runtime configuration must be a JSON file inside .cred.")
    if path.is_symlink() or path.parent.is_symlink():
        raise ConfigurationError("Private configuration cannot use symbolic links.")
    return path


def load_runtime_config(path: Path | None = None) -> RuntimeConfig:
    path = _storage_path(path or runtime_config_path())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if set(raw) != {"version", "revision", "profiles", "bindings"}:
            raise ValueError
        profiles = {}
        for profile_id, values in raw["profiles"].items():
            if set(values) != {"provider", "label", "connection_string", "enabled"}:
                raise ValueError
            profiles[profile_id] = RuntimeProfile(profile_id=profile_id, **values)
        bindings = []
        for value in raw["bindings"]:
            if set(value) != {"profile_id", "credential_file"}:
                raise ValueError
            filename = Path(value["credential_file"])
            if filename.is_absolute() or filename.parent != Path("."):
                raise ValueError
            bindings.append(CredentialBinding(value["profile_id"], path.parent / filename))
        result = RuntimeConfig(raw["version"], raw["revision"], profiles, tuple(bindings))
        return validate_runtime_config(result)
    except ConfigurationError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise ConfigurationError("Runtime configuration could not be loaded; check its format and private storage.") from None


def save_runtime_config(config: RuntimeConfig, path: Path | None = None, *,
                        expected_revision: str | None = None) -> RuntimeConfig:
    """Atomically save a validated snapshot, returning its new revision.

    A stale editor cannot silently overwrite a newer saved revision. ACLs are
    prepared by Configure-Runtime.ps1 before this function is called.
    """
    validate_runtime_config(config)
    path = _storage_path(path or runtime_config_path())
    if not path.parent.is_dir():
        raise ConfigurationError("Run Configure-Runtime.ps1 to prepare private storage first.")
    saved = RuntimeConfig(1, str(uuid4()), config.profiles, config.bindings)
    for binding in saved.bindings:
        if binding.credential_file.is_absolute() and binding.credential_file.parent != path.parent:
            raise ConfigurationError("Credential bindings must stay in the configuration's .cred directory.")
    raw = {"version": saved.version, "revision": saved.revision,
           "profiles": {key: {"provider": value.provider, "label": value.label,
                               "connection_string": value.connection_string, "enabled": value.enabled}
                        for key, value in saved.profiles.items()},
           "bindings": [{"profile_id": b.profile_id, "credential_file": b.credential_file.name}
                        for b in saved.bindings]}
    temporary = None
    lock_path = path.with_suffix(".lock")
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        raise ConfigurationError("Configuration is being saved elsewhere or its lock needs administrator attention.") from None
    try:
        if path.exists() and load_runtime_config(path).revision != expected_revision:
            raise ConfigurationError("Configuration changed since it was opened. Reopen the configuration screen.")
        if not path.exists() and expected_revision is not None:
            raise ConfigurationError("Configuration was removed since it was opened. Reopen the configuration screen.")
        descriptor, temporary = tempfile.mkstemp(prefix="runtime-", suffix=".tmp", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(raw, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        raise ConfigurationError("Configuration could not be saved in private storage.") from None
    finally:
        os.close(lock_descriptor)
        for leftover in (temporary, lock_path):
            try:
                if leftover and os.path.exists(leftover):
                    os.unlink(leftover)
            except OSError:
                pass
    return load_runtime_config(path)


def empty_runtime_config(path: Path | None = None) -> RuntimeConfig:
    path = _storage_path(path or runtime_config_path())
    return RuntimeConfig(1, str(uuid4()), {
        name: RuntimeProfile(name, "postgresql", f"MILSTRIP {name.title()}", "", False)
        for name in ("stage", "prod")
    }, (CredentialBinding("stage", path.parent / "api-credential.json"),
        CredentialBinding("prod", path.parent / "api-prod-credential.json")))
