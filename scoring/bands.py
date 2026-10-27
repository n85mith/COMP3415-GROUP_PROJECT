INF = float("inf")

RESPIRATORY_RATE_BANDS = [
    (8, 3),
    (11, 1),
    (20, 0),
    (24, 2),
    (INF, 3),
]

SPO2_SCALE_1_BANDS = [
    (91, 3),
    (93, 2),
    (95, 1),
    (INF, 0),
]

SYSTOLIC_BP_BANDS = [
    (90, 3),
    (100, 2),
    (110, 1),
    (219, 0),
    (INF, 3),
]

PULSE_BANDS = [
    (40, 3),
    (50, 1),
    (90, 0),
    (110, 1),
    (130, 2),
    (INF, 3),
]

TEMPERATURE_BANDS = [
    (35.0, 3),
    (36.0, 1),
    (38.0, 0),
    (39.0, 1),
    (INF, 2),
]

SUPPLEMENTAL_OXYGEN_SCORE = 2
ROOM_AIR_SCORE = 0

ALERT = "A"
CONSCIOUSNESS_ALERT_SCORE = 0
CONSCIOUSNESS_NOT_ALERT_SCORE = 3

HIGH_RISK_MIN_TOTAL = 7
MEDIUM_RISK_MIN_TOTAL = 5
SINGLE_PARAMETER_ESCALATION_SCORE = 3
