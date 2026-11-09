import hashlib
import hmac
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import escalations
import observations
from scoring import score_observation

app = FastAPI(title="CareSight")


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    expected = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(expected, stored)


USERS = {
    "clinician": {"password": hash_password("password123"), "role": "Clinician", "name": "Dr. Aris Thorne"},
    "nurse": {"password": hash_password("password123"), "role": "Nurse", "name": "Nurse Jordan Lee"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str


class ObservationRequest(BaseModel):
    patient_id: str = ""
    recorded_by: str = ""
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


@app.post("/api/register")
def register(data: RegisterRequest):
    key = data.username.lower().strip()

    if not key:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not data.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name cannot be empty")
    if key in USERS:
        raise HTTPException(status_code=409, detail="Username already taken")

    USERS[key] = {
        "password": hash_password(data.password),
        "role": "Patient",
        "name": data.full_name.strip(),
    }

    return {
        "username": key,
        "name": data.full_name.strip(),
        "role": "Patient",
    }


@app.post("/api/login")
def login(data: LoginRequest):
    user = USERS.get(data.username.lower().strip())
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "username": data.username.lower().strip(),
        "name": user["name"],
        "role": user["role"],
    }


@app.post("/api/observations")
def record_observation(data: ObservationRequest):
    values = data.model_dump()
    errors = {}

    for field in ("patient_id", "recorded_by"):
        if not str(values[field] or "").strip():
            errors[field] = "This field is required."

    errors.update(observations.validate_observation_values(values))

    if errors:
        return JSONResponse(status_code=422, content={"detail": "Invalid observation", "errors": errors})

    observation = {
        "patient_id": values["patient_id"].strip(),
        "recorded_by": values["recorded_by"].strip(),
        "recorded_at": datetime.now().isoformat(),
    }
    for field in observations.OBSERVATION_FIELDS:
        observation[field["id"]] = values[field["id"]]

    observations.save_observation(observation)
    score = score_observation(observation)
    escalation = escalations.create_escalation_if_required(observation, score)

    return {"observation": observation, "score": score, "escalation": escalation}


@app.get("/api/patients/{patient_id}/observations")
def patient_history(patient_id: str):
    history = observations.get_observations_for_patient(patient_id)
    return [{"observation": obs, "score": score_observation(obs)} for obs in history]


@app.get("/api/escalations")
def list_escalations(status: Optional[str] = escalations.OPEN):
    return escalations.list_escalations(status or None)
