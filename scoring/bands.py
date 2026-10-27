"""NEWS2 Scale 1 band thresholds (Royal College of Physicians chart).

This is the ONLY place the scoring thresholds are defined (NFR-04). Changing
a threshold means editing this file and nothing else.

Each numeric parameter is a list of (upper_limit, score) pairs checked in
order: the first pair whose upper_limit is >= the value wins. The last pair
uses infinity so every value maps to a score.
"""

INF = float("inf")

RESPIRATORY_RATE_BANDS = [
    (8, 3),      # <= 8
    (11, 1),     # 9 - 11
    (20, 0),     # 12 - 20
    (24, 2),     # 21 - 24
    (INF, 3),    # >= 25
]

SPO2_SCALE_1_BANDS = [
    (91, 3),     # <= 91
    (93, 2),     # 92 - 93
    (95, 1),     # 94 - 95
    (INF, 0),    # >= 96
]

SYSTOLIC_BP_BANDS = [
    (90, 3),     # <= 90
    (100, 2),    # 91 - 100
    (110, 1),    # 101 - 110
    (219, 0),    # 111 - 219
    (INF, 3),    # >= 220
]

PULSE_BANDS = [
    (40, 3),     # <= 40
    (50, 1),     # 41 - 50
    (90, 0),     # 51 - 90
    (110, 1),    # 91 - 110
    (130, 2),    # 111 - 130
    (INF, 3),    # >= 131
]

TEMPERATURE_BANDS = [
    (35.0, 3),   # <= 35.0
    (36.0, 1),   # 35.1 - 36.0
    (38.0, 0),   # 36.1 - 38.0
    (39.0, 1),   # 38.1 - 39.0
    (INF, 2),    # >= 39.1
]

SUPPLEMENTAL_OXYGEN_SCORE = 2   # on supplemental oxygen
ROOM_AIR_SCORE = 0

ALERT = "A"
CONSCIOUSNESS_ALERT_SCORE = 0
CONSCIOUSNESS_NOT_ALERT_SCORE = 3   # C, V, P or U

# Aggregate thresholds
HIGH_RISK_MIN_TOTAL = 7
MEDIUM_RISK_MIN_TOTAL = 5
SINGLE_PARAMETER_ESCALATION_SCORE = 3
