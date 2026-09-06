import unittest

from ai.mission_planner import build_mission_plan


class MissionPlannerTests(unittest.TestCase):
    def test_high_risk_event_is_prioritized(self):
        alerts = [
            {
                'sat1': 'A', 'sat2': 'B', 'miss_distance_km': 2.0,
                'time_to_closest_s': 600.0, 'step': 1,
                'relative_speed_km_s': 10.0, 'risk_score': 90.0,
                'risk_level': 'CRITICAL',
            },
            {
                'sat1': 'C', 'sat2': 'D', 'miss_distance_km': 40.0,
                'time_to_closest_s': 7200.0, 'step': 2,
                'relative_speed_km_s': 2.0, 'risk_score': 20.0,
                'risk_level': 'LOW',
            },
        ]
        plan = build_mission_plan(alerts)
        self.assertEqual(plan[0]['priority'], 'P1')
        self.assertEqual(plan[0]['decision'], 'ESCALATE')
        self.assertIn('estimated_delta_v_m_s', plan[0])


if __name__ == '__main__':
    unittest.main()
