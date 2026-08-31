"""Validation registry: the model against public, checkable data points.

Two kinds of points, honestly separated:
  CALIBRATED — the rung constants were tuned so these reproduce; passing
    proves internal consistency, not predictive power.
  EMERGENT — behaviors the model was not directly tuned to (the survey
    plateau and the survey/energy-weighted divergence emerge from the
    adoption mechanism in fleet.py; the density verdicts follow from
    published rack specs).

Every expected value cites a REFERENCES.md entry. Sources are public:
company-published fleet figures quoted as facts, US-government (DOE lab)
reports in the public domain, vendor spec sheets, and industry survey
headline numbers.
"""

from dataclasses import dataclass

from .ladder import RUNGS, feasible_rungs, pue
from .fleet import simulate


@dataclass(frozen=True)
class Point:
    name: str
    kind: str          # "calibrated" | "emergent"
    ref: str           # REFERENCES.md entry
    expected: float
    tolerance: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.actual - self.expected) <= self.tolerance


def points():
    """All validation points, computed fresh from the model."""
    sim = simulate(seed=7)
    survey_2014, _ = sim[2014]
    survey_2024, weighted_2024 = sim[2024]

    return (
        # -- calibrated: fleet-published PUE figures --------------------
        Point("google-fleet-ttm-pue", "calibrated", "[3]", 1.09, 0.05,
              pue(RUNGS[1], "temperate", "evaporative")),
        # PUE-level consistency match only: Meta's fleet is direct-
        # evaporative/outside-air cooled, not rear-door — the rung choice
        # matches the published number, not Meta's technology.
        Point("meta-fleet-avg-pue", "calibrated", "[4]", 1.09, 0.05,
              pue(RUNGS[2], "cold", "evaporative")),
        Point("nrel-esif-pue", "calibrated", "[5]", 1.036, 0.02,
              pue(RUNGS[3], "cold", "evaporative")),
        Point("immersion-vendor-claim", "calibrated", "[13]", 1.04, 0.03,
              pue(RUNGS[4], "temperate", "evaporative")),
        Point("legacy-stock-pue", "calibrated", "[6]", 1.90, 0.15,
              pue(RUNGS[0], "temperate", "evaporative")),
        # The 2014 survey average is the simulation's tuned initial
        # condition (fleet.py starts as an all-legacy stock chosen to
        # match it) — calibrated, not emergent.
        Point("uptime-2014-survey-avg", "calibrated", "[2]", 1.70, 0.10,
              survey_2014),
        # -- emergent: the two-fleets story ------------------------------
        Point("uptime-2024-survey-avg", "emergent", "[2]", 1.56, 0.10,
              survey_2024),
        Point("energy-weighted-divergence", "emergent", "[2][3][7]",
              0.30, 0.15, survey_2024 - weighted_2024),
        # -- emergent: density verdicts from published rack specs --------
        # The direct-to-chip-fits half is true by construction (that
        # rung's ceiling IS the NVL72 spec); the emergent content is
        # that every air rung and the rear-door rung are excluded.
        Point("nvl72-feasible-rungs", "emergent", "[10]", 2.0, 0.0,
              float(len(feasible_rungs(120.0)))),
        Point("dgx-h100-rack-needs-rear-door", "emergent", "[11]", 3.0, 0.0,
              float(len(feasible_rungs(41.0)))),
    )


def validate():
    """Return (points, all_ok)."""
    ps = points()
    return ps, all(p.ok for p in ps)
