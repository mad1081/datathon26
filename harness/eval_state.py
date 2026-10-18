"""Post-steps on cached pass-1 answers: door / laptop / safe-key state checks, scored like eval.py."""
import argparse
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import checks
import config
import eval_zoom
import state_checks as sc
from analyze import select_violations
from eval import list_videos, load_results
from frames import video_info
from labels import load_ground_truth

OUT = None


def _r(t):
    return round(t * 2) / 2


def plan(parsed, kept, duration):
    """Return list of (check, times, role) requests for one repeat."""
    last = _r(max(duration - 0.3, 0.0))
    reqs = []
    for v in kept:
        if v["type_id"] == "door_left_open":
            reqs.append(("door", (_r(min(v["timecode_sec"] + 5, last)), last), v))
        elif v["type_id"] == "workstation_unlocked":
            tc = v["timecode_sec"]
            reqs.append(("laptop", (_r(max(tc - 3, 0.0)), _r(min(tc + 1, last)), last), v))
            reqs.append(("laptop2", (_r(max(tc - 3, 0.0)), _r(min(tc + 1, last)), last), v))
            reqs.append(("laptop3", (_r(max(tc - 3, 0.0)), _r(min(tc + 1, last)), last), v))
    exits = [t for t, text in checks._events(parsed or {}) if checks.CASHIER_LEAVES.search(text)]
    if exits:
        reqs.append(("key", (_r(min(exits[0] + 2, last)), last), {"type_id": "safe_key_left", "timecode_sec": exits[0]}))
        reqs.append(("desk", (_r(min(exits[0] + 2, last)), last), {"type_id": "desk", "timecode_sec": exits[0]}))
    only = [c for c in (config.os.getenv("STATE_CHECKS") or "").split(",") if c]
    return [r for r in reqs if not only or r[0] in only]


def req_path(key, check, times):
    return OUT / key / f"{check}_{'_'.join(f'{t:.1f}' for t in times)}.json"


def answer(key, check, times):
    p = req_path(key, check, times)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def decide(check, rec):
    ans = [a for a in rec["answers"] if a]
    if check == "door":
        st = sc.per_frame_majority(ans, "door", 2)
        return st[0] != "closed", st
    if check == "laptop":
        scr = sc.per_frame_majority(ans, "screen", 3)
        b = scr[1] if scr[1] != "not_visible" else scr[2]
        return b == "table_or_program", scr
    if check == "laptop2":
        scr = sc.per_frame_majority(ans, "screen", 3)
        b = scr[1] if scr[1] != "not_visible" else scr[2]
        return b == "bright", scr
    if check == "laptop3":
        scr = sc.per_frame_majority(ans, "screen", 3)
        b = scr[1] if scr[1] != "not_visible" else scr[2]
        return b == "white", scr
    if check == "desk":
        items = sc.items_majority(ans, 1)
        return bool(items), sorted(items)
    if check == "key":
        st = sc.per_frame_majority(ans, "key_in_lock", 2)
        return st[1] == "yes", st
    raise ValueError(check)


