"""Admission: ride-through and headroom asked at the moment a job starts."""

import sys
import unittest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling import ladder  # noqa: E402
from cooling.admission import (  # noqa: E402
    ADMIT, DENY, STAGGER, Admission, Feeder, Hall, Start, admit, thinnest_rung)

D2C = ladder.rung("direct-to-chip")
RDX = ladder.rung("rear-door-hx")
AIR = ladder.rung("legacy-air")
IMM = ladder.rung("immersion")


def hall(hall_id, feeder="F1", rung=D2C, kw=100.0, running=0, feed=8.0):
    return Hall(hall_id=hall_id, feeder_id=feeder, rung=rung,
                kw_per_rack=kw, racks_running=running, feed_mw=feed)


def world(*halls, limit=40.0, step=40.0, feeders=None):
    hs = {h.hall_id: h for h in halls}
    if feeders is None:
        ids = {h.feeder_id for h in halls}
        feeders = {i: Feeder(i, limit, step) for i in ids}
    return hs, feeders


class TestRideThrough(unittest.TestCase):
    def test_the_thinnest_buffer_is_in_the_middle_of_the_ladder(self):
        """Not the bottom rung and not the top: the one AI density lands on."""
        self.assertEqual(thinnest_rung(ladder.RUNGS).name, "direct-to-chip")

    def test_the_thin_rung_holds_seconds_where_air_holds_minutes(self):
        thin = ladder.ride_through_s(D2C, D2C.max_kw_per_rack)
        air = ladder.ride_through_s(AIR, AIR.max_kw_per_rack)
        self.assertLess(thin, 15.0)
        self.assertGreater(air, 200.0)

    def test_at_one_density_the_rung_decides_admissibility(self):
        """Same 132 kW/rack, two rungs that cool it, opposite verdicts.

        This is the whole point of promoting ride-through to an admission
        field: the density passes the ladder gate either way, and a job that
        needs thirty seconds is admissible in one room and not the other.
        """
        thin = hall("thin", rung=D2C, kw=132.0, feed=20.0)
        thick = hall("thick", feeder="F2", rung=IMM, kw=132.0, feed=20.0)
        halls, feeders = world(thin, thick)
        need30 = dict(min_ride_through_s=30.0)

        a = admit(Start("j", {"thin": 1}, **need30), halls, feeders)
        b = admit(Start("j", {"thick": 1}, **need30), halls, feeders)
        self.assertEqual(a.verdict, DENY)
        self.assertEqual(b.verdict, ADMIT)
        self.assertIn("holds 11 s", " ".join(a.reasons))

    def test_a_job_that_asks_for_nothing_is_never_denied_on_ride_through(self):
        halls, feeders = world(hall("h", kw=132.0, feed=20.0))
        self.assertEqual(admit(Start("j", {"h": 1}), halls, feeders).verdict,
                         ADMIT)


class TestHallHeadroom(unittest.TestCase):
    def test_a_start_that_does_not_fit_is_denied(self):
        # 8 MW feed, PUE ~1.06 at direct-to-chip/temperate: 40 racks of
        # 100 kW is 4 MW of IT and about 4.2 MW of facility draw.
        halls, feeders = world(hall("h", feed=3.0))
        out = admit(Start("j", {"h": 40}), halls, feeders)
        self.assertEqual(out.verdict, DENY)
        self.assertIn("MW of feed left", " ".join(out.reasons))

    def test_headroom_counts_what_is_already_running(self):
        empty = hall("h", feed=8.0, running=0)
        busy = hall("h", feed=8.0, running=60)
        for h, want in ((empty, ADMIT), (busy, DENY)):
            halls, feeders = world(h)
            self.assertEqual(admit(Start("j", {"h": 20}), halls,
                                   feeders).verdict, want)

    def test_a_denial_on_headroom_is_not_downgraded_to_a_stagger(self):
        """Telling an operator to stagger a start that never fits is worse
        than saying no, so the destination checks run first and stop."""
        halls, feeders = world(hall("a", feed=1.0), hall("b", feed=1.0),
                               step=0.001)
        out = admit(Start("j", {"a": 40, "b": 40}), halls, feeders)
        self.assertEqual(out.verdict, DENY)
        self.assertNotIn("at once", " ".join(out.reasons))


