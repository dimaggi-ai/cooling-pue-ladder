"""Ladder invariants."""

import sys
import unittest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling import ladder  # noqa: E402


class TestRungs(unittest.TestCase):
    def test_density_ceilings_strictly_increase(self):
        caps = [r.max_kw_per_rack for r in ladder.RUNGS]
        self.assertEqual(caps, sorted(caps))
        self.assertEqual(len(set(caps)), len(caps))

    def test_pue_floor_never_below_one(self):
        for r in ladder.RUNGS:
            self.assertGreaterEqual(r.pue_floor, 1.0)
            for climate in ladder.CLIMATES:
                for mode in ladder.WATER_MODES:
                    self.assertGreaterEqual(ladder.pue(r, climate, mode), 1.0)

    def test_liquid_rungs_never_worse_pue(self):
        # Contained-air -> direct-to-chip -> immersion never raises PUE
        # in any climate. Rear-door is deliberately excluded: it buys
        # density, and in free-cooling-rich climates its water loop
        # costs a little PUE against best-in-class contained air.
        seq = (ladder.rung("contained-air"), ladder.rung("direct-to-chip"),
               ladder.rung("immersion"))
        for climate in ladder.CLIMATES:
            pues = [ladder.pue(r, climate) for r in seq]
            for a, b in zip(pues, pues[1:]):
                self.assertGreaterEqual(a, b)

    def test_rear_door_buys_density_not_efficiency(self):
        # The C1->C2 step: density ceiling jumps 2.5x while cold-climate
        # PUE gets slightly WORSE — the rung exists for kW/rack.
        c1, c2 = ladder.rung("contained-air"), ladder.rung("rear-door-hx")
        self.assertGreaterEqual(c2.max_kw_per_rack, 2.5 * c1.max_kw_per_rack)
        self.assertGreater(ladder.pue(c2, "cold"), ladder.pue(c1, "cold"))
        self.assertAlmostEqual(ladder.pue(c2, "cold"),
                               ladder.pue(c1, "cold"), delta=0.05)
        # In hot-humid climates the lower penalty wins it back.
        self.assertLess(ladder.pue(c2, "hot-humid"),
                        ladder.pue(c1, "hot-humid"))

    def test_more_free_cooling_never_hurts(self):
        for r in ladder.RUNGS:
            self.assertGreaterEqual(ladder.pue(r, "hot-humid"),
                                    ladder.pue(r, "cold"))

    def test_legacy_air_ignores_climate(self):
        r = ladder.rung("legacy-air")
        self.assertEqual(ladder.pue(r, "cold"), ladder.pue(r, "hot-humid"))

    def test_dry_rejection_trades_pue_for_water(self):
        r = ladder.rung("direct-to-chip")
        self.assertGreater(ladder.pue(r, "hot-dry", "dry"),
                           ladder.pue(r, "hot-dry", "evaporative"))
        self.assertLess(ladder.wue("dry"), ladder.wue("evaporative"))

    def test_heat_capture_air_vs_liquid(self):
        # Capture is NOT monotonic on the ladder: rear-door neutralizes
        # most rack heat into its water loop (~0.85), direct-to-chip
        # captures ~0.75 with the rest to room air, immersion ~0.95 [12].
        # The invariant is air rungs capture nothing, liquid rungs most.
        for r in ladder.RUNGS[:2]:
            self.assertEqual(r.heat_capture, 0.0)
        for r in ladder.RUNGS[2:]:
            self.assertGreaterEqual(r.heat_capture, 0.7)
        self.assertEqual(max(r.heat_capture for r in ladder.RUNGS),
                         ladder.rung("immersion").heat_capture)

    def test_unknown_names_rejected(self):
        with self.assertRaises(ValueError):
            ladder.rung("water-wheel")
        with self.assertRaises(ValueError):
            ladder.pue(ladder.RUNGS[0], "tropical")
        with self.assertRaises(ValueError):
            ladder.pue(ladder.RUNGS[0], "cold", "sea-water")


class TestGate(unittest.TestCase):
    def test_nvl72_rack_forces_liquid(self):
        # ~120 kW NVL72-class rack [10]: only direct-to-chip and
        # immersion remain.
        names = [r.name for r in ladder.feasible_rungs(120.0)]
        self.assertEqual(names, ["direct-to-chip", "immersion"])

    def test_dgx_h100_rack_needs_rear_door(self):
        # 4x DGX H100 (10.2 kW each [11]) in a rack: contained air is out.
        names = [r.name for r in ladder.feasible_rungs(41.0)]
        self.assertEqual(names, ["rear-door-hx", "direct-to-chip",
                                 "immersion"])

    def test_beyond_the_ladder_is_empty(self):
        self.assertEqual(ladder.feasible_rungs(250.0), ())

    def test_nonpositive_density_rejected(self):
        with self.assertRaises(ValueError):
            ladder.feasible_rungs(0.0)


class TestRideThrough(unittest.TestCase):
    def test_direct_to_chip_is_the_minimum(self):
        # At each rung's own density ceiling, the middle of the ladder
        # holds the least thermal buffer — seconds, not minutes.
        rts = {r.name: ladder.ride_through_s(r, r.max_kw_per_rack)
               for r in ladder.RUNGS}
        self.assertEqual(min(rts, key=rts.get), "direct-to-chip")
        self.assertLess(rts["direct-to-chip"], 30.0)
        self.assertGreater(rts["legacy-air"], 120.0)
        self.assertGreater(rts["immersion"], 120.0)

    def test_density_above_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            ladder.ride_through_s(ladder.rung("contained-air"), 40.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
