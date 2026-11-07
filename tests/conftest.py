from copy import deepcopy

import pytest

import auth
from fastapi.testclient import TestClient

import observations
import patients
from main import app


@pytest.fixture(autouse=True)
def isolated_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr(observations, "OBSERVATIONS_FILE", str(tmp_path / "observations.json"))
    monkeypatch.setattr(patients, "PATIENTS_FILE", str(tmp_path / "patients.json"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def normal_values():
    return {
        "respiratory_rate": 16,
        "spo2": 98,
        "supplemental_oxygen": False,
        "systolic_bp": 120,
        "pulse": 70,
        "consciousness": "A",
        "temperature": 37.0,
    }


@pytest.fixture
def patient_data():
    return {"patient_id": "P-001", "name": "Max Mustermann", "ward": "Ward A", "bed": "1"}


@pytest.fixture
def existing_patient(patient_data):
    return patients.create_patient(dict(patient_data))


@pytest.fixture
def valid_request(existing_patient, normal_values):
    return {"patient_id": "P-001", "recorded_by": "nurse", **normal_values}


@pytest.fixture(autouse=True)
def isolated_auth(monkeypatch):
    monkeypatch.setattr(auth, "_sessions", {})
    monkeypatch.setattr(auth, "USERS", deepcopy(auth.USERS))
    monkeypatch.setattr("main.USERS", auth.USERS)


@pytest.fixture
def staff_client(client):
    response = client.post("/api/login", json={"username": "nurse", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client
