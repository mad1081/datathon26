"""Targeted object-state checks on a few full-resolution, cropped frames (door, laptop, safe key)."""
import json
from collections import Counter

import cv2
import numpy as np

import config
from client import chat
from frames import _read_indices, b64, video_info

CROP_TOP = config.env_float("STATE_CROP_TOP", 0.65)  # the room (door, safe, desk) sits in the upper part of the frame
UPSCALE = config.env_float("STATE_UPSCALE", 1.6)
N_VOTES = config.env_int("STATE_VOTES", 3)
STATE_TEMPERATURE = config.env_float("STATE_TEMPERATURE", 0.6)

SYSTEM = """Ты смотришь на кадры камеры видеонаблюдения в кассовой комнате банка (вид сверху). В комнате: стол кассира с ноутбуком и счётной машиной, серый металлический сейф с замком, стеклянная перегородка со стеклянной дверью. Отвечай только о состоянии указанного предмета на каждом кадре, по тому, что действительно видно. Если предмет не виден или закрыт человеком — "not_visible". Ответ — только один JSON-объект без markdown."""

QUESTIONS = {
    "door": ('Для каждого кадра: дверь в кассовую комнату (стеклянная дверь в перегородке) закрыта или открыта (есть щель или проём между дверью и рамой)?',
             '{"frames": [{"t": 0.0, "door": "open|closed|not_visible"}]}'),
    "laptop": ('Для каждого кадра: что сейчас на экране ноутбука, стоящего на столе: таблица или рабочая программа, экран блокировки, тёмный экран, или крышка закрыта?',
               '{"frames": [{"t": 0.0, "screen": "table_or_program|lock_screen|dark|lid_closed|not_visible"}]}'),
    "laptop2": ('Для каждого кадра: экран ноутбука сейчас светлый (белый, рабочая программа) или тёмный/чёрный, или крышка закрыта?',
                '{"frames": [{"t": 0.0, "screen": "bright|dark|lid_closed|not_visible"}]}'),
    "laptop3": ('Для каждого кадра: что на экране ноутбука, стоящего на столе? white — белый экран с таблицей или документом (рабочая программа); picture — цветная картинка или синий фон (экран блокировки / заставка); dark — тёмный или чёрный экран; lid_closed — крышка закрыта.',
                '{"frames": [{"t": 0.0, "screen": "white|picture|dark|lid_closed|not_visible"}]}'),
    "desk": ('Для каждого кадра: что лежит на столе кассира, кроме ноутбука, телефона, счётной машины и детектора? cash — деньги, купюры, пачки; seals — печати, штампы, пломбы, небольшие цилиндры; documents — буклет, бумаги, документы; bag — сумка; nothing — ничего из этого.',
             '{"frames": [{"t": 0.0, "items": ["cash|seals|documents|bag|nothing"]}]}'),
    "key": ('Для каждого кадра: торчит ли ключ (или связка ключей) из замка сейфа?',
            '{"frames": [{"t": 0.0, "key_in_lock": "yes|no|not_visible"}]}'),
}


def _crop(img):
    h, w = img.shape[:2]
    img = img[: int(h * CROP_TOP)]
    if UPSCALE > 1.0:
        img = cv2.resize(img, (round(img.shape[1] * UPSCALE), round(img.shape[0] * UPSCALE)),
                         interpolation=cv2.INTER_CUBIC)
    return img


def load_frames(path, times):
    info = video_info(path)
    vfps, n = info["fps"], max(info["frame_count"], 1)
    idx = {t: min(max(int(round(t * vfps)), 0), n - 1) for t in times}
    raw = _read_indices(path, idx.values(), 10_000, 95)
    out = []
    for t, i in idx.items():
        if i not in raw:
            continue
        img = cv2.imdecode(np.frombuffer(raw[i], np.uint8), cv2.IMREAD_COLOR)
        ok, buf = cv2.imencode(".jpg", _crop(img), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        out.append({"t": round(i / vfps, 1), "jpeg": buf.tobytes()})
    return out


def ask(check, frames):
    q, fmt = QUESTIONS[check]
    content = []
    for f in frames:
        content.append({"type": "text", "text": f"[t={f['t']:.1f} с]"})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64(f["jpeg"])}})
    content.append({"type": "text", "text": f"{q}\nФормат ответа: {fmt}"})
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    return chat(msgs, temperature=STATE_TEMPERATURE, max_tokens=300)


def per_frame_majority(answers, field, n_frames):
    """answers: list of parsed dicts. Returns list (per frame position) of majority value."""
    out = []
    for j in range(n_frames):
        vals = []
        for a in answers:
            fr = (a or {}).get("frames") or []
            if j < len(fr) and isinstance(fr[j], dict):
                vals.append(str(fr[j].get(field, "not_visible")).strip().lower())
        out.append(Counter(vals).most_common(1)[0][0] if vals else "not_visible")
    return out


def items_majority(answers, frame_pos):
    from collections import Counter as C
    cnt, n = C(), 0
    for a in answers:
        fr = (a or {}).get("frames") or []
        if frame_pos < len(fr) and isinstance(fr[frame_pos], dict):
            n += 1
            items = fr[frame_pos].get("items") or []
            if isinstance(items, str):
                items = [items]
            cnt.update({str(i).strip().lower() for i in items})
    return {i for i, c in cnt.items() if n and c * 2 > n and i != "nothing"}
