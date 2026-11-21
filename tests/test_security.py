import pytest

from fastapi.testclient import TestClient

from main import app

PROTECTED_ROUTES = [
    ("post", "/api/logout"),
    ("post", "/api/observations"),
    ("get", "/api/patients/P-001/observations"),
    ("post", "/api/patients"),
    ("get", "/api/patients"),
    ("get", "/api/wards"),
    ("get", "/api/ward-list"),
    ("get", "/api/escalations"),
]


@pytest.fixture
def client():
    return TestClient(app)


def login(client, username):
    response = client.post(
        "/api/login",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("method, path", PROTECTED_ROUTES)
def test_protected_routes_reject_missing_session(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401


@pytest.mark.parametrize("method, path", PROTECTED_ROUTES)
def test_protected_routes_reject_invalid_session(client, method, path):
    headers = {"Authorization": "Bearer not-a-real-token"}
    response = getattr(client, method)(path, headers=headers)
    assert response.status_code == 401


def test_admin_cannot_access_clinical_routes(client, patient_data):
    headers = login(client, "admin")

    assert client.post("/api/observations", headers=headers, json={
        "patient_id": patient_data["patient_id"],
        "respiratory_rate": 16,
        "spo2": 98,
        "supplemental_oxygen": False,
        "systolic_bp": 120,
        "pulse": 70,
        "consciousness": "A",
        "temperature": 37.0,
    }).status_code == 403

    assert client.get("/api/patients", headers=headers).status_code == 403
    assert client.get("/api/ward-list", headers=headers).status_code == 403
    assert client.get("/api/escalations", headers=headers).status_code == 403


def test_patient_self_registration_is_removed(client):
    assert client.post("/api/register").status_code == 404
    assert client.post("/api/signup").status_code == 404


def test_login_does_not_accept_patient_role(client, monkeypatch):
    import auth

    monkeypatch.setitem(auth.USERS["nurse"], "role", "Patient")

    response = client.post(
        "/api/login",
        json={"username": "nurse", "password": "password123"},
    )

    assert response.status_code == 401
    