"""Build a local-only review manifest from the container/label audit."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
audit = json.loads((ROOT / "analysis/dataset_audit.json").read_text(encoding="utf-8"))
groups = {}
for record in audit["records"]:
    assert (ROOT / "open/videos" / record["file"]).is_file(), record["file"]
    group = groups.setdefault(record["sha256"], {
        "id": record["sha256"],
        "file": record["file"],
        "duration_sec": record["duration_sec"],
        "source_labels": [],
    })
    group["source_labels"].append({
        "file": record["file"],
        "label": record["label"],
        "timestamp_sec": record["timestamp_sec"],
    })

records = list(groups.values())
for record in records:
    record["positive"] = any(x["timestamp_sec"] is not None for x in record["source_labels"])
    record["timestamps_sec"] = sorted({x["timestamp_sec"] for x in record["source_labels"] if x["timestamp_sec"] is not None})
records.sort(key=lambda r: (not r["positive"], int(r["file"].split("-")[1].split(".")[0])))
assert len(records) == 40
assert sum(len(x["source_labels"]) for x in records) == 42
assert sum(x["positive"] for x in records) == 21
payload = {"schema_version": 1, "records": records}
serialized = json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")
(HERE / "manifest.js").write_text("window.REVIEW_MANIFEST = " + serialized + ";\n", encoding="utf-8")
print("Manifest verified: 42 existing files, 40 unique clips, 21 positive, 19 negative; both duplicate-positive timestamps retained.")
