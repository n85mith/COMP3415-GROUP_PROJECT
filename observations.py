from datetime import datetime

import db
import patients
from scoring import score_observation


OBSERVATION_FIELDS = [
    {
        "id": "respiratory_rate",
        "label": "Respiratory rate (breaths/min) (min 1, max 60)",
        "type": "int",
        "min": 1,
        "max": 60
    },
    {
        "id": "spo2",
        "label": "SpO2 (min 50%, max 100%)",
        "type": "int",
        "min": 50,
        "max": 100
    },
    {
        "id": "supplemental_oxygen",
        "label": "Is the patient on supplemental oxygen? (Y/N)",
        "type": "boolean"
    },
    {
        "id": "systolic_bp",
        "label": "Systolic blood pressure (mmHg) (min 40, max 300)",
        "type": "int",
        "min": 40,
        "max": 300
    },
    {
        "id": "pulse",
        "label": "Pulse (beats/min) (min 20, max 250)",
        "type": "int",
        "min": 20,
        "max": 250
    },
    {
        "id": "consciousness",
        "label": (
            "Consciousness level:\n"
            "(A = Alert, C = New confusion, V = Responds to voice, "
            "P = Responds to pain, U = Unresponsive)"
        ),
        "type": "choice",
        "options": ["A", "C", "V", "P", "U"]
    },
    {
        "id": "temperature",
        "label": "Temperature (C) (min 30.0, max 43.0)",
        "type": "float",
        "min": 30.0,
        "max": 43.0
    }
]


def get_valid_value(field):

    while True:
        answer = input(f"\n{field['label']}: ").strip()

        if field["type"] == "boolean":
            answer = answer.upper()

            if answer == "Y":
                return True
            if answer == "N":
                return False

            print("Invalid input. Enter Y or N.")
            continue

        if field["type"] == "choice":
            answer = answer.upper()

            if answer in field["options"]:
                return answer

            print("Invalid input. Enter one of:", ", ".join(field["options"]))
            continue

        try:
            if field["type"] == "int":
                value = int(answer)
            else:
                value = float(answer)
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if value < field["min"] or value > field["max"]:
            print(
                f"Invalid value. Enter a number between "
                f"{field['min']} and {field['max']}."
            )
            continue

        return value


def get_required_text(prompt):

    while True:
        answer = input(prompt).strip()

        if answer:
            return answer

        print("This field cannot be empty.")


def collect_observation():

    observation = {}

    while True:
        patient_id = patients.normalize_patient_id(get_required_text("Enter patient ID: "))
        if patients.patient_exists(patient_id):
            break
        print("Unknown patient ID. Create the patient in the web app first.")
    observation["patient_id"] = patient_id
    observation["recorded_by"] = get_required_text("Enter your staff username: ")
    observation["recorded_at"] = datetime.now().isoformat()

    for field in OBSERVATION_FIELDS:
        observation[field["id"]] = get_valid_value(field)

    return observation


def _from_row(row):
    observation = dict(row)
    observation["supplemental_oxygen"] = bool(observation["supplemental_oxygen"])
    return observation


def load_observations():
    with db.transaction() as conn:
        return [_from_row(r) for r in conn.execute("SELECT * FROM observations ORDER BY id")]


def save_observation(observation):
    observation.setdefault("recorded_at", datetime.now().isoformat())
    columns = ["patient_id", "recorded_by", "recorded_at"] + [field["id"] for field in OBSERVATION_FIELDS]
    values = [observation[c] for c in columns]
    values[columns.index("supplemental_oxygen")] = int(bool(observation["supplemental_oxygen"]))

    with db.transaction(write=True) as conn:
        cursor = conn.execute(
            f"INSERT INTO observations ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            values,
        )
        observation["id"] = cursor.lastrowid

    return observation


def get_observations_for_patient(patient_id):
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM observations WHERE patient_id = ? ORDER BY recorded_at, id", (patient_id,)
        )
        return [_from_row(r) for r in rows]


def get_latest_observation(patient_id):
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT * FROM observations WHERE patient_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
            (patient_id,),
        ).fetchone()
    return _from_row(row) if row else None


def validate_observation_values(values):

    errors = {}

    for field in OBSERVATION_FIELDS:
        field_id = field["id"]
        value = values.get(field_id)

        if value is None or value == "":
            errors[field_id] = "This field is required."
            continue

        if field["type"] == "boolean":
            if not isinstance(value, bool):
                errors[field_id] = "Must be true or false."

        elif field["type"] == "choice":
            if value not in field["options"]:
                errors[field_id] = "Must be one of: " + ", ".join(field["options"])

        else:
            is_number = isinstance(value, (int, float)) and not isinstance(value, bool)

            if not is_number or (field["type"] == "int" and value != int(value)):
                kind = "a whole number" if field["type"] == "int" else "a number"
                errors[field_id] = f"Must be {kind}."
            elif value < field["min"] or value > field["max"]:
                errors[field_id] = (
                    f"Must be between {field['min']} and {field['max']}."
                )

    return errors


def display_observation(observation, score_result):

    print("\n==============================")
    print("Observation Saved")
    print("==============================")

    print("Patient ID:", observation["patient_id"])
    print("Recorded by:", observation["recorded_by"])
    print("Recorded at:", observation["recorded_at"])

    print("\nObservation Values:")

    for field in OBSERVATION_FIELDS:
        value = observation[field["id"]]

        if field["type"] == "boolean":
            value = "Yes" if value else "No"

        print(f"{field['label']}: {value}")

    print("\n==============================")
    print("NEWS2 Result")
    print("==============================")

    for row in score_result["breakdown"]:
        flag = "  <-- scores 3" if row["scores_three"] else ""
        print(f"{row['label']}: {row['raw_value']} -> {row['sub_score']}{flag}")

    print("\nTotal score:", score_result["total_score"])
    print("Risk level:", score_result["risk_level"])
    print("Monitoring:", score_result["monitoring_frequency"])
    print("Next observation due:", score_result["next_observation_due"])
    print("Escalation required:", score_result["escalation_required"])
    print("Clinical response:", score_result["clinical_response"])


def main():
    print("Welcome to CareSight Observation Entry")

    try:
        observation = collect_observation()
    except (KeyboardInterrupt, EOFError):
        print("\n\nEntry cancelled. Nothing was saved.")
        return

    save_observation(observation)
    print(f"\nSaved to {db.DB_FILE}")

    score_result = score_observation(observation)
    display_observation(observation, score_result)


if __name__ == "__main__":
    main()
