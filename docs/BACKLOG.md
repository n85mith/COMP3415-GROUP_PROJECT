# Updated Product Backlog (P3)

Status as of the end of the P3 iteration.

| ID | User story | Priority | Points | P1 status | **Current status** | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| US-01 | Login and Role-Based Access | Blocker | 5 | To Do | **Done** | Expiring bearer sessions, shared role dependency, logout revocation and access-denial tests. Patient self-registration removed. |
| US-02 | Manage Patient Records | Blocker | 3 | To Do | **Done (ward assignment partial)** | Create and list patients (ID, name, ward, bed); duplicate IDs and occupied beds rejected; missing fields highlighted; ward list with latest score and risk, filterable by ward. Observations only accepted for existing patients. Staff are not yet assigned to a ward, so a nurse filters by ward rather than seeing only their own ward; staff-to-ward assignment moves to US-12. |
| US-04 | NEWS2 Sub-Scores | Blocker | 5 | To Do | **Done** | All seven scorers and boundary tests. |
| US-03 | Record Observations | Blocker | 5 | To Do | **Done (storage partial)** | Entry, validation, timestamp and recorder work via UI, API and CLI. Saves to a JSON file, not a database. |
| US-05 | Aggregate Score, Risk Level and Observation Frequency | Critical | 5 | To Do | **Done** | Risk level, frequency, next-due time and escalation flag. |
| US-06 | Score Breakdown | Critical | 2 | To Do | **Done** | Breakdown table in UI and API; parameters scoring 3 highlighted. |
| US-07 | Escalation Alerts | Critical | 5 | To Do | **Done** | Every observation with a total of 5+ or any single 3 creates an Open escalation (patient, score, risk level, required response). Clinician-only escalation list, sorted by risk level then oldest first, with patient name, ward and bed. In-app alert on save. |
| US-08 | Acknowledge and Respond to Escalation | Critical | 3 | To Do | **To Do** | US-07 and US-01 are in place; escalations already carry a status field ready for Acknowledged. Next iteration. |
| US-09 | Overdue Observation Flags | Major | 3 | To Do | **To Do** | Next-due time is already calculated and the ward list (US-02) now exists, so this is unblocked. |
| US-12 | Manage Staff, Roles and Wards | Major | 3 | To Do | **To Do** | Also takes over assigning staff to wards (from US-02). |
| US-10 | Score Trend View | Major | 5 | To Do | **To Do** | History endpoint already returns scored observations. |
| US-11 | Audit Log | Major | 5 | To Do | **To Do** | |
| US-13 | Export Escalation Summary | Minor | 3 | To Do | **To Do** | |

## Progress summary

- **Done:** US-01, US-02, US-03, US-04, US-05, US-06, US-07 = 30 of 52 points (58%).
- **In progress:** None.
- **Remaining:** 22 points (US-08 to US-13), plus staff-to-ward assignment and the database move.
- **P3 owners:** US-01 Krish, US-02 Clara, US-07 Nischal (plus integration).

## Significant changes from P1

1. **Re-ordered work.** Sprint 1 planned US-01, US-02 and US-04. We completed US-04 and also delivered US-03, US-05 and US-06, which P1 had scheduled for Sprint 2, because those were being built in parallel by different members and together complete the observe-score-explain loop. US-02 slipped to the next iteration.
2. **Storage.** The P1 plan assumed a database from the start. For this iteration observations are stored in a JSON file behind two functions (`load_observations`, `save_observation`) so the loop could be demonstrated; the database move is now an explicit task.
3. **Added tasks (no new stories):** CI pipeline, test suite, password hashing, and a documented architecture.
4. **Roles to reconcile.** Patient self-registration has been removed in US-01. Supported roles are Nurse, Clinician and Admin. Administrator-created staff accounts remain part of US-12.
5. **Estimates unchanged.** The scoring stories (US-04, US-05) were estimated at 5 points each; US-04 matched the estimate. US-06 (2 points) was in line with its estimate.
6. **Velocity.** About 17 points were delivered this iteration against a plan of 13, so the planning figure of 13-15 points per sprint stays, but we will re-measure after the next iteration.
