"""Extra state checks on cached pass-1 answers: safe door, client ID, notes returned, leave moment; type recovery."""
import argparse
import json
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import checks
import config
import eval_state as es
import eval_zoom
import state_checks as sc
from analyze import select_violations
from eval import list_videos, load_results
from frames import video_info
from labels import load_ground_truth

OUT = None
BASE_DIR = None  # dir with cached laptop3/desk answers

sc.QUESTIONS.update({
    "safe2": None,
    "safe": ('Для каждого кадра: дверца серого металлического сейфа плотно закрыта (вровень с корпусом) или открыта / приоткрыта (дверца отведена от корпуса, видна щель или внутренность сейфа)?',
             '{"frames": [{"t": 0.0, "safe_door": "closed|ajar|open|not_visible"}]}'),
    "idcard": ('Для каждого кадра: видна ли небольшая светлая карточка (удостоверение личности, ID-карта) в руках кассира, в руках клиента или лежащая на столе? Купюры и деньги — это не карточка.',
               '{"frames": [{"t": 0.0, "id_card": "yes|no|not_visible"}]}'),
    "notes": ('Для каждого кадра: где сейчас купюры? cashier — у кассира в руках, в счётной машине или на столе перед кассиром; client — купюры в руках клиента или на столе перед клиентом (кассир отдал их клиенту); none — купюр не видно.',
              '{"frames": [{"t": 0.0, "notes": ["cashier|client|none"]}]}'),
    "where": ('Для каждого кадра: где кассир? desk — сидит или стоит у своего стола; safe — у сейфа; leaving — отошёл от стола и сейфа, идёт к двери или у двери; gone — кассира нет в комнате.',
              '{"frames": [{"t": 0.0, "cashier": "desk|safe|leaving|gone|not_visible"}]}'),
    "desk2": ('Для каждого кадра: что лежит на столе кассира, кроме ноутбука, телефона, счётной машины и детектора? cash — деньги, купюры, пачки; bag — сумка, цветной мешок или пакет, инкассаторская сумка, кошелёк; seals — печати, штампы, пломбы, небольшие цилиндры, сейф-пакеты; documents — буклет, книжка, папка, бумаги, документы; nothing — ничего из этого.',
              '{"frames": [{"t": 0.0, "items": ["cash|bag|seals|documents|nothing"]}]}'),
})
sc.QUESTIONS["safe2"] = sc.QUESTIONS["safe"]

TAKE_FROM_SAFE = re.compile(r"(сейф[^.;]{0,60}(доста|вынима|вынул|забира|бер[её]т|взял)|(доста|вынима|вынул|забира|бер[её]т|взял)[^.;]{0,60}сейф)")
TAKE_CASH = re.compile(r"(принима|бер[её]т|забира|получа|взял)[^.;]{0,50}(пачк|купюр|деньг|наличн|банкнот)")
SAFE_OPEN = re.compile(r"сейф[^.;]{0,30}откры|откры[^.;]{0,40}сейф")
BACK_TO_DESK = re.compile(r"(сад|к столу|за стол|отход|возвращ)")
COUNT = re.compile(r"(пересч|машинк|счётн|счетн)")
CLIENT = re.compile(r"(клиент|посетител)")
LEAVE_TYPES = {"workstation_unlocked", "cash_unattended", "seals_docs_unattended", "safe_key_left", "phone_or_personal_items"}


def _r(t):
    return round(t * 2) / 2


def plan2(parsed, kept, duration):
    last = _r(max(duration - 0.3, 0.0))
    ev = checks._events(parsed or {})

    def cl(t):
        return _r(min(max(t, 0.0), last))

    reqs = []
    s = [t for t, x in ev if TAKE_FROM_SAFE.search(x)]
    if s:
        reqs.append(("safe", tuple(sorted({cl(s[0] + 4), cl(s[0] + 7)})), {"type_id": "safe_left_open", "timecode_sec": s[0] + 1}))
    n = [t for t, x in ev if COUNT.search(x)]
    if n:
        so = [t for t, x in ev if SAFE_OPEN.search(x) and t <= n[0]]
        back = [t for t, x in ev if so and so[0] < t <= n[0] and BACK_TO_DESK.search(x)]
        tc = back[0] if back else n[0]
        reqs.append(("safe2", tuple(sorted({cl(n[0] + 1), cl(n[0] + 3)})), {"type_id": "safe_left_open", "timecode_sec": tc}))
    if any(CLIENT.search(x) for _, x in ev):
        c = [t for t, x in ev if TAKE_CASH.search(x)]
        if c:
            reqs.append(("idcard", tuple(sorted({cl(c[0] - 6), cl(c[0] - 4), cl(c[0] - 2), cl(c[0])})),
                         {"type_id": "no_client_id_check", "timecode_sec": c[0]}))
        n = [t for t, x in ev if COUNT.search(x)]
        if n:
            e = n[-1]
            reqs.append(("notes", tuple(sorted({cl(e + 1), cl(e + 3), cl(e + 5), cl(e + 7)})),
                         {"type_id": "suspicious_note_returned", "timecode_sec": e + 2}))
    exits = [t for t, x in ev if checks.CASHIER_LEAVES.search(x)]
    if exits and any(v["type_id"] in LEAVE_TYPES for v in kept):
        reqs.append(("where", tuple(sorted({cl(exits[0] + d) for d in range(-8, 3)})), {"type_id": "where", "timecode_sec": exits[0]}))
    if exits:
        reqs.append(("desk2", (cl(exits[0] + 2), last), {"type_id": "desk", "timecode_sec": exits[0]}))
    only = [c for c in (config.os.getenv("STATE_CHECKS2") or "").split(",") if c]
    return [r for r in reqs if not only or r[0] in only]


