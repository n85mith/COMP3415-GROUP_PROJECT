import json

import db
import observations
from observations import validate_observation_values


def test_valid_values_have_no_errors(normal_values):
    assert validate_observation_values(normal_values) == {}


def test_missing_parameter_is_reported(normal_values):
    del normal_values["pulse"]
    assert list(validate_observation_values(normal_values)) == ["pulse"]


def test_out_of_range_value_is_reported(normal_values):
    normal_values["respiratory_rate"] = 200
    errors = validate_observation_values(normal_values)
    assert list(errors) == ["respiratory_rate"]


def test_wrong_types_are_reported(normal_values):
    normal_values["spo2"] = "high"
    normal_values["supplemental_oxygen"] = "yes"
    normal_values["consciousness"] = "X"
    normal_values["pulse"] = 70.5
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


def test_corrupt_legacy_file_is_kept_not_overwritten(tmp_path, normal_values):
    path = tmp_path / "observations.json"
    path.write_text("{ this is not valid json")

    observations.save_observation({"patient_id": "P-001", "recorded_by": "nurse",
                                   "recorded_at": "2026-11-05T09:00:00", **normal_values})

    assert path.read_text() == "{ this is not valid json"
    assert len(observations.load_observations()) == 1


def test_legacy_json_observations_are_imported_once(tmp_path, normal_values):
    legacy = {"patient_id": "P-001", "recorded_by": "nurse", "recorded_at": "2026-11-05T09:00:00", **normal_values}
    (tmp_path / "observations.json").write_text(json.dumps([legacy, legacy]))

    assert len(observations.load_observations()) == 2
    db._initialised.clear()
    assert len(observations.load_observations()) == 2


def test_stored_values_keep_their_types(valid_request):
    observations.save_observation(dict(valid_request, supplemental_oxygen=True, temperature=38.5))
    [stored] = observations.get_observations_for_patient("P-001")

    assert stored["supplemental_oxygen"] is True
    assert stored["temperature"] == 38.5
    assert isinstance(stored["respiratory_rate"], int)
    assert stored["id"]


def test_history_is_returned_oldest_first(valid_request):
    for when in ("2026-11-05T12:00:00", "2026-11-05T08:00:00", "2026-11-05T10:00:00"):
        observations.save_observation(dict(valid_request, recorded_at=when))

    history = observations.get_observations_for_patient("P-001")
    assert [o["recorded_at"][11:13] for o in history] == ["08", "10", "12"]
    assert observations.get_latest_observation("P-001")["recorded_at"].endswith("12:00:00")
