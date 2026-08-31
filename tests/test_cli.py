"""CLI behavior, including the CI-gate exit codes."""

import contextlib
import io
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from cooling.cli import main  # noqa: E402


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(list(argv))
    return code, buf.getvalue()


class TestCli(unittest.TestCase):
    def test_ladder_lists_all_rungs(self):
        code, out = run("ladder")
        self.assertEqual(code, 0)
        for name in ("legacy-air", "contained-air", "rear-door-hx",
                     "direct-to-chip", "immersion"):
            self.assertIn(name, out)

    def test_gate_blocks_air_at_nvl72_density(self):
        code, out = run("gate", "--density", "120", "--rung",
                        "contained-air")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED", out)

    def test_gate_passes_liquid_at_nvl72_density(self):
        code, out = run("gate", "--density", "120", "--rung",
                        "direct-to-chip")
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_gate_blocks_beyond_ladder(self):
        code, out = run("gate", "--density", "250")
        self.assertEqual(code, 1)

    def test_capacity_prints_freed_mw(self):
        code, out = run("capacity", "--feed-mw", "10",
                        "--pue-from", "1.5", "--pue-to", "1.2")
        self.assertEqual(code, 0)
        self.assertIn("+1.67 MW", out)

    def test_fleet_runs(self):
        code, out = run("fleet")
        self.assertEqual(code, 0)
        self.assertIn("2024", out)

    def test_validate_passes(self):
        code, out = run("validate")
        self.assertEqual(code, 0)
        self.assertNotIn("FAIL\n", out)

    def test_invalid_input_exits_2_without_traceback(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code, _ = run("gate", "--density", "0")
        self.assertEqual(code, 2)
        self.assertIn("error:", buf.getvalue())
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code, _ = run("capacity", "--feed-mw", "-10",
                          "--pue-from", "1.5", "--pue-to", "1.2")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
