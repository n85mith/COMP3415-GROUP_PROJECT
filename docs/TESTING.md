# Testing Plan and Tests (updated for P4)

## Approach

| Level | What is tested | How | Files |
| :--- | :--- | :--- | :--- |
| Unit | Every NEWS2 band edge for each of the seven parameters | `pytest` parametrized boundary-value tests taken from the RCP NEWS2 chart | `tests/test_scorers.py` |
| Unit | Risk level, observation frequency and escalation decision for each total-score range, including "any single 3" | `pytest`, direct calls to `evaluate_result` and `score_observation` | `tests/test_news2.py` |
| Unit | Observation validation and storage (missing, out-of-range and wrong-type values; stored types preserved; history ordered; old JSON data imported once, unreadable JSON left untouched) | `pytest` with a temporary SQLite database per test | `tests/test_observations.py` |
| Integration | Login, recording an observation through the HTTP API, validation failures, scored history | FastAPI `TestClient` against the real app | `tests/test_api.py` |
| Integration | Sessions and role checks: missing, invalid, expired and revoked tokens, wrong roles, storage unchanged on refusal | FastAPI `TestClient` | `tests/test_auth.py`, `tests/test_access.py` |
| Unit + integration | Patient records: required fields and length limits, duplicate IDs, occupied beds, ward filter, single-patient view, partial and full updates, bed conflicts on update, observations only for existing patients | `pytest`, `TestClient` | `tests/test_patients.py` |
| Unit + integration | Escalations: created only at the thresholds, one per qualifying observation, ordered by risk then oldest first, Clinician-only listing, persisted in the database, best-effort email notification using mocked SMTP | `pytest`, `TestClient` | `tests/test_escalations.py`, `tests/test_notifications.py` |
| Unit + integration | Routing and acknowledgement: route and urgency per risk level, ward filter, required response note, acknowledge once only (including 8 simultaneous attempts), role checks, open escalations follow a patient who changes ward | `pytest`, `TestClient`, threads | `tests/test_acknowledge.py` |
| Unit + integration | Security: lockout and its expiry, per-address limit, identical behaviour for unknown usernames, password rules, security headers, CSP hash (with CRLF and LF files), no inline handlers, cookies ignored (CSRF), no CORS, sessions survive a restart and store only a token hash, audit log contents and Admin-only access | `pytest`, `TestClient` | `tests/test_hardening.py` |
| Unit + integration | Staff and wards: validation, case-insensitive duplicates, hashed passwords, Admin-only routes, storage errors return 503, old `staff.json` imported | `pytest`, `TestClient` | `tests/test_staff.py`, `tests/test_admin.py` |
| System (browser) | Sign-in and role navigation, session expiry and revocation, patient create/edit, observation form by keyboard on a narrow screen | Playwright (Chromium) against a server with a temporary database | `browser_tests/workspace.spec.cjs` |
| System (browser) | Raise an escalation as a nurse and acknowledge it as a charge nurse, focus handling, nurses cannot see the inbox, overdue flag (with a controlled clock), trend chart and its text alternative, patient text never runs as script, audit log screen, no CSP violations | Playwright (Chromium) | `browser_tests/escalations.spec.cjs` |

The scoring tests are the most thorough because NFR-01 requires the scoring engine to pass 100% of the boundary cases. Each test uses its own temporary SQLite database, so tests never touch real data and can run in any order.

Run everything with `pytest -v`. Lint runs with `flake8 .`. Browser tests run with `npm run test:browser`. GitHub Actions runs lint and the backend tests, then the browser tests, on every push and pull request.

### Regression policy

All tests from P2 and P3 are kept. Tests that read the old JSON files directly (five from P2/P3 and six from the US-12 branch) were rewritten to check the same behaviour against the database (storage unchanged on refused requests, records persisted, unreadable old data never overwritten). No test was deleted.

The browser tests share one temporary database per run and use fixed patient IDs, so run them once per server start (CI does this).

## Latest execution result

```
pytest:     313 passed (flake8: no problems)
Playwright: 14 passed (Chromium)
```

