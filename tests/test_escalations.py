import json
from datetime import datetime

import pytest

import escalations
from scoring import score_observation


def make_observation(normal_values, patient_id="P-001", **changes):
    return {
        "patient_id": patient_id,
        "recorded_by": "nurse",
        "recorded_at": "2026-11-05T09:00:00",
        **normal_values,
        **changes,
    }


def raise_for(observation):
    return escalations.create_escalation_if_required(observation, score_observation(observation))


def test_low_score_creates_no_escalation(normal_values):
    assert raise_for(make_observation(normal_values)) is None
    assert escalations.load_escalations() == []


def test_low_score_above_zero_creates_no_escalation(normal_values):
    assert raise_for(make_observation(normal_values, pulse=95)) is None
    assert escalations.list_escalations() == []


def test_single_parameter_three_creates_low_medium_escalation(normal_values):
    escalation = raise_for(make_observation(normal_values, consciousness="C"))
    assert escalation["risk_level"] == "Low-medium"
    assert escalation["parameters_scoring_three"] == ["consciousness"]


def test_medium_score_creates_open_escalation_with_details(normal_values):
    obs = make_observation(normal_values, respiratory_rate=22, pulse=95, consciousness="C")
    escalation = raise_for(obs)

    assert escalation["status"] == "Open"
    assert escalation["patient_id"] == "P-001"
    assert escalation["total_score"] == 6
    assert escalation["risk_level"] == "Medium"
    assert escalation["recorded_by"] == "nurse"
    assert escalation["observation_recorded_at"] == obs["recorded_at"]
    assert escalation["created_at"]
    assert escalation["clinical_response"]
    assert escalations.list_escalations() == [escalation]


def test_escalation_is_persisted_to_file(normal_values):
    raise_for(make_observation(normal_values, consciousness="U"))
    with open(escalations.ESCALATIONS_FILE) as file:
        assert len(json.load(file)) == 1


def test_each_qualifying_observation_creates_its_own_escalation(normal_values):
    first = raise_for(make_observation(normal_values, consciousness="C"))
    second = raise_for(make_observation(normal_values, respiratory_rate=25, consciousness="V", pulse=135))

    assert first["id"] != second["id"]
    assert len(escalations.list_escalations()) == 2


def test_different_patients_get_separate_escalations(normal_values):
    raise_for(make_observation(normal_values, patient_id="P-001", consciousness="C"))
    raise_for(make_observation(normal_values, patient_id="P-002", consciousness="C"))
    assert {e["patient_id"] for e in escalations.list_escalations()} == {"P-001", "P-002"}


def test_list_puts_highest_risk_first(normal_values):
    raise_for(make_observation(normal_values, patient_id="P-LOWMED", consciousness="C"))
    raise_for(make_observation(normal_values, patient_id="P-HIGH", respiratory_rate=25, consciousness="V", pulse=135))
    raise_for(make_observation(normal_values, patient_id="P-MED", respiratory_rate=22, pulse=95, consciousness="C"))

    order = [e["risk_level"] for e in escalations.list_escalations()]
    assert order == ["High", "Medium", "Low-medium"]


def freeze_clock(monkeypatch, *timestamps):
    times = iter(timestamps)

    class FakeDatetime:
        @staticmethod
        def now():
            return datetime.fromisoformat(next(times))

    monkeypatch.setattr(escalations, "datetime", FakeDatetime)


def test_same_risk_level_is_listed_oldest_first(normal_values, monkeypatch):
    freeze_clock(monkeypatch, "2026-11-05T10:00:00", "2026-11-05T08:00:00", "2026-11-05T09:00:00")
    for patient in ("P-NEWEST", "P-OLDEST", "P-MIDDLE"):
        raise_for(make_observation(normal_values, patient_id=patient, consciousness="C"))

    order = [e["patient_id"] for e in escalations.list_escalations()]
    assert order == ["P-OLDEST", "P-MIDDLE", "P-NEWEST"]


