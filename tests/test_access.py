from pathlib import Path

import pytest

import auth
import observations


def login(client, username):
    response = client.post("/api/login", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == auth.SESSION_TTL_SECONDS
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("username", ["nurse", "clinician"])
def test_clinical_roles_can_save_and_read(client, valid_request, username):
    headers = login(client, username)
    valid_request["recorded_by"] = "someone-else"
    response = client.post("/api/observations", json=valid_request, headers=headers)
    assert response.status_code == 200
    assert response.json()["observation"]["recorded_by"] == username
    history = client.get("/api/patients/P-001/observations", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


@pytest.mark.parametrize("credential", ["missing", "invalid", "admin", "expired", "revoked"])
@pytest.mark.parametrize("existing_data", [False, True])
def test_denied_requests_do_not_change_storage(client, valid_request, monkeypatch, credential, existing_data):
    path = Path(observations.OBSERVATIONS_FILE)
    if existing_data:
        assert client.post("/api/observations", json=valid_request, headers=login(client, "nurse")).status_code == 200
    before = path.read_bytes() if path.exists() else None
    if credential == "missing":
        headers = {}
    elif credential == "invalid":
        headers = {"Authorization": "Bearer forged-token"}
    else:
        headers = login(client, "admin" if credential == "admin" else "nurse")
        if credential == "expired":
            future = auth.time.time() + auth.SESSION_TTL_SECONDS
            monkeypatch.setattr(auth.time, "time", lambda: future)
        elif credential == "revoked":
            assert client.post("/api/logout", headers=headers).status_code == 204
    valid_request["role"] = "Nurse"
    expected = 403 if credential == "admin" else 401
    assert client.post("/api/observations", json=valid_request, headers=headers).status_code == expected
    assert client.get("/api/patients/P-001/observations", headers=headers).status_code == expected
    assert (path.read_bytes() if path.exists() else None) == before


def test_role_changes_apply_to_existing_sessions(client, valid_request, monkeypatch):
    headers = login(client, "nurse")
    monkeypatch.setitem(auth.USERS["nurse"], "role", "Admin")
    assert client.post("/api/observations", json=valid_request, headers=headers).status_code == 403
    assert not Path(observations.OBSERVATIONS_FILE).exists()


def test_removed_account_cannot_use_existing_session(client, monkeypatch):
    headers = login(client, "nurse")
    monkeypatch.delitem(auth.USERS, "nurse")
    assert client.get("/api/patients/P-001/observations", headers=headers).status_code == 401


@pytest.mark.parametrize("username", ["nurse", "clinician", "admin"])
def test_logout_revokes_only_its_session(client, username):
    first = login(client, username)
    second = login(client, username)
    assert first != second
    assert client.post("/api/logout", headers=first).status_code == 204
    assert client.post("/api/logout", headers=first).status_code == 401
    assert client.post("/api/logout", headers=second).status_code == 204


def test_logout_requires_a_session(client):
    assert client.post("/api/logout").status_code == 401


def test_observation_does_not_require_client_recorder(client, valid_request):
    del valid_request["recorded_by"]
    response = client.post("/api/observations", json=valid_request, headers=login(client, "nurse"))
    assert response.status_code == 200
    assert response.json()["observation"]["recorded_by"] == "nurse"


def test_unsupported_role_cannot_login(client, monkeypatch):
    monkeypatch.setitem(auth.USERS["nurse"], "role", "Patient")
    response = client.post("/api/login", json={"username": "nurse", "password": "password123"})
    assert response.status_code == 401
    assert auth._sessions == {}
