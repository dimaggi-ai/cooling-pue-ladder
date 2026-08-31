"""The cooling ladder: five rungs from legacy air to immersion.

Each rung carries a density ceiling, a mechanical-PUE model, a heat-capture
fraction, and a thermal buffer. The PUE model is deliberately simple:

    PUE = floor + (1 - f_eff) * penalty

where `floor` is the rung's best-case overhead with free cooling available
year-round, `penalty` is the full-mechanical-cooling overhead added when no
free-cooling hour is available, and `f_eff` is the effective free-cooling
fraction of the year (climate plus heat-rejection mode). Constants map to
entries in REFERENCES.md; values without a published anchor are labeled
planning assumptions and are meant to be overridden.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rung:
    name: str
    max_kw_per_rack: float      # density ceiling before this rung runs out
    pue_floor: float            # best-case PUE, year-round free cooling
    mech_penalty: float         # added PUE at zero free-cooling hours
    economizer_capable: bool    # False -> climate never helps (f_eff = 0)
    heat_capture: float         # fraction of IT heat leaving in liquid
    thermal_buffer_kj: float    # usable thermal mass per rack on cooling loss
    retrofit_usd_per_kw: float  # capex to reach this rung, per IT kW cooled


# Density ceilings: ~10 kW/rack is the classic uncontained-air comfort zone,
# ~20 kW stretches contained air, ~50 kW is the practical rear-door limit,
# 132 kW is the NVL72-class liquid rack shipping today [10], and immersion
# tanks are marketed to ~200 kW [13]. PUE floors/penalties are calibrated so
# the rungs reproduce the published fleet points in validation.py [2-5].
# Retrofit $/kW and thermal buffers are planning assumptions, not a survey.
RUNGS = (
    Rung("legacy-air",      10.0, 1.45, 0.45, False, 0.00,  2500.0,    0.0),
    Rung("contained-air",   20.0, 1.06, 0.35, True,  0.00,  2500.0,  250.0),
    Rung("rear-door-hx",    50.0, 1.09, 0.22, True,  0.85,  1200.0,  550.0),
    Rung("direct-to-chip", 132.0, 1.03, 0.15, True,  0.75,  1500.0,  900.0),
    Rung("immersion",      200.0, 1.02, 0.10, True,  0.95, 40000.0, 1400.0),
)
# Heat capture is NOT monotonic on the ladder: a rear-door exchanger
# neutralizes most-to-all rack exhaust heat into its water loop (marketed
# to 100%; modeled 0.85), while single-phase direct-to-chip captures
# ~70-80% to liquid with the remainder rejected to room air [12].


def rung(name: str) -> Rung:
    for r in RUNGS:
        if r.name == name:
            return r
    raise ValueError(f"unknown rung: {name!r}")


# Free-cooling fraction of the year by climate archetype. Synthetic planning
# profiles (not a weather dataset): the spread matters, not the third digit.
CLIMATES = {
    "cold":      0.97,
    "temperate": 0.85,
    "hot-dry":   0.55,
    "hot-humid": 0.35,
}

# Heat-rejection mode shifts the effective free-cooling fraction and sets the
# water bill: evaporative assist buys free-cooling hours at ~1 L/kWh-IT-class
# water use [3]; dry rejection gives the water back and returns some hours.
WATER_MODES = {
    # name: (f_eff shift, WUE liters per IT kWh — planning assumptions)
    "evaporative": (+0.10, 1.20),
    "hybrid":      (+0.03, 0.40),
    "dry":         (-0.12, 0.05),
}


def effective_free_cooling(climate: str, water_mode: str) -> float:
    if climate not in CLIMATES:
        raise ValueError(f"unknown climate: {climate!r}")
    if water_mode not in WATER_MODES:
        raise ValueError(f"unknown water mode: {water_mode!r}")
    shift, _ = WATER_MODES[water_mode]
    return min(1.0, max(0.0, CLIMATES[climate] + shift))


def pue(r: Rung, climate: str = "temperate",
        water_mode: str = "evaporative") -> float:
    """Mechanical PUE of a rung in a climate with a heat-rejection mode."""
    f = effective_free_cooling(climate, water_mode)
    f_eff = f if r.economizer_capable else 0.0
    return r.pue_floor + (1.0 - f_eff) * r.mech_penalty


def wue(water_mode: str) -> float:
    """Water use effectiveness of the heat-rejection mode, liters per IT kWh."""
    if water_mode not in WATER_MODES:
        raise ValueError(f"unknown water mode: {water_mode!r}")
    return WATER_MODES[water_mode][1]


def feasible_rungs(kw_per_rack: float):
    """Rungs whose density ceiling admits the target rack power."""
    if kw_per_rack <= 0:
        raise ValueError("rack power must be > 0")
    return tuple(r for r in RUNGS if kw_per_rack <= r.max_kw_per_rack)


def ride_through_s(r: Rung, kw_per_rack: float) -> float:
    """Seconds of thermal buffer after total cooling loss at this density.

    thermal_buffer_kj / kW = seconds. The middle of the ladder is the
    minimum: a direct-to-chip loop at NVL72 density holds seconds, an air
    room holds minutes, and an immersion tank's fluid mass buys minutes
    back. Buffers are planning assumptions, labeled in RUNGS.
    """
    if kw_per_rack <= 0:
        raise ValueError("rack power must be > 0")
    if kw_per_rack > r.max_kw_per_rack:
        raise ValueError(f"{r.name} cannot cool {kw_per_rack} kW/rack")
    return r.thermal_buffer_kj / kw_per_rack
