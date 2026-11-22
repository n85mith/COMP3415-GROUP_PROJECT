from datetime import datetime
import json
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import auth as auth_module
import escalations
import notifications
import observations
import patients
import staff
from auth import (
    ROLES, SESSION_TTL_SECONDS, bearer_scheme, create_session, get_account, get_current_user,
    require_role, revoke_session, verify_password,
)
from scoring import score_observation

USERS = auth_module.USERS

app = FastAPI(title="CareSight")


class LoginRequest(BaseModel):
    username: str
    password: str


class PatientRequest(BaseModel):
    patient_id: Optional[Any] = None
    name: Optional[Any] = None
    ward: Optional[Any] = None
    bed: Optional[Any] = None


class PatientUpdateRequest(BaseModel):
    name: Optional[Any] = None
    ward: Optional[Any] = None
    bed: Optional[Any] = None


class AcknowledgeRequest(BaseModel):
    response_note: Optional[Any] = None


class ObservationRequest(BaseModel):
    patient_id: str = ""
    respiratory_rate: Optional[Any] = None
    spo2: Optional[Any] = None
    supplemental_oxygen: Optional[Any] = None
    systolic_bp: Optional[Any] = None
    pulse: Optional[Any] = None
    consciousness: Optional[Any] = None
    temperature: Optional[Any] = None


class StaffRequest(BaseModel):
    username: str = ""
    name: str = ""
    password: str = ""
    role: str = ""
    ward: Optional[str] = None


class WardRequest(BaseModel):
    name: str = ""


@app.get("/")
def serve_ui():
    return FileResponse(Path(__file__).parent / "index.html")


