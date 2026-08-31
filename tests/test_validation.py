"""The validation project: public points and synthetic-fleet behaviors.

If a rung constant drifts away from what the public record supports,
these tests fail. Calibrated points check internal consistency against
published fleet figures; emergent points check that behaviors the model
was not tuned to still come out right.
"""

import sys
import unittest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling.fleet import simulate            # noqa: E402
from cooling.validation import points, validate  # noqa: E402


class TestPublicPoints(unittest.TestCase):
    def test_every_point_reproduces(self):
        for p in points():
            with self.subTest(point=p.name):
                self.assertTrue(
                    p.ok,
                    f"{p.name}: expected {p.expected} +/- {p.tolerance} "
                    f"{p.ref}, model gives {p.actual:.3f}")

    def test_validate_reports_all_ok(self):
        _, ok = validate()
        self.assertTrue(ok)

    def test_points_cite_their_sources(self):
        for p in points():
            self.assertTrue(p.ref.startswith("["), p.name)

    def test_both_kinds_present(self):
        kinds = {p.kind for p in points()}
        self.assertEqual(kinds, {"calibrated", "emergent"})


class TestSyntheticFleet(unittest.TestCase):
    def test_deterministic_under_seed(self):
        self.assertEqual(simulate(seed=7), simulate(seed=7))
        self.assertNotEqual(simulate(seed=7), simulate(seed=8))

    def test_survey_average_stays_high_while_fleet_modernizes(self):
        # The survey average must fall slowly (1.7-ish to 1.5-ish over a
        # decade [2]) — NOT collapse to hyperscale levels. Note the
        # model reproduces the endpoints, not the observed flat-since-
        # 2020 shape (disclosed in fleet.py and the skeptic section).
        sim = simulate(seed=7)
        s14, _ = sim[2014]
        s24, _ = sim[2024]
        self.assertGreater(s14 - s24, 0.05)
        self.assertGreater(s24, 1.40)

    def test_energy_weighted_diverges_from_survey(self):
        # The grid sees a much better fleet than the survey does: energy-
        # weighted PUE must run well below the site-count average by 2024.
        sim = simulate(seed=7)
        survey, weighted = sim[2024]
        self.assertGreater(survey - weighted, 0.15)
        self.assertLess(weighted, 1.35)

    def test_divergence_grows_over_time(self):
        sim = simulate(seed=7)
        gap14 = sim[2014][0] - sim[2014][1]
        gap24 = sim[2024][0] - sim[2024][1]
        self.assertGreater(gap24, gap14)

    def test_robust_across_seeds(self):
        # The mechanism, not the seed, produces the divergence.
        for seed in range(5):
            survey, weighted = simulate(seed=seed)[2024]
            self.assertGreater(survey - weighted, 0.15, f"seed {seed}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