class TestFeederStep(unittest.TestCase):
    def test_two_halls_on_one_feeder_stagger(self):
        """The load fits; the transition does not. The one 'later' verdict."""
        halls, feeders = world(hall("a", "F1"), hall("b", "F1"),
                               limit=40.0, step=1.5)
        out = admit(Start("j", {"a": 10, "b": 10}), halls, feeders)
        self.assertEqual(out.verdict, STAGGER)
        self.assertEqual(set(out.stagger_order), {"a", "b"})
        self.assertIn("at once", " ".join(out.reasons))

    def test_the_same_two_halls_on_separate_feeders_admit(self):
        """Nothing about the halls changed — only what they share."""
        halls, feeders = world(hall("a", "F1"), hall("b", "F2"),
                               limit=40.0, step=1.5)
        self.assertEqual(
            admit(Start("j", {"a": 10, "b": 10}), halls, feeders).verdict,
            ADMIT)

    def test_one_hall_too_big_to_step_cannot_be_staggered(self):
        halls, feeders = world(hall("a", "F1"), hall("b", "F1"),
                               limit=40.0, step=0.5)
        out = admit(Start("j", {"a": 10, "b": 10}), halls, feeders)
        self.assertEqual(out.verdict, DENY)
        self.assertIn("no order fixes it", " ".join(out.reasons))

    def test_the_feeder_ceiling_is_a_denial_not_a_stagger(self):
        halls, feeders = world(hall("a", "F1", feed=8.0),
                               hall("b", "F1", feed=8.0),
                               limit=1.0, step=40.0)
        out = admit(Start("j", {"a": 10, "b": 10}), halls, feeders)
        self.assertEqual(out.verdict, DENY)
        self.assertIn("ceiling is", " ".join(out.reasons))

    def test_other_tenants_on_the_feeder_count(self):
        halls, feeders = world(hall("a", "F1", feed=8.0), limit=3.0, step=40.0)
        light = admit(Start("j", {"a": 10}), halls, feeders)
        heavy = admit(Start("j", {"a": 10}), halls, feeders,
                      running_mw={"F1": 2.5})
        self.assertEqual(light.verdict, ADMIT)
        self.assertEqual(heavy.verdict, DENY)

    def test_the_stagger_order_is_deterministic(self):
        halls, feeders = world(hall("a", "F1"), hall("b", "F1"),
                               limit=40.0, step=1.5)
        # 5 racks steps 0.52 MW and 10 racks steps 1.04 MW; each clears the
        # 1.5 MW step limit alone and together they do not.
        first = admit(Start("j", {"a": 5, "b": 10}), halls, feeders)
        again = admit(Start("j", {"a": 5, "b": 10}), halls, feeders)
        self.assertEqual(first.stagger_order, again.stagger_order)
        self.assertEqual(first.stagger_order[0], "b")   # larger step first


class TestInputs(unittest.TestCase):
    def test_a_hall_cannot_be_denser_than_its_rung(self):
        with self.assertRaises(ValueError):
            hall("h", rung=RDX, kw=100.0)

    def test_an_empty_start_is_rejected(self):
        with self.assertRaises(ValueError):
            Start("j", {})

    def test_an_unknown_hall_is_an_error_not_a_denial(self):
        halls, feeders = world(hall("a"))
        with self.assertRaises(ValueError):
            admit(Start("j", {"z": 1}), halls, feeders)

    def test_an_unknown_feeder_is_an_error(self):
        halls = {"a": hall("a", feeder="missing")}
        with self.assertRaises(ValueError):
            admit(Start("j", {"a": 1}), halls, {"F1": Feeder("F1", 10, 10)})

    def test_explain_names_the_verdict(self):
        halls, feeders = world(hall("a"))
        self.assertTrue(admit(Start("j", {"a": 1}), halls,
                              feeders).explain().startswith("ADMIT"))


if __name__ == "__main__":
    unittest.main()
