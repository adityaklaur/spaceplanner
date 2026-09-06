"""Human-readable conjunction response guidance."""


def suggest_avoidance(alerts):
    suggestions = []
    for alert in alerts:
        distance = alert["miss_distance_km"]
        lead_minutes = alert["time_to_closest_s"] / 60.0

        if distance < 5:
            action = "Urgent review: test prograde/retrograde along-track maneuver candidates."
        elif distance < 20:
            action = "Priority review: evaluate a small along-track burn and re-propagate both objects."
        else:
            action = "Monitor closely: evaluate maneuver candidates only if the screening risk persists."

        if lead_minutes < 30:
            action += " Lead time is short; avoid presenting the estimate as an executable command."

        suggestions.append({**alert, "recommendation": action})
    return suggestions
