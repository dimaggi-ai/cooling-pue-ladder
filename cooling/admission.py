"""Ride-through and headroom as admission fields.

The ladder answers "can this rung cool that density." A control plane has to
answer a narrower question at the moment a job starts: *given what is already
running, may this start light up now?* Three fields decide it, and all three
already exist in the model — they were just never asked at admission time.

**Ride-through.** ``ladder.ride_through_s`` gives the seconds of thermal buffer
after total cooling loss. A job that needs longer than the hall holds is not
admissible in that hall at that density, whatever the power situation.

**Hall headroom.** A hall's utility feed caps its facility draw, and facility
draw is IT power times PUE. A start whose steady load does not fit is denied;
no amount of sequencing creates megawatts.

**Feeder step.** Halls that share a feeder are not independent. Lighting two of
them at once is a single step onto shared plant, and a step is a different limit
from a ceiling: the load fits, the *transition* does not. That case is a
stagger, not a denial — the one verdict here that says "later, one at a time"
rather than yes or no.

Order matters and is fixed: ride-through, then hall headroom, then the feeder
step. The first two are properties of the destination and cannot be sequenced
away; only the third can. A denial from either of the first two is reported even
when the feeder would also have complained, because telling an operator to
stagger a start that was never going to fit is worse than saying no.

Scope: this is admission arithmetic over declared inputs. It does not measure a
plant, model a transient, or know what a real feeder does with an inrush. The
step limit is an input, not a prediction.
"""

from dataclasses import dataclass, field
from typing import Dict, Mapping, Tuple

from .ladder import Rung, pue, ride_through_s

ADMIT = "ADMIT"
STAGGER = "STAGGER"
DENY = "DENY"


@dataclass(frozen=True)
class Hall:
    """A room with one rung, one density, and a share of a feeder."""
    hall_id: str
    feeder_id: str
    rung: Rung
    kw_per_rack: float
    racks_running: int
    feed_mw: float                    # utility feed available to this hall
    climate: str = "temperate"
    water_mode: str = "evaporative"

    def __post_init__(self):
        if self.kw_per_rack <= 0:
            raise ValueError("rack power must be > 0")
        if self.kw_per_rack > self.rung.max_kw_per_rack:
            raise ValueError(
                f"{self.hall_id}: {self.rung.name} cannot cool "
                f"{self.kw_per_rack} kW/rack")
        if self.racks_running < 0:
            raise ValueError("racks_running must be >= 0")
        if self.feed_mw <= 0:
            raise ValueError("feed must be > 0")

    @property
    def pue(self) -> float:
        return pue(self.rung, self.climate, self.water_mode)

    @property
    def ride_through_s(self) -> float:
        return ride_through_s(self.rung, self.kw_per_rack)

    def facility_mw(self, racks: int) -> float:
        """Facility megawatts drawn by `racks` racks in this hall."""
        if racks < 0:
            raise ValueError("racks must be >= 0")
        return racks * self.kw_per_rack / 1000.0 * self.pue

    @property
    def running_mw(self) -> float:
        return self.facility_mw(self.racks_running)

    @property
    def headroom_mw(self) -> float:
        return self.feed_mw - self.running_mw


@dataclass(frozen=True)
class Feeder:
    """Shared plant upstream of one or more halls.

    ``limit_mw`` is the steady ceiling. ``max_step_mw`` is the largest load
    increase the feeder takes in one go, which is a separate number and the
    reason a stagger exists at all.
    """
    feeder_id: str
    limit_mw: float
    max_step_mw: float

    def __post_init__(self):
        if self.limit_mw <= 0:
            raise ValueError("feeder limit must be > 0")
        if self.max_step_mw <= 0:
            raise ValueError("feeder step limit must be > 0")


@dataclass(frozen=True)
class Start:
    """A job start, expressed as racks to light in named halls."""
    job_id: str
    racks: Mapping[str, int]
    min_ride_through_s: float = 0.0

    def __post_init__(self):
        if not self.racks:
            raise ValueError("a start must light at least one hall")
        for hall_id, n in self.racks.items():
            if n <= 0:
                raise ValueError(f"{hall_id}: racks must be > 0")
        if self.min_ride_through_s < 0:
            raise ValueError("min_ride_through_s must be >= 0")


