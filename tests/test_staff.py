import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import db
import staff
from auth import verify_password


def database_dump():
    with closing(sqlite3.connect(db.DB_FILE)) as conn:
        return "\n".join(conn.iterdump())


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
    assert "ExamplePass123!" not in database_dump()
    assert "ExamplePass123!" not in Path(db.DB_FILE).read_bytes().decode("latin-1")


def test_staff_is_read_from_the_database():
    staff.create_ward("Ward A")
    create_nurse()

    with closing(sqlite3.connect(db.DB_FILE)) as conn, conn:
        conn.execute("UPDATE staff SET name = 'Updated Name' WHERE username = 'nurse.two'")

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
    before = database_dump()

    with pytest.raises(staff.StaffValidationError):
        create_nurse(**overrides)

    assert database_dump() == before


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


def test_corrupt_legacy_staff_file_is_not_overwritten(tmp_path):
    legacy = tmp_path / "staff.json"
    legacy.write_text("{broken")
    before = legacy.read_bytes()

    staff.create_ward("Ward A")

    assert legacy.read_bytes() == before
    assert staff.list_wards() == ["Ward A"]


def test_legacy_staff_file_is_imported(tmp_path):
    stored = {"name": "Legacy Nurse", "password": staff.hash_password("violet otter canoe"),
              "role": "Nurse", "ward": "Ward L"}
    (tmp_path / "staff.json").write_text(json.dumps({"staff": {"legacy.nurse": stored}, "wards": ["Ward L"]}))

    assert staff.list_wards() == ["Ward L"]
    assert staff.get_staff("legacy.nurse")["name"] == "Legacy Nurse"
    assert verify_password("violet otter canoe", staff.get_staff("legacy.nurse")["password"])
