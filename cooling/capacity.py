"""IT power headroom behind an existing utility feed.

At a fixed utility feed, IT power = feed / PUE. Improving PUE frees IT
capacity behind an interconnection that already exists. This arithmetic does
not establish retrofit lead time, permitting, or data-center load connection time.
"""

from .ladder import Rung, pue

# DGX H100 system: 8 GPUs, 10.2 kW maximum spec draw [11]. Used only to
# translate freed megawatts into a familiar unit.
H100_NODE_KW = 10.2
GPUS_PER_NODE = 8

# Conservative all-in build-cost anchor for new datacenter capacity, ~$10M
# per MW of IT load (site, shell, power, cooling — not GPUs) [14]; AI-
# optimized builds are commonly cited higher, which only strengthens the
# retrofit comparison. Planning anchor, not a quote.
NEW_BUILD_USD_PER_MW = 10_000_000.0

def it_mw(feed_mw: float, pue_value: float) -> float:
    """IT megawatts deliverable from a utility feed at a given PUE."""
    if feed_mw <= 0:
        raise ValueError("feed must be > 0")
    if pue_value < 1.0:
        raise ValueError("PUE cannot be below 1.0")
    return feed_mw / pue_value


def freed_mw(feed_mw: float, pue_from: float, pue_to: float) -> float:
    """IT megawatts freed by moving the same feed from pue_from to pue_to."""
    return it_mw(feed_mw, pue_to) - it_mw(feed_mw, pue_from)


def h100_equivalents(mw: float) -> int:
    """Freed IT megawatts expressed as DGX-H100-node GPU counts [11]."""
    if mw < 0:
        raise ValueError("megawatts must be >= 0")
    return int(mw * 1000.0 / H100_NODE_KW) * GPUS_PER_NODE


def retrofit_cost_usd(feed_mw: float, pue_to: float, to: Rung) -> float:
    """Capex to move a site onto rung `to`, charged per IT kW cooled there."""
    return to.retrofit_usd_per_kw * it_mw(feed_mw, pue_to) * 1000.0


def cost_per_freed_mw(feed_mw: float, pue_from: float, to: Rung,
                      climate: str = "temperate",
                      water_mode: str = "evaporative") -> tuple:
    """(freed IT MW, retrofit $, $ per freed MW) for a rung transition.

    Freed capacity must be positive — a transition that frees nothing has
    no cost-per-MW. NEW_BUILD_USD_PER_MW is a planning scenario, not a quote.
    This comparison does not model permitting or construction lead time.
    """
    pue_to = pue(to, climate, water_mode)
    mw = freed_mw(feed_mw, pue_from, pue_to)
    if mw <= 0:
        raise ValueError(
            f"moving from PUE {pue_from} to {to.name} "
            f"(PUE {pue_to:.3f}) frees no capacity")
    cost = retrofit_cost_usd(feed_mw, pue_to, to)
    return mw, cost, cost / mw
