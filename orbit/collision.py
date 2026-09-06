"""Backward-compatible collision helper."""
from orbit.predict_collision import predict_collisions


def detect_collisions(sat_positions, threshold_km=50.0, time_step_seconds=60.0):
    return predict_collisions(
        sat_positions,
        threshold_km=threshold_km,
        time_step_seconds=time_step_seconds,
    )
