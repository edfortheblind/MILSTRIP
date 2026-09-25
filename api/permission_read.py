"""Stateless qualification of bounded app-permission pages from a trusted broker.

Supplied JSON is not evidence of origin. Only the native lease-bound sharing
flow may use a fresh complete result to reach its existing mutation gates.
This module reads authorization state; it never writes, audits or issues HTTP.
"""
from datetime import datetime, timedelta, timezone
import json
import re
from urllib.parse import quote, quote_from_bytes, quote_plus, unquote_to_bytes
from uuid import UUID

from api.authorization import AuthorizationError, _authorized
from api.control import ControlStore, principal_key


MAX_PAGE_BYTES = 250_000
MAX_TOTAL_BYTES = 750_000
MAX_ROWS = 1000
OBSERVATION_SECONDS = 90
GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")
CURSOR = re.compile(r"(?:[A-Za-z0-9._~-]|%[0-9A-F]{2})+")
ROLES = {"CanView", "CanEdit", "Owner"}
PRINCIPAL_TYPES = {"User", "Group", "Tenant"}


def utc_now():
    return datetime.now(timezone.utc)


def strict_json_loads(value):
    """Reject duplicate keys/non-JSON numbers without retaining their contents."""
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = item
        return result

    def invalid_constant(_):
        raise ValueError("Invalid JSON constant")

    return json.loads(value, object_pairs_hook=unique, parse_constant=invalid_constant)


def permission_urls(app_id, tenant_id):
    route = f"https://api.powerapps.com/providers/Microsoft.PowerApps/apps/{app_id}/permissions?api-version=2017-06-01&%24filter="
    scope = f"environment eq 'Default-{tenant_id}'"
    return route + quote(scope, safe=""), route + quote_plus(scope, safe="") + "&%24skiptoken="


def _continuation(page, prefix):
    values = []
    for field in ("nextLink", "@odata.nextLink"):
        value = page.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError
        if value:
            values.append(value)
    if not values:
        return None
    if len(set(values)) != 1:
        raise ValueError
    value = values[0]
    if len(value) > 4096 or not value.startswith(prefix):
        raise ValueError
    suffix = value[len(prefix):]
    if not 1 <= len(suffix) <= 2048 or CURSOR.fullmatch(suffix) is None:
        raise ValueError
    decoded = unquote_to_bytes(suffix)
    if any(byte < 32 or byte == 127 for byte in decoded):
        raise ValueError
    if quote_from_bytes(decoded, safe="-._~") != suffix:
        raise ValueError
    return prefix + suffix


def _uuid(value):
    if not isinstance(value, str) or GUID.fullmatch(value) is None:
        raise ValueError
    return str(UUID(value))


def _assignment(row, prefix, tenant_id):
    if not isinstance(row, dict):
        raise ValueError
    name, identifier = row.get("name"), row.get("id")
    if (not isinstance(name, str) or NAME.fullmatch(name) is None or name == "." or ".." in name
            or not isinstance(identifier, str) or len(identifier) > 512 or identifier != prefix + name):
        raise ValueError
    properties = row.get("properties")
    if not isinstance(properties, dict) or properties.get("roleName") not in ROLES:
        raise ValueError
    principal = properties.get("principal")
    if not isinstance(principal, dict) or principal.get("type") not in PRINCIPAL_TYPES:
        raise ValueError
    object_id, observed_tenant = _uuid(principal.get("id")), _uuid(principal.get("tenantId"))
    if observed_tenant != tenant_id:
        raise ValueError
    return {"id": identifier, "name": name, "properties": {"roleName": properties["roleName"],
            "principal": {"id": object_id, "type": principal["type"], "tenantId": observed_tenant}}}


