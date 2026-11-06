import auth
import main


def test_valid_login_returns_role(client):
    res = client.post("/api/login", json={"username": "nurse", "password": "password123"})
    assert res.status_code == 200
    assert res.json()["role"] == "Nurse"


def test_invalid_login_is_generic_401(client):
    wrong_pass = client.post("/api/login", json={"username": "nurse", "password": "nope"})
    wrong_user = client.post("/api/login", json={"username": "ghost", "password": "nope"})
    assert wrong_pass.status_code == wrong_user.status_code == 401
    assert wrong_pass.json() == wrong_user.json()


def test_passwords_are_stored_as_salted_hashes():
    stored = main.USERS["nurse"]["password"]
    assert "password123" not in stored
    assert auth.hash_password("password123") != auth.hash_password("password123")
    assert main.verify_password("password123", stored)


def test_self_registration_is_removed(client):
    before = dict(main.USERS)
    response = client.post("/api/register", json={"username": "pat1", "password": "secret1", "full_name": "Pat One"})
    assert response.status_code == 404
    assert main.USERS == before
    assert {user["role"] for user in main.USERS.values()} == {"Nurse", "Clinician", "Admin"}


def test_valid_observation_is_saved_and_scored(staff_client, valid_request):
    res = staff_client.post("/api/observations", json=valid_request)
    assert res.status_code == 200
    body = res.json()
    assert body["observation"]["recorded_by"] == "nurse"
    assert body["observation"]["recorded_at"]
    assert body["score"]["total_score"] == 0

    history = staff_client.get("/api/patients/P-001/observations").json()
    assert len(history) == 1


def test_out_of_range_value_saves_nothing_and_names_the_field(staff_client, valid_request):
    valid_request["respiratory_rate"] = 200
    res = staff_client.post("/api/observations", json=valid_request)
    assert res.status_code == 422
    assert "respiratory_rate" in res.json()["errors"]
    assert staff_client.get("/api/patients/P-001/observations").json() == []


def test_missing_parameter_saves_nothing(staff_client, valid_request):
    del valid_request["temperature"]
    res = staff_client.post("/api/observations", json=valid_request)
    assert res.status_code == 422
    assert "temperature" in res.json()["errors"]
    assert staff_client.get("/api/patients/P-001/observations").json() == []


def test_missing_patient_id_is_rejected(staff_client, valid_request):
    valid_request["patient_id"] = "  "
    res = staff_client.post("/api/observations", json=valid_request)
    assert res.status_code == 422
    assert "patient_id" in res.json()["errors"]


def test_response_contains_breakdown_that_adds_up(staff_client, valid_request):
    valid_request.update(respiratory_rate=22, pulse=95, consciousness="C")
    score = staff_client.post("/api/observations", json=valid_request).json()["score"]

    assert len(score["breakdown"]) == 7
    assert sum(row["sub_score"] for row in score["breakdown"]) == score["total_score"]
    assert score["parameters_scoring_three"] == ["consciousness"]
    assert score["total_score"] == 6
    assert score["risk_level"] == "Medium"
    assert score["escalation_required"] is True
    assert score["next_observation_due"]


def test_history_is_scored_per_observation(staff_client, valid_request):
    staff_client.post("/api/observations", json=valid_request)
    valid_request["pulse"] = 135
    staff_client.post("/api/observations", json=valid_request)

    totals = [item["score"]["total_score"] for item in staff_client.get("/api/patients/P-001/observations").json()]
    assert totals == [0, 3]
