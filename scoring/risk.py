"""Risk classification from the aggregate NEWS2 score (US-05, FR-07).

Originally written by Clara (clara.py). Moved into the scoring package with
cleaned-up result keys and spelling; the risk rules are unchanged. The
thresholds come from scoring.bands so they are defined in one place.
"""

from scoring import bands


def evaluate_result(aggregate_score: int, has_one_three: bool):
    """Return the risk level, observation frequency and escalation decision.

    aggregate_score: sum of the seven sub-scores.
    has_one_three:   True if any single parameter scored 3.
    """

    if aggregate_score >= bands.HIGH_RISK_MIN_TOTAL:
        risk_level = "High"
        monitoring_frequency = "Continuous monitoring"
        hours_until_next_observation = 0
        escalation_required = True
        response = (
            "Emergency assessment by a clinical team with critical-care "
            "competencies; the patient will probably need transfer to a "
            "higher level of care."
        )

    elif aggregate_score >= bands.MEDIUM_RISK_MIN_TOTAL:
        risk_level = "Medium"
        monitoring_frequency = "Minimum every hour"
        hours_until_next_observation = 1
        escalation_required = True
        response = (
            "Urgent review by a ward-based doctor or acute-care team nurse "
            "to decide whether critical-care team assessment is needed."
        )

    elif has_one_three:
        risk_level = "Low-medium"
        monitoring_frequency = "Minimum every hour"
        hours_until_next_observation = 1
        escalation_required = True
        response = (
            "Urgent ward-based doctor review to decide the frequency of "
            "monitoring and the level of care."
        )

    else:
        risk_level = "Low"
        escalation_required = False
        response = (
            "Assessment by a competent registered nurse to decide the "
            "frequency of monitoring and the level of care."
        )

        if aggregate_score == 0:
            monitoring_frequency = "Minimum every 12 hours"
            hours_until_next_observation = 12
        else:
            monitoring_frequency = "Every 4 hours"
            hours_until_next_observation = 4

    return {
        "risk_level": risk_level,
        "monitoring_frequency": monitoring_frequency,
        "hours_until_next_observation": hours_until_next_observation,
        "escalation_required": escalation_required,
        "clinical_response": response,
    }
