# Iteration Review (P2.6)

## 1. What we planned

The Sprint 1 plan in P1 was a running skeleton: login by role (US-01), a ward patient list with a create form (US-02), and every NEWS2 sub-score verified by automated boundary tests (US-04), with CI running on every pull request. That was 13 story points plus setup (repository structure, FastAPI skeleton, CI, database schema and seed data).

## 2. What was completed and what remains

**Completed**

| Work | Story | Owner |
| :--- | :--- | :--- |
| Login and registration endpoints and UI | US-01 (partial) | Krish |
| Risk classification: level, frequency, escalation decision | US-05 | Clara |
| Observation entry, validation and safe JSON storage | US-03 | Nate |
| NEWS2 scorers, aggregate calculation, breakdown, API and UI integration | US-04, US-05, US-06 | Nischal |
| Automated tests (boundary, unit, API), lint and CI workflow | US-04 (NFR-01) | Nischal |
| Architecture, testing plan, updated backlog | P2 documentation | Team |

**Incomplete**

- US-01: sessions and server-side role checks.
- US-02: patient records and ward list. Patient IDs are free text for now.
- Database and migrations: observations are in a JSON file.
- Not started: US-07 to US-13.

## 3. Difficulties encountered

- **Parallel work arrived separately.** The observation-entry code, the risk logic and the login system were each written independently, so they used different field names and result formats (for example the risk function returned differently named keys and had no next-due time). We had to agree one result format and integrate them into a single `scoring` package and a single observation module.
- **Storage reliability.** The observation-entry code originally replaced the whole file with an empty list if it could not be read, which could delete earlier observations. This was fixed with atomic writes and a corrupt-file backup, and is covered by tests.
- **Scoring accuracy.** NEWS2 has many band edges and the P1 flagged transcription errors as a risk. We addressed this by writing thresholds once and testing every edge against the acceptance-criteria examples.
- **Plan versus reality.** The database and patient-list tasks planned for Sprint 1 were not started, while the scoring and observation stories planned for Sprint 2 were completed, so the iteration finished with a different set of stories than planned.
- **Role model mismatch.** The registration feature creates a Patient role that P1 does not include.

## 4. Adjustments for the next iteration

1. Finish US-01: session tokens, server-side role checks and the refused-access tests. Remove patient self-registration.
2. Build US-02 and replace the JSON file with a database behind the existing storage functions.
3. Start the escalation loop (US-07, then US-08) using the escalation decision that already exists in `scoring/risk.py`.
4. Add US-09 (overdue flags), which only needs the patient list and the next-due time we already calculate.
5. Process: every change goes through a branch and pull request with CI passing, and each member commits their own work, so contributions are visible in the history.
