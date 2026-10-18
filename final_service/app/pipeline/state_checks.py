"""Targeted object-state checks after the whole-video call.

One factual question about one object at one moment, asked on a few full-resolution cropped frames with
several votes. The question is about the object's state, never "is this a violation":
- laptop: what is on the screen when the cashier gets up; workstation_unlocked stays only for a white
  working screen;
- desk: what is left on the desk after the cashier has left; adds cash/seals left unattended;
- safe: whether the safe door is shut 1 and 3 s after counting starts; adds safe_left_open only if both
  frames show it ajar/open.
"""
from __future__ import annotations

import logging
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from . import checks
from .frames import b64, read_indices
from .vlm import extract_json

log = logging.getLogger("state_checks")

SYSTEM = """Ты смотришь на кадры камеры видеонаблюдения в кассовой комнате банка (вид сверху). В комнате: стол кассира с ноутбуком и счётной машиной, серый металлический сейф с замком, стеклянная перегородка со стеклянной дверью. Отвечай только о состоянии указанного предмета на каждом кадре, по тому, что действительно видно. Если предмет не виден или закрыт человеком — "not_visible". Ответ — только один JSON-объект без markdown."""

QUESTIONS = {
    "laptop": ('Для каждого кадра: что на экране ноутбука, стоящего на столе? white — белый экран с таблицей или документом (рабочая программа); picture — цветная картинка или синий фон (экран блокировки / заставка); dark — тёмный или чёрный экран; lid_closed — крышка закрыта.',
               '{"frames": [{"t": 0.0, "screen": "white|picture|dark|lid_closed|not_visible"}]}'),
    "desk": ('Для каждого кадра: что лежит на столе кассира, кроме ноутбука, телефона, счётной машины и детектора? cash — деньги, купюры, пачки; bag — сумка, цветной мешок или пакет, инкассаторская сумка, кошелёк; seals — печати, штампы, пломбы, небольшие цилиндры, сейф-пакеты; documents — буклет, книжка, папка, бумаги, документы; nothing — ничего из этого.',
             '{"frames": [{"t": 0.0, "items": ["cash|bag|seals|documents|nothing"]}]}'),
    "safe": ('Для каждого кадра: дверца серого металлического сейфа плотно закрыта (вровень с корпусом) или открыта / приоткрыта (дверца отведена от корпуса, видна щель или внутренность сейфа)?',
             '{"frames": [{"t": 0.0, "safe_door": "closed|ajar|open|not_visible"}]}'),
}

SCREEN_RU = {"white": "рабочая программа на экране", "picture": "экран блокировки", "dark": "тёмный экран",
             "lid_closed": "крышка закрыта"}
ITEMS_RU = {"cash": "наличные", "seals": "пломбы/штампы", "documents": "документы", "bag": "сумка"}


COUNTING = re.compile(r"(пересч|машинк|счётн|счетн)")
SAFE_OPENED = re.compile(r"(сейф[^.;]{0,30}откры|откры[^.;]{0,40}сейф)")
BACK_TO_DESK = re.compile(r"(сад|к столу|за стол|отход|возвращ)")


def _r(t: float) -> float:
    return round(t * 2) / 2


def _per_frame(answers, field, n_frames):
    out = []
    for j in range(n_frames):
        vals = []
        for a in answers:
            fr = (a or {}).get("frames") or []
            if j < len(fr) and isinstance(fr[j], dict):
                vals.append(str(fr[j].get(field, "not_visible")).strip().lower())
        out.append(Counter(vals).most_common(1)[0][0] if vals else "not_visible")
    return out


def _items(answers, pos):
    cnt, n = Counter(), 0
    for a in answers:
        fr = (a or {}).get("frames") or []
        if pos < len(fr) and isinstance(fr[pos], dict):
            n += 1
            items = fr[pos].get("items") or []
            if isinstance(items, str):
                items = [items]
            cnt.update({str(i).strip().lower() for i in items})
    return {i for i, c in cnt.items() if n and c * 2 > n and i in ITEMS_RU}