(Run `pytest -v` to see each case. CI results are on the repository's Actions tab.)

## Traceability: user story -> implementation -> verification

| Story / criterion | Implementation | Verifying test |
| :--- | :--- | :--- |
| **US-04** RR 20 scores 0, RR 21 scores 2 | `RespiratoryRateScorer`, `bands.RESPIRATORY_RATE_BANDS` | `test_scorers.py::test_respiratory_rate[20-0]`, `[21-2]` |
| **US-04** SpO2 93 scores 2, 94 scores 1, 96 scores 0 | `Spo2Scorer` | `test_scorers.py::test_spo2_scale_1` |
| **US-04** Oxygen scores 2, room air 0 | `SupplementalOxygenScorer` | `test_scorers.py::test_supplemental_oxygen` |
| **US-04** Temp 36.0 -> 1, 36.1 -> 0, 38.1 -> 1, 39.1 -> 2 | `TemperatureScorer` | `test_scorers.py::test_temperature` |
| **US-04** C, V, P or U scores 3 | `ConsciousnessScorer` | `test_scorers.py::test_consciousness` |
| **US-04** Every band edge passes | all scorers | all of `test_scorers.py` |
| **US-05** Total 4, no 3 -> Low, due within 6 h | `risk.evaluate_result` | `test_news2.py::test_total_4_no_three_is_low_every_4_hours` |
| **US-05** Total 5-6 -> Medium, hourly; 7+ -> High, continuous | `risk.evaluate_result` | `test_news2.py::test_total_5_or_6_is_medium_hourly`, `test_total_7_or_more_is_high_continuous` |
| **US-05** Total < 5 with a single 3 -> Low-medium, at least hourly | `risk.evaluate_result` | `test_news2.py::test_total_below_5_with_a_single_three_is_low_medium` |
| **US-06** Seven parameters with raw values and sub-scores shown | `news2.score_observation` `breakdown` | `test_news2.py::test_breakdown_lists_seven_parameters_with_raw_values` |
| **US-06** Parameter scoring 3 is highlighted | `scores_three` flag, `tr.three` style | `test_news2.py::test_parameter_scoring_three_is_flagged_for_highlighting` |
| **US-06** Sub-scores add up to the total | `news2.score_observation` | `test_news2.py::test_sub_scores_add_up_to_total`, `test_api.py::test_response_contains_breakdown_that_adds_up` |
| **US-03** Valid set is saved with timestamp and recorder and appears in history | `POST /api/observations`, `save_observation` | `test_api.py::test_valid_observation_is_saved_and_scored` |
| **US-03** Out-of-range value (RR 200): nothing saved, field identified | `validate_observation_values` | `test_api.py::test_out_of_range_value_saves_nothing_and_names_the_field` |
| **US-03** Missing parameter: nothing saved | `validate_observation_values` | `test_api.py::test_missing_parameter_saves_nothing` |
| **US-01** Valid login returns the role; invalid login is a generic error | `POST /api/login` | `test_api.py::test_valid_login_returns_role`, `test_invalid_login_is_generic_401` |
| **US-01** Missing, invalid, expired or revoked token returns 401; wrong role returns 403; storage unchanged | `auth.require_role` | `test_access.py::test_denied_requests_do_not_change_storage` |
| **US-01** Recorder comes from session, logout revokes only its token, patient registration removed | `auth.py`, `main.py` | `test_access.py`, `test_api.py::test_self_registration_is_removed` |
| **US-02** New patient with all fields appears in the ward list with a unique ID | `patients.create_patient`, `GET /api/ward-list` | `test_patients.py::test_staff_can_create_and_list_patients`, `test_duplicate_patient_id_is_rejected`, `test_ward_list_shows_latest_score_and_risk` |
| **US-02** Missing required field is rejected and named | `patients.validate_patient` | `test_patients.py::test_missing_fields_are_reported`, `test_icomplete_patient_saves_nothing` |
| **US-02** Ward list can be limited to one ward | `patients.list_patients(ward)` | `test_patients.py::test_list_can_be_filtered_by_ward` |
| **US-07** Total 5+ or any single 3 creates an Open escalation with patient, score, risk level and required response | `escalations.create_escalation_if_required` | `test_escalations.py::test_medium_score_creates_open_escalation_with_details`, `test_single_parameter_three_creates_low_medium_escalation`, `test_high_observation_via_api_raises_escalation` |
| **US-07** Below all thresholds: no escalation | `escalations.create_escalation_if_required` | `test_escalations.py::test_low_score_creates_no_escalation`, `test_low_score_above_zero_creates_no_escalation`, `test_normal_observation_via_api_has_no_escalation` |
| **US-07** Open escalations listed by risk level, then oldest first | `escalations.list_escalations` | `test_escalations.py::test_list_puts_highest_risk_first`, `test_same_risk_level_is_listed_oldest_first`, `test_higher_score_does_not_jump_ahead_within_a_risk_level` |
| **US-07 / FR-09** Escalations are routed to clinicians only | `GET /api/escalations` with `require_role("Clinician")` | `test_escalations.py::test_only_clinicians_can_list_escalations` |
| **US-02** Patient details can be viewed and corrected; a bed that is already taken is rejected | `GET`/`PATCH /api/patients/{id}`, `patients.update_patient` | `test_patients.py::test_patch_updates_name_ward_and_bed`, `test_patch_into_occupied_bed_is_rejected`, `test_patch_with_invalid_values_changes_nothing` |
| **US-07** Escalation is routed to the team that matches the risk level and to the patient's ward | `escalations.ROUTES`, `create_escalation_if_required(ward=...)` | `test_acknowledge.py::test_escalation_is_routed_by_risk_level`, `test_escalations_can_be_filtered_by_ward` |
| **US-08** Clinician acknowledges with a response note; who and when are recorded; status becomes Acknowledged | `POST /api/escalations/{id}/acknowledge` | `test_acknowledge.py::test_clinician_acknowledges_with_a_response_note`, `test_acknowledged_escalation_leaves_the_open_list` |
| **US-08** An escalation cannot be acknowledged twice, even by two clinicians at once | conditional update inside a write transaction | `test_acknowledge.py::test_escalation_cannot_be_acknowledged_twice`, `test_simultaneous_acknowledgements_only_one_wins` |
| **US-08** Only clinicians can acknowledge; a missing note is rejected and nothing changes | `require_role("Clinician")`, `validate_response_note` | `test_acknowledge.py::test_only_clinicians_can_acknowledge`, `test_acknowledge_needs_a_valid_note` |
| **US-07** A newly persisted escalation schedules one sanitized, verified-TLS email notification; no escalation means no notification | `main.py` background task, `notifications.py` runtime configuration and SMTP sender | `tests/test_notifications.py` |
| **US-01** Repeated failed sign-ins lock the account and are audited | `security.LoginThrottle`, `POST /api/login` | `test_hardening.py::test_account_locks_after_five_failures_even_with_the_right_password`, `test_failed_and_locked_logins_are_audited_without_passwords` |
| **US-01** Sessions survive a restart; only token hashes are stored | `sessions` table, `auth.create_session` | `test_hardening.py::test_session_survives_a_server_restart`, `test_only_a_hash_of_the_token_is_stored` |
| **US-08 UI** Charge nurse responds from the inbox and the escalation moves to Acknowledged | acknowledge panel in `index.html` | `escalations.spec.cjs` "nurse raises an escalation and a charge nurse acknowledges it" |
| **US-09** Overdue patients are flagged on the ward list | Next observation column in `index.html` | `escalations.spec.cjs` "ward list flags a patient whose next observation is overdue" |
| **US-10** Score trend per patient | trend panel in `index.html` | `escalations.spec.cjs` "trend shows each observation score" |
| **US-11** Changes are recorded with who, what and when; only Admins can read them | `audit.py`, `GET /api/admin/audit` | `test_hardening.py::test_clinical_actions_are_audited`, `test_only_admins_can_read_the_audit_log` |
| **NFR-06** Passwords stored as salted hashes | `hash_password` | `test_api.py::test_passwords_are_stored_as_salted_hashes` |

## Not yet tested

- Real Gmail delivery - the sender is tested with a mocked SMTP server; a live send needs the project account's App Password.
- Performance target NFR-03 (95% of submissions scored in under 500 ms) - not measured yet.

US-01 browser verification covered Nurse login, an authenticated observation save, sign-out, Admin login without clinical controls, and Admin sign-out. Observation data was isolated from the regular app storage.
