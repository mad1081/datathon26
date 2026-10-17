"""Robust JSON extraction from model output."""
from __future__ import annotations

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> dict | None:
    if not text:
        return None
    m = _FENCE.search(text)
    if m:
        text = m.group(1)
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start:i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    try:  # common fixes: trailing commas, single quotes
                        chunk2 = re.sub(r",\s*([}\]])", r"\1", chunk)
                        return json.loads(chunk2)
                    except json.JSONDecodeError:
                        return None
    return None


def _f(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def normalize_window(obj: dict | None, valid_ids: set[str], t0: float, t1: float) -> tuple[str, list[dict]]:
    if not isinstance(obj, dict):
        return "", []
    events = []
    for e in obj.get("events") or []:
        if not isinstance(e, dict):
            continue
        typ = str(e.get("type", "other")).strip()
        if typ not in valid_ids:
            typ = "other"
        conf = max(0.0, min(1.0, _f(e.get("confidence"), 0.0)))
        s = _f(e.get("start_sec"), t0)
        en = _f(e.get("end_sec"), t1)
        pk = _f(e.get("peak_sec"), s)
        clamp = lambda v: max(t0, min(t1, v))  # noqa: E731
        s, en, pk = clamp(s), clamp(en), clamp(pk)
        if en < s:
            s, en = en, s
        events.append({"type": typ, "confidence": conf, "start_sec": s, "end_sec": en,
                       "peak_sec": pk, "evidence": str(e.get("evidence", ""))[:500]})
    return str(obj.get("scene", ""))[:300], events


def normalize_verify(obj: dict | None) -> tuple[bool, float, str]:
    if not isinstance(obj, dict):
        return False, 0.0, ""
    vis = obj.get("visible")
    if isinstance(vis, str):
        vis = vis.strip().lower() in ("true", "yes", "да", "1")
    conf = max(0.0, min(1.0, _f(obj.get("confidence"), 0.0)))
    return bool(vis), conf, str(obj.get("evidence", ""))[:300]


def normalize_states(obj: dict | None, flags: tuple[str, ...]) -> dict[str, bool]:
    """Per-window scene state flags (optional in model output; missing -> False)."""
    st = obj.get("states") if isinstance(obj, dict) else None
    if not isinstance(st, dict):
        return {}
    out = {}
    for k in flags:
        v = st.get(k)
        if isinstance(v, str):
            v = v.strip().lower() in ("true", "yes", "да", "1")
        out[k] = bool(v)
    return out


def states_to_tracks(win_states: list[tuple[float, float, dict[str, bool]]], merge_gap: float = 0.5) -> list[dict]:
    """Union of window intervals where a flag is true -> [{label, start_sec, end_sec}] sorted by start."""
    by: dict[str, list[list[float]]] = {}
    for a, b, st in sorted(win_states, key=lambda x: x[0]):
        for k, v in st.items():
            if not v:
                continue
            iv = by.setdefault(k, [])
            if iv and a <= iv[-1][1] + merge_gap:
                iv[-1][1] = max(iv[-1][1], b)
            else:
                iv.append([a, b])
    tracks = [{"label": k, "start_sec": round(a, 2), "end_sec": round(b, 2)} for k, ivs in by.items() for a, b in ivs]
    return sorted(tracks, key=lambda t: (t["start_sec"], t["label"]))
