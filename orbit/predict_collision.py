"""Conjunction screening for propagated satellite trajectories."""
import numpy as np


def _risk_score(miss_distance_km, threshold_km, lead_time_s, relative_speed_km_s):
    """Transparent risk score for prioritisation (not collision probability)."""
    distance_term = np.clip(1.0 - miss_distance_km / max(threshold_km, 1e-9), 0.0, 1.0)
    lead_term = np.clip(1.0 - lead_time_s / (6.0 * 3600.0), 0.0, 1.0)
    speed_term = np.clip(relative_speed_km_s / 15.0, 0.0, 1.0)
    return float(100.0 * (0.65 * distance_term + 0.20 * lead_term + 0.15 * speed_term))


def _risk_level(score):
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MODERATE"
    return "LOW"


def predict_collisions(sat_positions, threshold_km=50.0, time_step_seconds=60.0):
    """Screen every satellite pair for its closest approach.

    A linear interpolation is performed between each pair of sampled points so
    the closest approach is not restricted to the discrete propagation grid.
    This is suitable for an educational screening dashboard; operational
    conjunction assessment requires covariance data and higher-fidelity tools.
    """
    alerts = []
    names = list(sat_positions.keys())
    dt = float(time_step_seconds)
    if dt <= 0:
        raise ValueError("time_step_seconds must be positive")

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            sat1, sat2 = names[i], names[j]
            p1 = np.asarray(sat_positions[sat1], dtype=float)
            p2 = np.asarray(sat_positions[sat2], dtype=float)
            n = min(len(p1), len(p2))
            if n == 0:
                continue

            rel = p1[:n] - p2[:n]
            best_distance = float("inf")
            best_time_s = 0.0
            best_step = 0
            best_rel_speed = 0.0

            if n == 1:
                best_distance = float(np.linalg.norm(rel[0]))
            else:
                for k in range(n - 1):
                    r0 = rel[k]
                    dr = rel[k + 1] - rel[k]
                    denom = float(np.dot(dr, dr))
                    fraction = 0.0 if denom <= 1e-16 else float(np.clip(-np.dot(r0, dr) / denom, 0.0, 1.0))
                    closest_vector = r0 + fraction * dr
                    distance = float(np.linalg.norm(closest_vector))
                    if distance < best_distance:
                        best_distance = distance
                        best_time_s = (k + fraction) * dt
                        best_step = min(k + int(fraction >= 0.5), n - 1)
                        best_rel_speed = float(np.linalg.norm(dr) / dt)

            if best_distance <= float(threshold_km):
                score = _risk_score(best_distance, float(threshold_km), best_time_s, best_rel_speed)
                alerts.append({
                    "sat1": sat1,
                    "sat2": sat2,
                    "miss_distance_km": best_distance,
                    "time_to_closest_s": best_time_s,
                    "step": best_step,
                    "relative_speed_km_s": best_rel_speed,
                    "risk_score": score,
                    "risk_level": _risk_level(score),
                })

    alerts.sort(key=lambda a: (a["miss_distance_km"], a["time_to_closest_s"]))
    return alerts
