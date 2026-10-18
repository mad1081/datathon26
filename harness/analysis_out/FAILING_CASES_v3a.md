# Root causes of the remaining failures (exp-v3a, prompt_v3, 40×5: 0.775, TP16/FP4/FN5/TN15)

Per-video detail: `failing_cases_v3a.csv`; simulated text-only fixes: `failure_fixes_sim.csv`.

| Video | Truth (human labels) | What the VLM wrote | Class | Generalizable fix |
|---|---|---|---|---|
| X-1 miss | Part of the notes is put back in front of the client after counting (22–25 s), no act | "отдает пересчитанные деньги клиенту" — same wording as clean X-3 | Seen, misjudged | Rule: accepted cash never goes back to the client; visual check of where the money is in the last 5 s and whether it is all of it |
| X-2 miss | Bundle goes straight into the machine, no ID shown | "Клиент кладёт на стол документ… просматривает документ" — bundle read as an ID card | Contradicted | Describe the object (white card vs stack of notes); ID check needs ≥2 s of examination before cash; full-res crop at handover |
| X-4 miss | Client 1's bundle stays on the desk from 41 s; client 2's bundle stacked on it at 66–70 s | "Клиент 1 забирает деньги" / "убирает деньги в сейф" | Contradicted | At every "person enters / sits down" event ask on full-res frames whether cash is on the desk and whether it was there before |
| X-22 miss | Key left in the safe lock, cashier leaves | Key never mentioned; invented safe opening | Absent | At departure crop the safe lock at full resolution: "ключ торчит из замка?" |
| X-44 miss | Rejected notes merged back without detector check | "подносит к детектору" — contradicts the label | Absent, label unclear | Lowest priority; list as known limitation |
| X-3 false alarm | Clean: card examined ~3 s, bundle into the machine | A different invented violation in each repeat | Unstable | Same last-5-s money check as X-1 |
| X-31 false alarm | Clean: door closed and checked by hand | "дверь остаётся приоткрытой" 5/5 | Contradicted | Compare door state at the first frame, entry + 5 s and the last frame |
| X-25 false alarm | Clean: seals in safe, key removed, desk empty | "ноутбук разблокирован" (r1, r3 noticed "закрывает ноутбук") | Contradicted | Compare laptop lid/screen between a working frame and the departure frame |
| X-27 false alarm | Clean: bundle into the safe, key taken | "помещает деньги внутрь сейфа" then "на столе остаются деньги" | Seen, self-contradicting | Laptop comparison as X-25; text rule alone does not change the score |

Counts: 6 perception failures (fact missing or contradicted), 2 seen but misjudged (X-1, X-27), 1 unstable (X-3). Text-only post-processing on cached answers does not help (majority-same-type 0.775 → 0.750, cross-repeat laptop/door contradiction 0.750 each, money-into-safe check no change). Proposed next step: targeted visual state checks (one state question per object at a known moment) instead of the earlier "is there a violation?" zoom window. Upper bound if they work: −3 false alarms (X-31, X-25, X-27), +2 catches (X-4, X-22).
