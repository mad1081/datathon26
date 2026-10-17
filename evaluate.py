"""Labels + metrics. Predictions format: {video: {"verdict": bool, "t": float | None}}."""
import re

import openpyxl

LABELS_PATH = "open/open_labels.xlsx"
# Byte-identical duplicates of Х-4 / Х-5 (md5 match); Х-47 label (68 s) contradicts Х-4 (57 s).
DUPLICATES = {"Х-47", "Х-48"}
TIME_TOLERANCE_SEC = 2.0


def parse_time(text):
    if not text:
        return None
    minutes = re.search(r"(\d+)\s*мин", text)
    seconds = re.search(r"(\d+)\s*сек", text)
    return (int(minutes.group(1)) * 60 if minutes else 0) + (int(seconds.group(1)) if seconds else 0)


def load_labels():
    ws = openpyxl.load_workbook(LABELS_PATH).active
    rows = list(ws.iter_rows(values_only=True))[1:]
    return {
        name.strip(): {"verdict": status.strip() == "нарушение", "t": parse_time(ts)}
        for name, ts, status in rows
        if name and name.strip() not in DUPLICATES
    }


def score(preds, labels=None):
    labels = labels or load_labels()
    tp = fp = fn = tn = hits = 0
    for name, gt in labels.items():
        p = preds.get(name, {"verdict": False, "t": None})
        if gt["verdict"] and p["verdict"]:
            tp += 1
            hits += p["t"] is not None and abs(p["t"] - gt["t"]) <= TIME_TOLERANCE_SEC
        elif gt["verdict"]:
            fn += 1
        elif p["verdict"]:
            fp += 1
        else:
            tn += 1
    n = len(labels)
    return {"acc": round((tp + tn) / n, 3), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            f"time_hit@{TIME_TOLERANCE_SEC}s": f"{hits}/{tp}"}


if __name__ == "__main__":
    labels = load_labels()
    assert parse_time("1минута 8 секунда") == 68 and parse_time("22 секунда") == 22
    assert len(labels) == 40 and sum(v["verdict"] for v in labels.values()) == 21
    print("all-violation baseline:", score({k: {"verdict": True, "t": None} for k in labels}))
