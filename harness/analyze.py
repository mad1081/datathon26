import re
import sys
import time
from pathlib import Path

import config
from client import chat
from frames import b64, frames_at_times, sample_frames
from prompt import build_messages


def analyze_raw(video_path, temperature=None, repeat=0):
    """Run the VLM on one video and return the raw (unfiltered) result."""
    video_path = Path(video_path)
    t0 = time.time()
    frames = sample_frames(video_path)
    t_frames = time.time() - t0
    messages = build_messages(frames)
    res = chat(messages, temperature=temperature, mock_seed=f"{config.video_key(video_path.name)}:{repeat}")
    return {
        "video": video_path.name,
        "key": config.video_key(video_path.name),
        "repeat": repeat,
        "model": config.VLM_MODEL,
        "params": {"fps": config.FPS, "max_frames": config.MAX_FRAMES, "max_side": config.MAX_SIDE,
                   "temperature": config.TEMPERATURE if temperature is None else temperature,
                   "disable_thinking": config.DISABLE_THINKING},
        "n_frames": len(frames),
        "frames_sec": round(t_frames, 3),
        "latency_sec": res["latency_sec"],
        "attempts": res["attempts"],
        "error": res["error"],
        "usage": res.get("usage"),
        "raw_text": res["text"],
        "parsed": res["parsed"],
    }


def _to_float(v, default=None):
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    m = re.match(r"^(\d+):(\d+(?:\.\d+)?)$", s)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else default


def verdict_types(mode=None, extra=None):
    mode = mode or config.VERDICT_MODE
    extra = config.EXTRA_VERDICT_TYPES if extra is None else extra
    rules = config.rules_by_id()
    if mode == "all":
        ids = {rid for rid in rules if rid != "other"}
    else:
        ids = {rid for rid, r in rules.items() if r.get("count_in_verdict")}
    return ids | set(extra)


def normalize_violations(parsed):
    if not isinstance(parsed, dict):
        return []
    out = []
    for v in parsed.get("violations") or []:
        if not isinstance(v, dict):
            continue
        tid = str(v.get("type_id") or v.get("type") or "").strip()
        conf = _to_float(v.get("confidence"), 0.5)
        if conf is not None and conf > 1.0:
            conf = conf / 100.0
        out.append({
            "type_id": tid,
            "timecode_sec": max(0.0, _to_float(v.get("timecode_sec"), 0.0)),
            "confidence": min(max(conf, 0.0), 1.0),
            "observed": str(v.get("observed") or "").strip(),
        })
    return out


def select_violations(parsed, offset=None, mode=None, extra=None, merge_window=None):
    """Split model violations into (verdict_violations, observations)."""
    offset = config.THRESHOLD_OFFSET if offset is None else offset
    merge_window = config.MERGE_WINDOW_SEC if merge_window is None else merge_window
    rules = config.rules_by_id()
    allowed = verdict_types(mode, extra)
    kept, obs = [], []
    for v in normalize_violations(parsed):
        rule = rules.get(v["type_id"])
        if rule is None or v["type_id"] not in allowed:
            obs.append(v)
            continue
        if v["confidence"] >= float(rule.get("threshold", 0.6)) + offset:
            kept.append(v)
        else:
            obs.append(v)
    kept.sort(key=lambda x: (x["type_id"], x["timecode_sec"]))
    merged = []
    for v in kept:
        prev = merged[-1] if merged else None
        if prev and prev["type_id"] == v["type_id"] and v["timecode_sec"] - prev["last_t"] <= merge_window:
            prev["confidence"] = max(prev["confidence"], v["confidence"])
            prev["last_t"] = v["timecode_sec"]
            if v["observed"] and v["observed"] not in prev["observed"]:
                prev["observed"] = (prev["observed"] + "; " + v["observed"]).strip("; ")
            continue
        merged.append(dict(v, last_t=v["timecode_sec"]))
    for m in merged:
        m.pop("last_t", None)
    merged.sort(key=lambda x: x["timecode_sec"])
    return merged, obs


def _mmss(t):
    t = int(round(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def describe(rule, v):
    acts = config.load_rules().get("acts", {})
    basis = "требует ручной проверки"
    cits = rule.get("citations") or []
    if cits:
        c = cits[0]
        act = acts.get(c.get("act"), {}).get("short", c.get("act", ""))
        basis = f"{act}, {c.get('clause', '')}: «{c.get('quote', '')}»"
    observed = v["observed"] or "см. кадры-доказательства"
    return f"{rule['name_ru']}. Наблюдение ({_mmss(v['timecode_sec'])}): {observed}. Основание: {basis}."


def to_contract(raw, video_path, offset=None, mode=None, extra=None, with_evidence=True):
    kept, obs = select_violations(raw.get("parsed"), offset=offset, mode=mode, extra=extra)
    rules = config.rules_by_id()
    duration = None
    out = []
    for v in kept:
        rule = rules[v["type_id"]]
        item = {
            "type": rule["name_ru"],
            "type_id": v["type_id"],
            "timecode_sec": round(v["timecode_sec"], 1),
            "confidence": v["confidence"],
            "description": describe(rule, v),
            "evidence_frames": [],
        }
        if with_evidence:
            tc = v["timecode_sec"]
            if duration is None:
                from frames import video_info
                duration = video_info(video_path)["duration_sec"]
            times = sorted({round(min(max(t, 0.0), max(duration - 0.05, 0.0)), 2) for t in (tc - 1.5, tc, tc + 1.5)})
            item["evidence_frames"] = [{"timestamp_sec": f["timestamp_sec"], "image_base64": b64(f["jpeg"])}
                                       for f in frames_at_times(video_path, times)]
        out.append(item)
    result = {"verdict": "violation" if out else "no_violation", "violations": out}
    if obs:
        result["observations"] = [{"type_id": o["type_id"], "timecode_sec": round(o["timecode_sec"], 1),
                                   "confidence": o["confidence"], "observed": o["observed"]} for o in obs]
    if raw.get("parsed") is None:
        result["error"] = raw.get("error") or "model output is not valid JSON"
    return result


def analyze(video_path, temperature=None):
    raw = analyze_raw(video_path, temperature=temperature)
    return to_contract(raw, video_path)


if __name__ == "__main__":
    import json

    res = analyze(sys.argv[1])
    for v in res["violations"]:
        for f in v["evidence_frames"]:
            f["image_base64"] = f["image_base64"][:40] + "..."
    print(json.dumps(res, ensure_ascii=False, indent=2))
