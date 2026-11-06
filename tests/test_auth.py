import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import auth


@pytest.fixture
def protected_client():
    app = FastAPI()

    @app.get("/staff")
    def staff(user: dict = Depends(auth.require_role("Nurse", "Clinician"))):
        return user

    @app.get("/admin")
    def admin(user: dict = Depends(auth.require_role("Admin"))):
        return user

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("header", [None, "Bearer unknown", "Basic abc", "Bearer"])
def test_missing_or_invalid_session_is_401(protected_client, header):
    headers = {"Authorization": header} if header else {}
    response = protected_client.get("/staff", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("username", ["nurse", "clinician", "admin"])
def test_roles_are_enforced(protected_client, username):
    token = auth.create_session(username)
    headers = {"Authorization": f"Bearer {token}"}
    staff = protected_client.get("/staff", headers=headers)
    admin = protected_client.get("/admin", headers=headers)
    assert staff.status_code == (403 if username == "admin" else 200)
    assert admin.status_code == (200 if username == "admin" else 403)


def test_expired_session_is_401(protected_client, monkeypatch):
    now = auth.time.time()
    monkeypatch.setattr(auth.time, "time", lambda: now)
    token = auth.create_session("nurse")
    monkeypatch.setattr(auth.time, "time", lambda: now + auth.SESSION_TTL_SECONDS)
    assert protected_client.get("/staff", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_revoked_session_is_401(protected_client):
    token = auth.create_session("nurse")
    auth.revoke_session(token)
    assert protected_client.get("/staff", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("roles", [(), ("Patient",), ("Nurse", "Unknown")])
def test_helper_rejects_unsupported_roles(roles):
    with pytest.raises(ValueError):
        auth.require_role(*roles)
