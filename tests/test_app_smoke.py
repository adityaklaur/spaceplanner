import os
import unittest

# Avoid network dependency during CI/test discovery.
os.environ['TLE_OFFLINE'] = '1'
os.environ['SATELLITE_LIMIT'] = '3'
os.environ['PROPAGATION_STEPS'] = '12'


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dashboard.app import server, update
        cls.server = server
        cls.update = staticmethod(update)

    def test_health_endpoint(self):
        client = self.server.test_client()
        response = client.get('/health')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['status'], 'ok')
        self.assertGreaterEqual(payload['satellites_loaded'], 2)

    def test_full_dashboard_pipeline_returns_outputs(self):
        outputs = self.update(1, 50, 0)
        self.assertEqual(len(outputs), 7)
        map_figure, orbit_figure = outputs[0], outputs[1]
        self.assertGreater(len(map_figure.data), 0)
        self.assertGreater(len(orbit_figure.data), 0)


if __name__ == '__main__':
    unittest.main()
