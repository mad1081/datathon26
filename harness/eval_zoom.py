"""Two-pass eval: reuse cached whole-video results (pass 1), verify candidates on zoomed windows (pass 2)."""
import argparse
import json
import os
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import config
import zoom
from analyze import select_violations, verdict_types
from eval import _rates, list_videos, load_results
from labels import load_ground_truth


SKIP_OMISSION = config.env_bool("ZOOM_SKIP_OMISSION", False)


def candidates(parsed, sub_min):
    """Verdict candidates (kept) plus optional sub-threshold candidates of verdict types."""
    kept, obs = select_violations(parsed)
    allowed = verdict_types()
    out = [dict(v, source="kept") for v in kept]
    if sub_min is not None:
        for o in obs:
            if o.get("dropped") or o["type_id"] not in allowed or o["confidence"] < sub_min:
                continue
            if any(c["type_id"] == o["type_id"] and abs(c["timecode_sec"] - o["timecode_sec"]) <= 3 for c in out):
                continue
            out.append(dict(o, source="sub"))
    return out


def cpath(name, key, k, c):
    return config.RUNS_DIR / name / key / f"r{k}_{c['type_id']}_{c['timecode_sec']:.1f}.json"


def run_video(name, video, reps, repeats, sub_min, log):
    key = config.video_key(video.name)
    jobs = []
    for k in range(repeats):
        if k not in reps:
            continue
        for c in candidates(reps[k].get("parsed"), sub_min):
            if SKIP_OMISSION and c["type_id"] in OMISSION:
                continue
            if not cpath(name, key, k, c).exists():
                jobs.append((k, c))
    if not jobs:
        return
    wins, info = zoom.load_window_frames(video, sorted({c["timecode_sec"] for _, c in jobs}))
    for k, c in jobs:
        res = zoom.verify(c, wins[c["timecode_sec"]], reps[k].get("parsed"))
        if res["error"]:
            log(f"  {key} r{k} {c['type_id']}@{c['timecode_sec']} ERR {res['error'][:120]}")
            continue
        rec = dict(res, cand=c)
        p = cpath(name, key, k, c)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        tok = (res["usage"] or {}).get("prompt_tokens")
        log(f"  {key} r{k} {c['source']} {c['type_id']}@{c['timecode_sec']:.1f} -> "
            f"{'YES' if res['confirmed'] else 'no '} tc={res['timecode_sec']} {res['latency_sec']:.1f}s "
            f"frames={res['n_frames']} tok={tok}")


# absence of a required step cannot be seen in a 6 s window; these bypass verification in "zoom_state"
OMISSION = {"no_client_id_check", "collector_bag_no_check", "cash_accepted_without_count",
            "counting_without_client", "issue_without_count", "suspicious_note_returned", "counting_without_controller"}


def kept_after(name, key, k, parsed, variant, sub_min):
    """variant: base | zoom (kept verified, refined tc) | zoom_keep_tc | zoom_sub (kept+sub verified)."""
    kept, _ = select_violations(parsed)
    if variant == "base":
        return kept, 0.0, 0
    cands = candidates(parsed, sub_min if variant == "zoom_sub" else None)
    out, lat, n = [], 0.0, 0
    for c in cands:
        if variant == "zoom_state" and c["type_id"] in OMISSION:
            if c["source"] == "kept":
                out.append(c)
            continue
        p = cpath(name, key, k, c)
        if not p.exists():  # verification failed: keep pass-1 decision
            if c["source"] == "kept":
                out.append(c)
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        lat += r["latency_sec"]
        n += 1
        if not r["confirmed"]:
            continue
        tc = c["timecode_sec"]
        if variant == "zoom" and r["timecode_sec"] is not None and abs(r["timecode_sec"] - tc) <= zoom.ZOOM_HALF + 1:
            tc = r["timecode_sec"]
        out.append(dict(c, timecode_sec=tc))
    out.sort(key=lambda x: x["timecode_sec"])
    return out, lat, n


