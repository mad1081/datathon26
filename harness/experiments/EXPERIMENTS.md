# Experiment log

Each experiment folder holds the per-model `summary.json`, `per_video.csv`, `config.json`, the run log and a copy of the exact `prompt.py` used. Raw model answers for every call stay in `harness/runs/<run-name>/<video>/r<k>.json` (not committed).

Scoring: organizer labels (`open/open_labels.xlsx`, verdict + second), teammate's verified types (`labeled_dataset_pairs.csv`). 40 unique videos (X-47 = X-4, X-48 = X-5). Majority vote over repeats.

## EXP-001 — prompt v1, whole-video single call

- Code: branch `eval`, commit `ddbb2cc` ("feat: whole-video VLM eval harness (prompt v1)")
- Frames: 2 fps for videos < 120 s, 1 fps otherwise; long side 640 px; JPEG q80
- Sampling: 10 repeats, temperature 0.6, thinking disabled for Qwen3.5/3.6/3.8
- Verdict types: rules.json v0.4 count_in_verdict + workstation_unlocked, seals_docs_unattended, eating_drinking
- Started 07:55 Astana, 2026-10-18

| Model | Majority acc | TP/FP/FN/TN | Recall | Precision | TC ±2 s (of TP) | Type (of TP) | Latency mean / p95 / max (s, 8 concurrent) |
|---|---|---|---|---|---|---|---|
| qwen36-35b-a3b | 0.675 | 14/6/7/13 | 0.667 | 0.700 | 0.43 | 0.57 | 7.8 / 18.8 / 33.1 |

Findings (qwen36-35b-a3b):
- All 6 false positives are clean "leaving the workplace" / "start of shift" videos (X-12, X-21, X-23, X-25, X-27, X-29).
- The model contradicts its own timeline: it writes "кассир закрывает крышку ноутбука" and still reports `workstation_unlocked`.
- It flags `door_left_open` when the cashier exits; organizers count an open door only on entry (X-30, X-32, X-33).
- X-21: drinking from a mug with no cash nearby is labelled clean; X-46 (drink next to the cash bundle) is a violation.
- Misses: X-1 (suspicious note returned), X-2 (no ID shown), X-20 (safe ajar), X-32/X-33 (door on entry), X-44 (never detected).

Molmo2-8B was dropped: 32k context too small for 2 fps frames (~600 tokens/frame), broken JSON and 60–100 s per short video.
