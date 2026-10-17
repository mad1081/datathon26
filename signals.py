"""Per-second signal timeline from cached detections, printed next to the label timestamp.

Usage: uv run signals.py [video ...]
Row per second: people count | phone | bag | marker '<<' at labeled violation second.
"""
import json
import sys
from pathlib import Path

from evaluate import load_labels

DETS_DIR = Path("cache/dets")
PERSON_MIN_SCORE = 0.6
OBJECT_MIN_SCORE = 0.4
BAGS = {"handbag", "backpack", "suitcase"}


def timeline(video):
    frames = json.loads((DETS_DIR / f"{video}.json").read_text())["frames"]
    rows = []
    for f in frames:
        dets = f["dets"]
        rows.append({
            "t": f["t"],
            "people": sum(d[0] == "person" and d[1] >= PERSON_MIN_SCORE for d in dets),
            "phone": any(d[0] == "cell phone" and d[1] >= OBJECT_MIN_SCORE for d in dets),
            "bag": any(d[0] in BAGS and d[1] >= OBJECT_MIN_SCORE for d in dets),
        })
    return rows


def show(video, label):
    mark_t = label["t"] if label else None
    print(f"\n== {video}  {'VIOLATION @' + str(mark_t) if label and label['verdict'] else 'clean'}")
    line, seen = [], set()
    for r in timeline(video):
        if int(r["t"]) in seen:
            continue
        seen.add(int(r["t"]))
        cell = f"{int(r['t'])}:{r['people']}{'P' if r['phone'] else ''}{'B' if r['bag'] else ''}"
        line.append(cell + ("<<" if mark_t is not None and int(r["t"]) == mark_t else ""))
    print(" ".join(line))


if __name__ == "__main__":
    labels = load_labels()
    videos = sys.argv[1:] or sorted(p.stem for p in DETS_DIR.glob("*.json"))
    for v in videos:
        show(v, labels.get(v))
