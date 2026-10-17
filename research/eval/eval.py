"""Evaluate the pipeline on labelled training videos.

Usage:
  python -m eval.eval --data /workspace/datathon/data              # in-process (uses env config, e.g. VLM_BACKEND)
  python -m eval.eval --data ... --api http://127.0.0.1:8000 --key KEY   # through the running service
  python -m eval.eval --data ... --mapping mapping.csv              # if file names do not contain X-<n>

File -> label: the X-number is parsed from the file name (X-12.mov, Cyrillic Х-12.mov, x_12.MOV, "X 12 ...", 12.mov),
or taken from --mapping (CSV: filename,x_number). Unlabelled files are still run and reported.
A label is a second, a list of acceptable seconds (identical files labelled twice, e.g. X-4/X-47), or null.
With --typed (labels_typed.csv) the expected violation type is also compared (type_hit).
Outputs: eval/out/<timestamp>/results.csv, summary.json, raw/<file>.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VIDEO_EXT = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}


def x_number(name: str, mapping: dict[str, str]) -> str | None:
    if name in mapping:
        return mapping[name]
    stem = Path(name).stem
    m = re.search(r"[XxХх][\s_\-]*(\d+)", stem) or re.fullmatch(r"(\d+)", stem)
    return m.group(1) if m else None


def run_api(path: Path, api: str, key: str, timeout: float = 900) -> dict:
    import requests
    with open(path, "rb") as f:
        r = requests.post(f"{api}/api/v1/analyze", headers={"X-API-Key": key},
                          files={"file": (path.name, f, "video/quicktime")}, timeout=300)
    r.raise_for_status()
    jid = r.json()["job_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = requests.get(f"{api}/api/v1/jobs/{jid}", headers={"X-API-Key": key}, timeout=60).json()
        if j["status"] != "processing":
            return j
        time.sleep(2)
    return {"status": "failed", "error": "eval timeout"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/workspace/datathon/data")
    ap.add_argument("--labels", default=str(ROOT / "eval" / "labels.json"))
    ap.add_argument("--mapping", default=None)
    ap.add_argument("--typed", default=str(ROOT.parent / "labels_typed.csv"))
    ap.add_argument("--api", default=None)
    ap.add_argument("--key", default=None)
    ap.add_argument("--tol", type=float, default=2.0, help="timecode tolerance (s) for a 'hit'")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    labels = {k: v for k, v in json.load(open(args.labels)).items() if not k.startswith("_")}
    mapping = {}
    if args.mapping:
        with open(args.mapping) as f:
            mapping = {row[0]: row[1].lstrip("XxХх-_ ") for row in csv.reader(f) if row}
    gt_type: dict[str, str] = {}
    if args.typed and Path(args.typed).exists():
        with open(args.typed, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                gt_type[r["x_id"].lstrip("XxХх-_ ")] = r["type_id"]
    files = sorted(p for p in Path(args.data).rglob("*") if p.suffix.lower() in VIDEO_EXT)
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"no videos in {args.data}")
        return 1

    analyzer = None
    if not args.api:
        from app.config import settings
        from app.pipeline.analyzer import Analyzer
        analyzer = Analyzer(settings)

    out = ROOT / "eval" / "out" / time.strftime("%Y%m%d-%H%M%S")
    (out / "raw").mkdir(parents=True)
    rows = []
    for p in files:
        x = x_number(p.name, mapping)
        gt = labels.get(x) if x else None
        has_label = x in labels if x else False
        t0 = time.time()
        try:
            res = run_api(p, args.api, args.key) if args.api else {"status": "done", **analyzer.run(str(p))}
        except Exception as e:  # noqa: BLE001
            res = {"status": "failed", "error": str(e)}
        dt = time.time() - t0
        slim = json.loads(json.dumps(res, default=str))
        for v in slim.get("violations", []) + slim.get("observations", []):
            for f in v.get("evidence_frames", []):
                f["image_base64"] = f"<{len(f.get('image_base64', ''))} chars>"
        (out / "raw" / f"{p.name}.json").write_text(json.dumps(slim, ensure_ascii=False, indent=1))
        pred = res.get("verdict")
        tcs = [v["timecode_sec"] for v in res.get("violations", [])]
        gts = [] if gt is None else (list(gt) if isinstance(gt, list) else [gt])
        err = min((abs(t - g) for t in tcs for g in gts), default=None) if gts else None
        types = [v.get("type_id", "") for v in res.get("violations", [])]
        exp_type = gt_type.get(x or "", "")
        row = {"file": p.name, "x": x or "", "labelled": has_label,
               "gt_verdict": ("violation" if gt is not None else "no_violation") if has_label else "",
               "gt_sec": ";".join(str(g) for g in gts), "gt_type": exp_type,
               "pred_verdict": pred or res.get("status"),
               "pred_timecodes": ";".join(f"{t:.2f}" for t in tcs),
               "pred_types": ";".join(types),
               "type_hit": (exp_type in types) if exp_type else "",
               "tc_abs_err": round(err, 2) if err is not None else "", "proc_sec": round(dt, 1),
               "status": res.get("status"), "error": res.get("error", "")}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    with open(out / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lab = [r for r in rows if r["labelled"]]
    tp = sum(r["gt_verdict"] == "violation" and r["pred_verdict"] == "violation" for r in lab)
    fn = sum(r["gt_verdict"] == "violation" and r["pred_verdict"] != "violation" for r in lab)
    fp = sum(r["gt_verdict"] == "no_violation" and r["pred_verdict"] == "violation" for r in lab)
    tn = sum(r["gt_verdict"] == "no_violation" and r["pred_verdict"] == "no_violation" for r in lab)
    errs = [r["tc_abs_err"] for r in lab if r["tc_abs_err"] != ""]
    summary = {
        "n_files": len(rows), "n_labelled": len(lab),
        "verdict_accuracy": round((tp + tn) / len(lab), 3) if lab else None,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "timecode_mae_sec": round(sum(errs) / len(errs), 2) if errs else None,
        "timecode_median_sec": sorted(errs)[len(errs) // 2] if errs else None,
        f"timecode_within_{args.tol}s": round(sum(e <= args.tol for e in errs) / max(1, tp), 3) if errs else None,
        "type_hit_rate": (round(sum(r["type_hit"] is True for r in lab) / max(1, sum(r["gt_type"] != "" for r in lab)), 3)
                          if any(r["gt_type"] for r in lab) else None),
        "max_proc_sec": max(r["proc_sec"] for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "unlabelled_files": [r["file"] for r in rows if not r["labelled"]],
        "out_dir": str(out),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
