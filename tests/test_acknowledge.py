import threading

import pytest

import escalations
import patients


def headers_for(client, username):
    response = client.post("/api/login", json={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def raised(client, valid_request):
    valid_request.update(respiratory_rate=25, consciousness="V", pulse=135)
    body = client.post("/api/observations", json=valid_request, headers=headers_for(client, "nurse")).json()
    return body["escalation"]


@pytest.fixture
def clinician(client):
    return headers_for(client, "clinician")


def acknowledge(client, headers, escalation_id, note="Reviewed at bedside, fluids started"):
    return client.post(f"/api/escalations/{escalation_id}/acknowledge", json={"response_note": note}, headers=headers)


@pytest.mark.parametrize("risk, values, team", [
    ("High", {"respiratory_rate": 25, "consciousness": "V", "pulse": 135}, "Critical care outreach team"),
    ("Medium", {"respiratory_rate": 22, "pulse": 95, "consciousness": "C"}, "Ward doctor or acute care team"),
    ("Low-medium", {"consciousness": "C"}, "Ward doctor"),
])
def test_escalation_is_routed_by_risk_level(client, valid_request, risk, values, team):
    valid_request.update(values)
    body = client.post("/api/observations", json=valid_request, headers=headers_for(client, "nurse")).json()
    escalation = body["escalation"]

    assert escalation["risk_level"] == risk
    assert escalation["routed_to"] == team
    assert escalation["urgency"] == ("Emergency" if risk == "High" else "Urgent")
    assert escalation["ward"] == "Ward A"
    assert escalation["observation_id"] == body["observation"]["id"]


def test_escalations_can_be_filtered_by_ward(client, valid_request, patient_data, clinician):
    patients.create_patient({**patient_data, "patient_id": "P-002", "ward": "Ward B"})
    nurse = headers_for(client, "nurse")
    for patient_id in ("P-001", "P-002"):
        client.post("/api/observations", json={**valid_request, "patient_id": patient_id, "consciousness": "C"},
                    headers=nurse)

    listed = client.get("/api/escalations", params={"ward": "ward b"}, headers=clinician).json()
    assert [e["patient_id"] for e in listed] == ["P-002"]
    assert len(client.get("/api/escalations", headers=clinician).json()) == 2


def test_unknown_status_filter_is_rejected(client, clinician):
    assert client.get("/api/escalations?status=Closed", headers=clinician).status_code == 422


def test_clinician_acknowledges_with_a_response_note(client, raised, clinician):
    res = acknowledge(client, clinician, raised["id"], "  Reviewed at bedside  ")

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "Acknowledged"
    assert body["acknowledged_by"] == "clinician"
    assert body["acknowledged_at"]
    assert body["response_note"] == "Reviewed at bedside"
    assert body["patient_name"] == "Max Mustermann"
    assert escalations.get_escalation(raised["id"])["status"] == "Acknowledged"


def test_acknowledged_escalation_leaves_the_open_list(client, raised, clinician):
    acknowledge(client, clinician, raised["id"])

    assert client.get("/api/escalations", headers=clinician).json() == []
    acknowledged = client.get("/api/escalations?status=Acknowledged", headers=clinician).json()
    assert [e["id"] for e in acknowledged] == [raised["id"]]
    assert len(client.get("/api/escalations?status=", headers=clinician).json()) == 1


def test_escalation_cannot_be_acknowledged_twice(client, raised, clinician):
    assert acknowledge(client, clinician, raised["id"], "first").status_code == 200

    res = acknowledge(client, clinician, raised["id"], "second")

    assert res.status_code == 409
    assert escalations.get_escalation(raised["id"])["response_note"] == "first"


def test_simultaneous_acknowledgements_only_one_wins(raised):
    results = []

    def attempt(name):
        try:
            escalations.acknowledge_escalation(raised["id"], name, f"note from {name}")
            results.append(name)
        except escalations.EscalationStateError:
            results.append("conflict")

    threads = [threading.Thread(target=attempt, args=(f"clinician{i}",)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    winners = [r for r in results if r != "conflict"]
    assert len(winners) == 1
    assert escalations.get_escalation(raised["id"])["acknowledged_by"] == winners[0]


@pytest.mark.parametrize("note", ["", "   ", None, 42, "x" * 1001])
def test_acknowledge_needs_a_valid_note(client, raised, clinician, note):
    res = acknowledge(client, clinician, raised["id"], note)

    assert res.status_code == 422
    assert "response_note" in res.json()["errors"]
    assert escalations.get_escalation(raised["id"])["status"] == "Open"


def test_unknown_escalation_is_404(client, clinician):
    assert acknowledge(client, clinician, "nope").status_code == 404
    assert client.get("/api/escalations/nope", headers=clinician).status_code == 404


def test_get_single_escalation(client, raised, clinician):
    body = client.get(f"/api/escalations/{raised['id']}", headers=clinician).json()
    assert body["id"] == raised["id"]
    assert body["bed"] == "1"


@pytest.mark.parametrize("username, expected", [("nurse", 403), ("admin", 403), (None, 401)])
def test_only_clinicians_can_acknowledge(client, raised, username, expected):
    headers = headers_for(client, username) if username else {}

    assert acknowledge(client, headers, raised["id"]).status_code == expected
    assert client.get(f"/api/escalations/{raised['id']}", headers=headers).status_code == expected
    assert escalations.get_escalation(raised["id"])["status"] == "Open"


def test_new_observation_after_acknowledgement_raises_a_new_escalation(client, raised, clinician, valid_request):
    acknowledge(client, clinician, raised["id"])
    valid_request["consciousness"] = "C"
    client.post("/api/observations", json=valid_request, headers=headers_for(client, "nurse"))

    [open_escalation] = client.get("/api/escalations", headers=clinician).json()
    assert open_escalation["id"] != raised["id"]


def test_moving_a_patient_moves_their_open_escalations(client, raised, clinician):
    client.patch("/api/patients/P-001", json={"ward": "Ward C", "bed": "9"}, headers=clinician)

    assert escalations.get_escalation(raised["id"])["ward"] == "Ward C"
    assert len(client.get("/api/escalations?ward=Ward C", headers=clinician).json()) == 1
