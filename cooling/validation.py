"""Validation registry: the model against public, checkable data points.

Three kinds of points, honestly separated:

  CALIBRATED — the rung constants were tuned so these reproduce. Passing
    proves the repo has not drifted from its citations; it is not evidence
    that the model predicts anything. Carries a ref.
  EMERGENT — a behavior the model was NOT tuned to produce, checked against
    a held-out published figure. Only two points qualify: the fleet is
    tuned to the 2014 survey average and then *predicts* the 2024 one, and
    the survey/energy-weighted divergence falls out of the adoption
    mechanism in fleet.py. Carries a ref because the ref is the held-out
    number, not an input.
  SANITY — properties of the model's own structure, pinned so they cannot
    drift silently. Cites nothing and claims nothing: where a published
    spec is an INPUT to one of these (a rack's kW draw, say), it belongs in
    the note, because a ref column beside a model output dresses a
    structural consequence as a sourced result.

DECLINED below names what this registry does NOT check, and the CLI prints
it under the table. tests/test_validation.py breaks the model on purpose
and requires named points to go red — a registry nobody has watched fail
is evidence that the registry is easy, not that the model is right.
"""

import statistics
from dataclasses import dataclass

from .ladder import RUNGS, feasible_rungs, pue
from .fleet import simulate

# Every fleet quantity below is a MEAN over these seeds, not a single draw.
# It used to be seed 7 alone, which sat near the top of the spread on all
# three fleet quantities — a single lucky draw and a published anchor are
# indistinguishable from a fitted one to anyone reading the code.
SEEDS = tuple(range(24))
DIVERGENCE_FLOOR = 0.25   # the two-fleets gap must clear this in every seed

# Densities these verdicts are computed FOR; inputs to a sanity point,
# not anchors for it.
NVL72_KW = 120.0            # [10] publishes this PER RACK.
# [11] publishes 10.2 kW per NODE, not a rack figure. Four nodes to a
# rack is OUR assumption and is not in [11]; keeping it as a bare 41.0
# cited to [11] attributed the packing decision to NVIDIA.
DGX_H100_NODE_KW = 10.2
DGX_H100_NODES_PER_RACK = 4
DGX_H100_KW = DGX_H100_NODE_KW * DGX_H100_NODES_PER_RACK

# Anchors a reader might reasonably expect, and why they are absent.
DECLINED: tuple[tuple[str, str], ...] = (
    ("Any measured PUE for a datacenter this repo modeled",
     "the calibrated points compare the ladder's rung constants against "
     "figures Google, Meta and NREL published for THEIR sites. Nothing here "
     "measures a facility, and the rung constants were tuned to these "
     "figures, so agreement is consistency, not prediction."),
    ("Meta's cooling technology",
     "meta-fleet-avg-pue matches a PUE LEVEL only. Meta's fleet is "
     "direct-evaporative outside-air cooled, not rear-door; the rung that "
     "reproduces the number is not the technology Meta runs."),
    ("The observed shape of the survey average since 2020",
     "the model reproduces the 2014 and 2024 endpoints and slides between "
     "them. The published series is roughly FLAT after 2020, which this "
     "adoption mechanism does not produce — a known miss, disclosed in "
     "fleet.py and docs/study.md rather than tuned away."),
    ("The SIZE of the decade decline",
     "both survey endpoints sit inside their bands, but the model falls "
     "about 0.086 over the decade where the published series falls about "
     "0.14: it starts ~0.055 below the 2014 anchor and lands on the 2024 "
     "one. Endpoint agreement is therefore weaker evidence than it looks, "
     "and no point here pins the slope."),
    ("Retrofit costs and thermal buffers",
     "retrofit_usd_per_kw and thermal_buffer_kj are planning assumptions "
     "with no published anchor. No point pins them, and the CLI's "
     "ride-through and payback outputs inherit that uncertainty."),
    ("Water use",
     "WUE per heat-rejection mode is a planning assumption; the repo "
     "reports a water/energy trade-off but validates neither side of it "
     "against a measured site."),
    ("Whether the free-cooling fractions describe real climates",
     "CLIMATES holds four synthetic planning archetypes, not a weather "
     "dataset. The spread is the content; no point claims that 0.85 is "
     "the right number for any named location."),
)


@dataclass(frozen=True)
class Point:
    name: str
    kind: str          # "calibrated" | "emergent" | "sanity"
    ref: str           # REFERENCES.md entry; "-" for sanity points
    expected: float
    tolerance: float
    actual: float
    note: str = ""

    @property
    def ok(self) -> bool:
        return abs(self.actual - self.expected) <= self.tolerance


