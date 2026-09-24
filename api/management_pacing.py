"""One durable in-flight call for the shared Power Automate Management connection.

The connector permits five calls per 60 seconds. A call holds the permit through
its completion callback; the next call waits another 13 seconds. Reserving only
future timestamps would let delayed flow runs bunch their actual calls together.
No API thread sleeps, no unknown call expires, and no platform API is called here.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .authorization import AuthorizationError, _sharing_context
from .control import ControlStore


INTERVAL_SECONDS = 13


def utc_now():
    return datetime.now(timezone.utc)


def _timestamp(value):
    return value.isoformat().replace("+00:00", "Z")


def _call_key(command):
    return str(command.lease_id) + ":" + command.step


def reserve_management_call(binding, command, store=None):
    """Reserve one fixed flow action under its current sharing execution."""
    store = store or ControlStore()

    def change(state):
        plan, target, user = _sharing_context(state, binding, command)
        lease = state.get("sharing_leases", {}).get(target)
        if (lease is None or lease["lease_id"] != str(command.lease_id)
                or lease["execution_id"] != str(command.execution_id)
                or lease["plan_id"] != plan["plan_id"] or lease["revision"] != plan["revision"]
                or lease["broker_id"] != binding["broker_id"] or lease["status"] != "RUNNING"):
            raise AuthorizationError(409, "Management call does not own a running sharing lease")
        if user["access_revision"] != plan["revision"]:
            raise AuthorizationError(409, "Sharing plan was superseded; reconcile the latest request")
        pacing = state.setdefault("management_pacing", {
            "not_before": "1970-01-01T00:00:00Z", "active": None, "reservations": {}})
        key = _call_key(command)
        previous = pacing["reservations"].get(key)
        if previous is not None:
            if previous["status"] != "RUNNING" or pacing["active"] != key:
                raise AuthorizationError(409, "Management action cannot restart; inspect its recorded outcome")
            return {field: previous[field] for field in ("reservation_id", "not_before")}
        if pacing["active"] is not None:
            raise AuthorizationError(409, "Management connection is busy; retry the same sharing command")
        not_before = max(utc_now(), datetime.fromisoformat(pacing["not_before"].replace("Z", "+00:00")))
        reservation = {"reservation_id": str(uuid4()), "lease_id": str(command.lease_id),
                       "execution_id": str(command.execution_id), "plan_id": plan["plan_id"],
                       "revision": plan["revision"], "broker_id": binding["broker_id"],
                       "step": command.step, "status": "RUNNING", "not_before": _timestamp(not_before)}
        pacing["reservations"][key] = reservation
        pacing["active"] = key
        return {field: reservation[field] for field in ("reservation_id", "not_before")}
    return store.mutate(change)


def record_management_call(binding, command, store=None):
    """Close only the exact broker-owned call, even if its plan was superseded."""
    store = store or ControlStore()

    def change(state):
        _sharing_context(state, binding, command)
        pacing = state.get("management_pacing", {})
        key = _call_key(command)
        reservation = pacing.get("reservations", {}).get(key)
        if (reservation is None or any(reservation[field] != value for field, value in (
                ("reservation_id", str(command.reservation_id)), ("execution_id", str(command.execution_id)),
                ("plan_id", str(command.plan_id)), ("revision", str(command.revision)),
                ("broker_id", binding["broker_id"])))):
            raise AuthorizationError(409, "Management callback does not own the call reservation")
        if reservation["status"] == "CLOSED":
            if not command.outcome_known:
                raise AuthorizationError(409, "Management action already closed with a known outcome")
            return {"reservation_id": reservation["reservation_id"], "status": "CLOSED"}
        if pacing["active"] != key:
            raise AuthorizationError(409, "Management callback does not hold the connection permit")
        if command.outcome_known:
            reservation["status"] = "CLOSED"
            pacing["active"] = None
            pacing["not_before"] = _timestamp(max(utc_now(), datetime.fromisoformat(pacing["not_before"].replace("Z", "+00:00")))
                                              + timedelta(seconds=INTERVAL_SECONDS))
        else:
            reservation["status"] = "UNKNOWN"
        return {"reservation_id": reservation["reservation_id"], "status": reservation["status"]}
    return store.mutate(change)
