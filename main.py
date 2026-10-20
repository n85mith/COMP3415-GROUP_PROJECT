from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="CareSight Login")

USERS = {
    "nurse": {"password": "password123", "role": "Nurse", "name": "Sarah Jenkins"},
    "clinician": {"password": "password123", "role": "Clinician", "name": "Dr. Aris Thorne"},
    "admin": {"password": "password123", "role": "Administrator", "name": "Admin User"},
}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
def serve_ui():
    return FileResponse(Path(__file__).parent / "index.html")

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

    