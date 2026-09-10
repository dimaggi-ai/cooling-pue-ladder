"""Regenerate figures/ (requires matplotlib)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cooling import capacity
from cooling.ladder import RUNGS, pue, ride_through_s
from cooling.fleet import simulate

FG = "#233"


def fig_ladder():
    names = [r.name for r in RUNGS]
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(names, [r.max_kw_per_rack for r in RUNGS],
            color="#9fb4ae", label="density ceiling (kW/rack)")
    ax1.axhline(120, color="#b3402f", ls="--", lw=1.2)
    ax1.text(0.02, 123, "NVL72-class rack, ~120 kW [10]",
             color="#b3402f", fontsize=9)
    ax1.set_ylabel("density ceiling, kW/rack")
    ax2 = ax1.twinx()
    for climate, marker in (("cold", "o"), ("hot-humid", "s")):
        ax2.plot(names, [pue(r, climate) for r in RUNGS], marker=marker,
                 lw=1.5, label=f"PUE, {climate} (evaporative)")
    ax2.set_ylabel("mechanical PUE")
    ax2.set_ylim(1.0, 2.0)
    ax1.set_title("The cooling ladder: density is bought in rungs, "
                  "PUE comes along")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig("figures/ladder.png", dpi=150)


def fig_capacity():
    feed = 10.0
    pues = [1.9, 1.7, 1.56, 1.4, 1.3, 1.2, 1.1, 1.05]
    it = [capacity.it_mw(feed, p) for p in pues]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(pues, it, marker="o", color="#0e7c6b")
    ax.invert_xaxis()
    ax.set_xlabel("site PUE")
    ax.set_ylabel(f"IT MW from a fixed {feed:.0f} MW feed")
    for p_from, p_to in ((1.56, 1.2),):
        mw = capacity.freed_mw(feed, p_from, p_to)
        gpus = capacity.h100_equivalents(mw)
        ax.annotate(
            f"{p_from} → {p_to}: +{mw:.2f} MW ≈ {gpus:,} H100s [11]\n"
            "Derived power headroom; deployment timing not modeled",
            xy=(p_to, capacity.it_mw(feed, p_to)), xytext=(1.85, 8.6),
            fontsize=9, color=FG,
            arrowprops=dict(arrowstyle="->", color=FG, lw=1))
    ax.set_title("IT-power headroom behind an existing utility feed")
    fig.tight_layout()
    fig.savefig("figures/capacity.png", dpi=150)


def fig_two_fleets():
    sim = simulate(seed=7)
    years = list(sim)
    survey = [sim[y][0] for y in years]
    weighted = [sim[y][1] for y in years]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(years, survey, marker="o", color="#b7791f",
            label="survey average (site count)")
    ax.plot(years, weighted, marker="s", color="#0e7c6b",
            label="energy-weighted average")
    ax.scatter([2014, 2024], [1.70, 1.56], s=90, facecolors="none",
               edgecolors="#b3402f", zorder=5,
               label="Uptime survey points [2]")
    ax.set_ylabel("fleet PUE")
    ax.set_title("The plateau is two fleets: progress ships in new builds")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig("figures/two_fleets.png", dpi=150)


if __name__ == "__main__":
    fig_ladder()
    fig_capacity()
    fig_two_fleets()
    print("figures/ regenerated")