class StateChecker:
    def __init__(self, settings, client):
        self.s = settings
        self.client = client

    def _frames(self, path, info, times):
        vfps, n = info["fps"], max(info["frame_count"], 1)
        idx = [min(max(int(round(t * vfps)), 0), n - 1) for t in times]
        raw = read_indices(path, idx, 10_000, 95)
        out = []
        for i in idx:
            if i not in raw:
                continue
            img = cv2.imdecode(np.frombuffer(raw[i], np.uint8), cv2.IMREAD_COLOR)
            h = img.shape[0]
            img = img[: int(h * self.s.state_crop_top)]
            if self.s.state_upscale > 1.0:
                img = cv2.resize(img, (round(img.shape[1] * self.s.state_upscale),
                                       round(img.shape[0] * self.s.state_upscale)), interpolation=cv2.INTER_CUBIC)
            ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if ok:
                out.append({"t": round(i / vfps, 1), "jpeg": buf.tobytes()})
        return out

    def _ask(self, check, frames, deadline, seed):
        q, fmt = QUESTIONS[check]
        content = []
        for f in frames:
            content.append({"type": "text", "text": f"[t={f['t']:.1f} с]"})
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64(f["jpeg"])}})
        content.append({"type": "text", "text": f"{q}\nФормат ответа: {fmt}"})
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
        try:
            return extract_json(self.client.chat(msgs, self.s.state_temperature, deadline, seed))
        except Exception as e:  # noqa: BLE001  a failed check never changes the verdict
            log.warning("state check %s failed: %s", check, str(e)[:200])
            return None

    def _run(self, check, frames, deadline):
        with ThreadPoolExecutor(max_workers=self.s.state_votes) as ex:
            futs = [ex.submit(self._ask, check, frames, deadline, f"{check}:{i}") for i in range(self.s.state_votes)]
            return [a for a in (f.result() for f in futs) if a]

    def apply(self, path, info, duration, kept, obs, parsed_list, deadline):
        """Return (kept, obs, notes) after the laptop and desk checks."""
        enabled = set(self.s.state_checks)
        if not enabled or deadline - time.time() < 30:
            return kept, obs, []
        last = _r(max(duration - 0.3, 0.0))
        jobs = []
        if "laptop" in enabled:
            for v in kept:
                if v["type_id"] == "workstation_unlocked":
                    tc = v["timecode_sec"]
                    jobs.append(("laptop", (_r(max(tc - 3, 0.0)), _r(min(tc + 1, last)), last), v))
        if "desk" in enabled:
            exits = []
            for p in parsed_list:
                exits = [t for t, text in checks._events(p or {}) if checks.CASHIER_LEAVES.search(text)]
                if exits:
                    break
            if exits:
                jobs.append(("desk", (_r(min(exits[0] + 2, last)), last), {"timecode_sec": exits[0]}))
        if "safe" in enabled and not any(x["type_id"] == "safe_left_open" for x in kept):
            for p in parsed_list:
                events = checks._events(p or {})
                counting = [t for t, text in events if COUNTING.search(text)]
                if not counting:
                    continue
                t0 = counting[0]
                opened = [t for t, text in events if t <= t0 and SAFE_OPENED.search(text)]
                tc = t0
                if opened:
                    back = [t for t, text in events if opened[0] < t <= t0 and BACK_TO_DESK.search(text)]
                    tc = back[0] if back else t0
                jobs.append(("safe", (_r(min(t0 + 1, last)), _r(min(t0 + 3, last))), {"timecode_sec": tc}))
                break
        if not jobs:
            return kept, obs, []

        def work(job):
            check, times, _ = job
            frames = self._frames(path, info, times)
            return self._run(check, frames, deadline) if frames else []

        with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            answers = list(ex.map(work, jobs))

        kept, obs, notes = list(kept), list(obs), []
        for (check, times, v), ans in zip(jobs, answers):
            if not ans:
                continue
            if check == "laptop":
                scr = _per_frame(ans, "screen", len(times))
                state = scr[1] if len(scr) > 1 and scr[1] != "not_visible" else scr[-1]
                notes.append({"check": "laptop", "times": list(times), "screen": scr})
                if state in ("picture", "dark", "lid_closed"):
                    kept = [x for x in kept if x is not v]
                    obs.append(dict(v, reason_not_counted=f"проверка экрана в момент ухода: {SCREEN_RU[state]}"))
            elif check == "safe":
                st = _per_frame(ans, "safe_door", len(times))
                notes.append({"check": "safe", "times": list(times), "safe_door": st})
                if all(x in ("ajar", "open") for x in st):
                    kept.append({"type_id": "safe_left_open", "timecode_sec": v["timecode_sec"], "confidence": 0.9,
                                 "observed": "дверца сейфа не закрыта плотно, пока кассир работает за столом"})
            else:
                items = _items(ans, len(times) - 1)
                notes.append({"check": "desk", "times": list(times), "items": sorted(items)})
                add = []
                if items & {"cash", "bag"}:
                    add.append("cash_unattended")
                if items & {"seals", "documents"}:
                    add.append("seals_docs_unattended")
                seen = ", ".join(ITEMS_RU[i] for i in sorted(items))
                for tid in add:
                    if not any(x["type_id"] == tid for x in kept):
                        kept.append({"type_id": tid, "timecode_sec": v["timecode_sec"], "confidence": 0.9,
                                     "observed": f"после ухода кассира на столе остаются: {seen}"})
        kept.sort(key=lambda x: x["timecode_sec"])
        return kept, obs, notes
