import json
import os
from datetime import datetime

PATIENTS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "patients.json"
)

PATIENT_FIELDS = ["patient_id", "name", "ward", "bed"]


class DuplicatePatientError(Exception):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def normalize_patient_id(patient_id):
    return str(patient_id or "").strip().upper()


def validate_patient(values):
    errors = {}
    for field in PATIENT_FIELDS:
        value = values.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "This field is required."
    return errors


def load_patients():
    if not os.path.exists(PATIENTS_FILE):
        return []
    with open(PATIENTS_FILE, "r") as file:
        try:
            patients = json.load(file)
        except json.JSONDecodeError:
            patients = None
    if isinstance(patients, list):
        return patients
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = PATIENTS_FILE.replace(".json", f".corrupt-{timestamp}.json")
    os.replace(PATIENTS_FILE, backup_file)
    print(f"\nWarning: {PATIENTS_FILE} could not be read.")
    print(f"It was moved to {backup_file} and a new file was started.")
    return []


def _write_patients(patients):
    temp_file = PATIENTS_FILE + ".tmp"
    with open(temp_file, "w") as file:
        json.dump(patients, file, indent=4)
    os.replace(temp_file, PATIENTS_FILE)


def get_patient(patient_id):
    key = normalize_patient_id(patient_id)
    for patient in load_patients():
        if patient["patient_id"] == key:
            return patient
    return None


def patient_exists(patient_id):
    return get_patient(patient_id) is not None


def create_patient(values):
    patient = {
        "patient_id": normalize_patient_id(values["patient_id"]),
        "name": values["name"].strip(),
        "ward": values["ward"].strip(),
        "bed": values["bed"].strip(),
    }
    patients = load_patients()
    for existing in patients:
        if existing["patient_id"] == patient["patient_id"]:
            raise DuplicatePatientError(
                "patient_id",
                f"Patient ID {patient['patient_id']} already exists."
            )
        same_ward = existing["ward"].lower() == patient["ward"].lower()
        if same_ward and existing["bed"].lower() == patient["bed"].lower():
            raise DuplicatePatientError(
                "bed",
                f"Bed {patient['bed']} on {patient['ward']} is already "
                f"taken by {existing['patient_id']}."
            )
    patients.append(patient)
    _write_patients(patients)
    return patient


def list_patients(ward=None):
    patients = load_patients()
    if ward:
        patients = [p for p in patients if p["ward"].lower() == ward.strip().lower()]
    return sorted(patients, key=lambda p: (p["ward"].lower(), p["bed"].lower(), p["patient_id"]))


def list_wards():
    return sorted({p["ward"] for p in load_patients()}, key=str.lower)
