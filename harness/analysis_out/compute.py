"""Offline analysis over cached runs (no model calls). Run from harness/: python analysis_out/compute.py"""
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HARNESS))

import config  # noqa: E402
from analyze import select_violations  # noqa: E402
from labels import load_ground_truth  # noqa: E402

OUT = HERE
RUNS = HARNESS / "runs"
MODELS = ["qwen35-9b", "qwen36-27b", "qwen36-35b-a3b", "qwen38-27b", "qwen3vl-30b-a3b", "qwen3vl-32b", "qwen3vl-8b"]
BASE_RUNS = [(m, "v1", m) for m in MODELS] + [(m, "v2", m + "-p2") for m in MODELS]
EXP_RUNS = [("qwen36-35b-a3b", "v3a", "exp-v3a"), ("qwen36-35b-a3b", "v3b", "exp-v3b"),
            ("qwen36-35b-a3b", "v2@848px", "exp-in-848"), ("qwen36-35b-a3b", "v2@3fps<40s", "exp-in-fps3")]

# primary violation group per violation video (for the difficulty map)
GROUP = {
    "X-1": "suspicious_note_returned", "X-2": "no_client_id_check", "X-4": "client_cash_left(foreign/unattended)",
    "X-11": "workstation_unlocked", "X-13": "cash_accepted_without_count", "X-15": "cash_unattended",
    "X-17": "collector_bag_no_check", "X-18": "outsider_in_cash_room", "X-20": "safe_left_open",
    "X-22": "safe_key_left", "X-24": "seals_docs_unattended", "X-26": "cash_unattended",
    "X-28": "workstation_unlocked", "X-30": "door_entry(+outsider)", "X-32": "door_entry(+outsider)",
    "X-33": "door_entry(+outsider)", "X-34": "counting_without_client", "X-38": "client_cash_left(foreign/unattended)",
    "X-40": "phone_or_personal_items", "X-44": "other(unclear: unchecked notes into bundle)",
    "X-46": "eating_drinking",
}
ORG_SEC = {}  # organizer seconds only (X-47 -> X-4)


def load_org():
    import openpyxl
    wb = openpyxl.load_workbook(HARNESS.parent / "open" / "open_labels.xlsx", read_only=True)
    from labels import parse_seconds, DUPLICATES
    for i, row in enumerate(wb.active.iter_rows(values_only=True)):
        if i == 0 or not row or not row[0]:
            continue
        key = config.video_key(row[0])
        tgt = DUPLICATES.get(key, key)
        s = parse_seconds(row[1])
        if s is not None:
            ORG_SEC.setdefault(tgt, []).append(s)


def load_run(run):
    d = RUNS / run
    res = {}
    if not d.exists():
        return res
    for vd in d.iterdir():
        if not vd.is_dir():
            continue
        for p in vd.glob("r*.json"):
            m = re.fullmatch(r"r(\d+)\.json", p.name)
            if not m:
                continue
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            res.setdefault(vd.name, {})[int(m.group(1))] = raw
    return res


def load_judge(name, source):
    import judge_eval
    src = load_run(source)
    dur = json.loads((RUNS / "judge" / "durations.json").read_text(encoding="utf-8"))
    out = judge_eval.load_judge_results(name, src, dur)
    if isinstance(out, tuple):
        out = out[0]
    return {k: v for k, v in out.items() if v}


def kept_of(raw, offset=None):
    kept, _ = select_violations(raw.get("parsed"), offset=offset)
    return kept


def build(results, gt, offset=None):
    """-> {video: [ {pred, kept} per repeat ]}"""
    out = {}
    for key, reps in results.items():
        if key not in gt:
            continue
        out[key] = [kept_of(reps[k], offset) for k in sorted(reps)]
    return out


def majority(kepts):
    n = len(kepts)
    votes = sum(bool(k) for k in kepts)
    maj = votes * 2 > n
    tc = Counter(v["type_id"] for kept in kepts for v in {x["type_id"]: x for x in kept}.values())
    win = tc.most_common(1)[0][0] if tc else None
    tcs = [min(v["timecode_sec"] for v in kept if v["type_id"] == win) for kept in kepts
           if any(v["type_id"] == win for v in kept)]
    med = statistics.median(tcs) if tcs else None
    return votes, n, maj, win, med


def near(tc, secs):
    return min(secs, key=lambda s: abs(tc - s)) if secs else None


