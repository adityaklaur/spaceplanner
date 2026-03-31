def suggest_avoidance(alerts):
    """
    Generate simple avoidance strategies
    """
    suggestions = []

    for a in alerts:
        sat1, sat2, dist, step = a

        # Simple rule-based logic
        if dist < 20:
            action = "🚨 Immediate maneuver: Increase altitude by +20 km"
        elif dist < 50:
            action = "⚠️ Adjust orbit: Increase altitude by +10 km"
        else:
            action = "ℹ️ Minor adjustment: Small inclination change"

        suggestions.append((sat1, sat2, action))

    return suggestions