import json
import os
import re
import tempfile
from pathlib import Path
from threading import RLock

import auth
import security
from auth import ROLES, hash_password

STAFF_FILE = Path(__file__).with_name("staff.json")
_store_lock = RLock()


class StaffValidationError(ValueError):
    pass


class StaffConflictError(ValueError):
    pass


def _load():
    path = Path(STAFF_FILE)
    if not path.exists():
        return {"staff": {}, "wards": []}

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("staff"), dict)
        or not isinstance(data.get("wards"), list)
        or not all(isinstance(ward, str) for ward in data["wards"])
        or not all(
            isinstance(username, str)
            and isinstance(user, dict)
            and isinstance(user.get("name"), str)
            and isinstance(user.get("password"), str)
            and user.get("role") in ROLES
            and (
                user.get("ward") is None
                or isinstance(user.get("ward"), str)
            )
            for username, user in data["staff"].items()
        )
    ):
        raise ValueError("Invalid staff storage format")

    return data


def _save(data):
    path = Path(STAFF_FILE)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".staff-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


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
    with _store_lock:
        stored = _load()["staff"].get(username)
        if stored is not None:
            return dict(stored)
        demo = auth.USERS.get(username)
        return dict(demo) if demo is not None else None


def list_staff():
    with _store_lock:
        stored = _load()["staff"]
        accounts = {**{key.lower(): dict(value) for key, value in auth.USERS.items()}, **stored}
        return [
            _public_user(username, accounts[username])
            for username in sorted(accounts)
        ]


def list_wards():
    with _store_lock:
        return sorted(_load()["wards"], key=str.casefold)


def create_ward(name):
    name = _text(name, "Ward name", 80)

    with _store_lock:
        data = _load()

        if any(
            existing.casefold() == name.casefold()
            for existing in data["wards"]
        ):
            raise StaffConflictError("This ward already exists.")

        data["wards"].append(name)
        _save(data)

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

    with _store_lock:
        data = _load()

        if any(
            existing.casefold() == username
            for existing in auth.USERS
        ) or any(
            existing.casefold() == username
            for existing in data["staff"]
        ):
            raise StaffConflictError("This username already exists.")

        if ward is not None:
            matching_ward = next(
                (
                    existing
                    for existing in data["wards"]
                    if existing.casefold() == ward.casefold()
                ),
                None,
            )
            if matching_ward is None:
                raise StaffValidationError(
                    "Create the ward before assigning staff to it."
                )
            ward = matching_ward

        user = {
            "name": name,
            "password": hash_password(password),
            "role": role,
            "ward": ward,
        }
        data["staff"][username] = user
        _save(data)

    return _public_user(username, user)
