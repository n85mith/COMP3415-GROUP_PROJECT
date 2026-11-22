import re
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import audit
import auth
import db
import security
from main import INDEX_FILE, app


def attempt(client, username="nurse", password="wrong-password"):
    return client.post("/api/login", json={"username": username, "password": password})


def bearer(client, username):
    response = attempt(client, username, "password123")
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def fail(client, times, username="nurse"):
    for _ in range(times):
        assert attempt(client, username).status_code == 401


# --- login rate limiting and lockout ---------------------------------------

def test_account_locks_after_five_failures_even_with_the_right_password(client):
    fail(client, security.LOGIN_MAX_FAILURES)

    locked = attempt(client, password="password123")

    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
    assert "Too many sign-in attempts" in locked.json()["detail"]
    assert "access_token" not in locked.text


def test_lockout_only_affects_the_targeted_account(client):
    fail(client, security.LOGIN_MAX_FAILURES)
    assert attempt(client, "clinician", "password123").status_code == 200


def test_lockout_expires(client, monkeypatch):
    now = security.time.time()
    monkeypatch.setattr(security.time, "time", lambda: now)
    fail(client, security.LOGIN_MAX_FAILURES)
    assert attempt(client, password="password123").status_code == 429

    monkeypatch.setattr(security.time, "time", lambda: now + security.LOGIN_LOCKOUT_SECONDS + 1)
    assert attempt(client, password="password123").status_code == 200


def test_successful_login_resets_the_failure_count(client):
    fail(client, security.LOGIN_MAX_FAILURES - 1)
    assert attempt(client, password="password123").status_code == 200
    fail(client, security.LOGIN_MAX_FAILURES - 1)
    assert attempt(client, password="password123").status_code == 200


def test_unknown_usernames_are_locked_the_same_way(client):
    known = [attempt(client, "nurse").json() for _ in range(security.LOGIN_MAX_FAILURES)]
    unknown = [attempt(client, "ghost").json() for _ in range(security.LOGIN_MAX_FAILURES)]
    assert known == unknown

    assert attempt(client, "nurse").json() == attempt(client, "ghost").json()
    assert attempt(client, "ghost").status_code == 429


def test_unknown_username_still_runs_a_password_check(client, monkeypatch):
    calls = []
    monkeypatch.setattr("main.burn_password_check", lambda password: calls.append(password))
    attempt(client, "ghost", "guess")
    assert calls == ["guess"]


def test_too_many_failures_from_one_address_blocks_that_address(client):
    for index in range(security.LOGIN_IP_MAX_FAILURES):
        assert attempt(client, f"spray{index}").status_code == 401

    assert attempt(client, "clinician", "password123").status_code == 429


def test_failed_and_locked_logins_are_audited_without_passwords(client):
    fail(client, security.LOGIN_MAX_FAILURES)
    actions = [entry["action"] for entry in audit.list_entries()]

    assert actions.count("login_failed") == security.LOGIN_MAX_FAILURES - 1
    assert actions[0] == "login_locked"
    assert "wrong-password" not in str(audit.list_entries())


# --- password rules ----------------------------------------------------------

@pytest.mark.parametrize("password, problem", [
    ("short", "12-128"),
    ("x" * 129, "12-128"),
    ("my-nurse.jordan-pass", "username"),
    ("Password1234", "too common"),
    ("aaaaaaaaaaaaaa", "too common"),
    (None, "required"),
])
def test_weak_passwords_are_rejected(password, problem):
    assert problem in " ".join(security.password_problems(password, "nurse.jordan"))


def test_strong_password_is_accepted():
    assert security.password_problems("correct horse battery", "nurse.jordan") == []


def test_admin_cannot_create_staff_with_a_weak_password(client):
    headers = bearer(client, "admin")
    assert client.post("/api/admin/wards", json={"name": "Ward A"}, headers=headers).status_code == 201

    weak = client.post("/api/admin/staff", headers=headers, json={
        "username": "sam.lee", "name": "Sam Lee", "password": "sam.lee-123456", "role": "Nurse", "ward": "Ward A",
    })
    strong = client.post("/api/admin/staff", headers=headers, json={
        "username": "sam.lee", "name": "Sam Lee", "password": "violet otter canoe", "role": "Nurse", "ward": "Ward A",
    })

    assert weak.status_code == 422
    assert "username" in weak.json()["detail"]
    assert strong.status_code == 201


# --- security headers and XSS ----------------------------------------------

