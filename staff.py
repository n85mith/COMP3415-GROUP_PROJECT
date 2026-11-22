import re

import auth
import db
import security
from auth import ROLES, hash_password


class StaffValidationError(ValueError):
    pass


class StaffConflictError(ValueError):
    pass


def _staff_row(row):
    return {"name": row["name"], "password": row["password"], "role": row["role"], "ward": row["ward"]}


def _text(value, field, maximum):
    if not isinstance(value, str) or not value.strip():
        raise StaffValidationError(f"{field} is required.")

    value = value.strip()
    if len(value) > maximum:
        raise StaffValidationError(
            f"{field} must be at most {maximum} characters."
        )

    return value


def _public_user(username, user):
    return {
        "username": username,
        "name": user["name"],
        "role": user["role"],
        "ward": user.get("ward"),
    }


def normalize_username(username):
    return _text(username, "Username", 50).lower()


def get_staff(username):
    if not isinstance(username, str):
        return None
    username = username.strip().lower()
    with db.transaction() as conn:
        row = conn.execute("SELECT * FROM staff WHERE username = ?", (username,)).fetchone()
    if row is not None:
        return _staff_row(row)
    demo = auth.USERS.get(username)
    return dict(demo) if demo is not None else None


def list_staff():
    with db.transaction() as conn:
        stored = {row["username"]: _staff_row(row) for row in conn.execute("SELECT * FROM staff")}
    accounts = {**{key.lower(): dict(value) for key, value in auth.USERS.items()}, **stored}
    return [
        _public_user(username, accounts[username])
        for username in sorted(accounts)
    ]


def list_wards():
    with db.transaction() as conn:
        rows = conn.execute("SELECT name FROM wards").fetchall()
    return sorted((row["name"] for row in rows), key=str.casefold)


def create_ward(name):
    name = _text(name, "Ward name", 80)

    with db.transaction(write=True) as conn:
        if conn.execute("SELECT 1 FROM wards WHERE name = ? COLLATE NOCASE", (name,)).fetchone():
            raise StaffConflictError("This ward already exists.")
        conn.execute("INSERT INTO wards (name) VALUES (?)", (name,))

    return {"name": name}


def create_staff(username, name, password, role, ward=None):
    username = _text(username, "Username", 50).lower()
    name = _text(name, "Name", 100)

    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,49}", username):
        raise StaffValidationError(
            "Username must contain 3-50 letters, numbers, dots, "
            "underscores or hyphens and start with a letter or number."
        )

    if not isinstance(role, str) or role not in ROLES:
        raise StaffValidationError(
            "Role must be Nurse, Clinician or Admin."
        )

    problems = security.password_problems(password, username)
    if problems:
        raise StaffValidationError(" ".join(problems))

    if ward is not None:
        ward = _text(ward, "Ward", 80)

    if role in {"Nurse", "Clinician"} and ward is None:
        raise StaffValidationError(
            "Nurses and clinicians must be assigned to a ward."
        )

    with db.transaction(write=True) as conn:
        taken = any(existing.casefold() == username for existing in auth.USERS) or conn.execute(
            "SELECT 1 FROM staff WHERE username = ?", (username,)
        ).fetchone()
        if taken:
            raise StaffConflictError("This username already exists.")

        if ward is not None:
            matching = conn.execute("SELECT name FROM wards WHERE name = ? COLLATE NOCASE", (ward,)).fetchone()
            if matching is None:
                raise StaffValidationError(
                    "Create the ward before assigning staff to it."
                )
            ward = matching["name"]

        user = {
            "name": name,
            "password": hash_password(password),
            "role": role,
            "ward": ward,
        }
        conn.execute(
            "INSERT INTO staff (username, name, password, role, ward) VALUES (?, ?, ?, ?, ?)",
            (username, user["name"], user["password"], user["role"], user["ward"]),
        )

    return _public_user(username, user)
