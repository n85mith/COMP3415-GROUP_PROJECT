# Testing Plan and Tests (updated for P3)

## Approach

| Level | What is tested | How | Files |
| :--- | :--- | :--- | :--- |
| Unit | Every NEWS2 band edge for each of the seven parameters | `pytest` parametrized boundary-value tests taken from the RCP NEWS2 chart | `tests/test_scorers.py` |
| Unit | Risk level, observation frequency and escalation decision for each total-score range, including "any single 3" | `pytest`, direct calls to `evaluate_result` and `score_observation` | `tests/test_news2.py` |
| Unit | Observation validation and safe storage (missing, out-of-range and wrong-type values; corrupt file is backed up, never overwritten) | `pytest` with a temporary observations file per test | `tests/test_observations.py` |
| Integration | Login, recording an observation through the HTTP API, validation failures, scored history | FastAPI `TestClient` against the real app | `tests/test_api.py` |
| Integration | Sessions and role checks: missing, invalid, expired and revoked tokens, wrong roles, storage unchanged on refusal | FastAPI `TestClient` | `tests/test_auth.py`, `tests/test_access.py` |
| Unit + integration | Patient records: required fields, duplicate IDs, occupied beds, ward filter, observations only for existing patients | `pytest`, `TestClient` | `tests/test_patients.py` |
| Unit + integration | Escalations: created only at the thresholds, one per qualifying observation, ordered by risk then oldest first, Clinician-only listing | `pytest`, `TestClient` | `tests/test_escalations.py` |

The scoring tests are the most thorough because NFR-01 requires the scoring engine to pass 100% of the boundary cases. Each test uses an isolated temporary storage file so tests never touch real data and can run in any order.

Run everything with `pytest -v`. Lint runs with `flake8 .`. GitHub Actions runs both on every push and pull request.

## Latest execution result

```
164 passed (flake8: no problems)
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
| **NFR-06** Passwords stored as salted hashes | `hash_password` | `test_api.py::test_passwords_are_stored_as_salted_hashes` |

## Not yet tested

- Browser UI behaviour - checked manually for this iteration; automated UI tests are a candidate for later.
- Performance target NFR-03 (95% of submissions scored in under 500 ms) - not measured yet.

US-01 browser verification covered Nurse login, an authenticated observation save, sign-out, Admin login without clinical controls, and Admin sign-out. Observation data was isolated from the regular app storage.
