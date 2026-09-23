"""Dedicated laptop-development identity; no tenant or forwarded-header trust."""
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path

import psycopg
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from psycopg.conninfo import conninfo_to_dict

basic = HTTPBasic(auto_error=False, scheme_name="basic-auth")
ITERATIONS = 600_000


def credential_path():
    override = os.getenv("MILSTRIP_API_CREDENTIAL_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / ".cred" / "api-credential.json"


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS).hex()


def local_boundary(request):
    try:
        peer = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        config = conninfo_to_dict(os.getenv("MILSTRIP_DATABASE_URL", ""))
    except psycopg.Error as error:
        raise HTTPException(503, "Database unavailable") from error
    except ValueError:
        peer, config = False, {}
    if (not peer or config.get("host") not in {"localhost", "127.0.0.1", "::1"}
            or config.get("hostaddr") not in {None, "127.0.0.1", "::1"}
            or config.get("dbname") != "trav3pl-psqldb-stage"
            or config.get("port", "5432") != "5432"
            or config.get("service")):
        raise HTTPException(403, "API is restricted to the approved laptop database and loopback peer")


def authenticate(request: Request, credentials: HTTPBasicCredentials | None = Depends(basic)):
    local_boundary(request)
    challenge = {"WWW-Authenticate": 'Basic realm="MILSTRIP local development"'}
    if credentials is None:
        raise HTTPException(401, "Authentication required", headers=challenge)
    try:
        config = json.loads(credential_path().read_text(encoding="utf-8"))
        username, salt, digest = config["username"], config["salt"], config["digest"]
        if (config["version"] != 1 or config["iterations"] != ITERATIONS
                or not isinstance(username, str) or not username.isascii()
                or not username.strip() or len(username) > 200 or ":" in username
                or len(bytes.fromhex(salt)) != 32 or len(bytes.fromhex(digest)) != 32):
            raise ValueError("Invalid credential configuration")
    except (OSError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(503, "Local API credentials are not configured") from error
    valid_user = hmac.compare_digest(credentials.username.encode(), username.encode())
    valid_password = hmac.compare_digest(password_digest(credentials.password, salt), digest)
    if not (valid_user and valid_password):
        raise HTTPException(401, "Invalid credentials", headers=challenge)
    request.state.reviewer = username
    return username
