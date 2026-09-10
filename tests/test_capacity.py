"""Capacity arithmetic: a PUE point priced in megawatts and dollars."""

import sys
import unittest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling import capacity, ladder  # noqa: E402


class TestFreedCapacity(unittest.TestCase):
    def test_identity(self):
        # 10 MW at PUE 1.5 -> 1.2 frees exactly 10/1.2 - 10/1.5 MW.
        self.assertAlmostEqual(capacity.freed_mw(10.0, 1.5, 1.2),
                               10.0 / 1.2 - 10.0 / 1.5)

    def test_survey_average_to_hyperscale(self):
        # The industry-average site [2] moved to a direct-to-chip-class
        # PUE frees ~1.9 MW per 10 MW of feed — ~1,500 H100s [11].
        freed = capacity.freed_mw(10.0, 1.56, 1.2)
        self.assertAlmostEqual(freed, 1.92, delta=0.02)
        gpus = capacity.h100_equivalents(freed)
        self.assertGreater(gpus, 1_400)
        self.assertLess(gpus, 1_600)

    def test_worse_pue_frees_negative(self):
        self.assertLess(capacity.freed_mw(10.0, 1.2, 1.5), 0.0)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            capacity.it_mw(0.0, 1.5)
        with self.assertRaises(ValueError):
            capacity.it_mw(10.0, 0.99)
        with self.assertRaises(ValueError):
            capacity.h100_equivalents(-1.0)


class TestRetrofitEconomics(unittest.TestCase):
    def test_retrofit_beats_new_build_per_mw(self):
        # A hot-humid site on dry-cooled contained air (model PUE ~1.33)
        # moving to direct-to-chip: dollars per freed MW must land under
        # the ~$10M/MW new-build planning anchor [14]. No timing comparison.
        to = ladder.rung("direct-to-chip")
        mw, cost, per_mw = capacity.cost_per_freed_mw(
            10.0, 1.33, to, climate="hot-humid")
        self.assertGreater(mw, 1.0)
        self.assertLess(per_mw, capacity.NEW_BUILD_USD_PER_MW)

    def test_flagship_transition_cost(self):
        # The F2 case in docs: survey-average 1.56 -> direct-to-chip,
        # temperate: ~$2.7M per freed MW, quoted in study.md.
        to = ladder.rung("direct-to-chip")
        _, _, per_mw = capacity.cost_per_freed_mw(10.0, 1.56, to)
        self.assertAlmostEqual(per_mw / 1e6, 2.7, delta=0.15)

    def test_no_freed_capacity_raises(self):
        # A site already at 1.05 gains nothing from rear-door-hx.
        with self.assertRaises(ValueError):
            capacity.cost_per_freed_mw(10.0, 1.05,
                                       ladder.rung("rear-door-hx"))

    def test_cost_scales_with_feed(self):
        to = ladder.rung("direct-to-chip")
        _, cost10, per10 = capacity.cost_per_freed_mw(10.0, 1.5, to)
        _, cost20, per20 = capacity.cost_per_freed_mw(20.0, 1.5, to)
        self.assertAlmostEqual(cost20, 2 * cost10)
        self.assertAlmostEqual(per20, per10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
