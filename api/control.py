"""One private, locked, atomic authority for membership and administration."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4


class ControlError(Exception):
    def __init__(self, status_code, message):
        self.status_code, self.message = status_code, message
        super().__init__(message)


def control_path():
    return Path(os.getenv("MILSTRIP_CONTROL_FILE") or Path(__file__).resolve().parents[1] / ".cred" / "control.json")


def principal_key(tenant_id, object_id):
    return f"{UUID(str(tenant_id))}:{UUID(str(object_id))}"


def now_text():
    return datetime.now(timezone.utc).isoformat()


def append_audit(state, event_type, actor_id, **details):
    # Callers provide identifiers/outcomes only. No source text, reasons,
    # connection strings, credential material or arbitrary exception content.
    state["audit"].append({"event_id": str(uuid4()), "at": now_text(), "event_type": event_type,
                           "actor_id": actor_id, **details})


def _require(condition):
    if not condition:
        raise ValueError("Invalid private control invariant")


def _utc_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0)
    return parsed


def _validate_management_pacing(state, previous):
    pacing = state.get("management_pacing")
    old = (previous or {}).get("management_pacing")
    if pacing is None:
        _require(old is None)
        return
    _require(isinstance(pacing, dict) and isinstance(pacing["reservations"], dict))
    _utc_timestamp(pacing["not_before"])
    open_keys = []
    for key, reservation in pacing["reservations"].items():
        from .broker_models import ManagementStep
        from typing import get_args
        _require(reservation["step"] in get_args(ManagementStep))
        _require(key == reservation["lease_id"] + ":" + reservation["step"])
        UUID(reservation["reservation_id"])
        _utc_timestamp(reservation["not_before"])
        _require(reservation["status"] in {"RUNNING", "UNKNOWN", "CLOSED"})
        plan = state["sharing_plans"][reservation["plan_id"]]
        _require(reservation["revision"] == plan["revision"])
        execution = plan["executions"][reservation["execution_id"]]
        _require(execution["lease_id"] == reservation["lease_id"]
                 and execution["broker_id"] == reservation["broker_id"])
        if reservation["status"] != "CLOSED":
            open_keys.append(key)
            target = principal_key(plan["target"]["tenant_id"], plan["target"]["object_id"])
            _require(state["sharing_leases"][target]["lease_id"] == reservation["lease_id"])
    _require(open_keys == ([] if pacing["active"] is None else [pacing["active"]]))
    if old is not None:
        _require(_utc_timestamp(pacing["not_before"]) >= _utc_timestamp(old["not_before"]))
        for key, before in old["reservations"].items():
            current = pacing["reservations"][key]
            for field in before.keys() - {"status"}:
                _require(current[field] == before[field])
            if before["status"] == "CLOSED":
                _require(current["status"] == "CLOSED")
            if before["status"] == "UNKNOWN":
                _require(current["status"] in {"UNKNOWN", "CLOSED"})


def _validate(state, previous=None):
    try:
        _require(state["version"] == 1 and type(state["version"]) is int)
        UUID(state["revision"])
        UUID(state["acl_revision"])
        security = state["security"]
        tenant = str(UUID(security["tenant_id"]))
        _require(type(security["enforced"]) is bool)
        _require(security["allowed_domain"] == "austinlighthouse.org")
        bindings = security["brokers"]
        _require(set(bindings) == {"stage", "prod"})
        credential_names = []
        for profile_id, binding in bindings.items():
            _require(binding["profile_id"] == profile_id and binding["tenant_id"] == tenant)
            _require(isinstance(binding["broker_id"], str) and binding["broker_id"])
            filename = Path(binding["credential_file"])
            _require(filename.name == str(filename) and filename.suffix == ".json")
            _require(filename.name not in {"control.json", "runtime.json"})
            credential_names.append(filename.name.casefold())
        _require(len(set(credential_names)) == 2)
        _require(isinstance(security["legacy_usernames"], list))
        _require(set(state["resources"]) == {"stage", "prod"})
        for resources in state["resources"].values():
            UUID(resources["app_id"])
            UUID(resources["flow_id"])
        _require(isinstance(state["users"], dict))
        _require(len(state["protected_owners"]) == 2 and len(set(state["protected_owners"])) == 2)
        for key, user in state["users"].items():
            _require(key == principal_key(user["tenant_id"], user["object_id"]))
            _require(user["tenant_id"] == tenant)
            _require(user["role"] in {"OWNER", "ADMIN", "OPERATOR"})
            _require(type(user["desired_active"]) is bool)
            _require(user["access_state"] in {"pending", "active", "denied"})
            UUID(user["access_revision"])
            _require(user["upn"].casefold().endswith("@" + security["allowed_domain"]))
            _require((user["role"] == "OWNER") == (key in state["protected_owners"]))
        for key in state["protected_owners"]:
            owner = state["users"][key]
            _require(owner["role"] == "OWNER" and owner["desired_active"] is True)
        for name in ("sharing_plans", "operations", "runtime"):
            _require(isinstance(state[name], dict))
        leases = state.get("sharing_leases", {})
        _require(isinstance(leases, dict))
        for key, lease in leases.items():
            plan = state["sharing_plans"][lease["plan_id"]]
            _require(key == principal_key(plan["target"]["tenant_id"], plan["target"]["object_id"]))
            _require(lease["revision"] == plan["revision"])
            _require(lease["status"] in {"RUNNING", "UNKNOWN"})
            UUID(lease["lease_id"])
            UUID(lease["execution_id"])
            _require(lease["broker_id"] in {binding["broker_id"] for binding in bindings.values()})
            _require(plan["executions"][lease["execution_id"]] == lease)
        for plan in state["sharing_plans"].values():
            for execution_id, execution in plan.get("executions", {}).items():
                native = execution.get("native_run")
                if native is not None:
                    from .broker_models import NativeSharingRun
                    parsed = NativeSharingRun.model_validate(native).model_dump(mode="json")
                    _require(parsed == native)
                    profile = next(name for name, binding in bindings.items()
                                   if binding["broker_id"] == execution["broker_id"])
                    _require(native["flow_id"] == state["resources"][profile]["flow_id"])
                    _require(native["environment_name"] == "Default-" + tenant)
                old = (previous or {}).get("sharing_plans", {}).get(plan["plan_id"], {}).get("executions", {}).get(execution_id)
                if old is not None:
                    _require(old.get("native_run") == native)
        _validate_management_pacing(state, previous)
        _require(isinstance(state["audit"], list))
        if previous:
            _require(state["protected_owners"] == previous["protected_owners"])
            _require(security["tenant_id"] == previous["security"]["tenant_id"])
            _require(not previous["security"]["enforced"] or security["enforced"])
            for key, held in previous.get("sharing_leases", {}).items():
                if leases.get(key, {}).get("lease_id") != held["lease_id"]:
                    execution = state["sharing_plans"][held["plan_id"]]["executions"][held["execution_id"]]
                    _require(execution["status"] == "CLOSED" and execution.get("result_digest"))
            for key in state["protected_owners"]:
                for field in ("tenant_id", "object_id", "upn", "display_name", "role", "desired_active"):
                    _require(state["users"][key][field] == previous["users"][key][field])
    except (KeyError, TypeError, ValueError, AttributeError, StopIteration):
        raise ControlError(503, "Private administration state is invalid") from None


class ControlStore:
    def __init__(self, path=None):
        self.path = Path(path or control_path()).absolute()
        if (self.path.parent.name != ".cred" or self.path.name != "control.json"
                or self.path.is_symlink() or self.path.parent.is_symlink()):
            raise ControlError(503, "Administration state requires private control.json storage")

    def exists(self):
        return self.path.exists()

    def read(self):
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ControlError(503, "Private administration state is unavailable") from None
        _validate(state)
        return state

    def _write(self, state):
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(prefix="control-", suffix=".tmp", dir=self.path.parent)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise ControlError(503, "Private administration state could not be saved") from None
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def _lock(self):
        descriptor = None
        try:
            # Ownership is held by the OS, not by the file's presence. A crash
            # releases the lock; never unlink this inode while other processes
            # can be waiting on it.
            descriptor = os.open(self.path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR, 0o600)
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return descriptor
        except OSError:
            if descriptor is not None:
                os.close(descriptor)
            raise ControlError(503, "Administration state is busy; retry the same command") from None

    def _unlock(self, descriptor):
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    def create(self, state):
        _validate(state)
        descriptor = self._lock()
        try:
            if self.path.exists():
                raise ControlError(409, "Administration state already exists")
            self._write(state)
        finally:
            self._unlock(descriptor)

    def mutate(self, callback, expected_revision=None):
        descriptor = self._lock()
        try:
            state = self.read()
            if expected_revision is not None and state["revision"] != str(expected_revision):
                raise ControlError(409, "Administration revision changed; reload")
            previous = deepcopy(state)
            result = callback(state)
            state["revision"] = str(uuid4())
            _validate(state, previous)
            self._write(state)
            return result
        finally:
            self._unlock(descriptor)
