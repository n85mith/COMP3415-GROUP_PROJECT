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

Sessions use random opaque tokens, stored as SHA-256 hashes in the `sessions` table of the SQLite database, and expire after eight hours. A server restart does not sign anyone out. Expired sessions are deleted the next time anyone signs in.

## Sign-in protection

`security.login_throttle` runs before the password check:

- 5 failed sign-ins for one username within 15 minutes lock it for 15 minutes.
- 20 failed sign-ins from one IP address within 15 minutes block that address for the rest of the window.
- Blocked attempts return `429` with a `Retry-After` header, even if the password is correct.
- Unknown usernames are counted and locked in the same way, and a dummy password hash is checked, so neither the response nor its timing reveals whether an account exists.
- A successful sign-in clears the failure count for that username.

These counters are held in memory, so they are per process and reset on restart. Every sign-in, failure, lockout and sign-out is written to the audit log.


## Endpoint access

| Endpoint | Access |
| --- | --- |
| `GET /` | Public sign-in page |
| `POST /api/login` | Public, valid credentials required |
| `POST /api/logout` | Any authenticated Nurse, Clinician or Admin |
| `POST /api/observations` | Nurse or Clinician |
| `GET /api/patients/{patient_id}/observations` | Nurse or Clinician |
| `GET`, `POST /api/patients`; `GET`, `PATCH /api/patients/{patient_id}` | Nurse or Clinician |
| `GET /api/wards`, `GET /api/ward-list` | Nurse or Clinician |
| `GET /api/escalations`, `GET /api/escalations/{id}`, `POST /api/escalations/{id}/acknowledge` | Clinician |
| `GET`, `POST /api/admin/staff`; `GET`, `POST /api/admin/wards`; `GET /api/admin/audit` | Admin |

`POST /api/register` has been removed. Demo accounts are defined in `auth.USERS`; Admins create other staff accounts (US-12). Use the session user's `username` for saved actions. Never trust a client-supplied role or recorder.

The browser keeps its token in memory and sends it with protected requests. Refreshing the page requires another login. Logout revokes the current token. A `401` during observation entry returns the user to sign-in, while `403` shows a permission error.
