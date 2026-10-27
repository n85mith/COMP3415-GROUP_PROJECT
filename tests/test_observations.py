"""Validation and storage of observations (US-03)."""

import json

import observations
from observations import validate_observation_values


def test_valid_values_have_no_errors(normal_values):
    assert validate_observation_values(normal_values) == {}


def test_missing_parameter_is_reported(normal_values):
    del normal_values["pulse"]
    assert list(validate_observation_values(normal_values)) == ["pulse"]


def test_out_of_range_value_is_reported(normal_values):
    normal_values["respiratory_rate"] = 200           # P1 AC example
    errors = validate_observation_values(normal_values)
    assert list(errors) == ["respiratory_rate"]


def test_wrong_types_are_reported(normal_values):
    normal_values["spo2"] = "high"
    normal_values["supplemental_oxygen"] = "yes"
    normal_values["consciousness"] = "X"
    normal_values["pulse"] = 70.5                     # must be whole number
    errors = validate_observation_values(normal_values)
    assert set(errors) == {"spo2", "supplemental_oxygen", "consciousness", "pulse"}


def test_boolean_is_not_accepted_as_a_number(normal_values):
    normal_values["spo2"] = True
    assert "spo2" in validate_observation_values(normal_values)


def test_save_and_load_by_patient(valid_request):
    observations.save_observation(dict(valid_request))
    observations.save_observation({**valid_request, "patient_id": "P-002"})

    assert len(observations.get_observations_for_patient("P-001")) == 1
    assert len(observations.get_observations_for_patient("P-002")) == 1
    assert observations.get_observations_for_patient("nobody") == []


def test_corrupt_file_is_kept_not_overwritten(tmp_path, valid_request):
    path = tmp_path / "observations.json"
    path.write_text("{ this is not valid json")

    observations.save_observation(dict(valid_request))

    backups = list(tmp_path.glob("observations.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text() == "{ this is not valid json"
    assert len(json.loads(path.read_text())) == 1
