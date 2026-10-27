def evaluate_result (aggregate_score: int, has_one_three: bool):
    """
    Evaluates the final aggregate score and returns the risk level, the required observation rate, and wheather an escalation alert is needet or not."""

    if aggregate_score >=7:
        risk_level = "high"
        monitoring_frequency = "continuous monitoring"
        hours_until_next_observation = 0
        escalation_alert = True
        response = "The patient requires immediate by a clinical team or an intensive care team, an will likely need to be transfered to a facility with a higher level of care"

    elif aggregate_score in [5,6]:
        risk_level = "medium"
        monitoring_frequency = "minimum every hour"
        hours_until_next_observation = 1
        escalation_alert = True
        response = "It is urgently necessary for a ward physician or a nurse from the acute care team to examine the patient in order to make a decision regarding whether the intensive care team should assess the patient's condiiton."

    elif has_one_three:
        risk_level = "low medium"
        monitoring_frequency = "minimum every hour"
        hours_until_next_observation = 1
        escalation_alert = True
        response = "An evaluation by a ward physician is urgendly needet to determine the frequency of clinical monitoring and the level of care."

    else: 
        risk_level = "low"
        escalation_alert = False
        response = "Assesment by a qualifide, licensed nurse or an equivalent professional to determine the frequency of clinical monitoring and the level of care."

        if aggregate_score == 0:
            monitoring_frequency = "minimum every 12 hours"
            hours_until_next_observation = 12 

        else:
            monitoring_frequency = "every 4 hours"
            hours_until_next_observation = 4

    return {
        "Aggregate score" : (aggregate_score, has_one_three),
        "Level of risk" : risk_level,
        "Monitoring frequentcy" : monitoring_frequency,
        "Hours until the next observation" : hours_until_next_observation,
        "Escalation alert" : escalation_alert,
        "Clinical response" : response
    }






