# Cash-desk VLM: data and results analysis

Snapshot: 2026-10-18 ~09:20 Astana. Every number here was recomputed offline from cached answers in `harness/runs/` by `analysis_out/compute.py` (no model calls). Scoring matches `eval.py`: consistency checks on, `count_in_verdict` plus `workstation_unlocked, seals_docs_unattended, eating_drinking`, majority vote over repeats (ties count as "no violation"), timecode compared with the organizer second (X-4 accepts 57 s and 68 s; 68 s comes from X-47). v3a, v3b, fps3 and zoom runs were still running at the snapshot (2.5–4.5 repeats per video).

Helper files in this folder: `run_summary.csv`, `detection_matrix.csv`, `type_correct_matrix.csv`, `difficulty_by_type.csv`, `difficulty_by_scenario.csv`, `fp_map_clean_videos.csv`, `fp_type_totals.csv`, `timecode_errors.csv`, `timecode_by_type.csv`, `timecode_shift_by_pred_type.csv`, `timecode_shift_gain.csv`, `timecode_snap_leaving.csv`, `model_pairs.csv`, `pairs_with_v3.csv`, `ensemble_extra.json`, `exp_vs_baseline.csv`, `type_ablation.csv`, `type_priority_demote.csv`, `judge_error_classes.csv`.

## 1. Label sanity

