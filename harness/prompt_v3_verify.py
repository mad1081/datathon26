"""Second VLM stage: targeted verification of first-pass candidates (and optional scenario probes).

Reads cached first-pass answers from runs/<src>, asks the VLM one focused question per
(video, violation type) on a short high-resolution window around the candidate, and writes
filtered answers to runs/<dst> so that `eval.py --name <dst> --score-only` can score them.

usage: PROMPT_MODULE=prompt_v3 python harness/prompt_v3_verify.py --src exp-v3a --dst exp-v3a-ver
"""
import argparse
import json
import re
import statistics
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from analyze import select_violations
from client import chat
from eval import list_videos
from frames import b64, frames_at_times, video_info

ROLE = """Ты — специалист видеоконтроля кассовой дисциплины в банке. Камера сверху над рабочим местом кассира: стол, ноутбук, счётная машина, сейф (серый металлический шкаф/тумба рядом со столом), стеклянная дверь кассы слева вверху, место клиента напротив кассира.
Описывай только то, что видно на кадрах. Не распознавай лица. Каждый кадр подписан временем [t=.. с] от начала видео.
Тебе задают один проверочный вопрос. Видеомодель на первом проходе часто ошибается, поэтому отвечай «да», только если это ясно видно на кадрах; если не видно или сомневаешься — «нет»."""

FORMAT = """Ответь строго одним JSON-объектом без markdown:
{"seen": "что видно на кадрах по сути вопроса, 1–2 предложения", "answer": "да" или "нет", "timecode_sec": секунда, когда это видно (или null)}"""

# type-specific question and frame window (relative to candidate second, or absolute for "start")
QUESTIONS = {
    "workstation_unlocked": ("Кассир уходит от рабочего места. Работал ли он перед этим в ноутбуке, и в момент ухода крышка ноутбука открыта и на экране видна таблица/рабочая программа (не экран блокировки, не тёмный экран, не закрытая крышка)?", -8, 5),
    "door_left_open": ("Кассир входит в кассу. Остаётся ли стеклянная дверь открытой (створка развёрнута, виден проход) через 3–5 с после того, как кассир прошёл внутрь и отошёл от двери? Если кассир закрыл дверь за собой — ответ «нет». Выход из кассы не учитывай.", "start", 10),
    "outsider_in_cash_room": ("Входит ли в кассовое помещение (или появляется в открытом дверном проёме и заходит) человек, который не является обслуживаемым клиентом, сидящим напротив кассира, и не инкассатором, передающим сумку? Либо подходит второй посетитель, пока обслуживается первый клиент?", -8, 8),
    "safe_left_open": ("После того как кассир открыл сейф и отошёл от него, дверца сейфа закрыта не полностью (видна щель, дверца выступает под углом) или открыта?", -6, 8),
    "safe_key_left": ("Кассир уходит от сейфа / из помещения. Остаётся ли ключ вставленным в замок сейфа (ключ не вынут и не забран с собой)?", -8, 5),
    "cash_unattended": ("Кассир уходит от рабочего места или помещение пустое. Остаются ли на столе, машинке или тумбе наличные деньги или сумка с ценностями (не убраны в сейф)?", -8, 6),
    "seals_docs_unattended": ("Кассир уходит. Остаются ли на столе пломбы, печати/штампы, ключи или папка/буклет с документами (не убраны в сейф)?", -8, 6),
    "foreign_cash_on_desk": ("Лежит ли на столе пачка денег предыдущего клиента (не убранная в сейф), когда подходит и начинает обслуживаться следующий клиент, или деньги двух клиентов кладутся вместе?", -12, 8),
    "no_client_id_check": ("Кассир берёт наличные у клиента. Передавал ли клиент до этого карточку/документ, удостоверяющий личность, и смотрел ли его кассир? Ответь «да», если документа НЕ было (нарушение), «нет», если документ был передан и просмотрен.", "start", 6),
    "eating_drinking": ("Есть ли на рабочем столе рядом с наличными еда или напиток (стакан, кружка, бутылка), или кассир ест/пьёт, пока на столе деньги?", -6, 6),
    "phone_or_personal_items": ("Кладёт ли кассир на рабочий стол личные вещи (сумку, куртку, телефон) или пользуется телефоном на рабочем месте?", -6, 6),
    "collector_bag_no_check": ("Инкассатор передаёт сумку. Кассир принимает её, НЕ просматривая документ инкассатора и НЕ осматривая пломбу/шов сумки? (Если кассир смотрел документ или вертел сумку, рассматривая пломбу, — ответ «нет».)", "start", 8),
    "cash_accepted_without_count": ("Убирает ли кассир наличные (из сумки или от клиента) в сейф, НЕ пересчитав их на машинке или вручную?", -12, 6),
    "counting_without_client": ("Пересчитывает ли кассир деньги клиента уже после того, как клиент ушёл (а не при клиенте)?", -8, 6),
    "suspicious_note_returned": ("После пересчёта/осмотра отделяет ли кассир часть купюр и возвращает их клиенту (кладёт перед клиентом, клиент забирает)?", -8, 6),
}


def generic_question(rule):
    return (f"Видно ли на кадрах нарушение «{rule['name_ru']}»? Признаки: {rule['visual_criteria']} "
            f"Не является нарушением: {rule['negatives']}")


def window_times(tc, spec, duration, step=1.0, max_frames=22):
    lo_spec, hi = spec
    lo = 0.0 if lo_spec == "start" else tc + lo_spec
    hi = tc + hi
    lo, hi = max(0.0, lo), min(duration - 0.1, hi)
    if hi <= lo:
        lo, hi = max(0.0, tc - 5), min(duration - 0.1, tc + 5)
    n = int((hi - lo) / step) + 1
    if n > max_frames:
        step = (hi - lo) / (max_frames - 1)
        n = max_frames
    return [round(lo + i * step, 2) for i in range(n)]


