import argparse
import importlib
import csv
import json
import os
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from analyze import analyze_raw, select_violations
from labels import DUPLICATES, load_ground_truth, mapping_table


def list_videos(limit=None):
    vids = [p for p in config.VIDEOS_DIR.glob("*.mov") if config.video_key(p.name) not in DUPLICATES]
    vids.sort(key=lambda p: config.video_number(p.name))
    return vids[:limit] if limit else vids


def run_dir(name):
    return config.RUNS_DIR / name


def cache_path(name, video, k):
    return run_dir(name) / config.video_key(video.name) / f"r{k}.json"


def run_inference(name, videos, repeats, temperature, concurrency):
    jobs = [(v, k) for k in range(repeats) for v in videos if not cache_path(name, v, k).exists()]
    total = len(jobs)
    if not total:
        print("all results cached")
        return
    print(f"running {total} calls (concurrency={concurrency}) ...", flush=True)
    lock = threading.Lock()
    done = [0, 0]
    t0 = time.time()

    def work(video, k):
        raw = analyze_raw(video, temperature=temperature, repeat=k)
        if raw["error"]:
            return video, k, raw, False
        p = cache_path(name, video, k)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)
        return video, k, raw, True

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [ex.submit(work, v, k) for v, k in jobs]
        for fut in as_completed(futs):
            try:
                video, k, raw, ok = fut.result()
            except Exception as e:
                with lock:
                    done[1] += 1
                print(f"  job crashed: {type(e).__name__}: {e}", flush=True)
                continue
            with lock:
                done[0] += 1
                if not ok:
                    done[1] += 1
                n = done[0]
            nv = len((raw.get("parsed") or {}).get("violations") or []) if raw.get("parsed") else "-"
            status = "ERR " + str(raw["error"])[:120] if not ok else ("ok" if raw["parsed"] is not None else "BADJSON")
            print(f"  [{n}/{total}] {raw['key']} r{k} {raw['latency_sec']:.1f}s frames={raw['n_frames']} "
                  f"viol={nv} {status}  (elapsed {time.time() - t0:.0f}s)", flush=True)
    if done[1]:
        print(f"{done[1]} calls failed (not cached; rerun to retry)")


def load_results(name, videos, repeats):
    res = {}
    for v in videos:
        key = config.video_key(v.name)
        res[key] = {}
        for k in range(repeats):
            p = cache_path(name, v, k)
            if p.exists():
                res[key][k] = json.loads(p.read_text(encoding="utf-8"))
    return res


def _hit(kept, seconds, tol):
    return any(abs(v["timecode_sec"] - s) <= tol for v in kept for s in seconds)


def _rates(rows):
    """rows: list of dicts with gt, pred, kept, seconds, type_ids."""
    tp = sum(1 for r in rows if r["gt"] and r["pred"])
    fp = sum(1 for r in rows if not r["gt"] and r["pred"])
    fn = sum(1 for r in rows if r["gt"] and not r["pred"])
    tn = sum(1 for r in rows if not r["gt"] and not r["pred"])
    n = len(rows)
    pos = [r for r in rows if r["gt"]]
    tps = [r for r in pos if r["pred"]]
    typed = [r for r in pos if r["type_ids"]]
    out = {
        "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": round((tp + tn) / n, 4) if n else None,
        "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
    }
    out["f1"] = (round(2 * out["precision"] * out["recall"] / (out["precision"] + out["recall"]), 4)
                 if out["precision"] and out["recall"] else 0.0)
    for tol in (2, 3):
        hits = sum(1 for r in tps if _hit(r["kept"], r["seconds"], tol))
        out[f"tc_hit{tol}_of_pos"] = round(hits / len(pos), 4) if pos else None
        out[f"tc_hit{tol}_of_tp"] = round(hits / len(tps), 4) if tps else None
    th = sum(1 for r in typed if r["pred"] and any(v["type_id"] in r["type_ids"] for v in r["kept"]))
    out["type_hit_of_pos"] = round(th / len(typed), 4) if typed else None
    tth = [r for r in typed if r["pred"]]
    out["type_hit_of_tp"] = round(th / len(tth), 4) if tth else None
    return out


