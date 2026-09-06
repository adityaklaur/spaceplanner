import unittest

import numpy as np

from orbit.predict_collision import predict_collisions
from orbit.optimizer import estimate_delta_v


class CollisionScreeningTests(unittest.TestCase):
    def test_interpolated_closest_approach_is_detected(self):
        positions = {
            "A": np.array([[-10.0, 0.0, 0.0], [10.0, 0.0, 0.0]]),
            "B": np.array([[0.0, -10.0, 0.0], [0.0, 10.0, 0.0]]),
        }
        alerts = predict_collisions(positions, threshold_km=1.0, time_step_seconds=60.0)
        self.assertEqual(len(alerts), 1)
        self.assertLess(alerts[0]["miss_distance_km"], 1e-9)
        self.assertAlmostEqual(alerts[0]["time_to_closest_s"], 30.0, places=6)

    def test_safe_pair_does_not_alert(self):
        positions = {
            "A": np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
            "B": np.array([[0.0, 100.0, 0.0], [1.0, 100.0, 0.0]]),
        }
        alerts = predict_collisions(positions, threshold_km=50.0, time_step_seconds=60.0)
        self.assertEqual(alerts, [])

    def test_delta_v_estimate_is_non_negative(self):
        alert = {"miss_distance_km": 20.0, "time_to_closest_s": 3600.0}
        dv = estimate_delta_v(alert, target_miss_distance_km=75.0)
        self.assertGreaterEqual(dv, 0.0)
        self.assertAlmostEqual(dv, 55_000.0 / 3600.0, places=6)


if __name__ == "__main__":
    unittest.main()
