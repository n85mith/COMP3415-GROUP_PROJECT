# Authentication and role checks

Import the shared dependency from `auth.py` for every protected endpoint.

```python
from fastapi import Depends
from auth import require_role

@app.post("/api/example")
def example(user: dict = Depends(require_role("Nurse", "Clinician"))):
    return {"recorded_by": user["username"]}
```

Supported roles are `Nurse`, `Clinician` and `Admin`. List each allowed role explicitly. Admin does not implicitly inherit clinical permissions. The dependency returns the authenticated username, name and current server-side role, without the password hash.

Send the login response's `access_token` in `Authorization: Bearer <token>`. Missing, malformed, expired and revoked tokens return `401` with a Bearer challenge. An authenticated user with a disallowed role receives `403` before the endpoint runs.

Sessions use random opaque tokens, stored as SHA-256 hashes on the server, and expire after eight hours. Session state is held in memory for this iteration. Run a single server worker. A restart signs everyone out. Shared persistent session storage is needed before using multiple workers.
