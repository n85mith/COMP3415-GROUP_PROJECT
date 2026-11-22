import json
import os
import sqlite3
from contextlib import contextmanager
from threading import Lock

DB_FILE = os.environ.get("CARESIGHT_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "caresight.db"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ward TEXT NOT NULL,
    bed TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS patients_ward_bed ON patients (lower(ward), lower(bed));

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    recorded_by TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    respiratory_rate INTEGER NOT NULL,
    spo2 INTEGER NOT NULL,
    supplemental_oxygen INTEGER NOT NULL,
    systolic_bp INTEGER NOT NULL,
    pulse INTEGER NOT NULL,
    consciousness TEXT NOT NULL,
    temperature REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS observations_patient ON observations (patient_id, recorded_at);

CREATE TABLE IF NOT EXISTS escalations (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    observation_id INTEGER REFERENCES observations (id),
    ward TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    observation_recorded_at TEXT NOT NULL,
    recorded_by TEXT NOT NULL,
    total_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    parameters_scoring_three TEXT NOT NULL,
    clinical_response TEXT NOT NULL,
    routed_to TEXT,
    urgency TEXT,
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    response_note TEXT
);
CREATE INDEX IF NOT EXISTS escalations_status ON escalations (status, created_at);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    username TEXT,
    action TEXT NOT NULL,
    target TEXT,
    details TEXT
);
CREATE INDEX IF NOT EXISTS audit_log_at ON audit_log (at);

CREATE TABLE IF NOT EXISTS wards (
    name TEXT PRIMARY KEY COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS staff (
    username TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Nurse', 'Clinician', 'Admin')),
    ward TEXT REFERENCES wards (name)
);
"""

LEGACY_FILES = ("patients.json", "observations.json", "escalations.json")

_initialised = set()
_init_lock = Lock()


def _connect():
    conn = sqlite3.connect(DB_FILE, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_schema():
    with _init_lock:
        if DB_FILE in _initialised:
            return
        is_new = not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            if is_new:
                _import_legacy_json(conn)
        finally:
            conn.close()
        _initialised.add(DB_FILE)


@contextmanager
def transaction(write=False):
    _ensure_schema()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.close()


def _read_legacy(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as file:
            rows = json.load(file)
    except (OSError, json.JSONDecodeError):
        rows = None
    if not isinstance(rows, list):
        print(f"Warning: {path} could not be read and was not imported. The file was left unchanged.")
        return []
    return rows


def _read_legacy_staff(path):
    empty = {"staff": {}, "wards": []}
    if not os.path.exists(path):
        return empty
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("staff"), dict) or not isinstance(
            data.get("wards"), list):
        print(f"Warning: {path} could not be read and was not imported. The file was left unchanged.")
        return empty
    return data


def _import_legacy_json(conn):
    folder = os.path.dirname(os.path.abspath(DB_FILE))
    patients, observations, escalations = (
        _read_legacy(os.path.join(folder, name)) for name in LEGACY_FILES
    )
    staff_data = _read_legacy_staff(os.path.join(folder, "staff.json"))
    if not (patients or observations or escalations or staff_data["staff"] or staff_data["wards"]):
        return

    conn.execute("BEGIN IMMEDIATE")
    try:
        for p in patients:
            conn.execute(
                "INSERT OR IGNORE INTO patients (patient_id, name, ward, bed) VALUES (?, ?, ?, ?)",
                (p["patient_id"], p["name"], p["ward"], p["bed"]),
            )
        for o in observations:
            conn.execute(
                "INSERT INTO observations (patient_id, recorded_by, recorded_at, respiratory_rate, spo2,"
                " supplemental_oxygen, systolic_bp, pulse, consciousness, temperature)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (o["patient_id"], o["recorded_by"], o["recorded_at"], o["respiratory_rate"], o["spo2"],
                 int(bool(o["supplemental_oxygen"])), o["systolic_bp"], o["pulse"], o["consciousness"],
                 o["temperature"]),
            )
        for e in escalations:
            conn.execute(
                "INSERT OR IGNORE INTO escalations (id, patient_id, status, created_at, observation_recorded_at,"
                " recorded_by, total_score, risk_level, parameters_scoring_three, clinical_response)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (e["id"], e["patient_id"], e["status"], e["created_at"], e["observation_recorded_at"],
                 e["recorded_by"], e["total_score"], e["risk_level"],
                 json.dumps(e.get("parameters_scoring_three", [])), e["clinical_response"]),
            )
        for ward in staff_data["wards"]:
            conn.execute("INSERT OR IGNORE INTO wards (name) VALUES (?)", (ward,))
        for username, user in staff_data["staff"].items():
            conn.execute(
                "INSERT OR IGNORE INTO staff (username, name, password, role, ward) VALUES (?, ?, ?, ?, ?)",
                (username.lower(), user["name"], user["password"], user["role"], user.get("ward")),
            )
    except (KeyError, TypeError, ValueError, AttributeError, sqlite3.Error) as err:
        conn.execute("ROLLBACK")
        print(f"Warning: existing JSON data could not be imported ({err!r}). The JSON files were left unchanged.")
        return
    conn.execute("COMMIT")
    print(f"Imported existing JSON data into {DB_FILE}. The JSON files were left in place.")
