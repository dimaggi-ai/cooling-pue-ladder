# The cooling ladder: heat out, priced in PUE, megawatts, and seconds

**The question.** AI racks jumped from ~40 kW H100-era configurations
[11] to 120+ kW in one product generation [10] — and from a ~10 kW
enterprise norm in under a decade. Cooling decides three things at once: whether a site can
host the rack at all (density), how much of the utility feed reaches the
GPUs (PUE), and how many seconds the site survives a cooling fault
(ride-through). This study makes all three executable as one ladder.

## 1. The model

Five rungs — legacy air, contained air, rear-door heat exchange,
direct-to-chip liquid, immersion — each with a density ceiling, a PUE
model `floor + (1 − f_eff) × penalty` (where `f_eff` is the effective
free-cooling fraction from climate and heat-rejection mode), a
heat-capture fraction, a thermal buffer, and a retrofit cost. Constants
are calibrated to published fleet figures [2-6][10][11][13] or labeled
planning assumptions in the code.

## 2. Findings

**F1 — Density, not efficiency, forces the ladder.** Contained air ends
near ~20 kW/rack and rear-door heat exchange near ~50 kW; an NVL72-class
rack at ~120 kW [10] leaves exactly two rungs standing (`pue-ladder gate
--density 120`). The C1→C2 step is the clean proof: density ceiling ×2.5
while cold-climate PUE gets slightly *worse* — operators climb the lower
ladder for kilowatts, not PUE. For current-generation AI, direct-to-chip
is the entry ticket, and its PUE gain arrives as a side effect.

**F2 — A PUE point is unqueued megawatts.** At a fixed feed, IT power =
feed / PUE. Moving a 10 MW site from the survey-average 1.56 [2] to a
direct-to-chip-class 1.2 frees ~1.9 MW of IT — roughly 1,500 H100s'
worth [11] — behind an interconnection that already exists. The
alternative, new grid capacity, waits a median ~5 years in the queue [8]
while data centers head toward 6.7-12% of US electricity [7]. Priced
with our planning-assumption retrofit costs, freed capacity lands at
roughly $2-5.5M per freed MW depending on the starting PUE, destination
rung, and climate — ~$2.7M for the flagship case above (survey-average
1.56 to direct-to-chip, temperate) — a fraction of the ~$10M/MW
new-build anchor [14], which is itself deliberately conservative for
AI-optimized builds. Retrofits also ship on a construction schedule,
not a queue schedule.

**F3 — The plateau is two fleets.** The survey average has been stuck
near ~1.55-1.6 for years [2] while hyperscalers publish ~1.08-1.10
[3][4]. The synthetic-fleet simulation shows one mechanism reproduces
the 2014 (~1.7, its calibrated starting point) and 2024 (~1.56) survey
levels and the hyperscale fleet figures at once: PUE progress ships
almost entirely in new builds; new builds are few by site count (what a
survey averages) and huge by energy (what the grid sees). By 2024 the
simulated survey average (~1.56) and energy-weighted average (~1.23)
diverge by ~0.31-0.36 across seeds (mean 0.33 over 24). One
honest caveat: the simulation reproduces the two survey *levels* and
the divergence, not the observed shape between them — the published
series falls to ~2020 and then flattens, while the simulated average
falls smoothly. The practical read stands either way: fleet-average PUE
is the wrong KPI for a buyer — ask for the energy-weighted number, and
treat survey averages as a census of the retrofit backlog.

**F4 — Efficiency sells ride-through, immersion buys it back.** Thermal
buffer over rack power gives seconds of survival on total cooling loss:
minutes for an air room at 10 kW/rack, ~24 s for rear-door at 50 kW,
~11 s for a direct-to-chip loop at 132 kW — then ~200 s again for an
immersion tank, whose fluid mass is the buffer. The rung AI needs today
is the ladder's ride-through *minimum*, which makes cooling-loss a
first-class fault (pumps, CDUs, valves — the layer a chaos program must
inject at) rather than a facilities footnote.

**F5 — Water is a priced axis, not an ideology.** Evaporative heat
rejection buys free-cooling hours at a WUE on the order of ~1 L/kWh [3];
dry rejection returns the water and gives back some PUE (modeled: +0.015
to +0.08 depending on rung and climate; +0.02-0.03 on direct-to-chip,
where most AI capacity is heading). One model artifact worth knowing:
in the cold archetype the free-cooling fraction caps at 1.0, so
evaporative and hybrid modes land on identical PUE — evaporative is
strictly dominated there, paying ~3× the water for nothing. The model
prices the trade both ways so a site in a water-constrained region can
choose with numbers.

**F6 — Ride-through and headroom are admission fields, not facility
trivia.** F4 makes cooling loss a first-class fault. The next step is to
ask it at the moment a job starts, which `cooling/admission.py` does with
three fields the model already had. Two of them are properties of the
destination and no amount of sequencing helps: a job needing 30 s of
ride-through is refused on a direct-to-chip room at 132 kW/rack (~11 s)
and admitted on an immersion room at the *same density* (~303 s) — the
ladder gate passes both, and only the buffer separates them. Hall
headroom is the same kind of no: facility draw is IT power times PUE, and
sequencing does not create megawatts. The third is different. Halls that
share a feeder are not independent, and lighting two at once is one step
onto shared plant — a limit distinct from the ceiling, because the load
fits and the *transition* does not. That case is a **stagger**, the only
verdict here that means "later, in pieces." Move the same two halls onto
separate feeders and nothing else changes: the start admits. The order of
checks is fixed and stated — destination first, feeder last — because
telling an operator to stagger a start that was never going to fit is
worse than saying no.

