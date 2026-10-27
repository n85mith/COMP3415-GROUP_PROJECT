# Updated Product Backlog (P2.5)

Status as of the end of the P2 iteration.

| ID | User story | Priority | Points | P1 status | **Current status** | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| US-01 | Login and Role-Based Access | Blocker | 5 | To Do | **In Progress** | Login, registration and salted hashing work; role is returned to the UI. Sessions and server-side role checks are not built yet. |
| US-02 | Manage Patient Records | Blocker | 3 | To Do | **To Do** | Patient ID is free text for now. Needs the patient model and ward list. |
| US-04 | NEWS2 Sub-Scores | Blocker | 5 | To Do | **Done** | All seven scorers and boundary tests. |
| US-03 | Record Observations | Blocker | 5 | To Do | **Done (storage partial)** | Entry, validation, timestamp and recorder work via UI, API and CLI. Saves to a JSON file, not a database. |
| US-05 | Aggregate Score, Risk Level and Observation Frequency | Critical | 5 | To Do | **Done** | Risk level, frequency, next-due time and escalation flag. |
| US-06 | Score Breakdown | Critical | 2 | To Do | **Done** | Breakdown table in UI and API; parameters scoring 3 highlighted. |
| US-07 | Escalation Alerts | Critical | 5 | To Do | **To Do** | `risk.py` already decides *whether* escalation is required; creating and listing escalations is next. |
| US-08 | Acknowledge and Respond to Escalation | Critical | 3 | To Do | **To Do** | Depends on US-07 and US-01 roles. |
| US-09 | Overdue Observation Flags | Major | 3 | To Do | **To Do** | Next-due time is already calculated; needs the ward list (US-02). |
| US-12 | Manage Staff, Roles and Wards | Major | 3 | To Do | **To Do** | |
| US-10 | Score Trend View | Major | 5 | To Do | **To Do** | History endpoint already returns scored observations. |
| US-11 | Audit Log | Major | 5 | To Do | **To Do** | |
| US-13 | Export Escalation Summary | Minor | 3 | To Do | **To Do** | |

## Progress summary

- **Done:** US-03, US-04, US-05, US-06 = 17 of 52 points.
- **In progress:** US-01 (5 points, part done).
- **Remaining:** 30 points, plus the unfinished part of US-01.

## Significant changes from P1

1. **Re-ordered work.** Sprint 1 planned US-01, US-02 and US-04. We completed US-04 and also delivered US-03, US-05 and US-06, which P1 had scheduled for Sprint 2, because those were being built in parallel by different members and together complete the observe-score-explain loop. US-02 slipped to the next iteration.
2. **Storage.** The P1 plan assumed a database from the start. For this iteration observations are stored in a JSON file behind two functions (`load_observations`, `save_observation`) so the loop could be demonstrated; the database move is now an explicit task.
3. **Added tasks (no new stories):** CI pipeline, test suite, password hashing, and a documented architecture.
4. **Roles to reconcile.** Registration currently creates a "Patient" account, but P1 says patients do not log in. We plan to remove self-registration as a patient, and have administrators create staff accounts (part of US-12).
5. **Estimates unchanged.** The scoring stories (US-04, US-05) were estimated at 5 points each; US-04 matched the estimate. US-06 (2 points) was in line with its estimate.
6. **Velocity.** About 17 points were delivered this iteration against a plan of 13, so the planning figure of 13-15 points per sprint stays, but we will re-measure after the next iteration.
