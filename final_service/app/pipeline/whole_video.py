"""Whole-video analysis: one VLM call over frames of the entire video (optionally N voted samples)."""
from __future__ import annotations

import logging
import os
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from . import checks
from .frames import b64, read_indices, sample_frames, video_info
from .prompt import build_messages
from .state_checks import StateChecker
from .vlm import VLMError, VLMRequestTooLarge, extract_json

log = logging.getLogger("whole_video")


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


def mmss(t: float) -> str:
    t = int(round(max(0.0, t)))
    return f"{t // 60:02d}:{t % 60:02d}"


def normalize_violations(parsed: dict, duration: float) -> list[dict]:
    out = []
    for v in parsed.get("violations") or []:
        if not isinstance(v, dict):
            continue
        conf = _to_float(v.get("confidence"), 0.5)
        if conf > 1.0:
            conf = conf / 100.0
        tc = max(0.0, _to_float(v.get("timecode_sec"), 0.0))
        if duration > 0:
            tc = min(tc, duration)
        # organizer labels are whole seconds
        if os.getenv("TIMECODE_WHOLE_SECONDS", "1") == "1":
            tc = float(round(tc))
        observed = str(v.get("observed") or "").strip()
        if not observed:
            # the model left the description empty: use its own timeline event closest to the timecode
            near = [(abs(_to_float(e.get("t"), 0.0) - tc), str(e.get("event") or "").strip())
                    for e in parsed.get("timeline") or [] if isinstance(e, dict) and e.get("event")]
            near = [x for x in near if x[0] <= 3]
            if near:
                observed = min(near)[1]
        out.append({
            "type_id": str(v.get("type_id") or v.get("type") or "").strip(),
            "timecode_sec": tc,
            "confidence": min(max(conf, 0.0), 1.0),
            "observed": observed,
        })
    return out


def normalize_timeline(parsed: dict) -> list[dict]:
    out = []
    for e in parsed.get("timeline") or []:
        if isinstance(e, dict) and e.get("event"):
            out.append({"t": round(_to_float(e.get("t"), 0.0), 1), "event": str(e["event"]).strip()})
    return sorted(out, key=lambda e: e["t"])


def verdict_type_ids(rb) -> set[str]:
    return {rid for rid, r in rb.rules.items() if rid != "other" and r.count_in_verdict}