@dataclass(frozen=True)
class Admission:
    verdict: str
    reasons: Tuple[str, ...]
    steps_mw: Dict[str, float] = field(default_factory=dict)
    stagger_order: Tuple[str, ...] = ()

    @property
    def admitted(self) -> bool:
        return self.verdict == ADMIT

    def explain(self) -> str:
        head = {
            ADMIT: f"ADMIT — {sum(self.steps_mw.values()):.2f} MW step",
            STAGGER: "STAGGER — the load fits, the transition does not",
            DENY: "DENY",
        }[self.verdict]
        body = "\n".join(f"  {r}" for r in self.reasons)
        if self.verdict == STAGGER:
            body += "\n  order: " + " then ".join(self.stagger_order)
        return head + ("\n" + body if body else "")


def admit(start: Start, halls: Mapping[str, Hall],
          feeders: Mapping[str, Feeder],
          running_mw: Mapping[str, float] = None) -> Admission:
    """Decide whether `start` may light now, later in pieces, or not at all.

    ``running_mw`` optionally gives load already on each feeder from halls not
    in `halls` (other tenants, other rooms). Omitted, the feeder carries only
    what the named halls are running.
    """
    reasons = []
    steps = {}

    for hall_id in start.racks:
        if hall_id not in halls:
            raise ValueError(f"start names unknown hall {hall_id!r}")
    for hall in halls.values():
        if hall.feeder_id not in feeders:
            raise ValueError(
                f"hall {hall.hall_id!r} sits on unknown feeder "
                f"{hall.feeder_id!r}")

    # 1. ride-through: a property of the destination, not of the sequence
    for hall_id, racks in sorted(start.racks.items()):
        hall = halls[hall_id]
        held = hall.ride_through_s
        if held < start.min_ride_through_s:
            reasons.append(
                f"{hall_id}: {hall.rung.name} at {hall.kw_per_rack:.0f} "
                f"kW/rack holds {held:.0f} s of cooling loss, the job needs "
                f"{start.min_ride_through_s:.0f} s")

    # 2. hall headroom: sequencing does not create megawatts
    for hall_id, racks in sorted(start.racks.items()):
        hall = halls[hall_id]
        step = hall.facility_mw(racks)
        steps[hall_id] = step
        if step > hall.headroom_mw + 1e-9:
            reasons.append(
                f"{hall_id}: start draws {step:.2f} MW, hall has "
                f"{hall.headroom_mw:.2f} MW of feed left")

    if reasons:
        return Admission(DENY, tuple(reasons), steps)

    # 3. the feeder: a ceiling and a step, checked separately
    by_feeder: Dict[str, list] = {}
    for hall_id in start.racks:
        by_feeder.setdefault(halls[hall_id].feeder_id, []).append(hall_id)

    stagger_reasons, stagger_halls = [], []
    for feeder_id, hall_ids in sorted(by_feeder.items()):
        feeder = feeders[feeder_id]
        carried = sum(h.running_mw for h in halls.values()
                      if h.feeder_id == feeder_id)
        if running_mw:
            carried += running_mw.get(feeder_id, 0.0)
        step = sum(steps[h] for h in hall_ids)

        if carried + step > feeder.limit_mw + 1e-9:
            reasons.append(
                f"{feeder_id}: carries {carried:.2f} MW, start adds "
                f"{step:.2f} MW, ceiling is {feeder.limit_mw:.2f} MW")
            continue

        if step > feeder.max_step_mw + 1e-9:
            biggest = max(steps[h] for h in hall_ids)
            if biggest > feeder.max_step_mw + 1e-9:
                reasons.append(
                    f"{feeder_id}: {max(hall_ids, key=lambda h: steps[h])} "
                    f"alone steps {biggest:.2f} MW onto a feeder that takes "
                    f"{feeder.max_step_mw:.2f} MW at once — no order fixes it")
                continue
            stagger_reasons.append(
                f"{feeder_id}: {len(hall_ids)} halls stepping "
                f"{step:.2f} MW at once onto a feeder that takes "
                f"{feeder.max_step_mw:.2f} MW")
            stagger_halls.extend(hall_ids)

    if reasons:
        return Admission(DENY, tuple(reasons), steps)
    if stagger_reasons:
        # Descending step, then hall id. Deterministic, and not a claim that
        # this is the best order — only that the same input gives the same one.
        order = tuple(sorted(stagger_halls,
                             key=lambda h: (-steps[h], h)))
        return Admission(STAGGER, tuple(stagger_reasons), steps, order)
    return Admission(ADMIT, (), steps)


def thinnest_rung(rungs) -> Rung:
    """The rung holding the fewest seconds when run at its own ceiling.

    Not the top of the ladder and not the bottom. An air room's mass buys
    minutes and an immersion tank's fluid buys them back; the middle, where AI
    density actually lands, is where the buffer is thin.
    """
    return min(rungs, key=lambda r: ride_through_s(r, r.max_kw_per_rack))
