"""Credential verification and the gateway's loopback API boundary."""
import hashlib
import hmac
import ipaddress
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

basic = HTTPBasic(auto_error=False, scheme_name="basic-auth")
ITERATIONS = 600_000


def credential_path():
    return Path(os.getenv("MILSTRIP_API_CREDENTIAL_FILE") or
                Path(__file__).resolve().parents[1] / ".cred" / "api-credential.json")


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS).hex()


@dataclass(frozen=True)
class CredentialVerifier:
    profile_id: str
    username: str
    salt: str = field(repr=False)
    digest: str = field(repr=False)


def load_verifier(path, profile_id):
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        username, salt, digest = config["username"], config["salt"], config["digest"]
        if (config["version"] != 1 or config["iterations"] != ITERATIONS
                or not isinstance(username, str) or not username.isascii()
                or not username.strip() or len(username) > 200 or ":" in username
                or any(ord(c) < 32 for c in username)
                or len(bytes.fromhex(salt)) != 32 or len(bytes.fromhex(digest)) != 32):
            raise ValueError
    except (OSError, KeyError, ValueError, TypeError):
        raise ValueError("API credential configuration is invalid") from None
    return CredentialVerifier(profile_id, username, salt, digest)


def local_boundary(request):
    try:
        peer = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        peer = False
    if not peer:
        raise HTTPException(403, "API requires a loopback gateway peer")


def authenticate(request: Request, credentials: HTTPBasicCredentials | None = Depends(basic)):
    from api.runtime import RequestContext, snapshot_for
    from api.control import ControlError, ControlStore
    local_boundary(request)
    challenge = {"WWW-Authenticate": 'Basic realm="MILSTRIP"'}
    if credentials is None:
        raise HTTPException(401, "Authentication required", headers=challenge)
    if request.url.path == "/api/v1/broker/invoke":
        from api.broker import authenticate_transport
        return authenticate_transport(request, credentials)
    try:
        store = ControlStore()
        if store.exists() and store.read()["security"]["enforced"]:
            raise HTTPException(403, "Direct API access is disabled; use the verified application broker")
    except ControlError:
        raise HTTPException(503, "Application access configuration is unavailable") from None
    snapshot = snapshot_for(request)
    selected = None
    for verifier in snapshot.verifiers:
        valid_user = hmac.compare_digest(credentials.username.encode(), verifier.username.encode())
        valid_password = hmac.compare_digest(password_digest(credentials.password, verifier.salt), verifier.digest)
        if valid_user and valid_password:
            selected = verifier
    if selected is None:
        raise HTTPException(401, "Invalid credentials", headers=challenge)
    request.state.context = RequestContext(selected.username, selected.profile_id, snapshot.config.revision)
    request.state.reviewer = selected.username
    return selected.username
