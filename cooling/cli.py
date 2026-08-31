"""pue-ladder: the cooling ladder as a command, CI-gateable.

  pue-ladder ladder                     the rungs, priced
  pue-ladder gate --density 120         exit 1 if no rung fits (CI gate)
  pue-ladder capacity --feed-mw 10 --pue-from 1.5 --pue-to 1.2
  pue-ladder fleet                      the two-fleets plateau demo
  pue-ladder validate                   model vs public data points
"""

import argparse
import sys

from . import capacity, ladder
from .fleet import simulate
from .validation import validate


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
    print("\nSurvey average stays in the high band while the energy-"
          "weighted fleet improves: PUE progress ships in new builds "
          "[2][3][7].")


def _cmd_validate(args):
    ps, ok = validate()
    print(f"{'point':<32}{'kind':<12}{'ref':<10}{'expected':>9}"
          f"{'actual':>9}{'tol':>7}  verdict")
    for p in ps:
        print(f"{p.name:<32}{p.kind:<12}{p.ref:<10}{p.expected:>9.3f}"
              f"{p.actual:>9.3f}{p.tolerance:>7.3f}  "
              f"{'PASS' if p.ok else 'FAIL'}")
    print(f"\n{'all points reproduced' if ok else 'VALIDATION FAILING'} "
          f"— calibrated points prove consistency, emergent points carry "
          f"the findings (see docs/study.md)")
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

    sub.add_parser("validate")

    args = ap.parse_args(argv)
    fn = {"ladder": _cmd_ladder, "gate": _cmd_gate,
          "capacity": _cmd_capacity, "fleet": _cmd_fleet,
          "validate": _cmd_validate}[args.cmd]
    try:
        return fn(args) or 0
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
