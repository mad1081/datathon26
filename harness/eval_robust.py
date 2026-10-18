"""Robustness eval: the normal eval with a deterministic transform applied to every sampled frame.

The transform is selected with ROBUST_TRANSFORM (mirror | crop85 | dark_jpeg50 | rot6) and is applied
to the decoded frame before resizing/JPEG encoding, so defaults in frames.py stay untouched.

  ROBUST_TRANSFORM=mirror python harness/eval_robust.py --name robust-mirror-v3b --repeats 3 --concurrency 3 ...
  python harness/eval_robust.py --compare robust-mirror-v3b robust-crop85-v3b --baseline exp-v3b --repeats 3

--compare scores runs read-only (nothing is written into the run dirs).
"""
import argparse
import os
import sys

import cv2
import numpy as np

import config
import frames


def _mirror(img):
    return cv2.flip(img, 1)


def _crop85(img):
    h, w = img.shape[:2]
    ch, cw = round(h * 0.85), round(w * 0.85)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return cv2.resize(img[y0:y0 + ch, x0:x0 + cw], (w, h), interpolation=cv2.INTER_LINEAR)


def _dark(img):
    # scaling by 0.75 lowers both mean brightness and contrast (std) by 25%
    return np.clip(img.astype(np.float32) * 0.75, 0, 255).astype(np.uint8)


def _rot6(img):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 6.0, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


TRANSFORMS = {"mirror": (_mirror, None), "crop85": (_crop85, None), "dark_jpeg50": (_dark, 50),
              "rot6": (_rot6, None)}


def install(name):
    fn, quality = TRANSFORMS[name]
    orig_resize = frames._resize
    frames._resize = lambda img, max_side: orig_resize(fn(img), max_side)
    if quality is not None:
        config.JPEG_QUALITY = quality


def compare(names, baseline, repeats):
    from eval import list_videos, load_results, score
    from labels import load_ground_truth

    videos = list_videos()
    gt = load_ground_truth()
    offset, mode, extra = config.THRESHOLD_OFFSET, config.VERDICT_MODE, config.EXTRA_VERDICT_TYPES

    def run(name):
        res = load_results(name, videos, repeats)
        n_calls = sum(len(r) for r in res.values())
        per_rep, maj, per_video = score(res, gt, repeats, offset, mode, extra)
        accs = [r["accuracy"] for r in per_rep]
        maj["rep_acc"] = sum(accs) / len(accs) if accs else None
        return maj, {r["video"]: r for r in per_video}, n_calls

    base_maj, base_pv, base_n = run(baseline)
    rows = [(f"{baseline} (r{repeats})", base_maj, base_pv, base_n)]
    for n in names:
        rows.append((n,) + run(n))

    def f(x):
        return "-" if x is None else f"{x:.3f}"

    print(f"| run | calls | acc (maj) | per-repeat acc | TP/FP/FN/TN | precision | recall | tc±3 (of pos) | type (of pos) | Δacc |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, m, _, nc in rows:
        d = "" if name.startswith(baseline) else f"{(m['accuracy'] - base_maj['accuracy']):+.3f}"
        print(f"| {name} | {nc} | {f(m.get('accuracy'))} | {f(m.get('rep_acc'))} | {m['tp']}/{m['fp']}/{m['fn']}/{m['tn']} | "
              f"{f(m.get('precision'))} | {f(m.get('recall'))} | {f(m.get('tc_hit3_of_pos'))} | "
              f"{f(m.get('type_hit_of_pos'))} | {d} |")
    print()
    for name, _, pv, _ in rows[1:]:
        flips = []
        for v, r in pv.items():
            b = base_pv.get(v)
            if b and b["majority"] != r["majority"]:
                tag = "fixed" if r["correct"] else "broke"
                flips.append(f"{v} {tag} (gt={r['gt'][:2]} base={b['votes_violation']} now={r['votes_violation']} "
                             f"type={r['winning_type'] or '-'}@{r['median_tc']})")
        print(f"{name} flips vs baseline: " + ("; ".join(flips) if flips else "none"))


def main():
    if "--compare" in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--compare", nargs="+", required=True)
        ap.add_argument("--baseline", default="exp-v3b")
        ap.add_argument("--repeats", type=int, default=3)
        a = ap.parse_args()
        compare(a.compare, a.baseline, a.repeats)
        return
    t = os.getenv("ROBUST_TRANSFORM", "")
    if t not in TRANSFORMS:
        sys.exit(f"set ROBUST_TRANSFORM to one of {sorted(TRANSFORMS)}")
    install(t)
    import eval as ev
    ev.main()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
