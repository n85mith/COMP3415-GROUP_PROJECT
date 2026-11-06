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

## What works in this iteration (P2)

| User story | Feature | Where |
| :--- | :--- | :--- |
| US-01 | Login with expiring session tokens and server-side Nurse / Clinician / Admin role checks | `main.py`, `index.html` |
| US-03 | Record the seven observations with validation, timestamp and recorder; invalid or incomplete sets are rejected and nothing is saved | `observations.py`, `main.py` |
| US-04 | One NEWS2 scorer per parameter behind a common interface, with thresholds in one file | `scoring/scorers.py`, `scoring/bands.py` |
| US-05 | Total score, risk level (Low / Low-medium / Medium / High), observation frequency and next-due time | `scoring/risk.py`, `scoring/news2.py` |
| US-06 | Score breakdown with raw values, sub-scores and total; parameters scoring 3 are highlighted | `index.html`, `scoring/news2.py` |

Not yet built: patient records and wards (US-02), escalations (US-07/08), overdue flags (US-09), trends (US-10), audit log (US-11), admin pages (US-12), export (US-13). See [`docs/BACKLOG.md`](docs/BACKLOG.md).

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

Nurse and Clinician accounts can record and read observations. Admin accounts are reserved for administration and cannot access clinical endpoints. Patient self-registration has been removed. Enter a patient ID (for example `P-001`) and the seven vital signs, then press **Save & Score**. Interactive API documentation is at http://127.0.0.1:8000/docs.

**Command-line entry** (no web server needed): `python observations.py`

Observations are saved to `observations.json` next to the code (ignored by git). It is replaced by a database in a later iteration.

## Running the tests

```bash
pytest -v          # all automated tests
flake8 .           # lint (also run in CI)
```

The test plan and the mapping from user stories to tests are in [`docs/TESTING.md`](docs/TESTING.md). GitHub Actions runs lint and the tests on every push and pull request (`.github/workflows/ci.yml`).

## Project layout

```
auth.py             Shared session management and require_role dependency
main.py             FastAPI app: login, logout, observation + history endpoints
index.html          Single-page UI: sign in, observation entry, score breakdown
observations.py     Observation fields, validation and JSON storage (also a CLI)
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
* **Storage**: JSON file for this iteration (PostgreSQL planned)
* **DevOps & QA**: pytest, flake8, GitHub Actions (CI)

## Authentication

Login returns an eight-hour bearer token. The browser holds it in memory, so refreshing requires signing in again. Sign out revokes the token on the server. Run one server worker because sessions are currently stored in memory and are cleared on restart. See [the shared authentication helper](docs/AUTH.md) for endpoint integration and the access matrix.
