import json
import pytest
import observations
import patients


def login(client, username):
    response = client.post("/api/login", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_and_get_patient(patient_data):
    patients.create_patient(dict(patient_data))
    assert patients.get_patient("P-001")["name"] == patient_data["name"]
    assert patients.get_patient("nobody") is None


def test_patient_id_is_normalized(patient_data):
    patient_data["patient_id"] = " p-001 "
    assert patients.create_patient(dict(patient_data))["patient_id"] == "P-001"
    assert patients.patient_exists("p-001")


def test_missing_fields_are_reported():
    errors = patients.validate_patient({"patient_id": "P-001", "name": " ", "ward": None})
    assert set(errors) == {"name", "ward", "bed"}


def test_corrupt_patients_file_is_kept_not_overwritten(tmp_path, patient_data):
    path = tmp_path / "patients.json"
    path.write_text("not json")

    patients.create_patient(dict(patient_data))

    backups = list(tmp_path.glob("patients.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text() == "not json"
    assert len(json.loads(path.read_text())) == 1


@pytest.mark.parametrize("username", ["nurse", "clinician"])
def test_staff_can_create_and_list_patients(client, patient_data, username):
    headers = login(client, username)

    res = client.post("/api/patients", json=patient_data, headers=headers)
    assert res.status_code == 201
    assert res.json() == patient_data

    listed = client.get("/api/patients", headers=headers).json()
    assert [p["patient_id"] for p in listed] == ["P-001"]


def test_duplicate_patient_id_is_rejected(staff_client, patient_data):
    assert staff_client.post("/api/patients", json=patient_data).status_code == 201

    res = staff_client.post("/api/patients", json={**patient_data, "patient_id": "p-001", "bed": "2"})

    assert res.status_code == 409
    assert "patient_id" in res.json()["errors"]
    assert len(patients.load_patients()) == 1


def test_occupied_bed_is_rejected(staff_client, patient_data):
    staff_client.post("/api/patients", json=patient_data)

    res = staff_client.post("/api/patients", json={**patient_data, "patient_id": "p-002", "ward": "ward a"})

    assert res.status_code == 409
    assert "bed" in res.json()["errors"]
    assert len(patients.load_patients()) == 1


def test_same_bed_number_on_another_ward_is_allowed(staff_client, patient_data):
    staff_client.post("/api/patients", json=patient_data)
    res = staff_client.post("/api/patients", json={**patient_data, "patient_id": "P-002", "ward": "Ward B"})
    assert res.status_code == 201


def test_icomplete_patient_saves_nothing(staff_client):
    res = staff_client.post("/api/patients", json={"patient_id": "P-009", "name": ""})
    assert res.status_code == 422
    assert set(res.json()["errors"]) == {"name", "ward", "bed"}
    assert patients.load_patients() == []


def test_list_can_be_filtered_by_ward(staff_client, patient_data):
    staff_client.post("/api/patients", json=patient_data)
    staff_client.post("/api/patients", json={**patient_data, "patient_id": "P-002", "ward": "Ward B"})

    filtered = staff_client.get("/api/patients", params={"ward": "ward b"}).json()
    assert [p["patient_id"] for p in filtered] == ["P-002"]
    assert staff_client.get("/api/wards").json() == ["Ward A", "Ward B"]


@pytest.mark.parametrize("credential", ["missing", "invalid", "admin"])
def test_denied_patient_create_saves_nothing(client, patient_data, credential):
    if credential == "missing":
        headers = {}
    elif credential == "invalid":
        headers = {"Authorization": "Bearer forget-token"}
    else:
        headers = login(client, "admin")

    res = client.post("/api/patients", json=patient_data, headers=headers)

    assert res.status_code == (403 if credential == "admin" else 401)
    assert patients.load_patients() == []


@pytest.mark.parametrize("url", ["/api/patients", "/api/wards", "/api/ward-list"])
def test_patients_lists_need_a_staff_session(client, url):
    assert client.get(url).status_code == 401
    assert client.get(url, headers=login(client, "admin")).status_code == 403


def test_observation_for_unknown_patient_is_rejected(staff_client, normal_values):
    res = staff_client.post("/api/observations", json={"patient_id": "P-004", **normal_values})

    assert res.status_code == 422
    assert "patient_id" in res.json()["errors"]
    assert observations.load_observations() == []


def test_observation_patient_id_matches_case_insensitively(staff_client, existing_patient, normal_values):
    res = staff_client.post("/api/observations", json={"patient_id": "p-001", **normal_values})

    assert res.status_code == 200
    assert res.json()["observation"]["patient_id"] == "P-001"


def test_ward_list_shows_latest_score_and_risk(staff_client, existing_patient, patient_data, normal_values):
    patients.create_patient({**patient_data, "patient_id": "P-002", "bed": "2"})

    staff_client.post("/api/observations", json={"patient_id": "P-001", **normal_values})
    staff_client.post("/api/observations", json={"patient_id": "P-001", **normal_values, "consciousness": "C"})

    rows = {row["patient_id"]: row for row in staff_client.get("/api/ward-list").json()}

    assert rows["P-001"]["total_score"] == 3
    assert rows["P-001"]["risk_level"] == "Low-medium"
    assert rows["P-001"]["last_observed_at"]
    assert rows["P-002"]["total_score"] is None
    assert rows["P-002"]["risk_level"] is None
