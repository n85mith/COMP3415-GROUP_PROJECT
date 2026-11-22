import json
from datetime import datetime

import db

ACTIONS = (
    "login", "login_failed", "login_locked", "logout",
    "patient_created", "patient_updated", "observation_recorded",
    "escalation_created", "escalation_acknowledged",
    "staff_created", "ward_created",
)


def record(action, username=None, target=None, conn=None, **details):
    if action not in ACTIONS:
        raise ValueError(f"Unknown audit action {action!r}")
    row = (
        datetime.now().isoformat(timespec="seconds"),
        username,
        action,
        None if target is None else str(target),
        json.dumps(details, sort_keys=True) if details else None,
    )
    sql = "INSERT INTO audit_log (at, username, action, target, details) VALUES (?, ?, ?, ?, ?)"
    if conn is not None:
        conn.execute(sql, row)
        return
    with db.transaction(write=True) as own:
        own.execute(sql, row)


def list_entries(limit=200, action=None, username=None):
    query = "SELECT * FROM audit_log WHERE 1 = 1"
    params = []
    if action:
        query += " AND action = ?"
        params.append(action)
    if username:
        query += " AND username = ?"
        params.append(username.strip().lower())
    query += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 1000)))
    with db.transaction() as conn:
        rows = conn.execute(query, params).fetchall()
    entries = []
    for row in rows:
        entry = dict(row)
        entry["details"] = json.loads(entry["details"]) if entry["details"] else {}
        entries.append(entry)
    return entries