## 3. The validation project

Fourteen points, three kinds, honestly separated (`pue-ladder validate`):

- **Calibrated** (constants tuned to reproduce them — consistency, not
  prediction): Google fleet ~1.09 [3], Meta ~1.09 [4], NREL ESIF 1.036
  [5], immersion vendor claims ~1.04 [13], legacy stock ~1.9 [6], and
  the 2014 Uptime survey average ~1.70 [2] — the fleet simulation's
  initial condition, so matching it is calibration, not evidence.
- **Emergent** (not directly tuned): the 2024 Uptime survey average and
  the survey/energy-weighted divergence out of the fleet simulation
  [2][7]. Both are means over 24 seeds, not a single draw — the default
  seed sat near the top of the spread on every fleet quantity.
- **Sanity** (the model's own structure, citing nothing): the NVL72 and
  DGX-H100 density verdicts. The rack draws are published specs [10][11],
  but they are INPUTS — no source publishes a count of feasible rungs, so
  these carry no ref. Plus a count that the two-fleets gap holds in every
  seed, so a mean carried by a few lucky draws would still be caught.

Two negative controls changed the registry rather than confirming it.
The 2024 survey point had a +/-0.10 band that reached up into the 2014
anchor's, and the cost of that was measurable: freeze the fleet at its
2014 all-legacy stock — no modernization at all for a decade — and it
still cleared the "held-out prediction" on **19 of 24 seeds**. The point
did fail on the seed this repo happened to ship, which is the
uncomfortable part: the check was not distinguishing a decade of
adoption from none, it was sampling. The band is now +/-0.035, chosen
so that [1.525, 1.595] and the 2014 anchor's [1.60, 1.80] are disjoint;
a frozen fleet now fails on every seed rather than most of them. The
tolerance is not fitted to the result — the model misses the published
figure by 0.0006, so anything from 0.001 to 0.04 gives the same verdict.
The divergence point had a +/-0.15 band on an expectation of 0.30,
admitting anything from 0.15 to 0.45; it is now +/-0.06. What survives
is disclosed in DECLINED: both endpoints sit in their bands, but the
model's decade decline is ~0.086 against a published ~0.14.

A third control found a mutation that was not testing what it claimed.
`fleet.py` does `from .ladder import pue`, binding its own name, so the
"replace the whole PUE model" mutation — which patched only the
registry's copy — left the entire simulated fleet running on the real
ladder. It now patches both modules, and reddens nine points instead of
five. A patch aimed at the wrong module does not fail loudly; it passes
quietly, which is why each mutation now names every module it reaches.

Three more sanity points arrived with the admission model, checking the
prose against the code rather than against the world: that the ladder's
ride-through minimum really is direct-to-chip, that at one density the
two rungs which cool it differ in ride-through by ~27x (the buffer
ratio — density decides which rungs are available, the rung decides how
long the room holds), and that a shared feeder turns two starts which
each admit alone into a stagger. The last one has real teeth: had the
feeder step been written as a second ceiling, the pair would deny
instead of stagger and the point would go red.

Synthetic data: the fleet simulation (seeded, deterministic,
`cooling/fleet.py`) generates a decade of site-level fleets; tests
assert the survey levels and the divergence hold across seeds. All
public inputs are non-copyrighted facts, publicly released
government-funded reports, or company-published figures quoted as
facts — see REFERENCES.md.

## 4. What a skeptic should attack

Retrofit $/kW and thermal-buffer constants are planning assumptions, not
a survey — both are exposed in `RUNGS` and meant to be overridden. The
climate model is four archetypes with a scalar free-cooling fraction,
not weather data. The fleet simulation's adoption timeline and growth
rates are stylized; it demonstrates a mechanism, it does not forecast —
and it reproduces the 2014/2024 survey levels and the divergence, not
the flat-since-2020 shape of the published series. The simulated
"survey" is itself a modeling choice: sites never exit the survey pool
once counted (real surveys churn respondents), and the survey metric
is an unweighted site average while the energy metric weights by
capacity — some of the divergence is definitional, which is part of the
point but should be said. WUE is a per-mode constant, not an
hour-by-hour schedule, so annual water figures are indicative. PUE
floors bundle operations maturity into the rung (a badly run
direct-to-chip site will miss 1.06). Heat-reuse revenue, refrigerant
regulations (two-phase fluids), and site water pricing are not modeled.
The ~$10M/MW new-build anchor [14] is an order-of-magnitude planning
figure — conservative, since AI-optimized builds are commonly quoted
well above it. The admission model is arithmetic
over declared inputs: it does not measure a plant, model an inrush
transient, or know what a real feeder does with one — the step limit is
an input, not a prediction, and the stagger order is deterministic
rather than optimal. Every one of these is a named constant in the code:
change it and rerun.
