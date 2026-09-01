# The Cooling Ladder: Density, PUE, and Ride-Through as One Executable Model for AI Facilities

**Margaret Nanyonga**, DIMAGGI AI

> Staged whitepaper. The claims, figures, and numbers here are reproduced
> by the accompanying open-source repository
> (`dimaggi-ai/cooling-pue-ladder`, MIT).

## Abstract

AI rack power moved from ~40 kW H100-era configurations to 120+ kW in
one product generation — and from a ~10 kW enterprise norm in under a
decade — turning cooling from a facilities line-item into the gate that decides
whether a site can host current-generation compute at all. We model the
cooling ladder — legacy air, contained air, rear-door heat exchange,
direct-to-chip liquid, immersion — as one executable object in which each
rung carries a density ceiling, a climate-dependent PUE
(`floor + (1 − f) × penalty`), a heat-capture fraction, a thermal buffer,
and a retrofit cost. Five findings follow. **(1)** Density, not
efficiency, forces the ladder: an NVL72-class ~120 kW rack leaves only the
two liquid rungs feasible, and the rear-door step buys 2.5× density while
slightly *worsening* cold-climate PUE against best-in-class contained
air. **(2)** A PUE point is unqueued megawatts: at fixed feed, IT power is
feed/PUE, so moving 10 MW from the industry-survey average of ~1.56 to
1.2 frees ~1.9 MW — ~1,500 H100s' worth — behind an existing
interconnection, against a median ~5-year queue for new grid capacity and
at roughly a fifth to a half of the ~$10M/MW new-build anchor. **(3)** The
2014 and 2024 survey-average PUE levels (~1.70, ~1.56) and published
hyperscale fleets (~1.08-1.10) are reproduced *at once* by one
adoption mechanism — efficiency ships in new builds, which are few by
site count and large by energy — implying energy-weighted PUE, not survey
averages, is the KPI a buyer should demand; our simulated 2024 gap is
~0.31-0.36 across seeds (mean 0.33 over 24). **(4)** Efficiency sells ride-through: the direct-to-chip rung AI
requires today is the ladder's thermal-buffer minimum (~11 s at 132
kW/rack, versus minutes for air rooms and immersion tanks), promoting
cooling-loss to a first-class fault class for chaos programs. **(5)**
Water is a priced axis: evaporative rejection buys free-cooling hours at
~1 L/kWh-class WUE; dry rejection returns the water for a modeled
+0.015-0.08 PUE (+0.02-0.03 on direct-to-chip). An eleven-point
validation registry separates three kinds: calibrated points (published
fleet PUEs and the 2014 survey initial condition, which the model was
tuned to and which therefore prove only that it has not drifted),
emergent points (the 2024 survey level and the divergence — held-out
figures nothing was fitted to), and sanity points (the density verdicts
and the per-seed dispersion check, which pin the ladder's own structure
and cite nothing). A negative-control suite breaks the model on purpose
and requires named points to go red; the registry also prints what it
does NOT check.

## 1. Model

Rungs are frozen dataclasses with exposed constants; PUE is
`floor + (1 − f_eff) × penalty` with `f_eff` the effective free-cooling
fraction (four climate archetypes, shifted by the heat-rejection mode:
evaporative +0.10, hybrid +0.03, dry −0.12, capped to [0,1]). Legacy air
is not economizer-capable and pins at ~1.9. Capacity arithmetic is the
identity IT = feed/PUE; retrofit economics charge $/kW on the IT capacity
cooled at the destination rung; ride-through is thermal buffer over rack
power. The synthetic fleet starts as an all-legacy stock matching the
2014 survey average, grows ~15%/yr with all growth arriving as large new
builds on the era's rung (contained air to 2017, rear-door to 2021,
direct-to-chip after), and retires legacy capacity at 2%/yr.

## 2. Validation

Calibrated points: Google fleet ~1.09, Meta ~1.09, NREL ESIF 1.036,
immersion vendor ~1.04, legacy stock ~1.9, and the Uptime 2014 survey
average (~1.70) — the simulation's initial condition, so matching it is
calibration, not evidence. Emergent points, both held-out: the Uptime
2024 (~1.56) survey average and the ~0.31-0.36 survey/energy-weighted
divergence from the fleet mechanism. Sanity points, which cite nothing:
NVL72 (2 feasible rungs) and a DGX-H100 rack (3 feasible rungs) are
verdicts the ladder returns for densities fed IN — the rack draws are
inputs, not anchors, and no source publishes a count of feasible rungs,
so a ref beside them would dress a structural consequence as a sourced
result. The per-seed divergence count is likewise structural. The
simulation
reproduces the two survey levels and the divergence, not the
flat-since-2020 shape of the published series. All sources are public:
company-published figures quoted as facts, publicly released DOE-lab
reports, vendor spec sheets, survey headline numbers. Synthetic data is
seeded and deterministic; tests assert the divergence mechanism holds
across seeds.

## 3. What a skeptic should attack

Retrofit costs and thermal buffers are planning assumptions; the climate
model is four scalar archetypes; the fleet simulation demonstrates a
mechanism rather than forecasting, and its simulated survey never churns
respondents while the divergence is partly definitional (unweighted site
average vs energy-weighted); PUE floors bundle operational maturity;
WUE is a per-mode constant, not hour-scheduled; heat-reuse revenue,
refrigerant regulation, and water pricing are unmodeled. Every disputed
number is a named constant — change it and rerun.

## 4. Conclusion

Cooling is the exchange rate between a grid feed and nominal IT power,
and the ladder is how a site buys density, efficiency, and risk in one
decision. The operator's question is not "what is a good PUE" but "which
rung does my rack force, what does the freed megawatt cost, and how many
seconds of thermal buffer am I trading away to get it."