def test_page_has_a_strict_content_security_policy(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    directives = dict(part.strip().split(" ", 1) for part in csp.split(";"))

    assert "'unsafe-inline'" not in directives["script-src"]
    assert directives["frame-ancestors"] == "'none'"
    assert directives["object-src"] == "'none'"
    assert directives["base-uri"] == "'none'"


def test_csp_hash_matches_the_page_script_with_any_line_endings(tmp_path):
    html = INDEX_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")
    crlf = tmp_path / "crlf.html"
    crlf.write_bytes(html.replace("\n", "\r\n").encode("utf-8"))
    lf = tmp_path / "lf.html"
    lf.write_bytes(html.encode("utf-8"))

    assert security.page_csp(crlf) == security.page_csp(lf)
    assert re.search(r"script-src 'sha256-[A-Za-z0-9+/=]{44}';", security.page_csp(lf))


def test_page_has_no_inline_event_handlers():
    html = INDEX_FILE.read_text(encoding="utf-8")
    assert not re.search(r"\son[a-z]+\s*=", html.split("<script>")[0])
    assert "javascript:" not in html


@pytest.mark.parametrize("path", ["/", "/api/wards", "/api/login"])
def test_common_security_headers_are_sent(client, path):
    response = client.post(path, json={}) if path == "/api/login" else client.get(path)
    for name, value in security.COMMON_HEADERS.items():
        assert response.headers[name] == value


def test_api_responses_are_not_cached(client):
    headers = bearer(client, "nurse")
    assert client.get("/api/patients", headers=headers).headers["Cache-Control"] == "no-store"


# --- CSRF: the API never trusts cookies --------------------------------------

def test_login_sets_no_cookies(client):
    response = attempt(client, password="password123")
    assert "set-cookie" not in response.headers
    assert not client.cookies


def test_a_session_token_in_a_cookie_is_ignored(client):
    token = attempt(client, password="password123").json()["access_token"]
    client.cookies.set("access_token", token)
    client.cookies.set("Authorization", f"Bearer {token}")

    assert client.post("/api/patients", json={"patient_id": "P-9", "name": "X", "ward": "W", "bed": "1"}
                       ).status_code == 401


def test_cross_origin_requests_get_no_cors_permission(client):
    preflight = client.options("/api/patients", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in preflight.headers


# --- persistent sessions (US-01) ---------------------------------------------

def test_session_survives_a_server_restart(client):
    headers = bearer(client, "nurse")
    db._initialised.clear()

    restarted = TestClient(app)
    assert restarted.get("/api/patients", headers=headers).status_code == 200


def test_only_a_hash_of_the_token_is_stored(client):
    token = attempt(client, password="password123").json()["access_token"]
    with closing(sqlite3.connect(db.DB_FILE)) as conn:
        stored = conn.execute("SELECT token_hash FROM sessions").fetchall()

    assert stored == [(auth._token_key(token),)]
    assert token not in str(stored)


def test_logout_removes_the_stored_session(client):
    headers = bearer(client, "nurse")
    assert auth.count_sessions() == 1
    assert client.post("/api/logout", headers=headers).status_code == 204
    assert auth.count_sessions() == 0


# --- audit log (US-11) --------------------------------------------------------

def test_clinical_actions_are_audited(client, normal_values):
    nurse, clinician = bearer(client, "nurse"), bearer(client, "clinician")
    client.post("/api/patients", json={"patient_id": "P-1", "name": "A", "ward": "W", "bed": "1"}, headers=nurse)
    client.patch("/api/patients/P-1", json={"bed": "2"}, headers=nurse)
    escalation = client.post("/api/observations", json={"patient_id": "P-1", **normal_values, "consciousness": "U"},
                             headers=nurse).json()["escalation"]
    client.post(f"/api/escalations/{escalation['id']}/acknowledge", json={"response_note": "seen"},
                headers=clinician)

    entries = audit.list_entries()
    trail = [(e["action"], e["username"], e["target"]) for e in reversed(entries) if e["action"] != "login"]
    assert trail == [
        ("patient_created", "nurse", "P-1"),
        ("patient_updated", "nurse", "P-1"),
        ("observation_recorded", "nurse", "P-1"),
        ("escalation_created", "nurse", escalation["id"]),
        ("escalation_acknowledged", "clinician", escalation["id"]),
    ]
    assert entries[0]["details"] == {"patient_id": "P-1"}


@pytest.mark.parametrize("username, expected", [("admin", 200), ("nurse", 403), ("clinician", 403), (None, 401)])
def test_only_admins_can_read_the_audit_log(client, username, expected):
    headers = bearer(client, username) if username else {}
    assert client.get("/api/admin/audit", headers=headers).status_code == expected


def test_audit_log_can_be_filtered(client):
    headers = bearer(client, "admin")
    fail(client, 2, "nurse")

    failed = client.get("/api/admin/audit", params={"action": "login_failed"}, headers=headers).json()
    assert [e["username"] for e in failed] == ["nurse", "nurse"]
    assert client.get("/api/admin/audit", params={"action": "nope"}, headers=headers).status_code == 422
