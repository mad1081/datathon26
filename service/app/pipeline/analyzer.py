"""Pipeline v0: sample -> sliding-window VLM -> aggregate -> refine -> evidence -> rules -> verdict."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import numpy as np

from . import prompts
from .aggregate import aggregate
from .backends import get_backend
from .parse import extract_json, normalize_states, normalize_verify, normalize_window, states_to_tracks
from .rules import load_rulebook
from .timeline import Candidate, SIGNAL_PROVIDERS, TIMELINE_RULES, motion_energy
from .video import ensure_decodable, probe, read_frame, read_range, sample_frames, tmpdir, to_jpeg_b64

log = logging.getLogger("analyzer")
MAX_FRAMES_PER_WINDOW = 8


def _fmt(t: float) -> str:
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m):02d}:{s:05.2f}"


def build_windows(duration: float, window: float, stride: float, max_windows: int) -> list[tuple[float, float]]:
    if duration <= window:
        return [(0.0, duration)]
    n = int(np.ceil((duration - window) / stride)) + 1
    if n > max_windows:
        stride = (duration - window) / (max_windows - 1)
        n = max_windows
    wins = [(i * stride, min(duration, i * stride + window)) for i in range(n)]
    if wins[-1][1] < duration:
        wins.append((max(0.0, duration - window), duration))
    return wins


class Analyzer:
    def __init__(self, settings):
        self.s = settings
        self.rb = load_rulebook(settings.rules_path)
        self.backend = get_backend(settings)
        self._window_system = prompts.window_system(self.rb)

    def _call(self, prompt: str, frames, kind: str) -> str:
        last = None
        system = self._window_system if kind == "window" else prompts.SYSTEM
        for _ in range(2):  # one retry
            try:
                return self.backend.generate(system, prompt, frames, kind)
            except Exception as e:  # noqa: BLE001
                last = e
                log.exception("backend call failed")
        raise RuntimeError(f"VLM call failed: {last}")

    # ------------------------------------------------------------------ main
    def run(self, video_path: str, progress: Callable[[float, str], None] = lambda p, s: None) -> dict:
        t_start = time.time()
        deadline = t_start + self.s.time_budget_sec
        warnings: list[str] = []
        work = tmpdir()
        path = ensure_decodable(video_path, work)
        info = probe(path)
        progress(0.05, "decoding")
        frames = sample_frames(info, self.s.sample_fps, self.s.frame_max_side)
        if not frames:
            raise RuntimeError("no frames decoded")
        duration = max(info.duration, frames[-1][0])
        windows = build_windows(duration, self.s.window_sec, self.s.stride_sec, self.s.max_windows)
        valid = set(self.rb.ids())

        # ---- 1. sliding windows (batched; adaptive re-planning keeps full coverage within the time budget)
        events, scenes, failed, win_states = [], [], [], []
        conc = max(1, self.s.window_concurrency)
        done_windows: list[tuple[float, float]] = []
        pending = list(windows)
        t_loop = time.time()
        while pending:
            batch, pending = pending[:conc], pending[conc:]
            with ThreadPoolExecutor(max_workers=conc) as ex:
                results = list(ex.map(lambda w: self._analyze_window(frames, w, valid), batch))
            for (a, b), (scene, evs, err, states) in zip(batch, results):
                wi = len(done_windows)
                done_windows.append((a, b))
                if err:
                    failed.append((a, b, err))
                    warnings.append(f"окно {a:.1f}-{b:.1f} с: {err}")
                    continue
                scenes.append({"start_sec": round(a, 2), "end_sec": round(b, 2), "scene": scene})
                if states:
                    win_states.append((a, b, states))
                for e in evs:
                    e["window"] = wi
                    events.append(e)
            progress(0.1 + 0.6 * len(done_windows) / (len(done_windows) + len(pending)), "analyzing")
            if pending:
                per_batch = (time.time() - t_loop) / (len(done_windows) / conc)
                budget_left = (deadline - time.time()) * 0.75  # keep 25% for refinement/evidence
                affordable = int(budget_left / max(per_batch, 1e-3)) * conc
                if affordable < len(pending):
                    a0, b1 = pending[0][0], duration
                    n = max(1, affordable)
                    span = (b1 - a0) / n
                    pending = [(a0 + i * span, min(b1, a0 + (i + 1) * span + 0.5)) for i in range(n)]
                    warnings.append(f"окна укрупнены после {a0:.1f} с для соблюдения лимита времени "
                                    f"({n} окон по ~{span:.1f} с)")
        windows = done_windows

        cands = aggregate(events, windows)

        # ---- 1b. timeline layer (detectors) — empty in v0, same Candidate format
        if SIGNAL_PROVIDERS and TIMELINE_RULES:
            signals: dict[str, list[float]] = {}
            for p in SIGNAL_PROVIDERS:
                signals.update(p.compute(frames))
            times = [t for t, _, _ in frames]
            for r in TIMELINE_RULES:
                cands.extend(r.evaluate(times, signals))

        # ---- 2. refine
        cands = [c for c in cands if c.score >= self.s.low_threshold]
        refined_any = False
        for ci, c in enumerate(cands[: self.s.max_violations * 2]):
            if not self.s.refine:
                break
            if time.time() > deadline - 30:
                warnings.append("уточнение таймкода пропущено: исчерпан бюджет времени")
                break
            try:
                self._refine(info, c)
                refined_any = True
            except Exception as e:  # noqa: BLE001
                warnings.append(f"уточнение {c.type}: {str(e)[:120]}")
            progress(0.7 + 0.2 * (ci + 1) / max(1, len(cands)), "refining")

        # ---- 3. decide + evidence
        violations, observations = [], []
        for c in sorted(cands, key=lambda c: c.extra.get("onset", c.peak_sec)):
            rule = self.rb.get(c.type)
            thr = rule.threshold + self.s.threshold_offset
            item = self._render(info, c, rule)
            if c.score >= thr and rule.count_in_verdict:
                violations.append(item)
            else:
                item["reason_not_counted"] = ("ниже порога уверенности" if c.score < thr
                                              else "тип без нормативного основания — не влияет на вердикт")
                observations.append(item)
        if len(violations) > self.s.max_violations:
            violations.sort(key=lambda v: -v["confidence"])
            observations.extend(violations[self.s.max_violations:])
            violations = sorted(violations[: self.s.max_violations], key=lambda v: v["timecode_sec"])
        for o in observations:  # keep payload small: 1 frame per observation
            o["evidence_frames"] = o["evidence_frames"][1:2] or o["evidence_frames"][:1]

        if failed:
            warnings.append(f"не проанализировано окон: {len(failed)} из {len(windows)}")
        if failed and len(failed) == len(windows):
            raise RuntimeError("all windows failed: " + failed[0][2])
        verdict = "violation" if violations else "no_violation"
        unanalyzed = [{"start_sec": round(a, 2), "end_sec": round(b, 2), "reason": r} for a, b, r in failed]
        # parts of the video no window covered (e.g. decode stopped early)
        covered_to = max((b for a, b in windows), default=0.0)
        if info.duration - covered_to > 1.0:
            unanalyzed.append({"start_sec": round(covered_to, 2), "end_sec": round(info.duration, 2),
                               "reason": "кадры не декодированы / не покрыты окнами"})
        review_reasons = []
        if unanalyzed:
            review_reasons.append("есть непроанализированные отрезки видео")
        if any(not v["rule"]["has_solid_clause"] for v in violations):
            review_reasons.append("у части нарушений норма косвенная или не найдена")
        if any(v["type_id"] == "other" for v in violations):
            review_reasons.append("тип нарушения вне базы правил")
        if not violations and any(o["confidence"] >= 0.5 for o in observations):
            review_reasons.append("есть наблюдения ниже порога")
        progress(1.0, "done")
        return {
            "verdict": verdict,
            "verdict_ru": ("Обнаружены признаки возможных нарушений" if violations else "Нарушение не обнаружено"),
            "violations": violations,
            "observations": observations,
            "unanalyzed_ranges": unanalyzed,
            "needs_manual_review": bool(review_reasons),
            "manual_review_reasons": review_reasons,
            "tracks": states_to_tracks(win_states),
            "meta": {
                "model": getattr(self.backend, "name", "?"),
                "duration_sec": round(duration, 2), "fps": round(info.fps, 3),
                "frames_sampled": len(frames), "windows": len(windows),
                "unanalyzed_ranges": unanalyzed,
                "partial": bool(failed), "refined": refined_any,
                "processing_sec": round(time.time() - t_start, 2),
                "warnings": warnings, "scenes": scenes,
            },
        }

    def _analyze_window(self, frames, win, valid):
        a, b = win
        wf = [(t, img) for t, _, img in frames if a - 1e-6 <= t <= b + 1e-6]
        if len(wf) > MAX_FRAMES_PER_WINDOW:
            idx = np.linspace(0, len(wf) - 1, MAX_FRAMES_PER_WINDOW).round().astype(int)
            wf = [wf[i] for i in idx]
        if not wf:
            return "", [], None, {}
        try:
            raw = self._call(prompts.window_prompt(self.rb, a, b, [t for t, _ in wf]), wf, "window")
        except Exception as e:  # noqa: BLE001
            return "", [], f"ошибка модели: {str(e)[:150]}", {}
        obj = extract_json(raw)
        if obj is None:
            return "", [], "модель вернула не-JSON", {}
        scene, evs = normalize_window(obj, valid, a, b)
        return scene, evs, None, normalize_states(obj, prompts.STATE_FLAGS)

    # ------------------------------------------------------------------ refine
    def _refine(self, info, c: Candidate) -> None:
        a = max(0.0, c.peak_sec - self.s.refine_span_sec)
        b = min(info.duration, c.peak_sec + self.s.refine_span_sec)
        every = max(1, int(round(info.fps / self.s.refine_fps)))
        coarse = read_range(info, a, b, max_side=self.s.frame_max_side, every=every)
        checks = []
        prev = None
        for t, idx, img in coarse:
            ctx = [(prev[0], prev[2])] if prev is not None else []
            raw = self._call(prompts.verify_prompt(self.rb, c.type, t), [(t, img)] + ctx, "verify")
            vis, conf, ev = normalize_verify(extract_json(raw))
            checks.append((t, idx, vis and conf >= 0.5, conf, ev))
            prev = (t, idx, img)
        pos = [x for x in checks if x[2]]
        c.extra["verify_hits"] = f"{len(pos)}/{len(checks)}"
        if not pos:
            c.score = round(c.score * 0.6, 3)   # model could not confirm -> lower, but never drop silently
            c.extra["onset"] = c.peak_sec
            return
        first = pos[0]
        c.score = round(min(1.0, 0.5 * c.score + 0.5 * max(x[3] for x in pos)), 3)
        if pos[0][4]:
            c.extra["verify_evidence"] = pos[0][4]
        onset_t, onset_idx = first[0], first[1]
        # full-fps refinement between last negative check and first positive: pick max visual change
        negs = [x for x in checks if not x[2] and x[0] < onset_t]
        if negs:
            lo = negs[-1][0]
            full = read_range(info, lo, onset_t, max_side=320)
            if len(full) >= 3:
                me = motion_energy(full)
                k = int(np.argmax(me[1:])) + 1
                onset_t, onset_idx = full[k][0], full[k][1]
        c.extra["onset"] = onset_t
        c.extra["onset_idx"] = onset_idx

    # ------------------------------------------------------------------ output
    def _rule_refs(self, rule) -> dict:
        """UI contract (review/forte_mockup.html): rule_ref {doc, clause, quote, url}; extras; rule_status."""
        refs = [{"doc": c["document"], "clause": c["clause"], "quote": c["quote"], "url": c["url"]}
                for c in self.rb.citation_objects(rule)]
        out: dict = {"rule_ref": refs[0] if refs else None}
        if len(refs) > 1:
            out["rule_refs_extra"] = refs[1:]
        if not refs:
            out["rule_status"] = ("vlm_type_outside_rule_base" if rule.id == "other"
                                  else "rule_not_found_manual_review")
        return out

    def _render(self, info, c: Candidate, rule) -> dict:
        onset = float(c.extra.get("onset", c.peak_sec))
        onset_idx = int(c.extra.get("onset_idx", round(onset * info.fps)))
        onset_idx = max(0, min(info.n_frames - 1, onset_idx))
        onset = onset_idx / info.fps
        times = [max(0.0, onset - 1.5), onset, min(info.duration - 1.0 / info.fps, max(onset + 1.5, c.end_sec))]
        frames_out, seen = [], []
        for t in times:
            idx = max(0, min(info.n_frames - 1, int(round(t * info.fps))))
            if any(abs(idx - s) < info.fps * 0.3 for s in seen):
                continue
            img = read_frame(info, idx)
            if img is None:
                continue
            seen.append(idx)
            frames_out.append({"timestamp_sec": round(idx / info.fps, 2), "frame_index": idx,
                               "role": "peak" if idx == onset_idx else ("before" if idx < onset_idx else "after"),
                               "image_base64": to_jpeg_b64(img, self.s.evidence_max_side)})
        frames_out.sort(key=lambda f: f["timestamp_sec"])
        observed = c.extra.get("verify_evidence") or c.evidence or rule.visual_criteria
        description = (f"{rule.name_ru}. Наблюдение ({_fmt(onset)}): {observed}. "
                       f"Почему это может быть нарушением: {rule.visual_criteria} "
                       f"{self.rb.citation_text(rule)}")
        if not rule.has_solid_clause and rule.citations:
            description += " (основание косвенное — требуется подтверждение проверяющим)"
        return {
            "type": rule.name_ru if self.s.type_field == "name" else rule.id,
            "type_id": rule.id,
            "type_name_ru": rule.name_ru,
            "timecode_sec": round(onset, 2),
            "timecode": _fmt(onset),
            "frame_index": onset_idx,
            "confidence": round(c.score, 3),
            "description": description,
            "observed": observed,
            "rule": {"citations": self.rb.citation_objects(rule), "strength": rule.strength,
                     "has_solid_clause": rule.has_solid_clause, "note": rule.note,
                     "not_claimed": rule.negatives},
            "interval_sec": [round(c.start_sec, 2), round(c.end_sec, 2)],
            "window_sec": [round(c.start_sec, 2), round(c.end_sec, 2)],
            **self._rule_refs(rule),
            "source": "vlm",
            "debug": {"support": c.support, **{k: v for k, v in c.extra.items() if k != "onset_idx"}},
            "evidence_frames": frames_out,
        }