def rpath(d, key, check, times):
    return d / key / f"{check}_{'_'.join(f'{t:.1f}' for t in times)}.json"


def answer(d, key, check, times):
    p = rpath(d, key, check, times)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def decide2(check, rec, times):
    ans = [a for a in rec["answers"] if a]
    n = len(times)
    if check in ("safe", "safe2"):
        st = sc.per_frame_majority(ans, "safe_door", n)
        return all(x in ("ajar", "open") for x in st), st
    if check == "idcard":
        st = sc.per_frame_majority(ans, "id_card", n)
        return not any(x == "yes" for x in st), st
    if check == "notes":
        conv = [{"frames": [{"items": f.get("notes")} for f in (a.get("frames") or []) if isinstance(f, dict)]} for a in ans]
        per = [sorted(sc.items_majority(conv, j)) for j in range(n)]
        return any("client" in p for p in per), per
    if check == "where":
        return True, sc.per_frame_majority(ans, "cashier", n)
    if check == "desk2":
        items = sc.items_majority(ans, 1)
        return bool(items), sorted(items)
    raise ValueError(check)


def leave_tc(times, st, mode):
    """First second the cashier is away from the desk ('notdesk') or leaving / gone ('leaving');
    'last': start of the final run of leaving / gone frames."""
    if mode == "last":
        start = None
        for t, s in zip(times, st):
            if s in ("leaving", "gone"):
                start = t if start is None else start
            elif s != "not_visible":
                start = None
        return start
    bad = {"desk"} if mode == "notdesk" else {"desk", "safe"}
    for t, s in zip(times, st):
        if s not in bad and s != "not_visible":
            return t
    return None


def _add_desk(out, items, v):
    add = set()
    if "cash" in items or "bag" in items:
        add.add("cash_unattended")
    if "seals" in items or "documents" in items:
        add.add("seals_docs_unattended")
    for t in add:
        if not any(x["type_id"] == t for x in out):
            out.append({"type_id": t, "timecode_sec": v["timecode_sec"], "confidence": 0.9})


def make_kept_after(durations, variant_flags):
    def kept_after(name, key, k, parsed, variant, sub_min):
        flags = variant_flags[variant]
        kept, _ = select_violations(parsed)
        out = list(kept)
        lat, n = 0.0, 0
        dur = durations[key]
        dropped_ws = None
        es.OUT = BASE_DIR
        for check, times, v in es.plan(parsed, kept, dur):
            if check not in ("laptop3", "desk") or (check == "desk" and "desk2" in flags):
                continue
            rec = es.answer(key, check, times)
            if rec is None:
                continue
            lat += max(rec["latencies"] or [0.0]); n += 1
            ok, items = es.decide(check, rec)
            if check == "desk":
                _add_desk(out, items, v)
            elif not ok:
                dropped_ws = v
                out = [x for x in out if x is not v]
        where = None
        for check, times, v in plan2(parsed, kept, dur):
            if check not in flags:
                continue
            rec = answer(OUT, key, check, times)
            if rec is None:
                continue
            ok, st = decide2(check, rec, times)
            lat += max(rec["latencies"] or [0.0]); n += 1
            if check == "where":
                where = (times, st)
            elif check == "desk2":
                _add_desk(out, st, v)
            elif ok and not any(x["type_id"] == v["type_id"] for x in out):
                out.append({"type_id": v["type_id"], "timecode_sec": v["timecode_sec"], "confidence": 0.9})
        if "prefer" in flags and any(x["type_id"] in ("cash_unattended", "seals_docs_unattended") for x in out):
            out = [x for x in out if x["type_id"] != "workstation_unlocked"]
        if "replace" in flags and dropped_ws is not None and not out:
            ev = " ".join(x for t, x in checks._events(parsed or {}) if t >= dropped_ws["timecode_sec"] - 5)
            if re.search(r"(наличн|купюр|пачк|деньг)[^.;]{0,40}(на стол|без присмотр|оставл)", ev):
                out.append({"type_id": "cash_unattended", "timecode_sec": dropped_ws["timecode_sec"], "confidence": 0.8})
            elif re.search(r"(сумк|пломб|печат|буклет|документ)[^.;]{0,40}(на стол|без присмотр|оставл)", ev):
                out.append({"type_id": "seals_docs_unattended", "timecode_sec": dropped_ws["timecode_sec"], "confidence": 0.8})
        for mode in ("notdesk", "leaving", "last"):
            if mode in flags and where is not None:
                t = leave_tc(where[0], where[1], mode)
                if t is not None:
                    out = [dict(x, timecode_sec=t) if x["type_id"] in LEAVE_TYPES else x for x in out]
        out.sort(key=lambda x: x["timecode_sec"])
        return out, lat, n
    return kept_after


