"""pue-ladder: the cooling ladder as a command, CI-gateable.

  pue-ladder ladder                     the rungs, priced
  pue-ladder gate --density 120         exit 1 if no rung fits (CI gate)
  pue-ladder capacity --feed-mw 10 --pue-from 1.5 --pue-to 1.2
  pue-ladder fleet                      the two-fleets plateau demo
  pue-ladder admit --density 132 --need-ride-through 30
                                        which rungs may take the start
  pue-ladder validate                   model vs public data points
"""

import argparse
import sys

from . import admission, capacity, ladder
from .fleet import simulate
from .validation import DECLINED, SEEDS as VALIDATION_SEEDS, validate


def _cmd_ladder(args):
    print(f"{'rung':<15}{'max kW/rack':>12}{'PUE (cold)':>12}"
          f"{'PUE (hot-humid)':>17}{'heat->liquid':>14}"
          f"{'ride-through @max':>19}{'retrofit $/kW':>15}")
    for r in ladder.RUNGS:
        rt = ladder.ride_through_s(r, r.max_kw_per_rack)
        print(f"{r.name:<15}{r.max_kw_per_rack:>12.0f}"
              f"{ladder.pue(r, 'cold'):>12.3f}"
              f"{ladder.pue(r, 'hot-humid'):>17.3f}"
              f"{r.heat_capture:>13.0%}"
              f"{rt:>17.0f} s"
              f"{r.retrofit_usd_per_kw:>15,.0f}")
    print("\nPUE = floor + (1 - free_cooling) * penalty; evaporative "
          "heat rejection. See REFERENCES.md for anchors.")


def _cmd_gate(args):
    ok = ladder.feasible_rungs(args.density)
    if args.rung:
        r = ladder.rung(args.rung)
        if r in ok:
            print(f"OK: {r.name} cools {args.density} kW/rack "
                  f"(ceiling {r.max_kw_per_rack:.0f})")
            return 0
        print(f"BLOCKED: {r.name} tops out at {r.max_kw_per_rack:.0f} "
              f"kW/rack; {args.density} kW needs "
              f"{', '.join(x.name for x in ok) or 'nothing on the ladder'}")
        return 1
    if not ok:
        print(f"BLOCKED: no rung on the ladder cools {args.density} kW/rack")
        return 1
    print(f"{args.density} kW/rack is coolable by: "
          f"{', '.join(r.name for r in ok)}")
    return 0


def _cmd_capacity(args):
    freed = capacity.freed_mw(args.feed_mw, args.pue_from, args.pue_to)
    gpus = capacity.h100_equivalents(max(freed, 0.0))
    print(f"feed {args.feed_mw:.1f} MW: PUE {args.pue_from} -> "
          f"{args.pue_to} frees {freed:+.2f} MW of IT "
          f"(~{gpus:,} H100s' worth [11])")
    print(f"the alternative — new grid capacity — waits a median "
          f"~{capacity.QUEUE_YEARS:.0f} years in the queue [8]")


def _cmd_fleet(args):
    sim = simulate(seed=args.seed)
    print(f"{'year':<6}{'survey avg':>12}{'energy-weighted':>17}")
    for year, (survey, weighted) in sim.items():
        print(f"{year:<6}{survey:>12.3f}{weighted:>17.3f}")
    print(f"\nSurvey average stays in the high band while the energy-"
          f"weighted fleet improves: PUE progress ships in new builds "
          f"[2][3][7].")
    print(f"This is ONE draw (seed {args.seed}). `pue-ladder validate` "
          f"reports means over {len(VALIDATION_SEEDS)} seeds, so its "
          f"numbers will not match this table row for row — the spread "
          f"across seeds is real and a single draw is not the finding.")


