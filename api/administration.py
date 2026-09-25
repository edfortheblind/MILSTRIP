"""Database configuration commands for authenticated, authorized administrators.

Saving or testing a draft never activates it. Only ApplyRuntimeDraft can change
an active profile, after draining that environment's existing request leases.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import SecretStr, ValidationError

from api.admin_models import (
    AdministrationOperationPayload, ApplyRuntimeDraftPayload, EmptyPayload,
    SaveRuntimeDraftPayload, TestRuntimeDraftPayload, InitializeRuntimeDraftPayload,
)
from api.authorization import AuthorizationError, _authorized, authorize
from api.control import ControlError
from api.persistence import open_repository, provision_schema
from api.profile_manager import ProfileBusy
from api.profiles import (
    ConfigurationError, CredentialBinding, RuntimeConfig, RuntimeProfile,
    normalized_target, target_summary, validate_runtime_config, detect_provider,
)


def profile_from_record(profile_id, record):
    return RuntimeProfile(profile_id, record["provider"], record["label"],
                          record["connection_string"], record["enabled"])


def validate_control_profiles(records, *, require_revisions=False):
    for record in records.values():
        revision = record.get("revision")
        if require_revisions or revision is not None:
            try:
                if str(UUID(revision)) != revision:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise ConfigurationError("Profile revision must be a canonical UUID") from None
    profiles = {key: profile_from_record(key, record) for key, record in records.items()}
    config = RuntimeConfig(1, str(uuid4()), profiles, (
        CredentialBinding("stage", Path("api-credential.json")),
        CredentialBinding("prod", Path("api-prod-credential.json"))))
    validate_runtime_config(config)
    return profiles


def import_runtime_config(store, config):
    """Explicit bootstrap import; never enables control-plane enforcement."""
    validate_runtime_config(config)
    def update(state):
        runtime = state["runtime"]
        if runtime.get("active") or runtime.get("profiles"):
            raise ControlError(409, "Runtime profiles have already been imported")
        runtime.update(active=False, profiles={key: {
            "revision": config.revision, "provider": value.provider,
            "label": value.label, "connection_string": value.connection_string,
            "enabled": value.enabled,
        } for key, value in config.profiles.items()}, drafts={}, tests={})
        return {"imported": True, "active": False}
    return store.mutate(update)


class AdministrationService:
    def __init__(self, store, manager, *, drain_timeout=30.0, test_lifetime_seconds=300, clock=None):
        self.store, self.manager = store, manager
        self.drain_timeout = drain_timeout
        self.test_lifetime = timedelta(seconds=test_lifetime_seconds)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def invoke(self, operation, payload, context):
        models = {"GetRuntimeProfiles": EmptyPayload, "SaveRuntimeDraft": SaveRuntimeDraftPayload,
                  "TestRuntimeDraft": TestRuntimeDraftPayload, "ApplyRuntimeDraft": ApplyRuntimeDraftPayload,
                  "InitializeRuntimeDraft": InitializeRuntimeDraftPayload,
                  "GetAdministrationOperation": AdministrationOperationPayload}
        if operation not in models:
            raise ControlError(400, "Unknown runtime administration operation")
        authorize(context, "runtime.configure", store=self.store)
        try:
            parsed = models[operation].model_validate(payload)
        except ValidationError:
            # Pydantic's default error detail includes the supplied input.
            raise ControlError(422, "Administration payload is invalid") from None
        methods = {"GetRuntimeProfiles": self.get_profiles, "SaveRuntimeDraft": self.save_draft,
                   "TestRuntimeDraft": self.test_draft, "ApplyRuntimeDraft": self.apply_draft,
                   "InitializeRuntimeDraft": self.initialize_draft,
                   "GetAdministrationOperation": self.get_operation}
        try:
            return methods[operation](parsed, context)
        except (ControlError, AuthorizationError):
            raise
        except ConfigurationError:
            raise ControlError(422, "Database configuration is invalid; verify provider, target and TLS settings") from None
        except ProfileBusy:
            raise ControlError(503, "Environment is changing, busy or requires administrator recovery; retain the same command") from None
        except (KeyError, TypeError, ValueError, OSError):
            raise ControlError(503, "Administration state is invalid; contact the host administrator") from None

    @staticmethod
    def _digest(payload):
        values = payload.model_dump()
        values = {key: value.get_secret_value() if isinstance(value, SecretStr) else value
                  for key, value in values.items()}
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()

    @staticmethod
    def _candidate_digest(record):
        return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _runtime(state):
        runtime = state["runtime"]
        if set(runtime.get("profiles", {})) != {"stage", "prod"}:
            raise ControlError(503, "Runtime profiles require explicit initialization")
        validate_control_profiles(runtime["profiles"], require_revisions=True)
        return runtime

    def _existing(self, state, operation, payload, context):
        entry = state["operations"].get(str(payload.command_id))
        if entry is None:
            return None
        if (entry.get("domain") != "runtime" or entry.get("operation") != operation
                or entry.get("actor_id") != context.actor_id or entry.get("profile_id") != context.profile_id
                or entry.get("payload_digest") != self._digest(payload)):
            raise ControlError(409, "Command ID was already used for another operation")
        if entry.get("status") != "COMPLETED":
            raise ControlError(409, "Command is incomplete; inspect its recorded outcome")
        return deepcopy(entry["result"])

    def _record(self, state, operation, payload, context, result):
        state["operations"][str(payload.command_id)] = {
            "domain": "runtime", "capability": "runtime.configure", "operation": operation,
            "actor_id": context.actor_id, "profile_id": context.profile_id,
            "payload_digest": self._digest(payload), "status": "COMPLETED", "result": deepcopy(result),
        }
        state["audit"].append({"event_id": str(uuid4()), "occurred_at": self.clock().isoformat(),
                               "event_type": operation, "actor_id": context.actor_id,
                               "profile_id": context.profile_id, "command_id": str(payload.command_id),
                               "outcome": result.get("status", "SAVED")})
        return result

    def _draft(self, state, payload, context):
        runtime = self._runtime(state)
        draft = runtime["drafts"].get(str(payload.draft_id))
        if draft is None or draft["profile_id"] != context.profile_id:
            raise ControlError(404, "Configuration draft was not found")
        if draft["revision"] != str(payload.draft_revision):
            raise ControlError(409, "Configuration draft revision changed")
        if draft["base_revision"] != runtime["profiles"][context.profile_id]["revision"]:
            raise ControlError(409, "The active configuration changed; create a new draft")
        return draft

    def get_profiles(self, payload, context):
        state = self.store.read()
        _authorized(state, context, "runtime.configure")
        runtime = self._runtime(state)
        result = []
        for key, record in runtime["profiles"].items():
            result.append({"profile_id": key, "revision": record["revision"],
                           "provider": record["provider"], "label": record["label"],
                           "enabled": record["enabled"], "target": target_summary(profile_from_record(key, record)),
                           "runtime_state": self.manager.status(key) if self.manager else "UNAVAILABLE",
                           "editable": key == context.profile_id})
        return {"active": bool(runtime.get("active")), "profiles": result}

    def save_draft(self, payload, context):
        def update(state):
            _authorized(state, context, "runtime.configure")
            replay = self._existing(state, "SaveRuntimeDraft", payload, context)
            if replay is not None:
                return replay
            runtime = self._runtime(state)
            previous = runtime["profiles"][context.profile_id]
            if previous["revision"] != str(payload.expected_active_revision):
                raise ControlError(409, "The active configuration changed; reload it")
            replacement = payload.replacement_connection_string
            replacement = replacement.get_secret_value() if replacement is not None else ""
            provider = (detect_provider(replacement) if replacement else previous["provider"]) if payload.provider == "auto" else payload.provider
            if provider != previous["provider"] and not replacement and previous["connection_string"]:
                raise ControlError(422, "Changing providers requires a replacement connection string")
            candidate = {"provider": provider, "label": payload.label.strip(),
                         "connection_string": replacement or previous["connection_string"],
                         "enabled": payload.enabled}
            records = {**runtime["profiles"], context.profile_id: candidate}
            validate_control_profiles(records)
            draft_id, revision = str(uuid4()), str(uuid4())
            runtime["drafts"][draft_id] = {
                "profile_id": context.profile_id, "revision": revision,
                "base_revision": previous["revision"], "candidate": candidate,
                "actor_id": context.actor_id, "created_at": self.clock().isoformat(),
            }
            result = {"draft_id": draft_id, "draft_revision": revision,
                      "base_revision": previous["revision"], "status": "SAVED",
                      "target": target_summary(profile_from_record(context.profile_id, candidate))}
            return self._record(state, "SaveRuntimeDraft", payload, context, result)
        return self.store.mutate(update)

    def initialize_draft(self, payload, context):
        # Serialize preparation with all control changes. The database operation
        # is additive and repeatable if a crash precedes the durable result.
        def update(state):
            _authorized(state, context, "runtime.configure")
            replay = self._existing(state, "InitializeRuntimeDraft", payload, context)
            if replay is not None:
                return replay
            runtime = self._runtime(state)
            if (not runtime.get("active") or not state["security"].get("enforced")
                    or self.manager is None or self.manager.control_path != self.store.path):
                raise ControlError(409, "Activate broker-only administration before initializing a database")
            if runtime["profiles"][context.profile_id]["enabled"]:
                raise ControlError(409, "Disable this environment before initializing its database")
            running = self.manager.snapshot(context.profile_id)
            if running.profile.enabled or running.revision != runtime["profiles"][context.profile_id]["revision"]:
                raise ControlError(409, "Running configuration differs from saved state; recover before initialization")
            draft = self._draft(state, payload, context)
            profile = profile_from_record(context.profile_id, draft["candidate"])
            if not profile.connection_string or payload.confirm_target != target_summary(profile):
                raise ControlError(412, "Confirm the exact saved draft target before initialization")
            try:
                provision_schema(profile.provider, profile.connection_string, context.profile_id)
            except Exception:
                raise ControlError(503, "Database initialization unconfirmed; check access and schema compatibility, then retry the same command") from None
            result = {"status": "INITIALIZED", "profile_id": context.profile_id,
                      "target": target_summary(profile)}
            return self._record(state, "InitializeRuntimeDraft", payload, context, result)
        return self.store.mutate(update)

    def test_draft(self, payload, context):
        state = self.store.read()
        _authorized(state, context, "runtime.configure")
        replay = self._existing(state, "TestRuntimeDraft", payload, context)
        if replay is not None:
            return replay
        draft = self._draft(state, payload, context)
        profile = profile_from_record(context.profile_id, draft["candidate"])
        if not profile.connection_string:
            raise ControlError(422, "Enter a database connection string before testing")
        passed = False
        try:
            with open_repository(profile.provider, profile.connection_string) as repository:
                if repository.health():
                    repository.validate_identity(profile.profile_id)
                    repository.validate_workflow_tracking()
                    passed = True
        except Exception:
            pass  # Driver messages can contain credentials; never return them.
        def update(current):
            _authorized(current, context, "runtime.configure")
            replay = self._existing(current, "TestRuntimeDraft", payload, context)
            if replay is not None:
                return replay
            latest = self._draft(current, payload, context)
            if latest != draft:
                raise ControlError(409, "Configuration changed while its test was running")
            test_id, checked_at = str(uuid4()), self.clock()
            expires_at = checked_at + self.test_lifetime
            current["runtime"]["tests"][test_id] = {
                "draft_id": str(payload.draft_id), "draft_revision": str(payload.draft_revision),
                "profile_id": context.profile_id, "base_revision": draft["base_revision"],
                "actor_id": context.actor_id,
                "candidate_digest": self._candidate_digest(draft["candidate"]),
                "passed": passed, "checked_at": checked_at.isoformat(), "expires_at": expires_at.isoformat(),
            }
            result = {"test_id": test_id, "status": "PASSED" if passed else "FAILED",
                      "checked_at": checked_at.isoformat(), "expires_at": expires_at.isoformat()}
            if not passed:
                result["detail"] = "Check database access, certificate trust, application schema, environment identity and intake workflow tracking"
            return self._record(current, "TestRuntimeDraft", payload, context, result)
        return self.store.mutate(update)

    def _check_apply(self, state, payload, context):
        runtime = self._runtime(state)
        if not runtime.get("active") or not state["security"].get("enforced"):
            raise ControlError(409, "Runtime administration is not activated; explicit security cutover is required")
        if self.manager is None or self.manager.control_path != self.store.path:
            raise ControlError(409, "Restart the API after security cutover before applying configuration")
        draft = self._draft(state, payload, context)
        previous = runtime["profiles"][context.profile_id]
        if previous["revision"] != str(payload.expected_active_revision):
            raise ControlError(409, "The active configuration changed; reload it")
        candidate = profile_from_record(context.profile_id, draft["candidate"])
        old_profile = profile_from_record(context.profile_id, previous)
        if old_profile.enabled and normalized_target(candidate) != normalized_target(old_profile):
            raise ControlError(409, "Disable this environment before moving its database target")
        if candidate.enabled:
            receipt = runtime["tests"].get(str(payload.test_id))
            if (receipt is None or not receipt["passed"] or receipt["profile_id"] != context.profile_id
                    or receipt.get("actor_id") != context.actor_id
                    or receipt["draft_id"] != str(payload.draft_id)
                    or receipt["draft_revision"] != str(payload.draft_revision)
                    or receipt["base_revision"] != previous["revision"]
                    or receipt["candidate_digest"] != self._candidate_digest(draft["candidate"])
                    or datetime.fromisoformat(receipt["expires_at"]) <= self.clock()):
                raise ControlError(412, "Test this exact configuration successfully before applying it")
        validate_control_profiles({**runtime["profiles"], context.profile_id: draft["candidate"]})
        return candidate, previous["revision"]

    def apply_draft(self, payload, context):
        state = self.store.read()
        replay = self._existing(state, "ApplyRuntimeDraft", payload, context)
        if replay is not None:
            return replay
        candidate, previous_revision = self._check_apply(state, payload, context)
        if self.manager.snapshot(context.profile_id).revision != previous_revision:
            raise ControlError(409, "Running configuration differs from its saved revision; restart for recovery")
        with self.manager.drain(context.profile_id, self.drain_timeout):
            def update(current):
                _authorized(current, context, "runtime.configure")
                replay = self._existing(current, "ApplyRuntimeDraft", payload, context)
                if replay is not None:
                    return replay
                latest, _ = self._check_apply(current, payload, context)
                if latest != candidate:
                    raise ControlError(409, "Configuration changed before activation")
                revision = str(uuid4())
                current["runtime"]["profiles"][context.profile_id] = {
                    **current["runtime"]["drafts"][str(payload.draft_id)]["candidate"], "revision": revision}
                result = {"status": "APPLIED", "profile_id": context.profile_id,
                          "revision": revision, "enabled": candidate.enabled,
                          "target": target_summary(candidate)}
                return self._record(current, "ApplyRuntimeDraft", payload, context, result)
            try:
                result = self.store.mutate(update)
            except Exception:
                # A write can have an uncertain outcome. Never reopen the old
                # destination unless the durable record proves it is unchanged.
                try:
                    unchanged = self.store.read()["runtime"]["profiles"][context.profile_id]["revision"] == previous_revision
                except Exception:
                    unchanged = False
                if not unchanged:
                    self.manager.block(context.profile_id)
                raise
            try:
                self.manager.publish(candidate, result["revision"])
            except Exception:
                self.manager.block(context.profile_id)
                raise ControlError(503, "Configuration was saved; this environment requires API restart for recovery") from None
            return result

    def get_operation(self, payload, context):
        state = self.store.read()
        _authorized(state, context, "runtime.configure")
        entry = state["operations"].get(str(payload.command_id))
        if (entry is None or entry.get("domain") != "runtime"
                or entry.get("profile_id") != context.profile_id):
            raise ControlError(404, "Administration operation was not found")
        return {"command_id": str(payload.command_id), "status": entry["status"],
                "result": deepcopy(entry["result"])}