def score(results, gt, repeats, offset, mode, extra):
    per_repeat = []
    for k in range(repeats):
        rows = []
        for key, reps in results.items():
            if k not in reps or key not in gt:
                continue
            kept, _ = select_violations(reps[k].get("parsed"), offset=offset, mode=mode, extra=extra)
            g = gt[key]
            rows.append({"gt": g["violation"], "pred": bool(kept), "kept": kept, "seconds": g["seconds"],
                         "type_ids": g["type_ids"]})
        if rows:
            per_repeat.append(dict(_rates(rows), repeat=k))

    per_video = []
    maj_rows = []
    for key, reps in results.items():
        if not reps or key not in gt:
            continue
        g = gt[key]
        votes = 0
        kept_all = []
        lat = []
        for k, raw in sorted(reps.items()):
            kept, _ = select_violations(raw.get("parsed"), offset=offset, mode=mode, extra=extra)
            votes += bool(kept)
            kept_all.append(kept)
            lat.append(raw.get("latency_sec") or 0.0)
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
        per_video.append({
            "video": key, "gt": "violation" if g["violation"] else "no_violation",
            "gt_seconds": "/".join(str(int(s)) for s in g["seconds"]),
            "gt_types": ",".join(g["type_ids"]),
            "votes_violation": f"{votes}/{n}",
            "majority": "violation" if majority else "no_violation",
            "correct": int(majority == g["violation"]),
            "winning_type": win_type or "",
            "median_tc": "" if med_tc is None else round(med_tc, 1),
            "types_seen": " ".join(f"{t}:{c}" for t, c in type_counts.most_common()),
            "timecodes": " ".join(f"{v['type_id']}@{v['timecode_sec']:.0f}" for kept in kept_all for v in kept),
            "parse_failures": sum(1 for r in reps.values() if r.get("parsed") is None),
            "latency_mean": round(statistics.mean(lat), 1) if lat else "",
            "latency_max": round(max(lat), 1) if lat else "",
        })
    majority_metrics = _rates(maj_rows) if maj_rows else {}
    return per_repeat, majority_metrics, per_video


def latency_stats(results):
    lat = sorted(r.get("latency_sec") or 0.0 for reps in results.values() for r in reps.values())
    n_total = len(lat)
    fails = sum(1 for reps in results.values() for r in reps.values() if r.get("parsed") is None)
    if not lat:
        return {"n_calls": 0}
    p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))]
    return {"n_calls": n_total, "latency_mean": round(statistics.mean(lat), 2), "latency_p95": round(p95, 2),
            "latency_max": round(lat[-1], 2), "parse_fail_rate": round(fails / n_total, 4)}