def metrics(table, gt, tc_shift=None):
    tp = fp = fn = tn = 0
    hit2 = hit3 = typ = 0
    for key, kepts in table.items():
        g = gt[key]
        votes, n, maj, win, med = majority(kepts)
        if g["violation"] and maj:
            tp += 1
            if med is not None:
                t = med + (tc_shift(win) if tc_shift else 0.0)
                d = min(abs(t - s) for s in ORG_SEC.get(key, g["seconds"]))
                hit2 += d <= 2
                hit3 += d <= 3
            typ += win in g["type_ids"]
        elif g["violation"]:
            fn += 1
        elif maj:
            fp += 1
        else:
            tn += 1
    n = tp + fp + fn + tn
    return dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn, acc=round((tp + tn) / n, 3) if n else None,
                recall=round(tp / (tp + fn), 3) if tp + fn else None,
                precision=round(tp / (tp + fp), 3) if tp + fp else None,
                tc2_tp=round(hit2 / tp, 3) if tp else None, tc3_tp=round(hit3 / tp, 3) if tp else None,
                tc2_pos=round(hit2 / (tp + fn), 3) if tp + fn else None,
                type_tp=round(typ / tp, 3) if tp else None)


def per_call_acc(table, gt, pairs=None):
    c = t = 0
    for key, kepts in table.items():
        for k, kept in enumerate(kepts):
            if pairs is not None and (key, k) not in pairs:
                continue
            t += 1
            c += bool(kept) == gt[key]["violation"]
    return round(c / t, 3) if t else None, t


