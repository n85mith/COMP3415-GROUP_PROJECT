from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import observations
import patients
from auth import (
    ROLES, SESSION_TTL_SECONDS, USERS, bearer_scheme, create_session, get_current_user,
    require_role, revoke_session, verify_password,
)
from scoring import score_observation

app = FastAPI(title="CareSight")


class LoginRequest(BaseModel):
    username: str
    password: str


class PatientRequest(BaseModel):
    patient_id: Optional[Any] = None
    name: Optional[Any] = None
    ward: Optional[Any] = None
    bed: Optional[Any] = None


class ObservationRequest(BaseModel):
    patient_id: str = ""
    respiratory_rate: Optional[Any] = None
    spo2: Optional[Any] = None
    supplemental_oxygen: Optional[Any] = None
    systolic_bp: Optional[Any] = None
    pulse: Optional[Any] = None
    consciousness: Optional[Any] = None
    temperature: Optional[Any] = None


@app.get("/")
def serve_ui():
    return FileResponse(Path(__file__).parent / "index.html")


@app.post("/api/login")
def login(data: LoginRequest, response: Response):
    username = data.username.lower().strip()
    user = USERS.get(username)
    if not user or user["role"] not in ROLES or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.headers["Cache-Control"] = "no-store"
    return {
        "access_token": create_session(username),
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "username": username,
        "name": user["name"],
        "role": user["role"],
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

    return {"observation": observation, "score": score_observation(observation)}


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

    for patient in patients.list_patients(ward):
        history = observations.get_observations_for_patient(patient["patient_id"])
        latest = max(reversed(history), key=lambda obs: obs["recorded_at"]) if history else None
        score = score_observation(latest) if latest else None

        rows.append({
            **patient,
            "last_observed_at": latest["recorded_at"] if latest else None,
            "total_score": score["total_score"] if score else None,
            "risk_level": score["risk_level"] if score else None,
            "escalation_required": score["escalation_required"] if score else None,
            "next_observation_due": score["next_observation_due"] if score else None,
        })

    return rows