def _mean_metric(per_repeat, key):
    vals = [r[key] for r in per_repeat if r.get(key) is not None]
    return round(statistics.mean(vals), 4) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--offset", type=float, default=None, help="threshold offset (default THRESHOLD_OFFSET env)")
    ap.add_argument("--mode", choices=["rules", "all"], default=None, help="which rule ids count in the verdict")
    ap.add_argument("--extra-types", default=None, help="comma-separated extra rule ids counted in the verdict")
    ap.add_argument("--score-only", action="store_true")
    args = ap.parse_args()

    offset = config.THRESHOLD_OFFSET if args.offset is None else args.offset
    mode = args.mode or config.VERDICT_MODE
    extra = (config.EXTRA_VERDICT_TYPES if args.extra_types is None
             else [t.strip() for t in args.extra_types.split(",") if t.strip()])

    videos = list_videos(args.limit)
    gt = load_ground_truth()
    print("Type mapping (teammate 'Тип нарушения' -> accepted rule ids):")
    print(mapping_table(gt))
    print()

    rd = run_dir(args.name)
    rd.mkdir(parents=True, exist_ok=True)
    cfg = {"name": args.name, "base_url": config.VLM_BASE_URL, "model": config.VLM_MODEL,
           "temperature": args.temperature if args.temperature is not None else config.TEMPERATURE,
           "fps": config.FPS, "fps_short": config.FPS_SHORT, "fps_long": config.FPS_LONG,
           "max_frames": config.MAX_FRAMES, "max_side": config.MAX_SIDE,
           "disable_thinking": config.DISABLE_THINKING, "max_tokens": config.MAX_TOKENS,
           "prompt_module": config.PROMPT_MODULE, "consistency_checks": config.CONSISTENCY_CHECKS}
    if not args.score_only:
        (rd / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        # exact system prompt used for this run, for later comparison across experiments
        prompt_mod = importlib.import_module(config.PROMPT_MODULE)
        (rd / "system_prompt.txt").write_text(prompt_mod.build_system_prompt(), encoding="utf-8")

    if not args.score_only:
        run_inference(args.name, videos, args.repeats, args.temperature, args.concurrency)

    results = load_results(args.name, videos, args.repeats)
    per_repeat, maj, per_video = score(results, gt, args.repeats, offset, mode, extra)
    lat = latency_stats(results)

    sweep = []
    for m in ("rules", "all"):
        for off in (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2):
            pr, mj, _ = score(results, gt, args.repeats, off, m, extra)
            sweep.append({"mode": m, "offset": off, "majority": mj,
                          "mean_repeat_accuracy": _mean_metric(pr, "accuracy")})

    summary = {
        "config": cfg, "scoring": {"offset": offset, "mode": mode, "extra_types": extra},
        "videos": len(videos), "repeats": args.repeats, "latency": lat,
        "majority": maj, "per_repeat": per_repeat,
        "per_repeat_mean": {k: _mean_metric(per_repeat, k) for k in
                            ("accuracy", "recall", "precision", "f1", "tc_hit2_of_pos", "tc_hit3_of_pos",
                             "type_hit_of_pos")},
        "sweep": sweep,
    }
    (rd / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    if per_video:
        with open(rd / "per_video.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(per_video[0].keys()))
            w.writeheader()
            w.writerows(per_video)

    print("Per video:")
    for r in per_video:
        print(f"  {r['video']:6s} gt={r['gt'][:2]} votes={r['votes_violation']:6s} maj={r['majority'][:2]} "
              f"{'OK ' if r['correct'] else 'BAD'} type={r['winning_type'] or '-'}@{r['median_tc']} "
              f"gt={r['gt_types'] or '-'}@{r['gt_seconds'] or '-'}")
    print()
    print("Sweep (majority accuracy / recall / precision / tc±3 / type):")
    for s in sweep:
        mj = s["majority"]
        print(f"  mode={s['mode']:5s} offset={s['offset']:+.1f}  acc={mj.get('accuracy')} rec={mj.get('recall')} "
              f"prec={mj.get('precision')} tc3={mj.get('tc_hit3_of_pos')} type={mj.get('type_hit_of_pos')} "
              f"repeat_acc={s['mean_repeat_accuracy']}")
    print()
    pm = summary["per_repeat_mean"]
    print(f"SUMMARY {args.name}: n={len(per_video)} rep={args.repeats} mode={mode} off={offset:+.2f} | "
          f"MAJ acc={maj.get('accuracy')} rec={maj.get('recall')} prec={maj.get('precision')} "
          f"TP/FP/FN/TN={maj.get('tp')}/{maj.get('fp')}/{maj.get('fn')}/{maj.get('tn')} "
          f"tc2={maj.get('tc_hit2_of_pos')} tc3={maj.get('tc_hit3_of_pos')} type={maj.get('type_hit_of_pos')} | "
          f"REP acc={pm['accuracy']} rec={pm['recall']} prec={pm['precision']} | "
          f"lat mean={lat.get('latency_mean')} p95={lat.get('latency_p95')} max={lat.get('latency_max')} "
          f"badjson={lat.get('parse_fail_rate')}")
    print(f"wrote {rd / 'summary.json'} and {rd / 'per_video.csv'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
