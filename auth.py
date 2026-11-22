import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import db

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


_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    verify_password(password if isinstance(password, str) else "", _DUMMY_HASH)


USERS = {
    "clinician": {"password": hash_password("password123"), "role": "Clinician", "name": "Dr. Aris Thorne"},
    "admin": {"password": hash_password("password123"), "role": "Admin", "name": "Demo Administrator"},
    "nurse": {"password": hash_password("password123"), "role": "Nurse", "name": "Nurse Jordan Lee"},
}


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(username: str) -> str:
    username = normalize_account_username(username)
    user = get_account(username)
    if user is None or user["role"] not in ROLES:
        raise ValueError("Cannot create a session for this user")
    token = secrets.token_urlsafe(32)
    now = time.time()
    with db.transaction(write=True) as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        conn.execute(
            "INSERT INTO sessions (token_hash, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_token_key(token), username, now, now + SESSION_TTL_SECONDS),
        )
    return token


def revoke_session(token: str) -> None:
    with db.transaction(write=True) as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_key(token),))


def count_sessions() -> int:
    with db.transaction() as conn:
        return conn.execute("SELECT COUNT(*) FROM sessions WHERE expires_at > ?", (time.time(),)).fetchone()[0]


def normalize_account_username(username: str) -> str:
    return username.strip().lower() if isinstance(username, str) else ""


def get_account(username: str) -> Optional[dict]:
    key = normalize_account_username(username)
    if not key:
        return None

    if key in USERS:
        user = USERS[key]
        return {
            "username": key,
            "name": user["name"],
            "password": user["password"],
            "role": user["role"],
            "ward": user.get("ward"),
        }

    import staff

    stored = staff.get_staff(key)
    if stored is None:
        return None
    return {"username": key, **stored}


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    unauthorized = HTTPException(
        status_code=401,
        detail="A valid session is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    key = _token_key(credentials.credentials)
    with db.transaction() as conn:
        session = conn.execute("SELECT username, expires_at FROM sessions WHERE token_hash = ?", (key,)).fetchone()
    if session is None:
        raise unauthorized
    if session["expires_at"] <= time.time():
        with db.transaction(write=True) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (key,))
        raise unauthorized
    user = get_account(session["username"])
    if user is None or user["role"] not in ROLES:
        raise unauthorized
    return {
        "username": session["username"],
        "name": user["name"],
        "role": user["role"],
        "ward": user.get("ward"),
    }


def require_role(*roles: str):
    if not roles or not set(roles).issubset(ROLES):
        raise ValueError("Specify at least one supported role")

    def check_role(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return user

    return check_role
