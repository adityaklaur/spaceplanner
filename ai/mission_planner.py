"""Autonomous mission-planning decisions for conjunction screening.

This is a transparent expert/decision system rather than a trained ML model.
It converts conjunction metrics into a prioritised response state so the
software can explain why it recommends monitoring, planning, or escalation.
"""
from orbit.avoidance import suggest_avoidance
from orbit.optimizer import optimize_avoidance


def _decision_state(alert):
    score = float(alert["risk_score"])
    lead_minutes = float(alert["time_to_closest_s"]) / 60.0

    if score >= 75 or lead_minutes <= 20:
        return "P1", "ESCALATE", "Immediate operator review and high-fidelity conjunction analysis"
    if score >= 50 or lead_minutes <= 60:
        return "P2", "PREPARE", "Prepare candidate maneuver and re-propagate before approval"
    if score >= 25:
        return "P3", "MONITOR", "Increase monitoring cadence and retain a maneuver option"
    return "P4", "WATCH", "Continue screening; no maneuver commitment at this stage"


def build_mission_plan(alerts, target_miss_distance_km=75.0):
    """Fuse risk, rule guidance, and maneuver estimates into ordered decisions."""
    suggestions = suggest_avoidance(alerts)
    estimates = optimize_avoidance(
        alerts,
        target_miss_distance_km=target_miss_distance_km,
    )

    plan = []
    for alert, suggestion, estimate in zip(alerts, suggestions, estimates):
        priority, state, rationale = _decision_state(alert)
        plan.append({
            **alert,
            "priority": priority,
            "decision": state,
            "decision_rationale": rationale,
            "recommendation": suggestion["recommendation"],
            "estimated_delta_v_m_s": estimate["estimated_delta_v_m_s"],
            "target_miss_distance_km": estimate["target_miss_distance_km"],
            "maneuver_guidance": estimate["maneuver_guidance"],
        })

    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    plan.sort(key=lambda row: (order[row["priority"]], -row["risk_score"], row["time_to_closest_s"]))
    return plan
