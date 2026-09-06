import unittest
from pathlib import Path

from orbit.tle_fetcher import _parse_three_line_tles
from orbit.tle_loader import load_tle
from orbit.propagator import propagate_orbit


class TLEPipelineTests(unittest.TestCase):
    def setUp(self):
        sample = Path('orbit/sample_tles.txt').read_text(encoding='utf-8')
        self.records = _parse_three_line_tles(sample, limit=1)

    def test_sample_tle_parses(self):
        self.assertEqual(len(self.records), 1)
        name, line1, line2 = self.records[0]
        self.assertTrue(name)
        self.assertTrue(line1.startswith('1 '))
        self.assertTrue(line2.startswith('2 '))

    def test_sgp4_propagates(self):
        _, line1, line2 = self.records[0]
        orbit = load_tle(line1, line2)
        times, positions = propagate_orbit(orbit, duration_hours=0.1, steps=4, start_time=orbit.epoch)
        self.assertEqual(positions.shape, (4, 3))
        self.assertEqual(len(times), 4)


if __name__ == '__main__':
    unittest.main()
