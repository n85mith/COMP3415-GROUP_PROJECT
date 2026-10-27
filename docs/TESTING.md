# Testing Plan and Initial Tests (P2.3)

## Approach

| Level | What is tested | How | Files |
| :--- | :--- | :--- | :--- |
| Unit | Every NEWS2 band edge for each of the seven parameters | `pytest` parametrized boundary-value tests taken from the RCP NEWS2 chart | `tests/test_scorers.py` |
| Unit | Risk level, observation frequency and escalation decision for each total-score range, including "any single 3" | `pytest`, direct calls to `evaluate_result` and `score_observation` | `tests/test_news2.py` |
| Unit | Observation validation and safe storage (missing, out-of-range and wrong-type values; corrupt file is backed up, never overwritten) | `pytest` with a temporary observations file per test | `tests/test_observations.py` |
| Integration | Login, recording an observation through the HTTP API, validation failures, scored history | FastAPI `TestClient` against the real app | `tests/test_api.py` |

The scoring tests are the most thorough because NFR-01 requires the scoring engine to pass 100% of the boundary cases. Each test uses an isolated temporary storage file so tests never touch real data and can run in any order.

Run everything with `pytest -v`. Lint runs with `flake8 .`. GitHub Actions runs both on every push and pull request.

## Latest execution result

```
92 passed
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
| **NFR-06** Passwords stored as salted hashes | `hash_password` | `test_api.py::test_passwords_are_stored_as_salted_hashes` |

## Not yet tested

- Role-based access refusal (US-01 criterion 3) - needs sessions, not yet built.
- Browser UI behaviour - checked manually for this iteration; automated UI tests are a candidate for later.
- Performance target NFR-03 (95% of submissions scored in under 500 ms) - not measured yet.
