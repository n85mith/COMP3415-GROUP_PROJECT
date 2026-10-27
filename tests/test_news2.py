"""Aggregate scoring, risk level and breakdown (US-05, US-06)."""

from datetime import datetime

import pytest

from scoring import score_observation
from scoring.risk import evaluate_result


# ── US-05: risk level and observation frequency ──

def test_total_4_no_three_is_low_every_4_hours():
    result = evaluate_result(4, has_one_three=False)
    assert result["risk_level"] == "Low"
    assert result["hours_until_next_observation"] == 4       # within 6 hours
    assert result["escalation_required"] is False


def test_total_0_is_low_every_12_hours():
    result = evaluate_result(0, has_one_three=False)
    assert result["risk_level"] == "Low"
    assert result["hours_until_next_observation"] == 12


@pytest.mark.parametrize("total", [5, 6])
def test_total_5_or_6_is_medium_hourly(total):
    result = evaluate_result(total, has_one_three=False)
    assert result["risk_level"] == "Medium"
    assert result["hours_until_next_observation"] == 1
    assert result["escalation_required"] is True


@pytest.mark.parametrize("total", [7, 12, 20])
def test_total_7_or_more_is_high_continuous(total):
    result = evaluate_result(total, has_one_three=False)
    assert result["risk_level"] == "High"
    assert result["monitoring_frequency"] == "Continuous monitoring"
    assert result["hours_until_next_observation"] == 0
    assert result["escalation_required"] is True


def test_total_below_5_with_a_single_three_is_low_medium():
    result = evaluate_result(3, has_one_three=True)
    assert result["risk_level"] == "Low-medium"
    assert result["hours_until_next_observation"] == 1
    assert result["escalation_required"] is True


def test_total_4_boundary_does_not_escalate():
    assert evaluate_result(4, False)["escalation_required"] is False
    assert evaluate_result(5, False)["escalation_required"] is True


# ── End-to-end through score_observation ──

def test_all_normal_observation_scores_zero(normal_values):
    result = score_observation(normal_values)
    assert result["total_score"] == 0
    assert result["risk_level"] == "Low"
    assert result["parameters_scoring_three"] == []


def test_single_three_gives_low_medium(normal_values):
    normal_values["consciousness"] = "C"              # new confusion -> 3
    result = score_observation(normal_values)
    assert result["total_score"] == 3
    assert result["parameters_scoring_three"] == ["consciousness"]
    assert result["risk_level"] == "Low-medium"
    assert result["escalation_required"] is True


def test_deteriorating_patient_is_high_risk():
    result = score_observation({
        "respiratory_rate": 26,       # 3
        "spo2": 90,                   # 3
        "supplemental_oxygen": True,  # 2
        "systolic_bp": 88,            # 3
        "pulse": 135,                 # 3
        "consciousness": "V",         # 3
        "temperature": 39.5,          # 2
    })
    assert result["total_score"] == 19
    assert result["risk_level"] == "High"
    assert len(result["parameters_scoring_three"]) == 5


# ── US-06: breakdown ──

def test_breakdown_lists_seven_parameters_with_raw_values(normal_values):
    result = score_observation(normal_values)
    assert len(result["breakdown"]) == 7
    assert {row["raw_value"] for row in result["breakdown"] if row["parameter"] == "pulse"} == {70}


def test_sub_scores_add_up_to_total():
    result = score_observation({
        "respiratory_rate": 22, "spo2": 94, "supplemental_oxygen": True,
        "systolic_bp": 105, "pulse": 95, "consciousness": "A", "temperature": 38.5,
    })
    assert sum(row["sub_score"] for row in result["breakdown"]) == result["total_score"]
    assert sum(result["sub_scores"].values()) == result["total_score"]


def test_parameter_scoring_three_is_flagged_for_highlighting(normal_values):
    normal_values["respiratory_rate"] = 30
    rows = {row["parameter"]: row for row in score_observation(normal_values)["breakdown"]}
    assert rows["respiratory_rate"]["scores_three"] is True
    assert rows["pulse"]["scores_three"] is False


# ── Next observation due time ──

def test_next_due_is_calculated_from_recorded_time(normal_values):
    normal_values["recorded_at"] = "2026-10-26T08:00:00"
    normal_values["pulse"] = 95                       # 1 point -> Low, 4 hours
    result = score_observation(normal_values)
    assert datetime.fromisoformat(result["next_observation_due"]) == datetime(2026, 10, 26, 12, 0)
