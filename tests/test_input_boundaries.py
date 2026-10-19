"""Malformed inputs are errors, never evidence for an admission verdict."""

from dataclasses import asdict, replace
import json
import math
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling import ladder
from cooling.admission import ADMIT, DENY, STAGGER, Feeder, Hall, Start, admit


INVALID_NUMBERS = (float("nan"), float("inf"), -float("inf"),
                   True, False, "1", None)
D2C = ladder.rung("direct-to-chip")


class TestAdmissionBoundary(unittest.TestCase):
    def setUp(self):
        self.hall = Hall("h", "f", D2C, 100.0, 0, 8.0)
        self.feeder = Feeder("f", 40.0, 40.0)
        self.start = Start("j", {"h": 1})

    def decide(self, *, hall=None, feeder=None, start=None, running_mw=None):
        return admit(start or self.start, {"h": hall or self.hall},
                     {"f": feeder or self.feeder}, running_mw)

    def test_four_reported_nan_admissions_raise_and_finite_controls_deny(self):
        # At the original pin all four NaN substitutions produced ADMIT.
        changes = (
            ("hall", self.hall, "feed_mw", 0.01),
            ("feeder", self.feeder, "limit_mw", 0.01),
            ("feeder", self.feeder, "max_step_mw", 0.01),
            ("start", self.start, "min_ride_through_s", 1000.0),
        )
        for argument, original, field, restrictive in changes:
            with self.subTest(field=field):
                result = self.decide(**{argument: replace(original, **{field: restrictive})})
                self.assertEqual(result.verdict, DENY)
                with self.assertRaises(ValueError):
                    self.decide(**{argument: replace(original, **{field: float("nan")})})

    def test_every_admission_numeric_field_rejects_nonfinite_and_wrong_types(self):
        targets = ((self.hall, ("kw_per_rack", "racks_running", "feed_mw")),
                   (self.feeder, ("limit_mw", "max_step_mw")),
                   (self.start, ("min_ride_through_s",)))
        for original, fields in targets:
            for field in fields:
                for value in INVALID_NUMBERS:
                    with self.subTest(field=field, value=value):
                        with self.assertRaises(ValueError):
                            replace(original, **{field: value})
        for value in INVALID_NUMBERS:
            with self.subTest(racks=value):
                with self.assertRaises(ValueError):
                    Start("j", {"h": value})

    def test_range_and_integrality_requirements(self):
        cases = ((self.hall, "kw_per_rack", (0, -1, 133)),
                 (self.hall, "feed_mw", (0, -1)),
                 (self.hall, "racks_running", (-1, 0.5)),
                 (self.feeder, "limit_mw", (0, -1)),
                 (self.feeder, "max_step_mw", (0, -1)),
                 (self.start, "min_ride_through_s", (-1,)))
        for original, field, values in cases:
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        replace(original, **{field: value})
        for racks in (0, -1, 1.5):
            with self.subTest(racks=racks):
                with self.assertRaises(ValueError):
                    Start("j", {"h": racks})

    def test_integral_floats_preserve_joined_call_and_arithmetic(self):
        hall = replace(self.hall, kw_per_rack=81.6, racks_running=0.0, feed_mw=0.6)
        result = self.decide(hall=hall, feeder=Feeder("f", 0.6, 0.6),
                             start=Start("job-0", {"h": 2.0}, 5.0))
        self.assertEqual(result.verdict, ADMIT)
        self.assertAlmostEqual(result.steps_mw["h"], 0.16932)
        self.assertEqual(hall.facility_mw(2), hall.facility_mw(2.0))
        self.assertEqual(replace(hall, racks_running=2.0).running_mw,
                         hall.facility_mw(2))
        self.assertEqual(hall.facility_mw(0.0), 0.0)
        self.assertAlmostEqual(hall.ride_through_s, 1500.0 / 81.6)

    def test_external_load_is_checked_before_early_denial_and_on_unused_feeders(self):
        halls = {"h": replace(self.hall, feed_mw=0.01)}
        feeders = {"f": self.feeder, "unused": Feeder("unused", 10, 10)}
        for value in (*INVALID_NUMBERS, -1):
            for feeder_id in feeders:
                with self.subTest(feeder=feeder_id, value=value):
                    with self.assertRaises(ValueError):
                        admit(self.start, halls, feeders, {feeder_id: value})
        with self.assertRaisesRegex(ValueError, "unknown feeder"):
            self.decide(running_mw={"missing": 0})
        self.assertEqual(self.decide(running_mw={"f": 0.0}).verdict, ADMIT)
        self.assertEqual(self.decide(feeder=Feeder("f", 1, 1),
                                     running_mw={"f": 0.99}).verdict, DENY)

    def test_mutating_start_mapping_does_not_bypass_admission_checks(self):
        for value in (*INVALID_NUMBERS, 0, -1, 0.5):
            racks = {"h": 1}
            start = Start("j", racks)
            racks["h"] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.decide(start=start)
        racks = {"h": 1}
        start = Start("j", racks)
        racks.clear()
        with self.assertRaises(ValueError):
            self.decide(start=start)

    def test_direct_admission_revalidates_all_dataclass_fields(self):
        # Simulate reconstruction that bypassed frozen-dataclass constructors.
        targets = ((self.hall, "hall", ("kw_per_rack", "racks_running", "feed_mw")),
                   (self.feeder, "feeder", ("limit_mw", "max_step_mw")),
                   (self.start, "start", ("min_ride_through_s",)))
        for original, argument, fields in targets:
            for field in fields:
                for value in INVALID_NUMBERS:
                    changed = replace(original)
                    object.__setattr__(changed, field, value)
                    with self.subTest(field=field, value=value):
                        with self.assertRaises(ValueError):
                            self.decide(**{argument: changed})

    def test_direct_facility_arithmetic_rejects_invalid_racks(self):
        for value in (*INVALID_NUMBERS, -1, 0.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.hall.facility_mw(value)

    def test_ids_and_mapping_relationships_are_validated(self):
        for value in ("", " ", None, True, 1):
            for original, field in ((self.hall, "hall_id"),
                                    (self.hall, "feeder_id"),
                                    (self.feeder, "feeder_id"),
                                    (self.start, "job_id")):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        replace(original, **{field: value})
            with self.assertRaises(ValueError):
                Start("j", {value: 1})
        with self.assertRaisesRegex(ValueError, "does not match"):
            admit(self.start, {"alias": self.hall}, {"f": self.feeder})
        with self.assertRaisesRegex(ValueError, "does not match"):
            admit(self.start, {"h": self.hall}, {"alias": self.feeder})

    def test_wrong_container_and_object_types_raise_value_error(self):
        for value in (None, [], "h", 1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Start("j", value)
                with self.assertRaises(ValueError):
                    admit(self.start, value, {"f": self.feeder})
                with self.assertRaises(ValueError):
                    admit(self.start, {"h": self.hall}, value)
                if value is not None:  # None means external load is omitted.
                    with self.assertRaises(ValueError):
                        self.decide(running_mw=value)
        with self.assertRaises(ValueError):
            admit({}, {"h": self.hall}, {"f": self.feeder})
        with self.assertRaises(ValueError):
            admit(self.start, {"h": {}}, {"f": self.feeder})
        with self.assertRaises(ValueError):
            admit(self.start, {"h": self.hall}, {"f": {}})

    def test_json_decoded_invalid_values_are_not_coerced(self):
        # Python's default decoder accepts nonstandard nonfinite constants.
        for token in ("NaN", "Infinity", "-Infinity", "true", '"1"', "null"):
            value = json.loads(token)
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    replace(self.hall, feed_mw=value)
                with self.assertRaises(ValueError):
                    Start("j", {"h": value})
                with self.assertRaises(ValueError):
                    self.decide(running_mw={"f": value})

    def test_all_finite_verdicts_serialize_as_strict_json(self):
        halls = {"h": self.hall, "b": replace(self.hall, hall_id="b")}
        start = Start("j", {"h": 10.0, "b": 10})
        for expected, feeder in ((ADMIT, self.feeder),
                                 (STAGGER, Feeder("f", 40, 1.5)),
                                 (DENY, Feeder("f", 1, 1.5))):
            with self.subTest(expected=expected):
                result = admit(start, halls, {"f": feeder})
                self.assertEqual(result.verdict, expected)
                self.assertTrue(all(math.isfinite(v) for v in result.steps_mw.values()))
                self.assertEqual(json.loads(json.dumps(asdict(result), allow_nan=False))["verdict"],
                                 expected)

    def test_finite_inputs_with_unrepresentable_arithmetic_raise(self):
        with self.assertRaises(ValueError):
            self.hall.facility_mw(1e308)
        huge = replace(D2C, max_kw_per_rack=10 ** 308)
        hall = replace(self.hall, rung=huge, kw_per_rack=10 ** 308)
        with self.assertRaises(ValueError):
            hall.facility_mw(10 ** 308)
        # Individually finite hall steps/running loads can overflow on a feeder.
        hall = replace(self.hall, kw_per_rack=1.0, feed_mw=1e308)
        halls = {"h": hall, "b": replace(hall, hall_id="b")}
        feeder = Feeder("f", 1e308, 1e308)
        with self.assertRaises(ValueError):
            admit(Start("j", {"h": 1e308, "b": 1e308}), halls,
                  {"f": feeder}, {"f": 1.7976931348623157e308})


class TestCustomRungBoundary(unittest.TestCase):
    def test_every_custom_rung_numeric_field_is_checked(self):
        fields = ("max_kw_per_rack", "pue_floor", "mech_penalty", "heat_capture",
                  "thermal_buffer_kj", "retrofit_usd_per_kw")
        for field in fields:
            for value in INVALID_NUMBERS:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        replace(D2C, **{field: value})
        for field, value in (("max_kw_per_rack", 0), ("pue_floor", 0.99),
                             ("mech_penalty", -1), ("heat_capture", -0.1),
                             ("heat_capture", 1.1), ("thermal_buffer_kj", -1),
                             ("retrofit_usd_per_kw", -1), ("economizer_capable", 1),
                             ("name", "")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    replace(D2C, **{field: value})

    def test_finite_custom_rungs_and_zero_buffer_remain_supported(self):
        custom = replace(D2C, name="custom", max_kw_per_rack=150,
                         pue_floor=1.05, mech_penalty=0.1, heat_capture=1,
                         thermal_buffer_kj=0, retrofit_usd_per_kw=0)
        hall = Hall("h", "f", custom, 140, 0, 8)
        feeders = {"f": Feeder("f", 40, 40)}
        self.assertAlmostEqual(ladder.pue(custom), 1.055)
        self.assertEqual(hall.ride_through_s, 0)
        self.assertEqual(admit(Start("j", {"h": 1}), {"h": hall}, feeders).verdict, ADMIT)
        self.assertEqual(admit(Start("j", {"h": 1}, 1), {"h": hall}, feeders).verdict, DENY)

    def test_direct_ladder_calls_validate_density_and_custom_rung(self):
        for value in (*INVALID_NUMBERS, 0, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ladder.feasible_rungs(value)
                with self.assertRaises(ValueError):
                    ladder.ride_through_s(D2C, value)
        for field in ("max_kw_per_rack", "pue_floor", "mech_penalty",
                      "thermal_buffer_kj"):
            changed = replace(D2C)
            object.__setattr__(changed, field, float("nan"))
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    ladder.pue(changed)
                with self.assertRaises(ValueError):
                    ladder.ride_through_s(changed, 100)
                with self.assertRaises(ValueError):
                    Hall("h", "f", changed, 100, 0, 8)
        for value in (None, "direct-to-chip", {}):
            with self.assertRaises(ValueError):
                ladder.pue(value)
        with self.assertRaises(ValueError):
            ladder.pue(replace(D2C, pue_floor=1e308, mech_penalty=1e308,
                               economizer_capable=False))
        with self.assertRaises(ValueError):
            ladder.ride_through_s(D2C, 5e-324)

    def test_hall_validates_climate_and_water_mode_at_construction(self):
        for value in (None, "unknown", [], True):
            for field in ("climate", "water_mode"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        Hall("h", "f", D2C, 100, 0, 8, **{field: value})


if __name__ == "__main__":
    unittest.main()