- Organizer and teammate verdicts agree on 40/40 videos (21 violations, 19 clean); timestamps agree on all 20 videos that have one in both files.
- Multi-event videos: X-4 (57 s client 1 money left, 68 s client 2 money stacked on it — the 68 s label is the organizer's X-47 row), X-38 (33 s, plus ~57 s), X-30 and X-33 (door left open, then an outsider enters), X-17 (`collector_bag_no_check` or `no_client_id_check`).
- No legal norm found for `workstation_unlocked` (X-11, X-28) although FAQ 32 says every dataset violation has an open norm. README must cite a real one or say none was found.
- X-44 has no type in the teammate labels; the basis is conditional (№ 231 п. 44). No run ever typed it right.

| Scenario | Violation | Clean |
|---|---|---|
| Уход с рабочего места | 6 (X-11, 15, 22, 24, 26, 28) | 5 (X-12, 23, 25, 27, 29) |
| Приём наличных от клиента | 4 (X-1, 2, 18, 34) | 5 (X-3, 5, 19, 35, 37) |
| Обработка денег без клиента | 3 (X-20, 44, 46) | 5 (X-8, 10, 21, 43, 45) |
| Вход в кассу | 4 (X-30, 32, 33, 40) | 1 (X-31) |
| Смена клиентов | 2 (X-4, 38) | 1 (X-39) |
| Инкассация: приём сумки | 1 (X-17) | 1 (X-16) |
| Вскрытие сумки и закладка в сейф | 1 (X-13) | 1 (X-14) |

| Violation | Clean pair | What differs |
|---|---|---|
| X-2 | X-3 | Client hands over an ID card, cashier looks at it ~3 s before taking the cash |
| X-4, X-38 | X-39 | Client 1's bundle goes into the safe before client 2 arrives |
| X-11, X-28 | X-12, X-29 | Lock screen / closed lid before leaving vs spreadsheet on screen |
| X-13 | X-14 | Bundles counted on the machine before the safe |
| X-17 | X-16 | Collector's document viewed, bag seal inspected |
| X-20 | X-21 | Safe locked vs door pushed ajar (one ~1 s swing at 3–4 s) |
| X-22 | X-23 | Key taken out vs left in the lock (a few pixels at 640 px) |
| X-24 | X-25 | Booklet and seals go into the safe |
| X-26 | X-27 | Small bundle goes into the safe |
| X-30, X-32, X-33 | X-31 | Door shut within 2–3 s of entering; outsider enters in X-30, X-33 |
| X-40 | X-31 | No bag or jacket on the desk |
| X-34 | X-35, X-37 | Bundle goes into the machine while the client is seated, not after they walk to the door |
| X-44 | X-43 | Separated note checked on the detector and kept apart |

Most differences come down to one object at one moment (door, safe door, key, screen, bundle) or one missing step (ID check, counting).

## 2. Difficulty map (7 models × v1/v2 = 14 base runs)

| Group (videos) | Flag rate | Type correct | Runs catching it |
|---|---|---|---|
| safe_key_left (X-22) | 0.18 | 0.03 | 1/14 |
| X-44 (other) | 0.24 | 0.00 | 3/14 |
| no_client_id_check (X-2) | 0.31 | 0.22 | 4/14 |
| safe_left_open (X-20) | 0.34 | 0.12 | 3/14 |
| door on entry (X-30, 32, 33) | 0.38 | 0.30 | 11/42 |
| suspicious_note_returned (X-1) | 0.47 | 0.02 | 5/14 |
| counting_without_client (X-34) | 0.53 | 0.06 | 9/14 |
| client cash left (X-4, 38) | 0.58 | 0.29 | 17/28 |
| workstation_unlocked (X-11, 28) | 0.62 | 0.53 | 19/28 |
| seals_docs_unattended (X-24) | 0.70 | 0.08 | 13/14 |
| eating_drinking (X-46) | 0.70 | 0.69 | 9/14 |
| outsider_in_cash_room (X-18) | 0.74 | 0.37 | 10/14 |
| collector_bag_no_check (X-17) | 0.76 | 0.66 | 11/14 |
| cash_accepted_without_count (X-13) | 0.76 | 0.11 | 10/14 |
| cash_unattended (X-15, 26) | 0.86 | 0.51 | 25/28 |
| phone_or_personal_items (X-40) | 0.93 | 0.90 | 14/14 |

- Many detections carry the wrong type (X-24 70% flagged / 8% right type, X-13 76/11, X-34 53/6, X-1 47/2); in leaving scenarios `workstation_unlocked` acts as a catch-all.
- False positives on clean videos (flagged calls, all 14 runs): `workstation_unlocked` 273 (X-25, X-27, X-29, X-23), `no_client_id_check` 167 (X-37, X-3, X-19, X-35, X-5, X-16), `door_left_open` 110, `phone_or_personal_items` 46 on X-10, `eating_drinking` 34 on X-21, `counting_without_client` on X-45/X-43, `collector_bag_no_check` 32 on X-16.

## 3. Timecodes

No constant per-type offset: fitted shifts look good in-sample (v2 ±2 s 0.643 → 0.714) but leave-one-video-out they hurt in 12 of 19 runs (v2 0.643 → 0.429). Errors come from which moment is reported:

| Video / type | Median error | Why |
|---|---|---|
| X-28 laptop | +3.0 s | Model gives the door exit, organizer marks leaving the desk |
| X-26 cash left | +5.0 s | Model gives the exit, organizer marks standing up |
| X-46 drink | +1.8 s | Model gives the sip, organizer marks the cup coming out |
| X-40 personal items | −3.0 s | Model gives the bag put down, organizer marks 17 s |
| X-18 outsider | −4.0 s | Model gives the entry, organizer marks taking the second person's card |
| X-20 safe ajar | −3.8 s | Model gives the safe opening, organizer marks walking away |
| X-13 not counted | −8.0 s | Model gives the bundling, organizer marks loading the safe |

Organizer convention: missing step → start of the action where the step should have happened (X-1 22, X-2 10, X-13 47, X-17 7, X-34 13); something left behind → when the cashier turns away from the last station, between standing up and the door (X-26 9, X-28 7, X-24 8, X-15 15, X-11 18, X-22 14). Fix with prompt wording, not offsets; keep the median over repeats.

## 4. Model comparison

| Run | Majority acc | TP/FP/FN/TN | Per call | ±2 s (TP) | Type (TP) | Latency |
|---|---|---|---|---|---|---|
| 35b-a3b v1 | 0.725 | 13/3/8/16 | 0.657 | 0.385 | 0.615 | 7.8 s |
| 27b v1 | 0.700 | 13/4/8/15 | 0.650 | 0.538 | 0.769 | 14.3 s |
| 35b-a3b v2 | 0.650 | 14/7/7/12 | 0.600 | 0.643 | 0.643 | 12.3 s |
| VL-32b v1 | 0.625 | 16/10/5/9 | 0.555 | 0.188 | 0.312 | 50 s |
| VL-32b v2 | 0.600 | 18/13/3/6 | 0.616 | 0.222 | 0.500 | 72 s |

- Majority voting adds 5–7 pp over single calls.
- Vote margin is not a reliable confidence signal.
- No 2-model AND/OR beats v3b alone; spend GPU time on more v3b repeats, not a second model.
- Dropping `workstation_unlocked` removes 3 FPs but loses 4 TPs.

## 5. Experiments (qwen36-35b-a3b, T=0.6, thinking off)

| Experiment | Calls | Majority acc | TP/FP/FN/TN | Per call vs same-call v2 | ±2 s (TP) | Type (TP) |
|---|---|---|---|---|---|---|
| v2 baseline | 200 | 0.650 | 14/7/7/12 | 0.600 | 0.643 | 0.643 |
| v3b | 161 | 0.850 | 16/1/5/18 | 0.727 vs 0.578 | 0.562 | 0.625 |
| v3a | 173 | 0.725 | 14/4/7/15 | 0.671 vs 0.578 | 0.429 | 0.643 |
| 3 fps for videos < 40 s | 182 | 0.675 | 13/5/8/14 | 0.676 vs 0.582 | 0.462 | 0.615 |
| 848 px | 200 | 0.600 | 12/7/9/12 | 0.595 vs 0.600 | 0.417 | 0.667 |
| Zoom check (v1, 29 videos) | 145 | 0.552 vs 0.724 | 8/2/11/8 | 0.545 vs 0.676 | | |
| Judge, local 27b | 200 | 0.650 | 11/4/10/15 | 0.625 | 0.636 | 0.636 |

### 5a. Judge errors: was the fact in the VLM description?

15 of 17 judge-error videos go back to the VLM description: fact missing or contradicted (X-1, X-2, X-4, X-20, X-22, X-32, X-33, X-34, X-38, X-44), false fact invented (X-10, X-25, X-27, X-29), step not mentioned (X-39). Fact present but misjudged: X-13, X-17 (both missing-step cases). When a fact is spelled out (X-33 "дверь остаётся широко открытой", X-38 "деньги первого клиента на столе") every judge gets it right. Fix perception first.

## 6. Top recommendations

1. Ship v3b with 5 votes (odd, no ties).
2. Timecode wording in the v3b prompt: report the second the cashier turns away from the desk/safe to leave (not the door exit, not the safe opening); safe loading for X-13; outsider's first contact for X-18.
3. Test 3 fps for videos under 40 s with v3b.
4. Classification: list cash, seals or key left behind ahead of `workstation_unlocked`.
5. Rule grounding: find an open norm for `workstation_unlocked` or state that none was found; report X-44-style cases as observations for manual review.

Not worth the time: a second model, the zoom check, a text judge, 848 px.

## Known limitations (real examples)

- Small objects at 640 px from above: X-22 key in lock caught by 1 of 14 runs; X-20 safe ajar described as "закрывает дверцу" in 4 of 5.
- Missing steps: X-2 gets an ID check that never happened; real ID handovers on clean X-3, X-5, X-37 are missed.
- Laptop lock state from above: X-25, X-27, X-29 false positives.
- Role confusion: X-34 client described as a "second worker".
- Rare or composite events: X-1 notes handed back (right type 2%); X-44 never typed right, label itself unclear.
- Wrong type in leaving scenarios: X-15, X-24, X-26 correct verdict but `workstation_unlocked`.
- Timecode meaning differs: door exit vs leaving the desk, safe opening vs walking away, entry vs first contact.
- Drinking: X-21 sip without cash nearby still flagged.
- Robustness not measured: one camera angle in the data; new types can only come out as `other`.
