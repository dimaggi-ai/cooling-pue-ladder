# Admission numeric boundary correction — 19 September 2026

This fixes the B02 cooling input-validation gap on the working checkout based on
`4b94c6d6fc653e9eebd2933402826cd76b3a108d`. It implements the cooling predicates
in the local `2026-09-19-maggie-first-decision/Domain-Contract.md` and handoff.
The pinned audit checkout was used read-only for finite-output comparison.

## Verified before the change

At that commit, all 69 existing tests passed. The following four substitutions
were reproduced with a direct-to-chip hall at 100 kW/rack, zero running racks,
8 MW hall feed, 40 MW feeder ceiling/step and a one-rack start:

| Substituted field | Restrictive finite control | Control result | NaN result |
|---|---:|---|---|
| `Hall.feed_mw` | 0.01 MW | DENY | ADMIT |
| `Feeder.limit_mw` | 0.01 MW | DENY | ADMIT |
| `Feeder.max_step_mw` | 0.01 MW | DENY | ADMIT |
| `Start.min_ride_through_s` | 1000 s | DENY | ADMIT |

Separate probes also reproduced ADMIT with NaN in `Hall.kw_per_rack`,
`Hall.racks_running`, a start rack count, external `running_mw`, custom
`Rung.pue_floor`, or custom `Rung.thermal_buffer_kj`. Density, start-rack and
PUE substitutions emitted NaN steps. A `True` or `1.5` start rack count also
produced ADMIT. String/null hall feeds already raised `TypeError`; those were
not equivalent admission bugs. Other newly checked invalid values are covered
by the correction's regression matrix, without claiming each previously admitted.

## Boundary behavior

Invalid input raises `ValueError`; it does not become a physical `DENY` verdict.
Numbers must be finite Python `int`/`float` values, excluding `bool`. Numeric
strings, null, NaN, infinities, and integers beyond finite float representation
are rejected rather than coerced. Successful calculation results must also be
finite; arithmetic overflow raises `ValueError`.

| Input | Accepted domain |
|---|---|
| Hall feed, feeder ceiling/step | Positive MW |
| Hall density | Positive kW/rack, at most the rung ceiling |
| Running racks / direct `Hall.facility_mw` racks | Nonnegative integral-valued count |
| Start racks | Positive integral-valued count in at least one hall |
| Minimum ride-through | Nonnegative seconds |
| External feeder running load | Nonnegative MW, keyed by a known feeder |
| IDs | Nonempty strings; map keys match object IDs; references resolve |
| Climate / water mode | Existing known strings |

Integral floats remain supported: the joined-model call with 81.6 kW/rack,
`2.0` racks, 0.6 MW limits and a five-second requirement still admits, drawing
0.16932 MW. Zero running load and zero required ride-through remain valid.

Custom `Rung` values remain supported with any nonempty name. Their complete
numeric fields are checked: positive density ceiling, PUE floor >= 1,
nonnegative mechanical penalty, liquid heat capture in [0, 1], and nonnegative
thermal buffer and retrofit cost. The economizer flag must be boolean. Zero
buffer remains valid and fails any positive ride-through requirement. Existing
rung constants, formulas, admission ordering, tolerances and stagger ordering
are unchanged.

Constructors validate fields; `admit` revalidates the supplied objects and
mappings before a verdict, including all supplied external loads. A frozen
`Start` still contains its caller's rack mapping, so a later invalid mutation
now raises at admission. Direct `facility_mw`, `pue`, `ride_through_s` and
`feasible_rungs` calls enforce their numeric domains too. This is ordinary API
validation, not protection from concurrent mapping changes or arbitrary hostile
Python subclasses. Callers must provide stable mappings for the duration of a call.

## Verification

Environment: existing audit `.venv/bin/python`, Python 3.12.6; stdlib only for
these checks. No new environment install was performed. From this repository:

```sh
PY=/Users/dmitriisherstobitov/Projects/dimaggi-ai/projects/infrastructure/_Audits/2026-09-17-repo-aware-strategy/.venv/bin/python
"$PY" -m unittest discover -s tests -q
"$PY" -m unittest discover -s tools -p 'test_*.py' -q
"$PY" tools/validate_evidence.py evidence.json
git diff --check
```

Results: 87 model/API/CLI tests and one evidence-validator test pass. The new
`tests/test_input_boundaries.py` covers the four reported cases with restrictive
finite controls, field/type/range rejection, reconstruction and mapping mutation,
external loads, direct arithmetic, custom rungs, overflow, and strict JSON output
for ADMIT/STAGGER/DENY. CLI tests check exit 2 for NaN and both infinities in the
five numeric admission options. Python's permissive JSON-decoder outputs are
rejected at the object boundary; this repository has no admission JSON endpoint.
Report serializers should continue to use `allow_nan=False`.

A read-only subprocess comparison against the pin gave byte-for-byte identical
strict JSON for all five rung definitions, climate/water constants, 60 PUE
combinations, five ceiling ride-through values, 24 fleet seeds, all 14 validation
points, reference freed MW and retrofit economics. After reviewing this parity,
the source dates/hashes for the changed ladder and README in `evidence.json`
were refreshed; no model claims or values were changed.

The patch does not establish plant measurements, input freshness, reservation,
live scheduler behavior, or operational safety. Standalone capacity/fleet input
boundaries are outside this correction; no blanket numeric-hardening claim is
made for them. Span was not changed: its separate finite/type guards already
exist. Joined callers retain the valid rack-float path, but this patch does not
run the complete joined application or publish a release.