def ask(video, tid, tc, temperature, max_side):
    rules = config.rules_by_id()
    q, lo, hi = QUESTIONS.get(tid, (generic_question(rules[tid]), -8, 6))
    duration = video_info(video)["duration_sec"]
    frames = frames_at_times(video, window_times(tc, (lo, hi), duration), max_side=max_side, quality=85)
    content = []
    for f in frames:
        content.append({"type": "text", "text": f"[t={f['timestamp_sec']:.1f} с]"})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64(f["jpeg"])}})
    content.append({"type": "text", "text": f"Вопрос: {q}\n{FORMAT}"})
    res = chat([{"role": "system", "content": ROLE}, {"role": "user", "content": content}],
               temperature=temperature, max_tokens=400)
    p = res.get("parsed") or {}
    ans = str(p.get("answer", "")).strip().lower()
    tcv = p.get("timecode_sec")
    try:
        tcv = float(tcv) if tcv is not None else None
    except (TypeError, ValueError):
        tcv = None
    return {"yes": ans.startswith("да"), "tc": tcv, "seen": p.get("seen"), "latency": res.get("latency_sec"),
            "error": res.get("error"), "n_frames": len(frames)}


ENTRY_RE = re.compile(r"кассир\w*[^.;]{0,30}(вход|вош|заход)|(вход|вош|заход)\w*[^.;]{0,30}кассир")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--votes", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-side", type=int, default=960)
    ap.add_argument("--retime", action="store_true", help="replace timecodes of confirmed types by verified median")
    ap.add_argument("--probe-entry", action="store_true", help="ask the door question when the first pass saw the cashier enter")
    args = ap.parse_args()

    src, dst = config.RUNS_DIR / args.src, config.RUNS_DIR / args.dst
    videos = list_videos()
    raws = {}
    for v in videos:
        key = config.video_key(v.name)
        raws[key] = {k: json.loads((src / key / f"r{k}.json").read_text(encoding="utf-8"))
                     for k in range(args.repeats) if (src / key / f"r{k}.json").exists()}

    # candidates: (video, type) -> list of first-pass timecodes (kept after checks + thresholds)
    cands = defaultdict(list)
    vid_of = {config.video_key(v.name): v for v in videos}
    for key, reps in raws.items():
        entry_votes = 0
        for k, raw in reps.items():
            kept, _ = select_violations(raw.get("parsed"))
            for x in kept:
                cands[(key, x["type_id"])].append(x["timecode_sec"])
            tl = " ".join(str(e.get("event", "")).lower() for e in ((raw.get("parsed") or {}).get("timeline") or [])
                          if isinstance(e, dict) and float(e.get("t") or 0) <= 12)
            entry_votes += bool(ENTRY_RE.search(tl))
        if args.probe_entry and entry_votes * 2 > len(reps) and (key, "door_left_open") not in cands:
            cands[(key, "door_left_open")] = []  # probe: no first-pass candidate

    jobs = [(key, tid, statistics.median(tcs) if tcs else 3.0, j)
            for (key, tid), tcs in cands.items() for j in range(args.votes)]
    print(f"{len(cands)} candidates, {len(jobs)} verification calls", flush=True)
    answers = defaultdict(list)
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(ask, vid_of[key], tid, tc, args.temperature, args.max_side): (key, tid) for key, tid, tc, _ in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            key, tid = futs[fut]
            try:
                a = fut.result()
            except Exception as e:
                a = {"yes": False, "tc": None, "seen": None, "error": repr(e), "latency": None}
            with lock:
                answers[(key, tid)].append(a)
            if i % 20 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    decisions = {}
    for c, ans in answers.items():
        valid = [a for a in ans if not a.get("error")]
        yes = sum(a["yes"] for a in valid)
        tcs = [a["tc"] for a in valid if a["yes"] and a["tc"] is not None]
        decisions[c] = {"confirmed": yes * 2 > len(valid) if valid else True, "yes": yes, "n": len(valid),
                        "tc": statistics.median(tcs) if tcs else None, "probe": not cands[c],
                        "seen": [a.get("seen") for a in valid]}

    for key, reps in raws.items():
        for k, raw in reps.items():
            raw = json.loads(json.dumps(raw))
            p = raw.get("parsed")
            if isinstance(p, dict):
                out = []
                for v in p.get("violations") or []:
                    if not isinstance(v, dict):
                        continue
                    d = decisions.get((key, str(v.get("type_id"))))
                    if d is None:
                        out.append(v)  # not in verdict set / below threshold: leave as is
                        continue
                    if not d["confirmed"]:
                        continue
                    if args.retime and d["tc"] is not None:
                        v["timecode_sec"] = d["tc"]
                    out.append(v)
                d = decisions.get((key, "door_left_open"))
                if d and d["probe"] and d["confirmed"]:
                    out.append({"type_id": "door_left_open", "timecode_sec": d["tc"] or 5.0, "confidence": 0.8,
                                "observed": "проверочный вопрос: дверь осталась открытой после входа"})
                p["violations"] = out
            raw["verification"] = {f"{t}": d for (kk, t), d in decisions.items() if kk == key}
            path = dst / key / f"r{k}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")

    lat = [a["latency"] for ans in answers.values() for a in ans if a.get("latency")]
    print(f"verification latency mean={statistics.mean(lat):.1f}s, calls={len(lat)}" if lat else "no calls")
    for (key, tid), d in sorted(decisions.items()):
        print(f"  {key:6s} {tid:26s} {'KEEP' if d['confirmed'] else 'DROP'} {d['yes']}/{d['n']} tc={d['tc']}"
              f"{' PROBE' if d['probe'] else ''}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