def split(rb, items: list[dict], offset: float, merge_window: float,
          parsed: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Split normalized model violations into (counted, observations); merge repeats of one type."""
    allowed = verdict_type_ids(rb)
    kept, obs = [], []
    for v in items:
        rule = rb.rules.get(v["type_id"])
        contradiction = checks.contradicted(v, parsed) if parsed is not None else None
        if rule is None or v["type_id"] not in allowed:
            reason = ("тип вне перечня правил" if rule is None or v["type_id"] == "other"
                      else "тип не влияет на вердикт (только ручная проверка)")
            obs.append(dict(v, reason_not_counted=reason))
        elif contradiction:
            obs.append(dict(v, reason_not_counted="противоречит хронологии: " + contradiction))
        elif v["confidence"] >= rule.threshold + offset:
            kept.append(v)
        else:
            obs.append(dict(v, reason_not_counted="ниже порога уверенности"))
    kept.sort(key=lambda x: (x["type_id"], x["timecode_sec"]))
    merged: list[dict] = []
    for v in kept:
        prev = merged[-1] if merged else None
        if prev and prev["type_id"] == v["type_id"] and v["timecode_sec"] - prev["_last"] <= merge_window:
            prev["confidence"] = max(prev["confidence"], v["confidence"])
            prev["_last"] = v["timecode_sec"]
            if v["observed"] and v["observed"] not in prev["observed"]:
                prev["observed"] = (prev["observed"] + "; " + v["observed"]).strip("; ")
            continue
        merged.append(dict(v, _last=v["timecode_sec"]))
    for m in merged:
        m.pop("_last", None)
    merged.sort(key=lambda x: x["timecode_sec"])
    return merged, obs


def vote(samples: list[tuple[list[dict], list[dict]]]) -> tuple[list[dict], list[dict], dict]:
    """Majority vote over N samples of (counted, observations): a type survives if it is counted in a strict
    majority of samples; its timecode is the median of the per-sample first occurrences."""
    n = len(samples)
    by_type: dict[str, list[dict]] = {}
    for counted, _ in samples:
        firsts: dict[str, dict] = {}
        for v in counted:
            if v["type_id"] not in firsts:
                firsts[v["type_id"]] = v
        for tid, v in firsts.items():
            by_type.setdefault(tid, []).append(v)
    votes = {tid: len(vs) for tid, vs in by_type.items()}
    n_violation = sum(1 for counted, _ in samples if counted)
    winners = [tid for tid, c in votes.items() if c * 2 > n]
    if n_violation * 2 > n and not winners and votes:
        best = max(votes.values())
        winners = [tid for tid, c in votes.items() if c == best]
    elif n_violation * 2 <= n:
        winners = []
    kept, obs = [], []
    for tid, vs in by_type.items():
        med = statistics.median(v["timecode_sec"] for v in vs)
        rep = min(vs, key=lambda v: abs(v["timecode_sec"] - med))
        item = {"type_id": tid, "timecode_sec": med,
                "confidence": round(sum(v["confidence"] for v in vs) / n, 3),
                "observed": rep["observed"], "votes": f"{len(vs)}/{n}"}
        if tid in winners:
            kept.append(item)
        else:
            obs.append(dict(item, reason_not_counted=f"не подтверждено большинством прогонов ({len(vs)}/{n})"))
    for _, o in samples[0:1]:
        obs.extend(o)
    kept.sort(key=lambda x: x["timecode_sec"])
    return kept, obs, {"samples": n, "samples_with_violation": n_violation, "votes": votes}


class WholeVideoAnalyzer:
    def __init__(self, settings, rulebook, client):
        self.s = settings
        self.rb = rulebook
        self.client = client
        self.state = StateChecker(settings, client)

    def _sample(self, messages, temperature: float, deadline: float, seed: str) -> dict:
        """One model answer; a JSON parse failure is retried once at temperature 0."""
        text = self.client.chat(messages, temperature, deadline, seed)
        parsed = extract_json(text)
        if parsed is None:
            log.warning("unparsable model output (%d chars), retrying at temperature 0", len(text or ""))
            text = self.client.chat(messages, 0.0, deadline, seed + ":retry")
            parsed = extract_json(text)
        if parsed is None:
            raise VLMError("model output is not valid JSON: " + (text or "")[:200].replace("\n", " "))
        return parsed

    def _prepare(self, path, info, max_frames):
        frames = sample_frames(path, info, self.s.fps_short, self.s.fps_long, self.s.short_video_sec,
                               max_frames, self.s.frame_max_side, self.s.jpeg_quality)
        if not frames:
            raise RuntimeError("no frames decoded from the video")
        return frames, build_messages(frames, list(self.rb.rules.values()), self.s.system_in_user, b64)

    def analyze(self, path: str, deadline: float, progress=lambda p, s: None) -> dict:
        t0 = time.time()
        info = video_info(path)
        progress(0.05, "sampling")
        frames, messages = self._prepare(path, info, self.s.max_frames)
        duration = max(info["duration_sec"], frames[-1]["t"])
        t_frames = time.time() - t0

        n = max(1, self.s.n_samples)
        left = deadline - time.time()
        warnings = []
        if n > 1 and left < self.s.min_sec_for_sampling:
            warnings.append(f"мало времени ({left:.0f} с) — один прогон модели вместо {n}")
            n = 1
        progress(0.15, "model")
        call_deadline = deadline - self.s.evidence_reserve_sec
        seed = f"{info['frame_count']}:{len(frames)}"
        if n == 1:
            try:
                parsed_list = [self._sample(messages, self.s.temperature, call_deadline, seed)]
            except VLMRequestTooLarge as e:
                fewer = max(16, int(len(frames) * 0.6))
                log.warning("%s; retrying with %d frames", e, fewer)
                warnings.append(f"запрос не поместился в контекст модели — повтор с {fewer} кадрами")
                frames, messages = self._prepare(path, info, fewer)
                parsed_list = [self._sample(messages, self.s.temperature, call_deadline, seed)]
            errors = []
        else:
            with ThreadPoolExecutor(max_workers=n) as ex:
                futs = [ex.submit(self._sample, messages, self.s.sample_temperature, call_deadline, f"{seed}:{i}")
                        for i in range(n)]
                parsed_list, errors = [], []
                for f in futs:
                    try:
                        parsed_list.append(f.result())
                    except Exception as e:  # noqa: BLE001
                        errors.append(str(e)[:200])
            if not parsed_list:
                raise VLMError("all model samples failed: " + errors[0])
            if errors:
                warnings.append(f"неуспешных прогонов модели: {len(errors)} из {n}")
        t_model = time.time() - t0 - t_frames

        samples = [split(self.rb, normalize_violations(p, duration), self.s.threshold_offset,
                         self.s.merge_window_sec, parsed=p) for p in parsed_list]
        if len(samples) == 1:
            kept, obs = samples[0]
            voting = None
        else:
            kept, obs, voting = vote(samples)
        progress(0.75, "state checks")
        kept, obs, state_notes = self.state.apply(path, info, duration, kept, obs, parsed_list, call_deadline)
        if len(kept) > self.s.max_violations:
            kept.sort(key=lambda v: -v["confidence"])
            obs = [dict(v, reason_not_counted="сверх лимита числа нарушений") for v in kept[self.s.max_violations:]] + obs
            kept = sorted(kept[: self.s.max_violations], key=lambda v: v["timecode_sec"])
        obs = sorted(obs, key=lambda v: -v["confidence"])[: self.s.max_observations]

        progress(0.85, "evidence")
        violations, observations = self._render(path, info, kept, obs)
        main = parsed_list[0]
        return {
            "verdict": "violation" if violations else "no_violation",
            "violations": violations,
            "observations": observations,
            "scenario": str(main.get("scenario") or "").strip(),
            "timeline": normalize_timeline(main),
            "meta": {
                "model": self.client.name,
                "duration_sec": round(duration, 2), "fps": round(info["fps"], 3),
                "frames_sampled": len(frames), "samples": len(parsed_list),
                "voting": voting, "warnings": warnings,
                "frames_sec": round(t_frames, 2), "model_sec": round(t_model, 2),
                "state_checks": state_notes,
            },
        }

    # ---------------------------------------------------------------- output
    def _render(self, path, info, kept, obs):
        vfps, n = info["fps"], max(info["frame_count"], 1)

        def idx(t):
            return min(max(int(round(t * vfps)), 0), n - 1)

        plans = []
        for v in kept:
            tc = v["timecode_sec"]
            plans.append(sorted({idx(t) for t in (tc - 1.5, tc, tc + 1.5)}))
        for o in obs:
            plans.append([idx(o["timecode_sec"])])
        jpegs = read_indices(path, {i for p in plans for i in p}, self.s.evidence_max_side, 88)

        def frames_for(plan, tc):
            peak = idx(tc)
            return [{"timestamp_sec": round(i / vfps, 2), "frame_index": i,
                     "role": "peak" if i == peak else ("before" if i < peak else "after"),
                     "image_base64": b64(jpegs[i])} for i in plan if i in jpegs]

        violations = [self._item(v, frames_for(p, v["timecode_sec"])) for v, p in zip(kept, plans)]
        observations = [dict(self._item(o, frames_for(p, o["timecode_sec"])),
                             reason_not_counted=o.get("reason_not_counted", ""))
                        for o, p in zip(obs, plans[len(kept):])]
        return violations, observations

    def _item(self, v: dict, evidence: list[dict]) -> dict:
        rule = self.rb.get(v["type_id"])
        tc = round(v["timecode_sec"], 1)
        observed = v["observed"] or "см. кадры-доказательства"
        cits = self.rb.citation_objects(rule)
        basis = (f"{cits[0]['short']}, {cits[0]['clause']}: «{cits[0]['quote']}»" if cits
                 else "прямая норма не найдена — требуется ручная проверка")
        refs = [{"doc": c["document"], "clause": c["clause"], "quote": c["quote"], "url": c["url"]} for c in cits]
        item = {
            "type": rule.name_ru,
            "type_id": rule.id if rule.id == v["type_id"] else (v["type_id"] or "other"),
            "timecode_sec": tc,
            "timecode": mmss(tc),
            "confidence": round(v["confidence"], 3),
            "description": f"{rule.name_ru}. Наблюдение ({mmss(tc)}): {observed}. Основание: {basis}.",
            "observed": observed,
            "evidence_frames": evidence,
            "rule": {"citations": cits, "strength": rule.strength, "has_solid_clause": rule.has_solid_clause,
                     "note": rule.note, "not_claimed": rule.negatives},
            "rule_ref": refs[0] if refs else None,
        }
        if "votes" in v:
            item["votes"] = v["votes"]
        return item
