"""One scorer per NEWS2 parameter, all behind a common interface (US-04).

Every scorer has a `key` (the observation field it reads), a `label` for
display, and a `score(value)` method returning an int from 0 to 3.
"""

from abc import ABC, abstractmethod

from scoring import bands


class ParameterScorer(ABC):
    """Common interface for every parameter scorer."""

    key = ""
    label = ""

    @abstractmethod
    def score(self, value):
        """Return the NEWS2 sub-score (0-3) for one raw value."""


class BandScorer(ParameterScorer):
    """Scores a numeric value against an ordered list of bands."""

    bands = []

    def score(self, value):
        for upper_limit, points in self.bands:
            if value <= upper_limit:
                return points
        raise ValueError(f"No band matched {self.key}={value}")


class RespiratoryRateScorer(BandScorer):
    key = "respiratory_rate"
    label = "Respiratory rate"
    bands = bands.RESPIRATORY_RATE_BANDS


class Spo2Scorer(BandScorer):
    key = "spo2"
    label = "SpO2 (Scale 1)"
    bands = bands.SPO2_SCALE_1_BANDS


class SystolicBpScorer(BandScorer):
    key = "systolic_bp"
    label = "Systolic BP"
    bands = bands.SYSTOLIC_BP_BANDS


class PulseScorer(BandScorer):
    key = "pulse"
    label = "Pulse"
    bands = bands.PULSE_BANDS


class TemperatureScorer(BandScorer):
    key = "temperature"
    label = "Temperature"
    bands = bands.TEMPERATURE_BANDS

    def score(self, value):
        # The chart uses one decimal place; rounding stops float noise such
        # as 36.1000000001 from landing in the wrong band.
        return super().score(round(value, 1))


class SupplementalOxygenScorer(ParameterScorer):
    key = "supplemental_oxygen"
    label = "Air or oxygen"

    def score(self, value):
        if value:
            return bands.SUPPLEMENTAL_OXYGEN_SCORE
        return bands.ROOM_AIR_SCORE


class ConsciousnessScorer(ParameterScorer):
    key = "consciousness"
    label = "Consciousness"

    def score(self, value):
        if value == bands.ALERT:
            return bands.CONSCIOUSNESS_ALERT_SCORE
        if value in ("C", "V", "P", "U"):
            return bands.CONSCIOUSNESS_NOT_ALERT_SCORE
        raise ValueError(f"Unknown consciousness level: {value!r}")


# Display order matches the NEWS2 chart.
ALL_SCORERS = [
    RespiratoryRateScorer(),
    Spo2Scorer(),
    SupplementalOxygenScorer(),
    SystolicBpScorer(),
    PulseScorer(),
    ConsciousnessScorer(),
    TemperatureScorer(),
]
