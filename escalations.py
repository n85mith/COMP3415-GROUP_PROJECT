import json
import uuid
from datetime import datetime

import db

OPEN = "Open"
ACKNOWLEDGED = "Acknowledged"
STATUSES = (OPEN, ACKNOWLEDGED)

MAX_NOTE_LENGTH = 1000

RISK_PRIORITY = {"High": 0, "Medium": 1, "Low-medium": 2, "Low": 3}

ROUTES = {
    "High": {"routed_to": "Critical care outreach team", "urgency": "Emergency"},
    "Medium": {"routed_to": "Ward doctor or acute care team", "urgency": "Urgent"},
    "Low-medium": {"routed_to": "Ward doctor", "urgency": "Urgent"},
}


class EscalationNotFound(Exception):
    pass


class EscalationStateError(Exception):
    pass


def route_for(risk_level):
    return ROUTES.get(risk_level, {"routed_to": "Ward doctor", "urgency": "Urgent"})


def _from_row(row):
    escalation = dict(row)
    escalation["parameters_scoring_three"] = json.loads(escalation["parameters_scoring_three"])
    return escalation


def load_escalations():
    with db.transaction() as conn:
        return [_from_row(r) for r in conn.execute("SELECT * FROM escalations ORDER BY created_at, rowid")]


def get_escalation(escalation_id):
    with db.transaction() as conn:
        row = conn.execute("SELECT * FROM escalations WHERE id = ?", (escalation_id,)).fetchone()
    return _from_row(row) if row else None


def create_escalation_if_required(observation, score, ward=None):

    if not score["escalation_required"]:
        return None

    escalation = {
        "id": uuid.uuid4().hex[:12],
        "patient_id": observation["patient_id"],
        "observation_id": observation.get("id"),
        "ward": ward,
        "status": OPEN,
        "created_at": datetime.now().isoformat(),
        "observation_recorded_at": observation["recorded_at"],
        "recorded_by": observation["recorded_by"],
        "total_score": score["total_score"],
        "risk_level": score["risk_level"],
        "parameters_scoring_three": score["parameters_scoring_three"],
        "clinical_response": score["clinical_response"],
        **route_for(score["risk_level"]),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "response_note": None,
    }

    row = {**escalation, "parameters_scoring_three": json.dumps(escalation["parameters_scoring_three"])}
    with db.transaction(write=True) as conn:
        conn.execute(
            f"INSERT INTO escalations ({', '.join(row)}) VALUES ({', '.join(':' + k for k in row)})", row
        )

    return escalation


def list_escalations(status=OPEN, ward=None):
    query = "SELECT * FROM escalations WHERE 1 = 1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if ward and ward.strip():
        query += " AND lower(ward) = lower(?)"
        params.append(ward.strip())

    with db.transaction() as conn:
        escalations = [_from_row(r) for r in conn.execute(query, params)]

    return sorted(
        escalations,
        key=lambda e: (RISK_PRIORITY.get(e["risk_level"], 99), e["created_at"]),
    )


def validate_response_note(note):
    if not isinstance(note, str) or not note.strip():
        return "Describe the clinical review or action taken."
    if len(note.strip()) > MAX_NOTE_LENGTH:
        return f"Must be at most {MAX_NOTE_LENGTH} characters."
    return None


def acknowledge_escalation(escalation_id, username, response_note):
    acknowledged_at = datetime.now().isoformat()
    with db.transaction(write=True) as conn:
        row = conn.execute("SELECT status FROM escalations WHERE id = ?", (escalation_id,)).fetchone()
        if row is None:
            raise EscalationNotFound(escalation_id)
        if row["status"] != OPEN:
            raise EscalationStateError(f"Escalation {escalation_id} is already {row['status'].lower()}.")
        conn.execute(
            "UPDATE escalations SET status = ?, acknowledged_by = ?, acknowledged_at = ?, response_note = ?"
            " WHERE id = ? AND status = ?",
            (ACKNOWLEDGED, username, acknowledged_at, response_note.strip(), escalation_id, OPEN),
        )
        updated = conn.execute("SELECT * FROM escalations WHERE id = ?", (escalation_id,)).fetchone()
    return _from_row(updated)


def count_open_by_patient():
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT patient_id, COUNT(*) AS open_count FROM escalations WHERE status = ? GROUP BY patient_id",
            (OPEN,),
        )
        return {r["patient_id"]: r["open_count"] for r in rows}