def _scope(state, binding, context, command):
    _authorized(state, context, "users.manage")
    configured = state["security"]["brokers"].get(context.profile_id)
    if (configured is None or any(binding.get(field) != configured[field]
            for field in ("broker_id", "profile_id", "tenant_id"))
            or (context.broker_id, context.tenant_id) != (configured["broker_id"], configured["tenant_id"])):
        raise AuthorizationError(403, "Permission reader broker is not authorized")
    plan = state["sharing_plans"].get(str(command.plan_id))
    if plan is None:
        raise AuthorizationError(404, "Sharing plan not found")
    if plan.get("revision") != str(command.revision) or plan.get("status") != "pending":
        raise AuthorizationError(409, "Sharing plan is not current and pending")
    target = plan["target"]
    tenant_id, target_id = str(UUID(target["tenant_id"])), str(UUID(target["object_id"]))
    user = state["users"].get(principal_key(tenant_id, target_id))
    if (tenant_id != context.tenant_id or user is None or user.get("access_revision") != plan["revision"]):
        raise AuthorizationError(409, "Sharing plan target was superseded")
    operation = state["operations"].get(plan["command_id"])
    if (operation is None or operation.get("domain") != "users" or operation.get("capability") != "users.manage"
            or operation.get("plan_id") != plan["plan_id"] or operation.get("status") != "pending"
            or operation.get("actor_id") != context.actor_id or operation.get("profile_id") != context.profile_id):
        raise AuthorizationError(403, "Permission reader requires the original access command actor and profile")
    resources = [r for r in plan["resources"] if r.get("kind") == "app"
                 and r.get("environment") == command.resource_environment]
    app_id = str(UUID(state["resources"][command.resource_environment]["app_id"]))
    if (len(resources) != 1 or resources[0].get("permission") != "CanView"
            or resources[0].get("resource_id") != app_id
            or type(resources[0].get("present")) is not bool
            or resources[0]["present"] != user["desired_active"]):
        raise AuthorizationError(409, "Sharing plan app resource is not current")
    return app_id, tenant_id, target_id


def validate_app_permission_read(binding, context, command, store=None, *, now=None):
    """Return sanitized qualification for this current actor's pending plan."""
    state = (store or ControlStore()).read()
    app_id, tenant_id, target_id = _scope(state, binding, context, command)
    started = datetime.fromisoformat(command.observation_started_at.replace("Z", "+00:00"))
    expires = started + timedelta(seconds=OBSERVATION_SECONDS)
    result = {"schema_version": 1, "plan_id": str(command.plan_id), "revision": str(command.revision),
              "resource_environment": command.resource_environment, "app_id": app_id, "tenant_id": tenant_id,
              "target_object_id": target_id, "phase": command.phase,
              "observation_started_at": command.observation_started_at, "expires_at": expires.isoformat(),
              "disposition": "INCOMPLETE", "reason": None, "page_count": len(command.pages),
              "row_count": 0, "next_url": None, "matching_assignments": []}

    def incomplete(reason):
        return {**result, "reason": reason}

    def expired():
        current = now if now is not None else utc_now()
        return current >= expires or started > current + timedelta(seconds=5)

    if expired():
        return incomplete("DEADLINE_EXPIRED")
    # All byte limits are checked before parsing any supplied page.
    try:
        sizes = [len(page.response_json.encode("utf-8")) for page in command.pages]
    except UnicodeError:
        return incomplete("INVALID_PAGE")
    if any(size > MAX_PAGE_BYTES for size in sizes) or sum(sizes) > MAX_TOTAL_BYTES:
        return incomplete("INVALID_PAGE")
    expected_url, cursor_prefix = permission_urls(app_id, tenant_id)
    assignment_prefix = f"/providers/Microsoft.PowerApps/apps/{app_id}/permissions/"
    routes, assignment_ids, principal_ids, matches = set(), set(), set(), []
    for page in command.pages:
        if page.request_url != expected_url or page.request_url in routes:
            return incomplete("INVALID_CURSOR")
        routes.add(page.request_url)
        try:
            body = strict_json_loads(page.response_json)
            if not isinstance(body, dict) or "error" in body or not isinstance(body.get("value"), list):
                raise ValueError
        except (ValueError, TypeError, RecursionError, OverflowError):
            return incomplete("INVALID_PAGE")
        rows = body["value"]
        result["row_count"] += len(rows)
        if result["row_count"] >= MAX_ROWS:
            return incomplete("ROW_LIMIT")
        for row in rows:
            try:
                clean = _assignment(row, assignment_prefix, tenant_id)
            except (ValueError, TypeError):
                return incomplete("INVALID_PAGE")
            identifier = clean["id"].casefold()
            principal_id = clean["properties"]["principal"]["id"]
            if identifier in assignment_ids or principal_id in principal_ids:
                return incomplete("DUPLICATE_ASSIGNMENT")
            assignment_ids.add(identifier)
            principal_ids.add(principal_id)
            if principal_id == target_id:
                matches.append(clean)
        try:
            expected_url = _continuation(body, cursor_prefix)
            if expected_url in routes:
                raise ValueError
        except (ValueError, TypeError):
            return incomplete("INVALID_CURSOR")
    if expired():
        return incomplete("DEADLINE_EXPIRED")
    if expected_url is not None:
        if len(command.pages) == 3:
            return incomplete("PAGE_LIMIT")
        return {**result, "disposition": "CONTINUE", "next_url": expected_url}
    return {**result, "disposition": "COMPLETE", "matching_assignments": matches}
