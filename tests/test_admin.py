from pathlib import Path

import pytest

import staff


def login(client, username="admin", password="password123"):
    response = client.post(
        "/api/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
        "response": response.json(),
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/admin/staff"),
        ("post", "/api/admin/staff"),
        ("get", "/api/admin/wards"),
        ("post", "/api/admin/wards"),
    ],
)
def test_admin_routes_require_authentication(client, method, path):
    if method == "get":
        response = getattr(client, method)(path)
    else:
        response = getattr(client, method)(path, json={})
    assert response.status_code == 401


@pytest.mark.parametrize("username", ["nurse", "clinician"])
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/admin/staff"),
        ("post", "/api/admin/staff"),
        ("get", "/api/admin/wards"),
        ("post", "/api/admin/wards"),
    ],
)
def test_admin_routes_reject_clinical_roles(client, username, method, path):
    headers = {"Authorization": login(client, username)["Authorization"]}
    if method == "get":
        response = getattr(client, method)(path, headers=headers)
    else:
        response = getattr(client, method)(path, headers=headers, json={})
    assert response.status_code == 403


def test_admin_creates_lists_and_persists_wards(client):
    headers = {"Authorization": login(client)["Authorization"]}
    response = client.post(
        "/api/admin/wards",
        headers=headers,
        json={"name": "Ward A"},
    )
    assert response.status_code == 201
    assert response.json() == {"name": "Ward A"}
    assert client.get("/api/admin/wards", headers=headers).json() == ["Ward A"]
    duplicate = client.post(
        "/api/admin/wards",
        headers=headers,
        json={"name": "ward a"},
    )
    assert duplicate.status_code == 409


@pytest.mark.parametrize("name", ["", "   ", None])
def test_invalid_ward_names_return_422(client, name):
    headers = {"Authorization": login(client)["Authorization"]}
    response = client.post(
        "/api/admin/wards",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 422


def test_admin_creates_staff_staff_can_login_and_logout(client):
    headers = {"Authorization": login(client)["Authorization"]}
    client.post(
        "/api/admin/wards",
        headers=headers,
        json={"name": "Ward A"},
    )
    response = client.post(
        "/api/admin/staff",
        headers=headers,
        json={
            "username": "Nurse.Two",
            "name": "Taylor Smith",
            "password": "ExamplePass123!",
            "role": "Nurse",
            "ward": "ward a",
        },
    )
    assert response.status_code == 201
    assert response.json() == {
        "username": "nurse.two",
        "name": "Taylor Smith",
        "role": "Nurse",
        "ward": "Ward A",
    }
    assert "password" not in response.text

    nurse = login(client, "NURSE.TWO", "ExamplePass123!")
    assert nurse["response"]["ward"] == "Ward A"
    nurse_headers = {"Authorization": nurse["Authorization"]}
    assert client.get("/api/admin/staff", headers=nurse_headers).status_code == 403
    assert client.post("/api/logout", headers=nurse_headers).status_code == 204
    assert client.get("/api/admin/staff", headers=nurse_headers).status_code == 401


@pytest.mark.parametrize(
    ("role", "ward"),
    [
        ("Patient", "Ward A"),
        ("Nurse", None),
        ("Clinician", "Unknown Ward"),
    ],
)
def test_invalid_staff_fields_return_422(client, role, ward):
    headers = {"Authorization": login(client)["Authorization"]}
    response = client.post(
        "/api/admin/staff",
        headers=headers,
        json={
            "username": "new.staff",
            "name": "New Staff",
            "password": "ExamplePass123!",
            "role": role,
            "ward": ward,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("username", ["ADMIN", "Nurse.Two"])
def test_duplicate_usernames_include_case_variations(client, username):
    headers = {"Authorization": login(client)["Authorization"]}
    if username == "Nurse.Two":
        client.post(
            "/api/admin/wards",
            headers=headers,
            json={"name": "Ward A"},
        )
        client.post(
            "/api/admin/staff",
            headers=headers,
            json={
                "username": "nurse.two",
                "name": "First Staff",
                "password": "ExamplePass123!",
                "role": "Admin",
            },
        )
    response = client.post(
        "/api/admin/staff",
        headers=headers,
        json={
            "username": username,
            "name": "Duplicate",
            "password": "ExamplePass123!",
            "role": "Admin",
        },
    )
    assert response.status_code == 409


def test_admin_created_admin_cannot_use_clinical_routes(client):
    headers = {"Authorization": login(client)["Authorization"]}
    response = client.post(
        "/api/admin/staff",
        headers=headers,
        json={
            "username": "admin.two",
            "name": "Second Admin",
            "password": "ExamplePass123!",
            "role": "Admin",
        },
    )
    assert response.status_code == 201
    admin = login(client, "admin.two", "ExamplePass123!")
    admin_headers = {"Authorization": admin["Authorization"]}
    assert client.get("/api/patients", headers=admin_headers).status_code == 403
    assert client.get("/api/admin/staff", headers=admin_headers).status_code == 200


def test_corrupt_staff_storage_is_not_overwritten(client):
    Path(staff.STAFF_FILE).write_text("{broken")
    before = Path(staff.STAFF_FILE).read_bytes()
    headers = {"Authorization": login(client)["Authorization"]}
    response = client.get("/api/admin/staff", headers=headers)
    assert response.status_code == 503
    assert Path(staff.STAFF_FILE).read_bytes() == before
