"""Boundary-value tests for every NEWS2 Scale 1 band edge (US-04, NFR-01).

Each case is (value, expected sub-score), taken from the RCP NEWS2 chart.
The P1 acceptance-criteria examples are marked with "AC".
"""

import pytest

from scoring.scorers import (
    ConsciousnessScorer,
    PulseScorer,
    RespiratoryRateScorer,
    Spo2Scorer,
    SupplementalOxygenScorer,
    SystolicBpScorer,
    TemperatureScorer,
)


@pytest.mark.parametrize("value, expected", [
    (1, 3), (8, 3),
    (9, 1), (11, 1),
    (12, 0), (20, 0),    # AC: 20 -> 0
    (21, 2), (24, 2),    # AC: 21 -> 2
    (25, 3), (60, 3),
])
def test_respiratory_rate(value, expected):
    assert RespiratoryRateScorer().score(value) == expected


@pytest.mark.parametrize("value, expected", [
    (50, 3), (91, 3),
    (92, 2), (93, 2),    # AC: 93 -> 2
    (94, 1), (95, 1),    # AC: 94 -> 1
    (96, 0), (100, 0),   # AC: 96 -> 0
])
def test_spo2_scale_1(value, expected):
    assert Spo2Scorer().score(value) == expected


@pytest.mark.parametrize("on_oxygen, expected", [(True, 2), (False, 0)])
def test_supplemental_oxygen(on_oxygen, expected):
    assert SupplementalOxygenScorer().score(on_oxygen) == expected


@pytest.mark.parametrize("value, expected", [
    (40, 3), (90, 3),
    (91, 2), (100, 2),
    (101, 1), (110, 1),
    (111, 0), (219, 0),
    (220, 3), (300, 3),
])
def test_systolic_bp(value, expected):
    assert SystolicBpScorer().score(value) == expected


@pytest.mark.parametrize("value, expected", [
    (20, 3), (40, 3),
    (41, 1), (50, 1),
    (51, 0), (90, 0),
    (91, 1), (110, 1),
    (111, 2), (130, 2),
    (131, 3), (250, 3),
])
def test_pulse(value, expected):
    assert PulseScorer().score(value) == expected


@pytest.mark.parametrize("value, expected", [
    (30.0, 3), (35.0, 3),
    (35.1, 1), (36.0, 1),   # AC: 36.0 -> 1
    (36.1, 0), (38.0, 0),   # AC: 36.1 -> 0
    (38.1, 1), (39.0, 1),   # AC: 38.1 -> 1
    (39.1, 2), (43.0, 2),   # AC: 39.1 -> 2
])
def test_temperature(value, expected):
    assert TemperatureScorer().score(value) == expected


def test_temperature_float_noise_does_not_change_band():
    assert TemperatureScorer().score(36.1000000000001) == 0


@pytest.mark.parametrize("level, expected", [
    ("A", 0),
    ("C", 3), ("V", 3), ("P", 3), ("U", 3),   # AC: any non-alert scores 3
])
def test_consciousness(level, expected):
    assert ConsciousnessScorer().score(level) == expected


def test_consciousness_rejects_unknown_level():
    with pytest.raises(ValueError):
        ConsciousnessScorer().score("X")
