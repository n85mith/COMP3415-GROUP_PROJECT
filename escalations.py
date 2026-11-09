import json
import os
import uuid
from datetime import datetime


ESCALATIONS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "escalations.json"
)

OPEN = "Open"

RISK_PRIORITY = {"High": 0, "Medium": 1, "Low-medium": 2, "Low": 3}


def load_escalations():

    if not os.path.exists(ESCALATIONS_FILE):
        return []

    with open(ESCALATIONS_FILE, "r") as file:
        try:
            escalations = json.load(file)
        except json.JSONDecodeError:
            escalations = None

    if isinstance(escalations, list):
        return escalations

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = ESCALATIONS_FILE.replace(".json", f".corrupt-{timestamp}.json")
    os.replace(ESCALATIONS_FILE, backup_file)

    return []


def _write_escalations(escalations):

    temp_file = ESCALATIONS_FILE + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(escalations, file, indent=4)

    os.replace(temp_file, ESCALATIONS_FILE)


def create_escalation_if_required(observation, score):

    if not score["escalation_required"]:
        return None

    escalation = {
        "id": uuid.uuid4().hex[:8],
        "patient_id": observation["patient_id"],
        "status": OPEN,
        "created_at": datetime.now().isoformat(),
        "observation_recorded_at": observation["recorded_at"],
        "recorded_by": observation["recorded_by"],
        "total_score": score["total_score"],
        "risk_level": score["risk_level"],
        "parameters_scoring_three": score["parameters_scoring_three"],
        "clinical_response": score["clinical_response"],
    }

    escalations = load_escalations()
    escalations.append(escalation)
    _write_escalations(escalations)

    return escalation


def list_escalations(status=OPEN):

    escalations = load_escalations()

    if status:
        escalations = [e for e in escalations if e["status"] == status]

    return sorted(
        escalations,
        key=lambda e: (RISK_PRIORITY.get(e["risk_level"], 99), e["created_at"]),
    )
