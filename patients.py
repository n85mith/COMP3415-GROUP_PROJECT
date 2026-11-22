import db

PATIENT_FIELDS = ["patient_id", "name", "ward", "bed"]
EDITABLE_FIELDS = ["name", "ward", "bed"]
MAX_LENGTH = {"patient_id": 32, "name": 100, "ward": 50, "bed": 20}


class DuplicatePatientError(Exception):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def normalize_patient_id(patient_id):
    return str(patient_id or "").strip().upper()


def _check_field(field, value):
    if not isinstance(value, str) or not value.strip():
        return "This field is required."
    if len(value.strip()) > MAX_LENGTH[field]:
        return f"Must be at most {MAX_LENGTH[field]} characters."
    return None


def validate_patient(values):
    errors = {}
    for field in PATIENT_FIELDS:
        message = _check_field(field, values.get(field))
        if message:
            errors[field] = message
    return errors


def validate_patient_update(values):
    errors = {}
    provided = {field: values[field] for field in EDITABLE_FIELDS if values.get(field) is not None}
    if not provided:
        return {"name": "Provide at least one of name, ward or bed."}
    for field, value in provided.items():
        message = _check_field(field, value)
        if message:
            errors[field] = message
    return errors


def _row(row):
    return dict(row) if row is not None else None


def load_patients():
    with db.transaction() as conn:
        return [_row(r) for r in conn.execute("SELECT * FROM patients ORDER BY rowid")]


def get_patient(patient_id):
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE patient_id = ?", (normalize_patient_id(patient_id),)
        ).fetchone()
    return _row(row)


def patient_exists(patient_id):
    return get_patient(patient_id) is not None


def _bed_taken(conn, ward, bed, except_id=None):
    return conn.execute(
        "SELECT patient_id FROM patients WHERE lower(ward) = lower(?) AND lower(bed) = lower(?)"
        " AND patient_id IS NOT ?",
        (ward, bed, except_id),
    ).fetchone()


def create_patient(values):
    patient = {
        "patient_id": normalize_patient_id(values["patient_id"]),
        "name": values["name"].strip(),
        "ward": values["ward"].strip(),
        "bed": values["bed"].strip(),
    }
    with db.transaction(write=True) as conn:
        if conn.execute("SELECT 1 FROM patients WHERE patient_id = ?", (patient["patient_id"],)).fetchone():
            raise DuplicatePatientError("patient_id", f"Patient ID {patient['patient_id']} already exists.")
        occupant = _bed_taken(conn, patient["ward"], patient["bed"])
        if occupant:
            raise DuplicatePatientError(
                "bed", f"Bed {patient['bed']} on {patient['ward']} is already taken by {occupant['patient_id']}."
            )
        conn.execute(
            "INSERT INTO patients (patient_id, name, ward, bed) VALUES (:patient_id, :name, :ward, :bed)", patient
        )
    return patient


def update_patient(patient_id, values):
    key = normalize_patient_id(patient_id)
    with db.transaction(write=True) as conn:
        current = _row(conn.execute("SELECT * FROM patients WHERE patient_id = ?", (key,)).fetchone())
        if current is None:
            return None
        for field in EDITABLE_FIELDS:
            if values.get(field) is not None:
                current[field] = values[field].strip()
        occupant = _bed_taken(conn, current["ward"], current["bed"], except_id=key)
        if occupant:
            raise DuplicatePatientError(
                "bed", f"Bed {current['bed']} on {current['ward']} is already taken by {occupant['patient_id']}."
            )
        conn.execute(
            "UPDATE patients SET name = :name, ward = :ward, bed = :bed WHERE patient_id = :patient_id", current
        )
        conn.execute(
            "UPDATE escalations SET ward = ? WHERE patient_id = ? AND status = 'Open'", (current["ward"], key)
        )
    return current


def list_patients(ward=None):
    query = "SELECT * FROM patients"
    params = ()
    if ward and ward.strip():
        query += " WHERE lower(ward) = lower(?)"
        params = (ward.strip(),)
    query += " ORDER BY lower(ward), lower(bed), patient_id"
    with db.transaction() as conn:
        return [_row(r) for r in conn.execute(query, params)]


def list_wards():
    with db.transaction() as conn:
        rows = conn.execute("SELECT DISTINCT ward FROM patients").fetchall()
    wards = {r["ward"] for r in rows}
    import staff

    wards.update(staff.list_wards())
    return sorted(wards, key=str.lower)
