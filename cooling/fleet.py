"""Synthetic fleet: why the survey-average PUE plateaued while the
energy-weighted truth kept improving.

Uptime's survey average has sat near ~1.55-1.6 since 2020 after falling
from ~1.7 in 2014 [2], while hyperscale fleets publish ~1.08-1.10 [3][4].
Both are real. The mechanism this simulation demonstrates: PUE progress
ships almost entirely in NEW capacity, new capacity is a small share of
SITE COUNT (what a survey averages) and a large share of ENERGY (what the
grid sees), and retrofit economics pin the legacy stock to its rung.

Scope, stated plainly: the simulation reproduces the 2014 and 2024
survey LEVELS and the survey/energy-weighted divergence. It does NOT
reproduce the observed shape between them (a fall to ~2020, then flat) —
the simulated average falls smoothly. What the mechanism explains is the
coexistence and the gap, not the year-by-year curve. A demonstration,
not a forecast; adoption constants are planning assumptions.
"""

import random
from dataclasses import dataclass

from .ladder import RUNGS, pue

CLIMATE_MIX = ("cold", "temperate", "temperate", "hot-dry", "hot-humid")

# Adoption timeline: which rung NEW capacity lands on, by build year.
# Planning assumption reflecting when each class went mainstream.
def _new_build_rung(year: int):
    if year < 2018:
        return RUNGS[1]           # contained-air era
    if year < 2022:
        return RUNGS[2]           # rear-door era
    return RUNGS[3]               # direct-to-chip era

GROWTH_RATE = 0.15               # fleet capacity CAGR — planning assumption
RETIRE_RATE = 0.02               # legacy capacity retired per year
NEW_SITE_MW = 20.0               # new builds are big (few sites, much energy)
LEGACY_SITE_MW = 1.0             # legacy stock is small (many sites)


@dataclass
class Site:
    rung_idx: int
    climate: str
    it_mw: float
    legacy: bool

    def pue(self) -> float:
        return pue(RUNGS[self.rung_idx], self.climate)


# Survey respondents below this size are dropped from the site-count
# average (a fractional-MW growth remainder is not a survey respondent).
SURVEY_FLOOR_MW = 0.1


def simulate(start_year: int = 2014, end_year: int = 2024,
             n_legacy: int = 400, seed: int = 7):
    """Evolve a fleet; return {year: (survey_avg, energy_weighted)} PUEs.

    Starts as an all-legacy stock (rungs 0-1) whose mix is the
    simulation's CALIBRATED initial condition, chosen to land near the
    2014 survey average [2]; growth of GROWTH_RATE per year then arrives
    as large new builds on the era's rung, and only the legacy stock
    retires capacity.
    """
    rng = random.Random(seed)
    fleet = [Site(rng.choice((0, 0, 1)), rng.choice(CLIMATE_MIX),
                  LEGACY_SITE_MW * rng.uniform(0.5, 2.0), True)
             for _ in range(n_legacy)]

    out = {}
    for year in range(start_year, end_year + 1):
        out[year] = _measure(fleet)
        total = sum(s.it_mw for s in fleet)
        # retire a slice of legacy capacity (new builds do not shrink)
        for s in fleet:
            if s.legacy:
                s.it_mw *= (1.0 - RETIRE_RATE)
        # growth arrives as new builds on the era's rung
        add_mw = total * GROWTH_RATE
        r = _new_build_rung(year)
        r_idx = RUNGS.index(r)
        while add_mw > 0:
            mw = min(NEW_SITE_MW, add_mw)
            fleet.append(Site(r_idx, rng.choice(CLIMATE_MIX), mw, False))
            add_mw -= mw
    return out


def _measure(fleet):
    surveyed = [s for s in fleet if s.it_mw >= SURVEY_FLOOR_MW]
    survey_avg = sum(s.pue() for s in surveyed) / len(surveyed)
    total_mw = sum(s.it_mw for s in fleet)
    energy_weighted = sum(s.pue() * s.it_mw for s in fleet) / total_mw
    return survey_avg, energy_weighted