def make_kept_after(results_meta):
    def kept_after(name, key, k, parsed, variant, sub_min):
        kept, _ = select_violations(parsed)
        if variant == "base":
            return kept, 0.0, 0
        use = {"door": {"door", "all"}, "laptop": {"laptop", "all"}, "key": {"key", "all"}, "laptop2": {"laptop2"}, "laptop3": {"laptop3", "l3desk"}, "desk": {"desk", "l3desk"}}
        out = list(kept)
        lat, n = 0.0, 0
        for check, times, v in plan(parsed, kept, results_meta[key]):
            if variant not in use[check]:
                continue
            rec = answer(key, check, times)
            if rec is None:
                continue
            lat += max(rec["latencies"] or [0.0])
            n += 1
            ok, _ = decide(check, rec)
            if check == "desk":
                _, items = decide(check, rec)
                add = set()
                if "cash" in items or "bag" in items:
                    add.add("cash_unattended")
                if "seals" in items or "documents" in items:
                    add.add("seals_docs_unattended")
                for t in add:
                    if not any(x["type_id"] == t for x in out):
                        out.append({"type_id": t, "timecode_sec": v["timecode_sec"], "confidence": 0.9, "observed": ",".join(items)})
            elif check == "key":
                if ok and not any(x["type_id"] == "safe_key_left" for x in out):
                    out.append({"type_id": "safe_key_left", "timecode_sec": v["timecode_sec"], "confidence": 0.9,
                                "observed": "ключ в замке сейфа"})
            elif not ok:
                out = [x for x in out if x is not v]
        out.sort(key=lambda x: x["timecode_sec"])
        return out, lat, n
    return kept_after


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="exp-in-state")
    ap.add_argument("--pass1", default="exp-v3b")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--score-only", action="store_true")
    args = ap.parse_args()
    OUT = config.RUNS_DIR / args.name
    OUT.mkdir(parents=True, exist_ok=True)

    videos = {config.video_key(v.name): v for v in list_videos()}
    gt = load_ground_truth()
    results = load_results(args.pass1, list(videos.values()), args.repeats)
    durations = {k: video_info(v)["duration_sec"] for k, v in videos.items()}

    todo = {}
    for key, reps in results.items():
        for k, raw in reps.items():
            kept, _ = select_violations(raw.get("parsed"))
            for check, times, _ in plan(raw.get("parsed"), kept, durations[key]):
                if not req_path(key, check, times).exists():
                    todo[(key, check, times)] = True
    print(f"{len(todo)} state requests x {sc.N_VOTES} votes", flush=True)

    if not args.score_only and todo:
        lock = threading.Lock()
        t0 = time.time()

        def work(item):
            key, check, times = item
            frames = sc.load_frames(videos[key], times)
            answers, lats = [], []
            for _ in range(sc.N_VOTES):  # in production the votes run in parallel
                res = sc.ask(check, frames)
                answers.append(res["parsed"])
                lats.append(res["latency_sec"])
            rec = {"check": check, "times": list(times), "answers": answers, "latencies": lats}
            p = req_path(key, check, times)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            ok, st = decide(check, rec)
            with lock:
                print(f"  {key} {check} {times} -> {st} {'KEEP/ADD' if ok else 'DROP/none'} "
                      f"{max(lats):.1f}s ({time.time() - t0:.0f}s)", flush=True)

        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            for f in [ex.submit(work, it) for it in todo]:
                try:
                    f.result()
                except Exception as e:
                    print(f"  crashed: {type(e).__name__}: {e}", flush=True)

    eval_zoom.kept_after = make_kept_after(durations)
    base_maj, base_pv, _, _, _ = eval_zoom.score(args.name, results, gt, args.repeats, "base", None)
    for var in ["base", "door", "laptop", "laptop2", "laptop3", "key", "desk", "l3desk"]:
        maj, pv, rep_acc, lats, calls = eval_zoom.score(args.name, results, gt, args.repeats, var, None)
        print(f"{var:7s} acc={maj['accuracy']} TP/FP/FN/TN={maj['tp']}/{maj['fp']}/{maj['fn']}/{maj['tn']} "
              f"rec={maj['recall']} prec={maj['precision']} tc2={maj['tc_hit2_of_tp']} tc3={maj['tc_hit3_of_tp']} "
              f"type={maj['type_hit_of_tp']} rep_acc={rep_acc} | extra lat/video={statistics.mean(lats):.1f}s "
              f"calls/video={statistics.mean(calls):.2f}")
        if var != "base":
            for b, z in zip(base_pv, pv):
                if b["votes"] != z["votes"] or b["type"] != z["type"]:
                    print(f"    {z['video']:5s} gt={'V' if z['gt'] else '-'} {z['gt_types']}  base {b['votes']} "
                          f"{b['type']}@{b['tc']} -> {z['votes']} {z['type']}@{z['tc']} {'OK' if z['correct'] else 'BAD'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
