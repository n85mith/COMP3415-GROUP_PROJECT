import json
import os
from datetime import datetime

from scoring import score_observation


OBSERVATIONS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "observations.json"
)


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

    observation["patient_id"] = get_required_text("Enter patient ID: ")
    observation["recorded_by"] = get_required_text("Enter your staff username: ")
    observation["recorded_at"] = datetime.now().isoformat()

    for field in OBSERVATION_FIELDS:
        observation[field["id"]] = get_valid_value(field)

    return observation


def load_observations():

    if not os.path.exists(OBSERVATIONS_FILE):
        return []

    with open(OBSERVATIONS_FILE, "r") as file:
        try:
            observations = json.load(file)
        except json.JSONDecodeError:
            observations = None

    if isinstance(observations, list):
        return observations

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = OBSERVATIONS_FILE.replace(".json", f".corrupt-{timestamp}.json")
    os.replace(OBSERVATIONS_FILE, backup_file)
    print(f"\nWarning: {OBSERVATIONS_FILE} could not be read.")
    print(f"It was moved to {backup_file} and a new file was started.")

    return []


def save_observation(observation):

    observations = load_observations()
    observations.append(observation)

    temp_file = OBSERVATIONS_FILE + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(observations, file, indent=4)

    os.replace(temp_file, OBSERVATIONS_FILE)

    return observation


def get_observations_for_patient(patient_id):

    observations = load_observations()
    patient_observations = []

    for observation in observations:
        if observation["patient_id"] == patient_id:
            patient_observations.append(observation)

    return patient_observations


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
    print(f"\nSaved to {OBSERVATIONS_FILE}")

    score_result = score_observation(observation)
    display_observation(observation, score_result)


if __name__ == "__main__":
    main()