@app.post("/api/login")
def login(data: LoginRequest, response: Response):
    username = data.username.strip().lower()
    user = get_account(username)
    if (
        not user
        or user["role"] not in ROLES
        or not verify_password(data.password, user["password"])
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.headers["Cache-Control"] = "no-store"
    return {
        "access_token": create_session(username),
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "username": username,
        "name": user["name"],
        "role": user["role"],
        "ward": user.get("ward"),
    }


@app.post("/api/logout", status_code=204)
def logout(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    revoke_session(credentials.credentials)


@app.post("/api/observations")
def record_observation(
    data: ObservationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    values = data.model_dump()
    errors = {}

    if not values["patient_id"].strip():
        errors["patient_id"] = "This field is required."
    elif not patients.patient_exists(values["patient_id"]):
        errors["patient_id"] = "Unknown patient ID. Create the patient first."

    errors.update(observations.validate_observation_values(values))

    if errors:
        return JSONResponse(status_code=422, content={"detail": "Invalid observation", "errors": errors})

    observation = {
        "patient_id": patients.normalize_patient_id(values["patient_id"]),
        "recorded_by": user["username"],
        "recorded_at": datetime.now().isoformat(),
    }
    for field in observations.OBSERVATION_FIELDS:
        observation[field["id"]] = values[field["id"]]

    observations.save_observation(observation)
    score = score_observation(observation)
    patient = patients.get_patient(observation["patient_id"]) or {}
    escalation = escalations.create_escalation_if_required(observation, score, ward=patient.get("ward"))
    if escalation is not None:
        background_tasks.add_task(
            notifications.send_escalation_notification,
            escalation,
        )

    return {"observation": observation, "score": score, "escalation": escalation}


@app.get("/api/patients/{patient_id}/observations")
def patient_history(
    patient_id: str,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    history = observations.get_observations_for_patient(patients.normalize_patient_id(patient_id))
    return [{"observation": obs, "score": score_observation(obs)} for obs in history]


@app.post("/api/patients", status_code=201)
def create_patient(
    data: PatientRequest,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    values = data.model_dump()
    errors = patients.validate_patient(values)

    if errors:
        return JSONResponse(status_code=422, content={"detail": "Invalid patient", "errors": errors})

    try:
        return patients.create_patient(values)
    except patients.DuplicatePatientError as err:
        return JSONResponse(status_code=409, content={"detail": err.message, "errors": {err.field: err.message}})


@app.get("/api/patients/{patient_id}")
def get_patient(
    patient_id: str,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    patient = patients.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.patch("/api/patients/{patient_id}")
def update_patient(
    patient_id: str,
    data: PatientUpdateRequest,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    values = data.model_dump()
    errors = patients.validate_patient_update(values)
    if errors:
        return JSONResponse(status_code=422, content={"detail": "Invalid patient", "errors": errors})

    try:
        patient = patients.update_patient(patient_id, values)
    except patients.DuplicatePatientError as err:
        return JSONResponse(status_code=409, content={"detail": err.message, "errors": {err.field: err.message}})

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get("/api/patients")
def list_patients(
    ward: Optional[str] = None,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    return patients.list_patients(ward)


@app.get("/api/wards")
def list_wards(user: dict = Depends(require_role("Nurse", "Clinician"))):
    return patients.list_wards()


@app.get("/api/ward-list")
def ward_list(
    ward: Optional[str] = None,
    user: dict = Depends(require_role("Nurse", "Clinician")),
):
    rows = []
    open_counts = escalations.count_open_by_patient()

    for patient in patients.list_patients(ward):
        latest = observations.get_latest_observation(patient["patient_id"])
        score = score_observation(latest) if latest else None

        rows.append({
            **patient,
            "last_observed_at": latest["recorded_at"] if latest else None,
            "total_score": score["total_score"] if score else None,
            "risk_level": score["risk_level"] if score else None,
            "escalation_required": score["escalation_required"] if score else None,
            "next_observation_due": score["next_observation_due"] if score else None,
            "open_escalations": open_counts.get(patient["patient_id"], 0),
        })

    return rows


@app.get("/api/admin/staff")
def list_admin_staff(user: dict = Depends(require_role("Admin"))):
    try:
        return staff.list_staff()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="Staff storage is unavailable")


@app.post("/api/admin/staff", status_code=201)
def create_admin_staff(
    data: StaffRequest,
    user: dict = Depends(require_role("Admin")),
):
    try:
        return staff.create_staff(
            data.username,
            data.name,
            data.password,
            data.role,
            data.ward,
        )
    except staff.StaffValidationError as err:
        return JSONResponse(
            status_code=422,
            content={"detail": str(err), "errors": {"staff": str(err)}},
        )
    except staff.StaffConflictError as err:
        return JSONResponse(
            status_code=409,
            content={"detail": str(err), "errors": {"username": str(err)}},
        )
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="Staff storage is unavailable")


@app.get("/api/admin/wards")
def list_admin_wards(user: dict = Depends(require_role("Admin"))):
    try:
        return staff.list_wards()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="Staff storage is unavailable")


@app.post("/api/admin/wards", status_code=201)
def create_admin_ward(
    data: WardRequest,
    user: dict = Depends(require_role("Admin")),
):
    try:
        return staff.create_ward(data.name)
    except staff.StaffValidationError as err:
        return JSONResponse(
            status_code=422,
            content={"detail": str(err), "errors": {"name": str(err)}},
        )
    except staff.StaffConflictError as err:
        return JSONResponse(
            status_code=409,
            content={"detail": str(err), "errors": {"name": str(err)}},
        )
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="Staff storage is unavailable")


@app.get("/api/escalations")
def list_escalations(
    status: Optional[str] = escalations.OPEN,
    ward: Optional[str] = None,
    user: dict = Depends(require_role("Clinician")),
):
    if status and status not in escalations.STATUSES:
        allowed = ", ".join(escalations.STATUSES)
        raise HTTPException(status_code=422, detail=f"Status must be one of: {allowed} (or empty for all)")
    return [_with_patient(e) for e in escalations.list_escalations(status or None, ward)]


def _with_patient(escalation):
    patient = patients.get_patient(escalation["patient_id"]) or {}
    return {
        **escalation,
        "patient_name": patient.get("name"),
        "ward": patient.get("ward", escalation.get("ward")),
        "bed": patient.get("bed"),
    }


@app.get("/api/escalations/{escalation_id}")
def get_escalation(
    escalation_id: str,
    user: dict = Depends(require_role("Clinician")),
):
    escalation = escalations.get_escalation(escalation_id)
    if escalation is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _with_patient(escalation)


@app.post("/api/escalations/{escalation_id}/acknowledge")
def acknowledge_escalation(
    escalation_id: str,
    data: AcknowledgeRequest,
    user: dict = Depends(require_role("Clinician")),
):
    error = escalations.validate_response_note(data.response_note)
    if error:
        return JSONResponse(status_code=422, content={"detail": error, "errors": {"response_note": error}})

    try:
        escalation = escalations.acknowledge_escalation(escalation_id, user["username"], data.response_note)
    except escalations.EscalationNotFound:
        raise HTTPException(status_code=404, detail="Escalation not found")
    except escalations.EscalationStateError as err:
        raise HTTPException(status_code=409, detail=str(err))

    return _with_patient(escalation)
