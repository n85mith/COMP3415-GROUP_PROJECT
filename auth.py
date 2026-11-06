import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ROLES = frozenset({"Nurse", "Clinician", "Admin"})
SESSION_TTL_SECONDS = 8 * 60 * 60
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    expected = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(expected, stored)


USERS = {
    "clinician": {"password": hash_password("password123"), "role": "Clinician", "name": "Dr. Aris Thorne"},
    "admin": {"password": hash_password("password123"), "role": "Admin", "name": "Demo Administrator"},
    "nurse": {"password": hash_password("password123"), "role": "Nurse", "name": "Nurse Jordan Lee"},
}


@dataclass(frozen=True)
class Session:
    username: str
    expires_at: float


_sessions: dict[str, Session] = {}
_session_lock = Lock()


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(username: str) -> str:
    if username not in USERS or USERS[username]["role"] not in ROLES:
        raise ValueError("Cannot create a session for this user")
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _session_lock:
        expired = [key for key, session in _sessions.items() if session.expires_at <= now]
        for key in expired:
            del _sessions[key]
        _sessions[_token_key(token)] = Session(username, now + SESSION_TTL_SECONDS)
    return token


def revoke_session(token: str) -> None:
    with _session_lock:
        _sessions.pop(_token_key(token), None)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    unauthorized = HTTPException(
        status_code=401,
        detail="A valid session is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    key = _token_key(credentials.credentials)
    with _session_lock:
        session = _sessions.get(key)
        if session is None:
            raise unauthorized
        if session.expires_at <= time.time():
            del _sessions[key]
            raise unauthorized
    user = USERS.get(session.username)
    if user is None or user["role"] not in ROLES:
        raise unauthorized
    return {"username": session.username, "name": user["name"], "role": user["role"]}


def require_role(*roles: str):
    if not roles or not set(roles).issubset(ROLES):
        raise ValueError("Specify at least one supported role")

    def check_role(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return user

    return check_role