def _cmd_admit(args):
    """Ride-through and headroom asked at the moment a job starts."""
    fits = ladder.feasible_rungs(args.density)
    if not fits:
        print(f"no rung on the ladder cools {args.density:.0f} kW/rack")
        return 1
    feeder = admission.Feeder("F1", args.feeder_limit_mw, args.feeder_step_mw)
    hall_ids = tuple(f"hall-{chr(ord('a') + i)}" for i in range(args.halls))

    print(f"{args.racks} rack(s) of {args.density:.0f} kW in {args.halls} "
          f"hall(s) on one feeder, job needs "
          f"{args.need_ride_through:.0f} s of ride-through\n")
    print(f"{'rung':<16}{'ride-through':>14}{'step':>12}  verdict")
    admitted = False
    for r in fits:
        halls = {h: admission.Hall(hall_id=h, feeder_id="F1", rung=r,
                                   kw_per_rack=args.density,
                                   racks_running=0, feed_mw=args.feed_mw,
                                   climate=args.climate)
                 for h in hall_ids}
        start = admission.Start(
            "job", {h: args.racks for h in hall_ids},
            min_ride_through_s=args.need_ride_through)
        out = admission.admit(start, halls, {"F1": feeder})
        held = ladder.ride_through_s(r, args.density)
        step = sum(out.steps_mw.values())
        print(f"{r.name:<16}{held:>12.0f} s{step:>9.2f} MW  {out.verdict}")
        for reason in out.reasons:
            print(f"    {reason}")
        if out.verdict == admission.STAGGER:
            print("    order: " + " then ".join(out.stagger_order))
        admitted = admitted or out.verdict == admission.ADMIT

    print("\nRide-through and hall headroom are properties of the "
          "destination; only the feeder step can be sequenced away.\n"
          "Exit 1 means no rung admits the start as submitted — a STAGGER "
          "counts as not-as-submitted, because the answer is 'later, in "
          "pieces' rather than 'yes'.")
    return 0 if admitted else 1


def _cmd_validate(args):
    ps, ok = validate()
    width = max(len(p.name) for p in ps) + 2
    print(f"{'point':<{width}}{'kind':<12}{'ref':<10}{'expected':>9}"
          f"{'actual':>9}{'tol':>7}  verdict")
    for p in ps:
        print(f"{p.name:<{width}}{p.kind:<12}{p.ref:<10}{p.expected:>9.3f}"
              f"{p.actual:>9.3f}{p.tolerance:>7.3f}  "
              f"{'PASS' if p.ok else 'FAIL'}")
    print("\nNOT CHECKED HERE — a registry that prints only its passes is "
          "a highlight reel:")
    for what, why in DECLINED:
        print(f"  - {what}: {why}")
    print(f"\n{'all points reproduced' if ok else 'VALIDATION FAILING'} "
          f"— calibrated points prove consistency, emergent points carry "
          f"the findings, sanity points pin the ladder's own structure and "
          f"cite nothing (see docs/study.md). tests/test_validation.py "
          f"breaks the model on purpose and requires these points to fail.")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pue-ladder", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ladder")

    g = sub.add_parser("gate")
    g.add_argument("--density", type=float, required=True,
                   help="target rack power, kW")
    g.add_argument("--rung", choices=[r.name for r in ladder.RUNGS])

    c = sub.add_parser("capacity")
    c.add_argument("--feed-mw", type=float, default=10.0)
    c.add_argument("--pue-from", type=float, required=True)
    c.add_argument("--pue-to", type=float, required=True)

    f = sub.add_parser("fleet")
    f.add_argument("--seed", type=int, default=7)

    a = sub.add_parser("admit")
    a.add_argument("--density", type=float, required=True,
                   help="rack power of the start, kW")
    a.add_argument("--need-ride-through", type=float, default=0.0,
                   help="seconds of cooling loss the job must survive")
    a.add_argument("--racks", type=int, default=10)
    a.add_argument("--halls", type=int, default=1)
    a.add_argument("--feed-mw", type=float, default=8.0)
    a.add_argument("--feeder-limit-mw", type=float, default=40.0)
    a.add_argument("--feeder-step-mw", type=float, default=1.5)
    a.add_argument("--climate", choices=sorted(ladder.CLIMATES),
                   default="temperate")

    sub.add_parser("validate")

    args = ap.parse_args(argv)
    fn = {"ladder": _cmd_ladder, "gate": _cmd_gate,
          "capacity": _cmd_capacity, "fleet": _cmd_fleet,
          "admit": _cmd_admit, "validate": _cmd_validate}[args.cmd]
    try:
        return fn(args) or 0
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
