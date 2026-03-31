import numpy as np

def compute_delta_v(pos1, pos2):
    """
    Approximate Δv needed to separate two satellites
    """
    distance = np.linalg.norm(pos1 - pos2)

    # Simple model: closer = higher Δv required
    if distance == 0:
        return 0

    dv = 1 / distance * 1000   # scaled for visibility

    return dv


def optimize_avoidance(alerts, sat_positions):
    """
    Generate optimized avoidance strategy
    """
    optimized = []

    for a in alerts:
        sat1, sat2, dist, step = a

        pos1 = sat_positions[sat1][step]
        pos2 = sat_positions[sat2][step]

        dv = compute_delta_v(pos1, pos2)

        if dv < 5:
            action = "🟢 Minor thrust adjustment"
        elif dv < 20:
            action = "🟡 Moderate burn required"
        else:
            action = "🔴 High fuel maneuver needed"

        optimized.append((sat1, sat2, dv, action))

    return optimized