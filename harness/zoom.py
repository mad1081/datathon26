"""Second pass: verify each candidate violation on a short high-fps, native-resolution window."""
import json
import time

import config
from client import chat
from frames import _read_indices, b64, video_info

ZOOM_FPS = config.env_float("ZOOM_FPS", 8.0)
ZOOM_HALF = config.env_float("ZOOM_HALF_SEC", 3.0)
ZOOM_MAX_SIDE = config.env_int("ZOOM_MAX_SIDE", 848)
ZOOM_TEMPERATURE = config.env_float("ZOOM_TEMPERATURE", 0.0)
# lenient: reject only on clear visual counter-evidence
ZOOM_LENIENT = config.env_bool("ZOOM_LENIENT", False)

LENIENT_RULES = """Правила проверки:
- По умолчанию confirmed = true: первичный анализ видел всё видео, а ты — только фрагмент.
- confirmed = false только если на кадрах фрагмента ЯВНО видно, что нарушения нет: правильное действие выполнено (например, сейф закрыт, ноутбук закрыт, деньги убраны, дверь закрыта) или ситуация подпадает под ограничения.
- timecode_sec — точный момент (в секундах от начала видео, по подписям [t=...]), когда нарушение впервые становится видно."""

SYSTEM = """Ты — специалист видеоконтроля соблюдения кассовой дисциплины в банке. Камера установлена сверху над рабочим местом кассира. Описывай только то, что видно на кадрах, не распознавай лица, называй людей по роли.

Первичный анализ всего видео (низкое разрешение, редкие кадры) предположил одно нарушение. Тебе показывают короткий фрагмент вокруг предполагаемого момента в высоком разрешении и с частыми кадрами. Задача — проверить именно это нарушение.

Тип нарушения: {name} ({tid}).
Признаки: {criteria}
Не является нарушением / ограничения: {negatives}

Правила проверки:
- confirmed = true, если признаки нарушения видны на кадрах фрагмента (для упущений — обязательное действие в этом фрагменте не выполнено, хотя должно было).
- confirmed = false, если на кадрах видно, что правильное действие выполнено, ситуация подпадает под ограничения, или признаков нарушения нет.
- timecode_sec — точный момент (в секундах от начала видео, по подписям [t=...]), когда нарушение впервые становится видно.

Формат ответа — только один JSON-объект без markdown:
{{"confirmed": true, "timecode_sec": 0.0, "evidence": "что именно видно на кадрах"}}
Текст — на русском языке."""

USER = """Выше — кадры фрагмента {a:.1f}–{b:.1f} с ({fps:g} кадров/с) в хронологическом порядке.
Контекст из первичного анализа (может содержать ошибки):
- сценарий: {scenario}
- хронология: {timeline}
- предполагаемое нарушение около t={tc:.1f} с: {observed}
Подтверди или опровергни это нарушение по кадрам фрагмента. Ответь строго одним JSON-объектом."""


def window(tc, duration, half=None):
    half = ZOOM_HALF if half is None else half
    a = max(0.0, tc - half)
    b = min(max(duration - 0.05, 0.0), tc + half)
    return a, b


def window_indices(tc, info, fps=None, half=None):
    fps = fps or ZOOM_FPS
    vfps = info["fps"]
    a, b = window(tc, info["duration_sec"], half)
    step = max(1, round(vfps / fps))
    i0, i1 = int(round(a * vfps)), int(round(b * vfps))
    return list(range(i0, i1 + 1, step))


def load_window_frames(path, tcs, fps=None, half=None):
    """Decode all windows of one video in a single pass. Returns {tc: [{"t", "jpeg"}]}."""
    info = video_info(path)
    per = {tc: window_indices(tc, info, fps, half) for tc in tcs}
    union = sorted({i for idx in per.values() for i in idx})
    jpegs = _read_indices(path, union, ZOOM_MAX_SIDE, config.JPEG_QUALITY)
    vfps = info["fps"]
    return {tc: [{"t": round(i / vfps, 2), "jpeg": jpegs[i]} for i in idx if i in jpegs] for tc, idx in per.items()}, info


def _timeline_text(parsed, limit=15):
    items = []
    for e in (parsed or {}).get("timeline") or []:
        if isinstance(e, dict):
            items.append(f"{e.get('t')} с — {e.get('event')}")
    return "; ".join(items[:limit]) or "нет"


def build_messages(cand, frames, parsed):
    rule = config.rules_by_id()[cand["type_id"]]
    tmpl = SYSTEM
    if ZOOM_LENIENT:
        head, rest = SYSTEM.split("Правила проверки:", 1)
        tmpl = head + LENIENT_RULES + "\n\n" + "Формат ответа" + rest.split("Формат ответа", 1)[1]
    system = tmpl.format(name=rule["name_ru"], tid=rule["id"], criteria=rule["visual_criteria"],
                           negatives=rule["negatives"])
    content = []
    for f in frames:
        content.append({"type": "text", "text": f"[t={f['t']:.1f} с]"})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64(f["jpeg"])}})
    a, b = (frames[0]["t"], frames[-1]["t"]) if frames else (0.0, 0.0)
    content.append({"type": "text", "text": USER.format(
        a=a, b=b, fps=ZOOM_FPS, scenario=(parsed or {}).get("scenario") or "нет",
        timeline=_timeline_text(parsed), tc=cand["timecode_sec"], observed=cand.get("observed") or "нет")})
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def verify(cand, frames, parsed, temperature=None):
    temperature = ZOOM_TEMPERATURE if temperature is None else temperature
    msgs = build_messages(cand, frames, parsed)
    res = chat(msgs, temperature=temperature, max_tokens=400)
    p = res["parsed"] or {}
    confirmed = p.get("confirmed")
    if isinstance(confirmed, str):
        confirmed = confirmed.strip().lower() in ("true", "yes", "да", "1")
    try:
        tc = float(p.get("timecode_sec"))
    except (TypeError, ValueError):
        tc = None
    return {"confirmed": bool(confirmed), "timecode_sec": tc, "evidence": str(p.get("evidence") or ""),
            "latency_sec": res["latency_sec"], "error": res["error"], "usage": res.get("usage"),
            "n_frames": len(frames), "raw_text": res["text"]}
