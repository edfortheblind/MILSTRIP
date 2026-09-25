"""The only business/admin transport after explicit broker-only cutover."""
import hmac
import json
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.auth import load_verifier, password_digest
from api.authorization import (AuthorizationError, acquire_sharing_lease, administration_operation, authorize, authorize_person,
    current_user, list_users, record_sharing_result, save_user_access)
from api.broker_models import (AcquireSharingLease, AdministrationOperationPayload, BrokerEnvelope, BrokerResult, ChildPagePayload,
    EmptyPayload, IntakePayload, IntakeWorkflowPayload, RecordManagementCall, RequestPagePayload, RequestPayload, ReserveManagementCall,
    ReviewPayload, SaveUserAccess, SharingResult, ValidateAppPermissionRead)
from api.control import ControlError, ControlStore
from api.management_pacing import record_management_call, reserve_management_call


router = APIRouter(prefix="/api/v1/broker", tags=["broker"])
BUSINESS = {"GetHealth", "ListIntakeRequests", "GetIntakeRequest", "ListRecordResults",
            "ListAuditEvents", "CreateIntakeRequest", "CreateReviewDecision", "GetIntakeWorkflow"}
CONFIGURATION = {"GetRuntimeProfiles", "SaveRuntimeDraft", "TestRuntimeDraft", "ApplyRuntimeDraft", "InitializeRuntimeDraft"}


def authenticate_transport(request, credentials):
    store = ControlStore()
    try:
        state = store.read()
        if state["security"]["enforced"] and not getattr(request.app.state, "control_active", False):
            raise HTTPException(503, "Restart the API to complete broker-only activation")
        selected = None
        usernames = set(state["security"]["legacy_usernames"])
        bindings = []
        for binding in state["security"]["brokers"].values():
            verifier = load_verifier(store.path.parent / binding["credential_file"], binding["profile_id"])
            if verifier.username in usernames:
                raise ValueError
            usernames.add(verifier.username)
            bindings.append((binding, verifier))
        for binding, verifier in bindings:
            valid_name = hmac.compare_digest(credentials.username.encode(), verifier.username.encode())
            valid_password = hmac.compare_digest(password_digest(credentials.password, verifier.salt), verifier.digest)
            if valid_name and valid_password:
                selected = binding
        if selected is None:
            raise HTTPException(401, "Invalid broker credentials", headers={"WWW-Authenticate": 'Basic realm="MILSTRIP broker"'})
        request.state.broker_binding = selected
        request.state.control_store = store
        return selected["broker_id"]
    except (ControlError, ValueError):
        raise HTTPException(503, "Broker authentication is not configured") from None


def _parse(model, payload):
    try:
        return model.model_validate(payload)
    except ValidationError:
        raise HTTPException(422, "Operation payload is invalid") from None


def _business(request, context, operation, payload):
    from api import app as intake_api
    from api import operator
    from api.operator_models import ReviewCommand
    from api.runtime import RequestContext, business_scope

    authorize(context, "business", store=request.state.control_store)
    with business_scope(request, context.profile_id) as lease:
        request.state.context = RequestContext(context.actor_id, context.profile_id, lease.revision)
        request.state.reviewer = context.actor_id
        if operation == "GetIntakeWorkflow":
            from api.runtime import repository
            parsed = _parse(IntakeWorkflowPayload, payload)
            with repository(request) as value:
                return value.workflow_status(context.actor_id, source_id=parsed.source_id)
        if operation == "GetHealth":
            _parse(EmptyPayload, payload)
            return intake_api.health(request)
        if operation == "CreateIntakeRequest":
            parsed = _parse(IntakePayload, payload)
            return intake_api.create_intake_request(intake_api.IntakeRequest(**parsed.model_dump()), request)
        if operation == "GetIntakeRequest":
            parsed = _parse(RequestPayload, payload)
            return intake_api.get_intake_request(parsed.request_id, request)
        if operation == "ListIntakeRequests":
            parsed = _parse(RequestPagePayload, payload)
            return operator.list_requests(request, parsed.limit, parsed.status, parsed.cursor)
        if operation in {"ListRecordResults", "ListAuditEvents"}:
            parsed = _parse(ChildPagePayload, payload)
            handler = operator.list_records if operation == "ListRecordResults" else operator.list_events
            return handler(parsed.request_id, request, parsed.limit, parsed.cursor)
        if operation == "CreateReviewDecision":
            parsed = _parse(ReviewPayload, payload)
            command = _parse(ReviewCommand, parsed.model_dump(exclude={"record_id"}))
            return operator.review_record(parsed.record_id, command, request, Response())
    raise HTTPException(422, "Operation is not supported")


