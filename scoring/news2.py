from datetime import datetime, timedelta

from scoring import bands
from scoring.risk import evaluate_result
from scoring.scorers import ALL_SCORERS


def score_observation(observation):

    breakdown = []
    sub_scores = {}

    for scorer in ALL_SCORERS:
        raw_value = observation[scorer.key]
        points = scorer.score(raw_value)
        sub_scores[scorer.key] = points
        breakdown.append({
            "parameter": scorer.key,
            "label": scorer.label,
            "raw_value": raw_value,
            "sub_score": points,
            "scores_three": points == bands.SINGLE_PARAMETER_ESCALATION_SCORE,
        })

    total_score = sum(sub_scores.values())
    parameters_scoring_three = [
        row["parameter"] for row in breakdown if row["scores_three"]
    ]

    result = evaluate_result(total_score, bool(parameters_scoring_three))

    recorded_at = observation.get("recorded_at")
    start = datetime.fromisoformat(recorded_at) if recorded_at else datetime.now()
    next_due = start + timedelta(hours=result["hours_until_next_observation"])

    return {
        "sub_scores": sub_scores,
        "breakdown": breakdown,
        "total_score": total_score,
        "parameters_scoring_three": parameters_scoring_three,
        "next_observation_due": next_due.isoformat(),
        **result,
    }
