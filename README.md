# CareSight: Explainable Early Warning Score and Escalation Platform

## Project Overview
**CareSight** is a ward-based clinical web application. Nurses record a patient's seven vital signs, and CareSight immediately calculates the **NEWS2** (National Early Warning Score 2, SpO2 Scale 1) sub-scores, the total, the risk level, the recommended clinical response and when the next observation is due. Every score is shown with its full breakdown, so staff can see *why* a patient scored as they did. All patient data is synthetic. CareSight is an educational simulation and is not for clinical use.

The full requirements, user stories and plan are in the P1 report. The architecture, test plan, backlog and iteration review for P2 are in [`docs/`](docs/).

---

##  Team Information — **Edge Case Devs**

| Full Name | Lakehead Email Address | GitHub Profile |
| :--- | :--- | :--- |
| **Krish Bista** | `kbista@lakeheadu.ca` | [@krish-bista](https://github.com/krish-bista) |
| **Nate Smith** | `Lnsmith1@lakeheadu.ca` | [@n85mith](https://github.com/n85mith) |
| **Clara Kress** | `cjkress@lakeheadu.ca` | _Profile Link_ |
| **Nischal Shrestha** | `nshrest2@lakeheadu.ca` | _Profile Link_ |

Repository: https://github.com/n85mith/COMP3415-GROUP_PROJECT

---

## What works in this iteration (P4)

| User story | Feature | Where |
| :--- | :--- | :--- |
| US-01 | Login with expiring session tokens stored in the database (they survive a restart), server-side Nurse / Clinician / Admin role checks, account lockout and sign-in rate limiting | `auth.py`, `security.py`, `main.py`, `index.html` |
| US-02 | Create, view, list and edit patients (ID, name, ward, bed); duplicate IDs and occupied beds get rejected; a ward list shows each patient's latest score, risk level and open escalation count, filterable by ward | `patients.py`, `main.py`, `index.html` |
| US-03 | Record the seven observations with validation, timestamp and recorder; invalid or incomplete sets are rejected and nothing is saved | `observations.py`, `main.py` |
| US-04 | One NEWS2 scorer per parameter behind a common interface, with thresholds in one file | `scoring/scorers.py`, `scoring/bands.py` |
| US-05 | Total score, risk level (Low / Low-medium / Medium / High), observation frequency and next-due time | `scoring/risk.py`, `scoring/news2.py` |
| US-06 | Score breakdown with raw values, sub-scores and total; parameters scoring 3 are highlighted | `index.html`, `scoring/news2.py` |
| US-07 | Observations with a total of 5+ or any single 3 create an Open escalation, routed by risk level (High: critical care outreach, Medium: ward doctor or acute care team, Low-medium: ward doctor) and tagged with the patient's ward; clinicians see open escalations by risk level, then oldest first, filterable by ward; configured recipients receive a best-effort email notification | `escalations.py`, `notifications.py`, `main.py`, `index.html` |
| US-07 (UI) | Escalation inbox coloured by risk level, filterable by status | `index.html` |
| US-08 | Clinicians acknowledge an open escalation with a required response note from the inbox; the record keeps who acknowledged it and when; an escalation can only be acknowledged once | `escalations.py`, `main.py`, `index.html` |
| US-09 | Ward list shows when each patient's next observation is due and flags overdue patients | `index.html` |
| US-10 | Per-patient NEWS2 score trend chart, with a text alternative for screen readers | `index.html` |
| US-11 | Audit log of sign-ins, patient, observation, escalation, staff and ward actions; Admin only | `audit.py`, `main.py`, `index.html` |
| US-12 | Admin-managed wards and staff accounts with server-side role enforcement | `staff.py`, `auth.py`, `main.py`, `index.html` |

Not yet built: export (US-13). See [`docs/BACKLOG.md`](docs/BACKLOG.md).

---

## Running the system

Requires Python 3.10 or newer.

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Start the web app
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 and sign in with a demo account. (If Windows reports an error about port 8000, use another port: `uvicorn main:app --port 8765` and open http://127.0.0.1:8765.)

| Role | Username | Password |
| :--- | :--- | :--- |
| Nurse | `nurse` | `password123` |
| Clinician | `clinician` | `password123` |
| Admin | `admin` | `password123` |

Nurse and Clinician accounts can record and read observations. Admin accounts are reserved for administration and cannot access clinical endpoints. Patient self-registration has been removed. From **Ward List**, open **Add patient** to create a synthetic record. Use the row’s **Observe** action or select the patient under **Record Observation**, then enter the seven observations and choose **Save & Score**. The UI labels the current Clinician role **Charge nurse**. Observations are only allowed for patients that exist. If the observation needs escalation (for example consciousness `V`), an alert is shown and the escalation appears under **Open Escalations** when signed in as `clinician`. Interactive API documentation is at http://127.0.0.1:8000/docs.

**Command-line entry** (no web server needed): `python observations.py`

All data is stored in a SQLite database, `caresight.db`, next to the code (ignored by git). Set `CARESIGHT_DB` to use a different file. If old `patients.json`, `observations.json`, `escalations.json` or `staff.json` files are present when the database is first created, their data is imported once and the JSON files are left untouched.

### US-12 staff and ward administration

An Admin can open **Administration** to create wards and staff accounts and to read the audit log. Wards may be used alongside ward names found in existing patient records. New staff passwords must contain 12-128 characters, must not contain the username and must not be a common password. Nurse and Clinician accounts require an existing ward; Admin accounts may omit one.

Demo accounts remain available with the usernames and password listed above. Staff accounts are stored (with hashed passwords) in `caresight.db`, which is git-ignored. Do not add real account credentials or the database to Git.

Ward assignment is account metadata; it does not restrict clinical patient or observation access.

### US-07 escalation email notifications

Email is disabled by default. To enable local testing, use a dedicated project Gmail account, turn on 2-Step Verification, and create a Google App Password if App Passwords are supported for that account. Use only the App Password; never use or share the account's normal Google password. Do not commit credentials.

Copy `.env.example` to `.env`, then set `CARESIGHT_EMAIL_ENABLED=true`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, and `ESCALATION_RECIPIENTS`. The recipients value is a comma-separated explicit allowlist; for a manual test, use only a test mailbox you control. This project does not automatically load `.env` files. Export its values in the shell before starting the server:

```bash
set -a
. ./.env
set +a
uvicorn main:app --reload
```

Restart the server after changing the environment. `.env` is git-ignored; `.env.example` contains blank placeholders only.

To manually test, sign in with a clinical account, create a synthetic patient, then save an observation that qualifies for an escalation (for example, consciousness `C` triggers a single-parameter escalation). Confirm that the escalation appears in the Clinician view and that the configured test recipient receives a message with the subject `[CareSight DEMO] Escalation alert`; check spam if it is not in the inbox. This project does not send a test message at startup or through an unauthenticated endpoint.

Delivery uses verified STARTTLS and is best-effort via an in-process background task. Invalid configuration or SMTP/network failures are logged in sanitized form and do not undo a saved observation or escalation. There are no automatic retries or durable queue, and process exit can lose a pending task; repeated qualifying observations create separate escalations and may each generate a notification. Notifications are for an educational simulation only, not a real clinical alert system.

## Running the tests

```bash
pytest -v          # backend tests
flake8 .           # lint (also run in CI)
```

The test plan and the mapping from user stories to tests are in [`docs/TESTING.md`](docs/TESTING.md). GitHub Actions runs lint and the tests on every push and pull request (`.github/workflows/ci.yml`).


Browser tests run separately with Node.js 20 or newer and the Python dependencies installed.

```bash
npm ci
npx playwright install chromium
npm run test:browser
```

Playwright starts an isolated FastAPI server on port 8767 with temporary storage. It uses the repository's `.venv` when available. Set `CARESIGHT_PYTHON` to select a different Python executable.

The patient edit form uses `PATCH /api/patients/{patient_id}` with any of `name`, `ward` and `bed` in the JSON body. It returns the updated patient record, `404` for an unknown patient, `409` when the bed is taken and `422` for invalid fields, using the existing field error format. The browser tests still stub the update so they can also check the unavailable-route message.

### Escalation API

| Method and path | Role | Purpose |
| :--- | :--- | :--- |
| `GET /api/escalations?status=Open&ward=` | Clinician | List escalations (`status` is `Open`, `Acknowledged` or empty for all) |
| `GET /api/escalations/{id}` | Clinician | One escalation with patient name, ward and bed |
| `POST /api/escalations/{id}/acknowledge` | Clinician | Body `{"response_note": "..."}`. Returns the updated escalation; `409` if already acknowledged, `422` if the note is missing or over 1000 characters |

## Project layout

```
auth.py             Shared session management and require_role dependency
main.py             FastAPI app: login, logout, patient, ward list, observation, history and escalation endpoints
db.py               SQLite connection, schema and one-time import of old JSON data
index.html          Single-page UI: sign in, ward list, add patient, observation entry, score breakdown
observations.py     Observation fields, validation and storage (also a CLI)
patients.py         Patient records (ID, name, ward, bed): create, update, list
escalations.py      Creates, routes, lists and acknowledges escalations from the scoring result
security.py         Sign-in lockout and rate limiting, password rules, security headers and CSP
audit.py            Audit log of user actions
staff.py            Staff accounts and wards (US-12)
notifications.py    Best-effort Gmail delivery for new escalations (US-07)
scoring/
  bands.py          NEWS2 thresholds (the one place they are defined)
  scorers.py        One scorer class per parameter
  risk.py           Risk level, frequency, escalation decision
  news2.py          Aggregates sub-scores into the full result
tests/              pytest suites
docs/               Architecture, testing plan, backlog, iteration review
```

---

##  Technology Stack

* **Frontend**: HTML, CSS and vanilla JavaScript (single page)
* **Backend API**: Python 3 with FastAPI
* **Storage**: SQLite (Python standard library `sqlite3`, no extra install)
* **DevOps & QA**: pytest, flake8, Playwright, GitHub Actions (CI runs lint, the backend tests and the browser tests)

## Authentication

Login returns an eight-hour bearer token. The browser holds it in memory, so refreshing requires signing in again. Sign out revokes the token on the server. Sessions are stored in the database (only a hash of each token), so a server restart does not sign people out. See [the shared authentication helper](docs/AUTH.md) for endpoint integration, the access matrix and the security measures.

### Security measures

| Threat | Protection |
| :--- | :--- |
| Password guessing | 5 failed sign-ins lock that username for 15 minutes; 20 failed sign-ins from one address in 15 minutes block that address. Both return `429` with `Retry-After`. Unknown usernames behave exactly like real ones. |
| Weak passwords | Staff passwords: 12-128 characters, not containing the username, not a common password. Stored as salted PBKDF2 hashes. |
| Cross-site scripting (XSS) | All data is escaped before display; the page has no inline event handlers; a Content-Security-Policy only allows the page's own script (by SHA-256 hash). |
| Cross-site request forgery (CSRF) | Not possible by design: the API only accepts the token in the `Authorization` header, never from cookies, and sends no CORS permission to other sites. |
| Clickjacking, MIME sniffing, leaks | `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on the API. |
| Accountability | Audit log of sign-ins (including failures and lockouts) and every change to patients, observations, escalations, staff and wards. |

The sign-in limits are kept in memory, so they reset when the server restarts and apply per server process.