def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with open(OUT / path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    load_org()
    gt = load_ground_truth()
    vids = sorted(gt, key=config.video_number)
    tables = {}
    labels = []
    for model, pv, run in BASE_RUNS + EXP_RUNS:
        res = load_run(run)
        if not res:
            continue
        lab = f"{model}:{pv}"
        tables[lab] = build(res, gt)
        labels.append((lab, run, res))
    # judge
    for jd in sorted((RUNS / "judge").iterdir()):
        if not jd.is_dir() or "__" not in jd.name:
            continue
        src, jm = jd.name.split("__", 1)
        try:
            jres = load_judge(jd.name, src)
            lab = f"judge[{jm}] on {src}"
            tables[lab] = build(jres, gt, offset=-1.0)
            labels.append((lab, "judge/" + jd.name, jres))
        except Exception as e:  # pragma: no cover
            print("judge load failed", jd.name, e)
    # zoom verification (pass 1 = qwen36-35b-a3b v1, first 5 repeats, only videos the zoom run touched)
    try:
        import eval_zoom
        zdir = RUNS / "exp-in-zoom"
        p1 = load_run("qwen36-35b-a3b")
        zv = {d.name for d in zdir.iterdir() if d.is_dir()}
        zb, zz = {}, {}
        for key in zv:
            if key not in gt or key not in p1:
                continue
            reps = [p1[key][k] for k in range(5) if k in p1[key]]
            zb[key] = [kept_of(r) for r in reps]
            zz[key] = [eval_zoom.kept_after("exp-in-zoom", key, k, r.get("parsed"), "zoom", None)[0]
                       for k, r in enumerate(reps)]
        tables["zoom-base(35b-a3b:v1 r0-4, zoom videos)"] = zb
        tables["zoom-verified(35b-a3b:v1 r0-4)"] = zz
        labels.append(("zoom-base(35b-a3b:v1 r0-4, zoom videos)", "qwen36-35b-a3b", {k: dict(enumerate(p1[k][i] for i in range(5))) for k in zb}))
        labels.append(("zoom-verified(35b-a3b:v1 r0-4)", "exp-in-zoom", {k: {} for k in zz}))
    except Exception as e:  # pragma: no cover
        print("zoom failed", e)

    # ---------- per-run summary ----------
    summ = []
    for lab, run, res in labels:
        t = tables[lab]
        m = metrics(t, gt)
        pca, ncalls = per_call_acc(t, gt)
        margins, unanim = [], 0
        for key, kepts in t.items():
            v, n, *_ = majority(kepts)
            margins.append(abs(2 * v - n) / n)
            unanim += v in (0, n)
        lat = [r.get("latency_sec") or 0 for reps in res.values() for r in reps.values()]
        summ.append(dict(run=lab, dir=run, videos=len(t), calls=ncalls,
                         reps_per_video=round(ncalls / len(t), 1) if t else 0, **m, per_call_acc=pca,
                         mean_vote_margin=round(statistics.mean(margins), 3) if margins else None,
                         unanimous_share=round(unanim / len(t), 3) if t else None,
                         latency_mean=round(statistics.mean(lat), 1) if lat else None))
    write_csv("run_summary.csv", summ)

    # ---------- detection matrix ----------
    det_rows, type_rows = [], []
    for key in vids:
        g = gt[key]
        r1 = {"video": key, "gt": int(g["violation"]), "group": GROUP.get(key, ""), "scenario": g["scenario"]}
        r2 = dict(r1)
        for lab in tables:
            kepts = tables[lab].get(key)
            if not kepts:
                r1[lab] = ""
                r2[lab] = ""
                continue
            n = len(kepts)
            r1[lab] = round(sum(bool(k) for k in kepts) / n, 2)
            r2[lab] = round(sum(any(v["type_id"] in g["type_ids"] for v in k) for k in kepts) / n, 2) \
                if g["violation"] else ""
        det_rows.append(r1)
        type_rows.append(r2)
    write_csv("detection_matrix.csv", det_rows)
    write_csv("type_correct_matrix.csv", [r for r in type_rows if r["gt"] == 1])

    base_labs = [f"{m}:{p}" for m, p, _ in BASE_RUNS if f"{m}:{p}" in tables]
    # per group / scenario difficulty (base runs only)
    def agg(keyfn, only_pos=None):
        acc = defaultdict(lambda: {"videos": set(), "calls": 0, "flag": 0, "typeok": 0, "maj_ok": 0, "maj_n": 0})
        for key in vids:
            g = gt[key]
            if only_pos is not None and g["violation"] != only_pos:
                continue
            grp = keyfn(key)
            for lab in base_labs:
                kepts = tables[lab].get(key) or []
                a = acc[grp]
                a["videos"].add(key)
                a["calls"] += len(kepts)
                a["flag"] += sum(bool(k) for k in kepts)
                a["typeok"] += sum(any(v["type_id"] in g["type_ids"] for v in k) for k in kepts)
                if kepts:
                    _, _, maj, _, _ = majority(kepts)
                    a["maj_n"] += 1
                    a["maj_ok"] += maj == g["violation"]
        return acc

    grp_rows = []
    for grp, a in sorted(agg(lambda k: GROUP[k], True).items(), key=lambda x: x[1]["flag"] / max(1, x[1]["calls"])):
        grp_rows.append(dict(group=grp, videos=" ".join(sorted(a["videos"], key=config.video_number)),
                             call_flag_rate=round(a["flag"] / a["calls"], 3),
                             call_type_correct_rate=round(a["typeok"] / a["calls"], 3),
                             runs_majority_detect=f"{a['maj_ok']}/{a['maj_n']}"))
    write_csv("difficulty_by_type.csv", grp_rows)
    scen_rows = []
    for (sc, pos), a in sorted(
            {(gt[k]["scenario"], gt[k]["violation"]): None for k in vids}.items()):
        pass
    sc_acc = agg(lambda k: (gt[k]["scenario"], "violation" if gt[k]["violation"] else "clean"))
    for (sc, cls), a in sorted(sc_acc.items()):
        scen_rows.append(dict(scenario=sc, cls=cls, n_videos=len(a["videos"]),
                              videos=" ".join(sorted(a["videos"], key=config.video_number)),
                              call_flag_rate=round(a["flag"] / a["calls"], 3),
                              majority_correct=f"{a['maj_ok']}/{a['maj_n']}",
                              majority_correct_rate=round(a["maj_ok"] / a["maj_n"], 3)))
    write_csv("difficulty_by_scenario.csv", scen_rows)

    # ---------- FP map ----------
    fp_rows = []
    fp_type_tot = Counter()
    for key in vids:
        if gt[key]["violation"]:
            continue
        c = Counter()
        calls = 0
        per_run_maj = 0
        for lab in base_labs:
            kepts = tables[lab].get(key) or []
            calls += len(kepts)
            for k in kepts:
                for t in {v["type_id"] for v in k}:
                    c[t] += 1
            if kepts and majority(kepts)[2]:
                per_run_maj += 1
        fp_type_tot.update(c)
        fp_rows.append(dict(video=key, scenario=gt[key]["scenario"], calls=calls,
                            calls_flagged=sum(1 for lab in base_labs for k in (tables[lab].get(key) or []) if k),
                            runs_majority_fp=f"{per_run_maj}/{len(base_labs)}",
                            top_hallucinated=" ".join(f"{t}:{n}" for t, n in c.most_common(4))))
    write_csv("fp_map_clean_videos.csv", fp_rows)
    write_csv("fp_type_totals.csv", [dict(type_id=t, flagged_calls_on_clean=n) for t, n in fp_type_tot.most_common()])

    # ---------- timecode errors ----------
    tc_rows = []
    for lab in tables:
        for key, kepts in tables[lab].items():
            g = gt[key]
            if not g["violation"]:
                continue
            secs = ORG_SEC.get(key, g["seconds"])
            for k, kept in enumerate(kepts):
                for v in kept:
                    s = near(v["timecode_sec"], secs)
                    tc_rows.append(dict(run=lab, video=key, group=GROUP[key], repeat=k, pred_type=v["type_id"],
                                        type_ok=int(v["type_id"] in g["type_ids"]), pred_tc=v["timecode_sec"],
                                        org_sec=s, err=round(v["timecode_sec"] - s, 1)))
    write_csv("timecode_errors.csv", tc_rows)
    # per group, type-correct only, base runs
    tce = []
    for grp in sorted(set(GROUP.values())):
        e = [r["err"] for r in tc_rows if r["group"] == grp and r["type_ok"] and r["run"] in base_labs]
        if not e:
            continue
        tce.append(dict(group=grp, n=len(e), median_err=statistics.median(e), mean_err=round(statistics.mean(e), 1),
                        within2=round(sum(abs(x) <= 2 for x in e) / len(e), 3),
                        within3=round(sum(abs(x) <= 3 for x in e) / len(e), 3),
                        early_gt2=round(sum(x < -2 for x in e) / len(e), 3),
                        late_gt2=round(sum(x > 2 for x in e) / len(e), 3)))
    write_csv("timecode_by_type.csv", tce)
    # per predicted type (deployable key), all base runs, type-correct
    pt = defaultdict(list)
    for r in tc_rows:
        if r["type_ok"] and r["run"] in base_labs:
            pt[r["pred_type"]].append((r["video"], r["err"]))

    def loo_shift(pred_type, video):
        e = [x for v, x in pt.get(pred_type, []) if v != video]
        if len(e) < 5 or len({v for v, _ in pt.get(pred_type, []) if v != video}) < 1:
            return 0.0
        med = statistics.median(e)
        return -med if abs(med) >= 1.0 else 0.0

    def fit_shift(pred_type):
        e = [x for _, x in pt.get(pred_type, [])]
        if len(e) < 5:
            return 0.0
        med = statistics.median(e)
        return -med if abs(med) >= 1.0 else 0.0

    shift_rows = []
    for t, lst in sorted(pt.items()):
        e = [x for _, x in lst]
        shift_rows.append(dict(pred_type=t, n=len(e), videos=" ".join(sorted({v for v, _ in lst}, key=config.video_number)),
                               median_err=statistics.median(e), proposed_shift=fit_shift(t)))
    write_csv("timecode_shift_by_pred_type.csv", shift_rows)

    # majority-level gain from shifts: in-sample and leave-one-video-out (shift for a video estimated w/o it)
    gain_rows = []
    for lab in tables:
        t = tables[lab]
        base = metrics(t, gt)
        ins = metrics(t, gt, tc_shift=fit_shift)
        # LOO needs the video, so compute manually
        hit2 = hit3 = tp = 0
        for key, kepts in t.items():
            g = gt[key]
            votes, n, maj, win, med = majority(kepts)
            if g["violation"] and maj:
                tp += 1
                if med is not None:
                    tt = med + loo_shift(win, key)
                    d = min(abs(tt - s) for s in ORG_SEC.get(key, g["seconds"]))
                    hit2 += d <= 2
                    hit3 += d <= 3
        gain_rows.append(dict(run=lab, tp=base["tp"], tc2_tp=base["tc2_tp"], tc3_tp=base["tc3_tp"],
                              tc2_tp_shift_insample=ins["tc2_tp"], tc3_tp_shift_insample=ins["tc3_tp"],
                              tc2_tp_shift_loo=round(hit2 / tp, 3) if tp else None,
                              tc3_tp_shift_loo=round(hit3 / tp, 3) if tp else None))
    write_csv("timecode_shift_gain.csv", gain_rows)

    # ---------- complementarity ----------
    majpred = {lab: {k: majority(v)[2] for k, v in tables[lab].items()} for lab in base_labs}
    pair_rows = []
    for a, b in combinations(base_labs, 2):
        common = [k for k in vids if k in majpred[a] and k in majpred[b]]
        res = {}
        for mode in ("or", "and", "pooled"):
            c = 0
            tp = fp = 0
            for k in common:
                if mode == "or":
                    p = majpred[a][k] or majpred[b][k]
                elif mode == "and":
                    p = majpred[a][k] and majpred[b][k]
                else:
                    ka, kb = tables[a][k], tables[b][k]
                    va = sum(bool(x) for x in ka) / len(ka)
                    vb = sum(bool(x) for x in kb) / len(kb)
                    p = (va + vb) / 2 > 0.5
                c += p == gt[k]["violation"]
                tp += p and gt[k]["violation"]
                fp += p and not gt[k]["violation"]
            res[mode] = (round(c / len(common), 3), tp, fp)
        # disagreement on positives
        only_a = [k for k in common if gt[k]["violation"] and majpred[a][k] and not majpred[b][k]]
        only_b = [k for k in common if gt[k]["violation"] and majpred[b][k] and not majpred[a][k]]
        pair_rows.append(dict(a=a, b=b, acc_a=metrics(tables[a], gt)["acc"], acc_b=metrics(tables[b], gt)["acc"],
                              acc_or=res["or"][0], tp_fp_or=f"{res['or'][1]}/{res['or'][2]}",
                              acc_and=res["and"][0], tp_fp_and=f"{res['and'][1]}/{res['and'][2]}",
                              acc_pooled=res["pooled"][0], tp_fp_pooled=f"{res['pooled'][1]}/{res['pooled'][2]}",
                              pos_only_a=" ".join(only_a), pos_only_b=" ".join(only_b)))
    pair_rows.sort(key=lambda r: -max(r["acc_or"], r["acc_and"], r["acc_pooled"]))
    write_csv("model_pairs.csv", pair_rows)

    # oracle and all-run pooled vote
    pooled = {}
    for k in vids:
        fr = [sum(bool(x) for x in tables[lab][k]) / len(tables[lab][k]) for lab in base_labs if tables[lab].get(k)]
        pooled[k] = statistics.mean(fr)
    best_thr = None
    for thr in [i / 20 for i in range(2, 19)]:
        acc = sum((pooled[k] > thr) == gt[k]["violation"] for k in vids) / len(vids)
        if best_thr is None or acc > best_thr[1]:
            best_thr = (thr, acc)
    json.dump({"pooled_all_base_runs_best_threshold": best_thr,
               "pooled_at_0.5": sum((pooled[k] > 0.5) == gt[k]["violation"] for k in vids) / len(vids),
               "videos_no_base_run_majority_correct": [k for k in vids if not any(
                   majpred[l].get(k) == gt[k]["violation"] for l in base_labs)],
               },
              open(OUT / "ensemble_extra.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    # ---------- exp runs vs baseline on the same (video, repeat) cells ----------
    base = tables.get("qwen36-35b-a3b:v2")
    exp_rows = []
    for lab in tables:
        if not any(lab == f"{m}:{p}" for m, p, _ in EXP_RUNS) and not lab.startswith("judge"):
            continue
        cells = {(k, i) for k, kepts in tables[lab].items() for i in range(len(kepts))}
        acc_exp, n = per_call_acc(tables[lab], gt)
        acc_b, nb = per_call_acc(base, gt, pairs=cells)
        # per-call fp/fn
        def rates(tb, pairs):
            tp = fp = fn = tn = 0
            for k, kepts in tb.items():
                for i, kept in enumerate(kepts):
                    if (k, i) not in pairs:
                        continue
                    g = gt[k]["violation"]
                    p = bool(kept)
                    tp += g and p
                    fp += (not g) and p
                    fn += g and not p
                    tn += (not g) and not p
            return tp, fp, fn, tn
        exp_rows.append(dict(run=lab, calls=n, per_call_acc=acc_exp, tp_fp_fn_tn="/".join(map(str, rates(tables[lab], cells))),
                             baseline_same_cells_acc=acc_b,
                             baseline_tp_fp_fn_tn="/".join(map(str, rates(base, cells)))))
    write_csv("exp_vs_baseline.csv", exp_rows)

    # self-consistency per model: video-level vote fractions std
    print("done")
    for r in summ:
        print(r)


if __name__ == "__main__":
    main()
