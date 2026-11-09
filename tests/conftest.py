import pytest
from fastapi.testclient import TestClient

import escalations
import observations
from main import app


@pytest.fixture(autouse=True)
def isolated_observations_file(tmp_path, monkeypatch):
    monkeypatch.setattr(observations, "OBSERVATIONS_FILE", str(tmp_path / "observations.json"))
    monkeypatch.setattr(escalations, "ESCALATIONS_FILE", str(tmp_path / "escalations.json"))


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
def valid_request(normal_values):
    return {"patient_id": "P-001", "recorded_by": "nurse", **normal_values}