def test_higher_score_does_not_jump_ahead_within_a_risk_level(normal_values, monkeypatch):
    freeze_clock(monkeypatch, "2026-11-05T08:00:00", "2026-11-05T09:00:00")
    high = {"respiratory_rate": 25, "consciousness": "V"}
    early = raise_for(make_observation(normal_values, patient_id="P-EARLY", pulse=115, **high))
    late = raise_for(make_observation(normal_values, patient_id="P-LATE", pulse=135, **high))

    assert early["risk_level"] == late["risk_level"] == "High"
    assert early["total_score"] < late["total_score"]
    assert [e["patient_id"] for e in escalations.list_escalations()] == ["P-EARLY", "P-LATE"]


def test_corrupt_file_is_backed_up_not_lost(tmp_path, normal_values):
    with open(escalations.ESCALATIONS_FILE, "w") as file:
        file.write("{not json")

    assert escalations.load_escalations() == []
    assert list(tmp_path.glob("escalations.corrupt-*.json"))


def auth_headers(client, username):
    response = client.post("/api/login", json={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_high_observation_via_api_raises_escalation(client, valid_request):
    nurse, clinician = auth_headers(client, "nurse"), auth_headers(client, "clinician")
    valid_request.update(respiratory_rate=25, consciousness="V", pulse=135)
    body = client.post("/api/observations", json=valid_request, headers=nurse).json()

    assert body["escalation"]["risk_level"] == "High"
    assert body["escalation"]["recorded_by"] == "nurse"
    listed = client.get("/api/escalations", headers=clinician).json()
    assert [e["id"] for e in listed] == [body["escalation"]["id"]]


def test_listed_escalation_includes_patient_details(client, valid_request, patient_data):
    valid_request["consciousness"] = "C"
    client.post("/api/observations", json=valid_request, headers=auth_headers(client, "nurse"))

    listed = client.get("/api/escalations", headers=auth_headers(client, "clinician")).json()
    assert listed[0]["patient_name"] == patient_data["name"]
    assert listed[0]["ward"] == patient_data["ward"]
    assert listed[0]["bed"] == patient_data["bed"]


def test_normal_observation_via_api_has_no_escalation(client, valid_request):
    body = client.post("/api/observations", json=valid_request, headers=auth_headers(client, "nurse")).json()
    assert body["escalation"] is None
    assert client.get("/api/escalations", headers=auth_headers(client, "clinician")).json() == []


def test_rejected_observation_raises_no_escalation(client, valid_request):
    valid_request.update(consciousness="U", respiratory_rate=200)
    response = client.post("/api/observations", json=valid_request, headers=auth_headers(client, "nurse"))
    assert response.status_code == 422
    assert escalations.load_escalations() == []


def test_unknown_patient_raises_no_escalation(client, valid_request):
    valid_request.update(patient_id="P-404", consciousness="U")
    response = client.post("/api/observations", json=valid_request, headers=auth_headers(client, "nurse"))
    assert response.status_code == 422
    assert escalations.load_escalations() == []


def test_list_can_filter_by_status(client, valid_request):
    valid_request["consciousness"] = "C"
    client.post("/api/observations", json=valid_request, headers=auth_headers(client, "nurse"))
    clinician = auth_headers(client, "clinician")

    assert len(client.get("/api/escalations?status=Open", headers=clinician).json()) == 1
    assert client.get("/api/escalations?status=Acknowledged", headers=clinician).json() == []
    assert len(client.get("/api/escalations?status=", headers=clinician).json()) == 1


@pytest.mark.parametrize("username, expected", [("nurse", 403), ("admin", 403), (None, 401)])
def test_only_clinicians_can_list_escalations(client, valid_request, username, expected):
    valid_request["consciousness"] = "U"
    client.post("/api/observations", json=valid_request, headers=auth_headers(client, "nurse"))
    headers = auth_headers(client, username) if username else {}

    response = client.get("/api/escalations", headers=headers)
    assert response.status_code == expected
    assert "patient_id" not in response.text
