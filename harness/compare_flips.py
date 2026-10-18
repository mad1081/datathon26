"""Compare per-video majority verdicts of a run against a baseline run (reads per_video.csv)."""
import csv
import json
import sys
from pathlib import Path

RUNS = Path(__file__).parent / "runs"


def load(name):
    with open(RUNS / name / "per_video.csv", encoding="utf-8-sig") as f:
        return {r["video"]: r for r in csv.DictReader(f)}


def quote(name, video, want_violation):
    """First repeat whose verdict matches the run's majority: its violations + short timeline."""
    for p in sorted((RUNS / name / video).glob("r*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        par = d.get("parsed") or {}
        vi = par.get("violations") or []
        if bool(vi) == want_violation:
            tl = "; ".join(f"{e.get('t')}: {e.get('event')}" for e in (par.get("timeline") or [])[:12])
            v = "; ".join(f"{x.get('type_id')}@{x.get('timecode_sec')}: {x.get('observed')}" for x in vi)
            ch = par.get("checks")
            return f"[{p.stem}] viol: {v or '-'}\n      timeline: {tl}" + (f"\n      checks: {ch}" if ch else "")
    return "-"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base, run = sys.argv[1], sys.argv[2]
    b, r = load(base), load(run)
    for v in r:
        bb, rr = b[v], r[v]
        flip = bb["correct"] != rr["correct"]
        tchg = rr["correct"] == "1" and rr["majority"] == "violation" and bb["winning_type"] != rr["winning_type"]
        if flip or tchg or (len(sys.argv) > 3 and v in sys.argv[3].split(",")):
            tag = ("FIXED" if rr["correct"] == "1" else "BROKE") if flip else "type"
            print(f"{v} {tag}: gt={rr['gt_types'] or 'clean'}@{rr['gt_seconds']} | {base} {bb['votes_violation']} "
                  f"{bb['winning_type']}@{bb['median_tc']} -> {run} {rr['votes_violation']} {rr['winning_type']}@{rr['median_tc']}")
            print("   ", quote(run, v, rr["majority"] == "violation"))