VARIANTS = {
    "l3desk": set(),
    "l3desk+prefer": {"prefer"},
    "l3desk+replace": {"replace"},
    "l3desk+prefer+replace": {"prefer", "replace"},
    "l3+desk2": {"desk2"},
    "l3+desk2+prefer": {"desk2", "prefer"},
    "l3desk+safe": {"safe"},
    "l3desk+safe2": {"safe2"},
    "l3desk+safe+safe2": {"safe", "safe2"},
    "l3desk+idcard": {"idcard"},
    "l3desk+notes": {"notes"},
    "l3desk+tc_notdesk": {"where", "notdesk"},
    "l3desk+tc_leaving": {"where", "leaving"},
    "l3desk+tc_last": {"where", "last"},
    "SHIP: l3+desk2+safe2": {"desk2", "safe2"},
    "SHIP+tc_last": {"desk2", "safe2", "where", "last"},
}


def main():
    global OUT, BASE_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="exp-st2")
    ap.add_argument("--base", default="exp-in-state")
    ap.add_argument("--pass1", default="exp-v3b")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--score-only", action="store_true")
    ap.add_argument("--variants", default="")
    args = ap.parse_args()
    OUT = config.RUNS_DIR / args.name
    BASE_DIR = config.RUNS_DIR / args.base
    OUT.mkdir(parents=True, exist_ok=True)
    videos = {config.video_key(v.name): v for v in list_videos()}
    gt = load_ground_truth()
    results = load_results(args.pass1, list(videos.values()), args.repeats)
    durations = {k: video_info(v)["duration_sec"] for k, v in videos.items()}

    todo = {}
    for key, reps in results.items():
        for k, raw in reps.items():
            kept, _ = select_violations(raw.get("parsed"))
            for check, times, _ in plan2(raw.get("parsed"), kept, durations[key]):
                if not rpath(OUT, key, check, times).exists():
                    todo[(key, check, times)] = True
    print(f"{len(todo)} state requests x {sc.N_VOTES} votes", flush=True)
    if not args.score_only and todo:
        lock = threading.Lock()
        t0 = time.time()

        def work(item):
            key, check, times = item
            frames = sc.load_frames(videos[key], times)
            answers, lats = [], []
            for _ in range(sc.N_VOTES):
                res = sc.ask(check, frames)
                answers.append(res["parsed"]); lats.append(res["latency_sec"])
            rec = {"check": check, "times": list(times), "answers": answers, "latencies": lats}
            p = rpath(OUT, key, check, times)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            ok, st = decide2(check, rec, times)
            with lock:
                print(f"  {key} {check} {times} -> {st} {ok} {max(lats):.1f}s ({time.time() - t0:.0f}s)", flush=True)

        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            for f in [ex.submit(work, it) for it in todo]:
                try:
                    f.result()
                except Exception as e:
                    print(f"  crashed: {type(e).__name__}: {e}", flush=True)

    eval_zoom.kept_after = make_kept_after(durations, VARIANTS)
    _, ref_pv, _, _, _ = eval_zoom.score(args.name, results, gt, args.repeats, "l3desk", None)
    sel = [v for v in args.variants.split(",") if v] or list(VARIANTS)
    for var in sel:
        maj, pv, rep_acc, lats, calls = eval_zoom.score(args.name, results, gt, args.repeats, var, None)
        print(f"{var:22s} acc={maj['accuracy']} TP/FP/FN/TN={maj['tp']}/{maj['fp']}/{maj['fn']}/{maj['tn']} "
              f"prec={maj['precision']} tc2={maj['tc_hit2_of_tp']} tc3={maj['tc_hit3_of_tp']} "
              f"type={maj['type_hit_of_tp']} rep_acc={rep_acc} | lat/video={statistics.mean(lats):.1f}s "
              f"calls/video={statistics.mean(calls):.2f}")
        for b, z in zip(ref_pv, pv):
            if b["votes"] != z["votes"] or b["type"] != z["type"] or b["tc"] != z["tc"]:
                print(f"    {z['video']:5s} gt={'V' if z['gt'] else '-'} {z['gt_types']}@{z['gt_sec']}  ref {b['votes']} "
                      f"{b['type']}@{b['tc']} -> {z['votes']} {z['type']}@{z['tc']} {'OK' if z['correct'] else 'BAD'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
