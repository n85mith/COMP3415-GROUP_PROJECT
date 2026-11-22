import json

import pytest

import staff
from auth import verify_password


@pytest.fixture(autouse=True)
def isolated_staff_file(tmp_path, monkeypatch):
    monkeypatch.setattr(staff, "STAFF_FILE", tmp_path / "staff.json")


def create_nurse(**overrides):
    values = {
        "username": "nurse.two",
        "name": "Taylor Smith",
        "password": "ExamplePass123!",
        "role": "Nurse",
        "ward": "Ward A",
    }
    values.update(overrides)
    return staff.create_staff(**values)


def test_admin_can_be_created_without_a_ward():
    result = staff.create_staff(
        username="admin.two",
        name="Second Admin",
        password="ExamplePass123!",
        role="Admin",
    )

    assert result["role"] == "Admin"
    assert result["ward"] is None
    assert "password" not in result


def test_create_ward_and_staff():
    staff.create_ward("Ward A")

    result = create_nurse()

    assert result == {
        "username": "nurse.two",
        "name": "Taylor Smith",
        "role": "Nurse",
        "ward": "Ward A",
    }


def test_password_is_hashed_and_not_returned():
    staff.create_ward("Ward A")
    result = create_nurse()
    stored = staff.get_staff("nurse.two")

    assert "password" not in result
    assert stored["password"] != "ExamplePass123!"
    assert verify_password("ExamplePass123!", stored["password"])
    assert "ExamplePass123!" not in staff.STAFF_FILE.read_text()


def test_staff_is_read_from_disk():
    staff.create_ward("Ward A")
    create_nurse()

    raw = json.loads(staff.STAFF_FILE.read_text())
    raw["staff"]["nurse.two"]["name"] = "Updated Name"
    staff.STAFF_FILE.write_text(json.dumps(raw))

    assert staff.get_staff("nurse.two")["name"] == "Updated Name"


def test_duplicate_username_is_case_insensitive():
    staff.create_ward("Ward A")
    create_nurse()

    with pytest.raises(staff.StaffConflictError):
        create_nurse(username="NURSE.TWO")


def test_demo_username_cannot_be_replaced():
    staff.create_ward("Ward A")

    with pytest.raises(staff.StaffConflictError):
        create_nurse(username="admin")


def test_duplicate_ward_is_case_insensitive():
    staff.create_ward("Ward A")

    with pytest.raises(staff.StaffConflictError):
        staff.create_ward("ward a")


def test_ward_assignment_uses_canonical_name():
    staff.create_ward("Ward A")
    result = create_nurse(ward="ward a")

    assert result["ward"] == "Ward A"


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "x"},
        {"username": "bad username"},
        {"name": ""},
        {"password": "short"},
        {"role": "Patient"},
        {"ward": None},
        {"ward": "Unknown Ward"},
    ],
)
def test_invalid_staff_is_not_saved(overrides):
    staff.create_ward("Ward A")
    before = staff.STAFF_FILE.read_bytes()

    with pytest.raises(staff.StaffValidationError):
        create_nurse(**overrides)

    assert staff.STAFF_FILE.read_bytes() == before


def test_staff_list_does_not_expose_passwords():
    staff.create_ward("Ward A")
    create_nurse()

    results = staff.list_staff()

    assert any(user["username"] == "nurse.two" for user in results)
    assert all("password" not in user for user in results)


def test_wards_are_sorted():
    staff.create_ward("Ward B")
    staff.create_ward("Ward A")

    assert staff.list_wards() == ["Ward A", "Ward B"]


def test_corrupt_storage_is_not_overwritten():
    staff.STAFF_FILE.write_text("{broken")
    before = staff.STAFF_FILE.read_bytes()

    with pytest.raises(json.JSONDecodeError):
        staff.create_ward("Ward A")

    assert staff.STAFF_FILE.read_bytes() == before
