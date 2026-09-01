"""The validation project: public points and synthetic-fleet behaviors.

If a rung constant drifts away from what the public record supports,
these tests fail. Calibrated points check internal consistency against
published fleet figures; emergent points check that behaviors the model
was not tuned to still come out right.
"""

import contextlib
import dataclasses
import sys
import unittest
import unittest.mock as mock

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling import fleet, ladder, validation  # noqa: E402
from cooling.fleet import simulate            # noqa: E402
from cooling.ladder import RUNGS              # noqa: E402
from cooling.validation import DECLINED, points, validate  # noqa: E402


def _red(*mutations):
    """Names of points that FAIL with (module, attribute, value) triples
    applied.

    Which module to patch is not a detail, and it cuts BOTH ways.
    `validation` does `from .ladder import pue, RUNGS`, so it holds its own
    names: patching `ladder.pue` would never reach the registry's calibrated
    points. But `feasible_rungs` reads `ladder.RUNGS` from inside `ladder`,
    so patching `validation.RUNGS` never reaches IT. `fleet` likewise does
    `from .ladder import RUNGS, pue` and holds a third copy, so a mutation
    meant to reach the simulated fleet must name `fleet`.

    A patch aimed at the wrong module is not a failing test — it is a
    silently passing one, because the point goes red for the reason the
    mutation intended to remove. Each mutation below names every module it
    has to reach and why.
    """
    with contextlib.ExitStack() as stack:
        for module, attr, value in mutations:
            stack.enter_context(mock.patch.object(module, attr, value))
        return {p.name for p in validation.points() if not p.ok}


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

    def test_evidence_points_cite_their_sources(self):
        # Sanity points deliberately cite nothing: they pin the ladder's own
        # structure, and a ref beside a model output would dress a
        # structural consequence as a sourced result.
        for p in points():
            if p.kind in ("calibrated", "emergent"):
                self.assertTrue(p.ref.startswith("["), p.name)
            else:
                self.assertEqual(p.ref, "-", p.name)

    def test_all_three_kinds_present(self):
        kinds = {p.kind for p in points()}
        self.assertEqual(kinds, {"calibrated", "emergent", "sanity"})

    def test_every_point_explains_itself(self):
        for p in points():
            self.assertGreater(len(p.note), 40, p.name)

    def test_no_tolerance_swamps_the_value_it_brackets(self):
        # A band wide enough to admit any plausible model is not a check.
        for p in points():
            if p.expected:
                self.assertLessEqual(
                    p.tolerance, 0.20 * abs(p.expected), p.name)

    def test_declined_list_is_populated_and_explained(self):
        self.assertGreaterEqual(len(DECLINED), 5)
        for what, why in DECLINED:
            self.assertTrue(what and why, what)
            self.assertGreater(len(why), 40, what)


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


class TestBreakingTheModelTurnsTheRegistryRed(unittest.TestCase):
    """Negative controls. Each mutation deletes one thing the study leans on
    and names the point that must notice. Without these, a green table only
    proves the checks were passable."""

    def test_the_unmutated_registry_is_green(self):
        # Control for the controls: every mutation below is measured against
        # a configuration that passes when nothing is broken.
        self.assertEqual(_red(), set())

    def test_a_drifted_rung_constant_is_noticed(self):
        # Push the contained-air rung's PUE floor up by 0.2: the rung no
        # longer reproduces Google's published fleet figure.
        rungs = list(RUNGS)
        rungs[1] = dataclasses.replace(rungs[1],
                                       pue_floor=rungs[1].pue_floor + 0.20)
        red = _red((validation, "RUNGS", tuple(rungs)))
        self.assertIn("google-fleet-ttm-pue", red)

    def test_a_fleet_that_never_modernizes_is_noticed(self):
        # Freeze the fleet at its 2014 all-legacy stock. The calibrated 2014
        # point still passes; the held-out 2024 prediction must not.
        #
        # This is the mutation that earned the tolerance change. Against the
        # single-seed registry this repo shipped before, at +/-0.10, the
        # frozen fleet CLEARED the 2024 band on 19 of 24 seeds: a decade of
        # modernization and none at all were the same answer on most draws.
        # The band now stops below the 2014 anchor's, so it fails on all of
        # them. The loop is the point — one seed cannot show that.
        def frozen(seed=0):
            sim = simulate(seed=seed)
            return {y: sim[2014] for y in sim}
        red = _red((validation, "simulate", frozen))
        self.assertIn("uptime-2024-survey-avg", red)
        self.assertNotIn("uptime-2014-survey-avg", red)

    def test_the_frozen_fleet_fails_on_every_seed_not_just_the_lucky_ones(self):
        # The claim above, checked rather than asserted once: no seed lets a
        # never-modernized fleet through the 2024 band.
        band = [p for p in points() if p.name == "uptime-2024-survey-avg"][0]
        for seed in range(24):
            frozen_2024 = simulate(seed=seed)[2014][0]
            self.assertGreater(
                abs(frozen_2024 - band.expected), band.tolerance,
                f"seed {seed}: a frozen fleet passes the held-out point")

    def test_collapsing_the_two_fleets_is_noticed(self):
        # Make energy-weighted PUE equal the site-count average — i.e. claim
        # the grid sees exactly what the survey sees. The whole two-fleets
        # finding is that it does not.
        def collapsed(seed=0):
            return {y: (s, s) for y, (s, _) in simulate(seed=seed).items()}
        red = _red((validation, "simulate", collapsed))
        self.assertIn("energy-weighted-divergence", red)

    def test_a_raised_density_ceiling_is_noticed(self):
        # Let contained air cool a 200 kW rack. Every rung then clears an
        # NVL72, and the ladder stops saying anything about density.
        rungs = tuple(dataclasses.replace(r, max_kw_per_rack=250.0)
                      for r in RUNGS)
        # feasible_rungs() reads ladder.RUNGS from inside ladder, so the
        # `ladder` patch is the one that bites; validation's copy is patched
        # only to keep the two consistent (it changes nothing here, since
        # max_kw_per_rack does not enter pue()).
        red = _red((ladder, "RUNGS", rungs), (validation, "RUNGS", rungs))
        self.assertIn("nvl72-feasible-rungs", red)
        self.assertIn("dgx-h100-rack-needs-rear-door", red)

    def test_a_broken_pue_model_is_noticed(self):
        # Return a constant PUE for every rung and climate: the ladder is
        # gone, and every point that reads a PUE should refuse it.
        # fleet.py holds its own `pue` binding, so patching only
        # validation's copy leaves the whole simulated fleet running on the
        # real ladder — the survey points would then go red for the wrong
        # reason, or not at all. Both modules, or this proves nothing.
        red = _red((validation, "pue", lambda *a, **k: 1.30),
                   (fleet, "pue", lambda *a, **k: 1.30))
        for name in ("google-fleet-ttm-pue", "meta-fleet-avg-pue",
                     "nrel-esif-pue", "legacy-stock-pue",
                     "immersion-vendor-claim", "uptime-2014-survey-avg",
                     "uptime-2024-survey-avg"):
            self.assertIn(name, red)

    def test_a_fleet_that_starts_modern_is_noticed(self):
        # The 2014 point is the simulation's calibrated initial condition.
        # Start the stock on direct-to-chip instead of legacy air and that
        # calibration is gone — if the point stays green it is pinning
        # nothing. Patch `fleet`, which is where simulate() reads it.
        red = _red((fleet, "INITIAL_STOCK_RUNGS", (3, 3, 3)))
        self.assertIn("uptime-2014-survey-avg", red)


if __name__ == "__main__":
    unittest.main(verbosity=2)
