# Updated Product Backlog (P4)

Status as of the end of the P4 iteration.

| ID | User story | Priority | Points | P1 status | **Current status** | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| US-01 | Login and Role-Based Access | Blocker | 5 | To Do | **Done** | Expiring bearer sessions, shared role dependency, logout revocation, patient self-registration removed. P4: sessions stored in the database (survive a restart), account lockout, sign-in rate limiting, security headers and CSP. |
| US-02 | Manage Patient Records | Blocker | 3 | To Do | **Done** | Create, view, list and edit patients (ID, name, ward, bed); duplicate IDs and occupied beds rejected on create and edit; missing or over-long fields named; ward list with latest score, risk, next-due time and open escalation count, filterable by ward. Ward assignment of staff is done in US-12. |
| US-04 | NEWS2 Sub-Scores | Blocker | 5 | To Do | **Done** | All seven scorers and boundary tests. |
| US-03 | Record Observations | Blocker | 5 | To Do | **Done** | Entry, validation, timestamp and recorder via UI, API and CLI. P4: stored in SQLite; old JSON data imported once; form has inline errors, keyboard use and a narrow-screen layout. |
| US-05 | Aggregate Score, Risk Level and Observation Frequency | Critical | 5 | To Do | **Done** | Risk level, frequency, next-due time and escalation flag. |
| US-06 | Score Breakdown | Critical | 2 | To Do | **Done** | Breakdown table in UI and API; parameters scoring 3 highlighted. |
| US-07 | Escalation Alerts | Critical | 5 | To Do | **Done** | A total of 5+ or any single 3 creates an Open escalation, routed by risk level (critical care outreach / ward doctor or acute care team / ward doctor) and tagged with the ward. Inbox coloured by risk level, sorted by risk then oldest first, filterable by status and ward. Best-effort email to a project Gmail account (disabled by default). |
| US-08 | Acknowledge and Respond to Escalation | Critical | 3 | To Do | **Done** | Charge nurse responds from the inbox with a required note; who and when are recorded; an escalation can only be acknowledged once, even by two people at the same moment. |
| US-09 | Overdue Observation Flags | Major | 3 | To Do | **Done** | Ward list shows the next-due time and flags overdue patients. |
| US-12 | Manage Staff, Roles and Wards | Major | 3 | To Do | **Done** | Admin creates wards and staff accounts (with ward assignment) and the password rules are enforced. Ward assignment does not yet limit which patients a nurse sees. |
| US-10 | Score Trend View | Major | 5 | To Do | **Done** | Per-patient chart of NEWS2 totals coloured by risk, with a text alternative. |
| US-11 | Audit Log | Major | 5 | To Do | **Done** | Sign-ins (including failures and lockouts) and every change to patients, observations, escalations, staff and wards; Admin-only screen and API. |
| US-13 | Export Escalation Summary | Minor | 3 | To Do | **To Do** | Not started; lowest priority. |

## Progress summary

- **Done:** US-01 to US-12 = 49 of 52 points (94%).
- **Remaining:** US-13 (3 points).
- **P4 plan:** Nate - web security, US-12, US-07 email, stretch US-11; Nischal - US-02 backend and database, US-07 core, US-08 backend, QA, CI and this report; Krish - sign-in, navigation, patient and observation UI with Playwright tests; Clara - escalation inbox, acknowledge screen, US-09, stretch US-10.

## Significant changes from P3

1. **Database.** All data (patients, observations, escalations, staff, wards, sessions, audit log) moved from JSON files to SQLite. Existing JSON data is imported once. PostgreSQL was considered; SQLite needs no server, so every member can run the project, and the move to PostgreSQL later only affects `db.py` and the SQL in the storage modules.
2. **Both stretch goals delivered.** US-10 and US-11 were stretch goals and are done.
3. **Security work counted inside US-01.** Lockout, rate limiting, password rules, security headers, CSP, CSRF and XSS checks are hardening tasks, not a new story, so they add no points.
4. **Browser testing added.** Playwright tests now cover the main flows of every role and run in CI.
5. **Velocity.** 19 points were delivered this iteration against a plan of 13-15.
