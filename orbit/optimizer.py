"""First-order maneuver screening estimates.

This module intentionally does not claim to solve a high-fidelity optimal-control
problem.  It provides a transparent linearized delta-v estimate that is useful
for ranking candidate responses in the educational dashboard.
"""


def estimate_delta_v(alert, target_miss_distance_km=75.0, minimum_lead_time_s=900.0):
    extra_separation_km = max(0.0, float(target_miss_distance_km) - float(alert["miss_distance_km"]))
    effective_time_s = max(float(alert["time_to_closest_s"]), float(minimum_lead_time_s))
    return extra_separation_km * 1000.0 / effective_time_s


def optimize_avoidance(alerts, sat_positions=None, target_miss_distance_km=75.0):
    estimates = []
    for alert in alerts:
        dv = estimate_delta_v(alert, target_miss_distance_km=target_miss_distance_km)
        if dv < 0.5:
            action = "Low screening Δv — evaluate minor along-track correction"
        elif dv < 2.0:
            action = "Moderate screening Δv — compare prograde and retrograde candidates"
        else:
            action = "High screening Δv — escalate for higher-fidelity maneuver planning"

        estimates.append({
            **alert,
            "estimated_delta_v_m_s": dv,
            "target_miss_distance_km": float(target_miss_distance_km),
            "maneuver_guidance": action,
        })
    return estimates