def points():
    """All validation points, computed fresh from the model."""
    sim = {s: simulate(seed=s) for s in SEEDS}
    survey_2014 = statistics.mean(sim[s][2014][0] for s in SEEDS)
    survey_2024 = statistics.mean(sim[s][2024][0] for s in SEEDS)
    weighted_2024 = statistics.mean(sim[s][2024][1] for s in SEEDS)
    gaps = [sim[s][2024][0] - sim[s][2024][1] for s in SEEDS]

    return (
        # -- calibrated: fleet-published PUE figures --------------------
        Point("google-fleet-ttm-pue", "calibrated", "[3]", 1.09, 0.05,
              pue(RUNGS[1], "temperate", "evaporative"),
              "Google's published trailing-twelve-month fleet PUE. The "
              "contained-air rung's floor and penalty were tuned to land "
              "here, so this pins the constant against drift."),
        Point("meta-fleet-avg-pue", "calibrated", "[4]", 1.09, 0.05,
              pue(RUNGS[2], "cold", "evaporative"),
              "PUE-level consistency only — see DECLINED: Meta cools with "
              "direct evaporative outside air, not the rear-door exchanger "
              "this rung models."),
        Point("nrel-esif-pue", "calibrated", "[5]", 1.036, 0.02,
              pue(RUNGS[3], "cold", "evaporative"),
              "NREL's ESIF facility, a DOE-lab published figure, against "
              "the direct-to-chip rung in a cold climate."),
        Point("immersion-vendor-claim", "calibrated", "[13]", 1.04, 0.03,
              pue(RUNGS[4], "temperate", "evaporative"),
              "A VENDOR claim, weaker evidence than the fleet figures "
              "above, and pinned as such."),
        Point("legacy-stock-pue", "calibrated", "[6]", 1.90, 0.15,
              pue(RUNGS[0], "temperate", "evaporative"),
              "The legacy air rung against the published figure for older "
              "enterprise stock — the top of the ladder, and the initial "
              "condition the fleet simulation starts from."),
        Point("uptime-2014-survey-avg", "calibrated", "[2]", 1.70, 0.10,
              survey_2014,
              "The simulation's TUNED initial condition: fleet.py starts as "
              "an all-legacy stock chosen to match this. Calibrated, not "
              "emergent, because it is an input."),

        # -- emergent: held-out figures the model was not tuned to -------
        Point("uptime-2024-survey-avg", "emergent", "[2]", 1.56, 0.035,
              survey_2024,
              "The held-out end of the survey series: the fleet is tuned to "
              "2014 and run forward, and nothing in the adoption mechanism "
              "was fitted to 2024. The model lands at 1.559 against a "
              "published 1.56. The tolerance used to be 0.10, which reached "
              "up into the 2014 anchor's band, and the consequence was "
              "measured, not guessed: a fleet FROZEN at its 2014 stock — no "
              "modernization at all for a decade — cleared the old band on "
              "19 of these 24 seeds. Whether this point caught a null model "
              "depended on the draw. At 0.035 the 2024 band [1.525, 1.595] "
              "and the 2014 band [1.60, 1.80] are disjoint, so no frozen "
              "fleet passes on ANY seed. 0.035 is not a number fitted to "
              "the result: the mean misses the published figure by 0.0006, "
              "so any tolerance from 0.001 up to the 0.04 that disjointness "
              "allows gives the identical verdict. See DECLINED for the "
              "shape and the size of the decline this still misses."),
        Point("energy-weighted-divergence", "emergent", "[2][3][7]",
              0.30, 0.06, statistics.mean(gaps),
              "The two-fleets finding: the grid sees a far better fleet "
              "than the site-count survey does. Falls out of new capacity "
              "landing on efficient rungs, which nothing tuned for. The "
              "tolerance was 0.15 on an expectation of 0.30 — a band that "
              "admits anything from 0.15 to 0.45 and so could not fail. It "
              "is now 20% of the expected value, the same cap every other "
              "point in this repo is held to."),

        # -- sanity: the model's own structure, citing nothing -------------
        Point("divergence-holds-in-every-seed", "sanity", "-",
              float(len(SEEDS)), 0.0,
              float(sum(1 for g in gaps if g > DIVERGENCE_FLOOR)),
              f"The two-fleets gap clears {DIVERGENCE_FLOOR} in all "
              f"{len(SEEDS)} seeds (observed {min(gaps):.3f}-{max(gaps):.3f}). "
              f"{DIVERGENCE_FLOOR} IS a threshold and a chosen one, sitting "
              f"below the observed spread — on the current model this point "
              f"cannot fail, and it is not evidence for the gap's size. What "
              f"it adds is dispersion: the point above reports a MEAN, and a "
              f"mean can be carried by a few large draws, so this counts "
              f"seeds instead and would catch a bimodal result the average "
              f"hid. It claims nothing external."),
        Point("nvl72-feasible-rungs", "sanity", "-", 2.0, 0.0,
              float(len(feasible_rungs(NVL72_KW))),
              f"How many of the five rungs clear an NVL72-class rack at "
              f"{NVL72_KW:.0f} kW: two, direct-to-chip and immersion. The "
              f"rack draw is a published spec [10] and is an INPUT here; no "
              f"source publishes a count of feasible rungs, so this claims "
              f"nothing external. Half of it is true by construction — that "
              f"rung's ceiling IS the NVL72 spec — and the content is that "
              f"every air rung and the rear-door rung are excluded."),
        Point("dgx-h100-rack-needs-rear-door", "sanity", "-", 3.0, 0.0,
              float(len(feasible_rungs(DGX_H100_KW))),
              f"The same structural check at {DGX_H100_KW:.1f} kW: three "
              f"rungs clear it, so contained air is already out and "
              f"rear-door is the entry point. The density is "
              f"{DGX_H100_NODES_PER_RACK} x {DGX_H100_NODE_KW} kW; only the "
              f"node figure is published [11], and the nodes-per-rack "
              f"packing is OUR assumption, which is why no ref sits in the "
              f"column. Input assumption, model verdict."),
    )


def validate():
    """Return (points, all_ok)."""
    ps = points()
    return ps, all(p.ok for p in ps)
