from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="CareSight")

# Pre-seeded clinician account(s) — patients register themselves
USERS = {
    "clinician": {"password": "password123", "role": "Clinician", "name": "Dr. Aris Thorne"},
}

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str

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
        "password": data.password,
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
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "username": data.username.lower().strip(),
        "name": user["name"],
        "role": user["role"],
    }