def score(name, results, gt, repeats, variant, sub_min):
    maj_rows, per_video, rep_rows, lats, calls = [], [], {k: [] for k in range(repeats)}, [], []
    for key, reps in results.items():
        if not reps or key not in gt:
            continue
        g = gt[key]
        kept_all, votes = [], 0
        for k, raw in sorted(reps.items()):
            kept, lat, n = kept_after(name, key, k, raw.get("parsed"), variant, sub_min)
            kept_all.append(kept)
            votes += bool(kept)
            lats.append(lat)
            calls.append(n)
            rep_rows[k].append({"gt": g["violation"], "pred": bool(kept), "kept": kept, "seconds": g["seconds"],
                                "type_ids": g["type_ids"]})
        n = len(reps)
        majority = votes * 2 > n
        type_counts = Counter(v["type_id"] for kept in kept_all for v in {x["type_id"]: x for x in kept}.values())
        win_type = type_counts.most_common(1)[0][0] if type_counts else None
        win_tcs = [min(v["timecode_sec"] for v in kept if v["type_id"] == win_type)
                   for kept in kept_all if any(v["type_id"] == win_type for v in kept)]
        med_tc = statistics.median(win_tcs) if win_tcs else None
        maj_kept = [{"type_id": win_type, "timecode_sec": med_tc}] if majority and win_type else []
        maj_rows.append({"gt": g["violation"], "pred": majority, "kept": maj_kept, "seconds": g["seconds"],
                         "type_ids": g["type_ids"]})
        per_video.append({"video": key, "gt": g["violation"], "votes": f"{votes}/{n}", "majority": majority,
                          "correct": majority == g["violation"], "type": win_type,
                          "tc": None if med_tc is None else round(med_tc, 1),
                          "gt_sec": g["seconds"], "gt_types": g["type_ids"]})
    per_rep = [_rates(rows) for rows in rep_rows.values() if rows]
    rep_acc = round(statistics.mean(r["accuracy"] for r in per_rep), 4) if per_rep else None
    return _rates(maj_rows), per_video, rep_acc, lats, calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="output run name for zoom verifications")
    ap.add_argument("--pass1", default="qwen36-35b-a3b", help="cached pass-1 run name")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--sub-min", type=float, default=None, help="also verify sub-threshold candidates >= this conf")
    ap.add_argument("--score-only", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    videos = list_videos(args.limit)
    gt = load_ground_truth()
    results = load_results(args.pass1, videos, args.repeats)
    rd = config.RUNS_DIR / args.name
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "config.json").write_text(json.dumps({
        "pass1": args.pass1, "zoom_fps": zoom.ZOOM_FPS, "zoom_half": zoom.ZOOM_HALF,
        "zoom_max_side": zoom.ZOOM_MAX_SIDE, "zoom_temperature": zoom.ZOOM_TEMPERATURE,
        "sub_min": args.sub_min, "model": config.VLM_MODEL}, indent=1), encoding="utf-8")

    if not args.score_only:
        lock = threading.Lock()

        def log(msg):
            with lock:
                print(msg, flush=True)

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futs = [ex.submit(run_video, args.name, v, results[config.video_key(v.name)], args.repeats,
                              args.sub_min, log) for v in videos]
            for f in futs:
                try:
                    f.result()
                except Exception as e:
                    print(f"  video crashed: {type(e).__name__}: {e}", flush=True)
        print(f"pass 2 done in {time.time() - t0:.0f}s")

    base_maj, base_pv, _, _, _ = score(args.name, results, gt, args.repeats, "base", args.sub_min)
    variants = ["base", "zoom", "zoom_keep_tc", "zoom_state"] + (["zoom_sub"] if args.sub_min is not None else [])
    summary = {}
    for var in variants:
        maj, pv, rep_acc, lats, calls = score(args.name, results, gt, args.repeats, var, args.sub_min)
        p1 = [r.get("latency_sec") or 0.0 for reps in results.values() for r in reps.values()]
        summary[var] = {"majority": maj, "rep_acc": rep_acc, "pass2_lat_mean": round(statistics.mean(lats), 2),
                        "pass2_calls_mean": round(statistics.mean(calls), 2), "pass1_lat_mean": round(statistics.mean(p1), 2)}
        print(f"{var:13s} acc={maj['accuracy']} TP/FP/FN/TN={maj['tp']}/{maj['fp']}/{maj['fn']}/{maj['tn']} "
              f"rec={maj['recall']} prec={maj['precision']} tc2={maj['tc_hit2_of_tp']} tc3={maj['tc_hit3_of_tp']} "
              f"type={maj['type_hit_of_tp']} rep_acc={rep_acc} | p1 lat={statistics.mean(p1):.1f}s "
              f"p2 extra/video={statistics.mean(lats):.1f}s calls/video={statistics.mean(calls):.2f}")
        if var != "base":
            for b, z in zip(base_pv, pv):
                if b["majority"] != z["majority"] or b["tc"] != z["tc"] or b["type"] != z["type"]:
                    print(f"    {z['video']:5s} gt={'V' if z['gt'] else '-'} {z['gt_types']}@{z['gt_sec']}  "
                          f"base {b['votes']} {b['type']}@{b['tc']} -> {z['votes']} {z['type']}@{z['tc']} "
                          f"{'OK' if z['correct'] else 'BAD'}")
    per_video_lat = {}
    for key, reps in results.items():
        ls = [kept_after(args.name, key, k, raw.get("parsed"), variants[-1], args.sub_min)[1] for k, raw in reps.items()]
        per_video_lat[key] = round(statistics.mean(ls), 1) if ls else 0.0
    summary["pass2_latency_by_video"] = per_video_lat
    print("pass-2 extra latency by video (sequential sum, mean over repeats):", per_video_lat)
    (rd / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