@router.post("/invoke", response_model=BrokerResult, operation_id="InvokeBroker")
def invoke(envelope: BrokerEnvelope, request: Request):
    request.state.broker_request_id = str(envelope.request_id)
    binding = getattr(request.state, "broker_binding", None)
    if binding is None:
        raise HTTPException(401, "Broker authentication is required")
    store = request.state.control_store
    try:
        try:
            if envelope.operation == "ValidateAppPermissionRead":
                from api.permission_read import strict_json_loads
                payload = strict_json_loads(envelope.payload_json)
            else:
                payload = json.loads(envelope.payload_json)
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, TypeError, RecursionError, OverflowError):
            raise HTTPException(422, "Operation payload must be a JSON object") from None
        if envelope.operation == "AcquireSharingLease":
            result = acquire_sharing_lease(binding, _parse(AcquireSharingLease, payload), store)
        elif envelope.operation == "RecordSharingResult":
            result = record_sharing_result(binding, _parse(SharingResult, payload), store)
        elif envelope.operation == "ReserveManagementCall":
            result = reserve_management_call(binding, _parse(ReserveManagementCall, payload), store)
        elif envelope.operation == "RecordManagementCall":
            result = record_management_call(binding, _parse(RecordManagementCall, payload), store)
        else:
            context = authorize_person(binding, envelope.actor, envelope.request_id, store)
            request.state.broker_context = context
            if envelope.operation in BUSINESS:
                result = _business(request, context, envelope.operation, payload)
            elif envelope.operation == "GetCurrentUser":
                _parse(EmptyPayload, payload)
                result = current_user(context, store)
            elif envelope.operation == "ListUsers":
                _parse(EmptyPayload, payload)
                result = list_users(context, store)
            elif envelope.operation == "SaveUserAccess":
                result = save_user_access(context, _parse(SaveUserAccess, payload), store)
            elif envelope.operation == "ValidateAppPermissionRead":
                from api.permission_read import validate_app_permission_read
                result = validate_app_permission_read(binding, context, _parse(ValidateAppPermissionRead, payload), store)
            elif envelope.operation == "GetAdministrationOperation":
                parsed = _parse(AdministrationOperationPayload, payload)
                result = administration_operation(context, parsed.command_id, store)
            elif envelope.operation in CONFIGURATION:
                from api.administration import AdministrationService
                result = AdministrationService(store, request.app.state.profile_manager).invoke(envelope.operation, payload, context)
            else:
                raise HTTPException(422, "Operation is not supported")
        return {"request_id": envelope.request_id, "result_json": json.dumps(jsonable_encoder(result), separators=(",", ":"))}
    except (AuthorizationError, ControlError) as error:
        raise HTTPException(error.status_code, error.message) from None


def install_error_handlers(app):
    async def validation_error(request, error):
        if request.url.path != "/api/v1/broker/invoke":
            return await request_validation_exception_handler(request, error)
        return JSONResponse(status_code=422, content={"request_id": None, "code": "INVALID_REQUEST", "message": "Broker request is invalid"})

    async def http_error(request, error):
        if request.url.path != "/api/v1/broker/invoke":
            return await http_exception_handler(request, error)
        codes = {401: "AUTHENTICATION_REQUIRED", 403: "ACCESS_DENIED", 404: "NOT_FOUND", 409: "CONFLICT",
                 422: "INVALID_REQUEST", 503: "UNAVAILABLE"}
        return JSONResponse(status_code=error.status_code, headers=error.headers,
            content={"request_id": getattr(request.state, "broker_request_id", None),
                     "code": codes.get(error.status_code, "REQUEST_FAILED"), "message": str(error.detail)})
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
