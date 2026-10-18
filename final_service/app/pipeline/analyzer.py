"""Pipeline: decode -> sample frames of the whole video -> one VLM call (or N voted) -> rules -> evidence."""
from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

from .frames import ensure_decodable
from .rules import load_rulebook
from .vlm import VLMClient
from .whole_video import WholeVideoAnalyzer

log = logging.getLogger("analyzer")


class Analyzer:
    def __init__(self, settings):
        self.s = settings
        self.rb = load_rulebook(settings.rules_path)
        self.client = VLMClient(settings)
        self.whole = WholeVideoAnalyzer(settings, self.rb, self.client)

    def run(self, video_path: str, progress: Callable[[float, str], None] = lambda p, s: None,
            created_at: float | None = None) -> dict:
        t_start = time.time()
        deadline = (created_at or t_start) + self.s.time_budget_sec
        work = Path(tempfile.mkdtemp(prefix="job_"))
        try:
            progress(0.02, "decoding")
            path = ensure_decodable(video_path, work)
            result = self.whole.analyze(path, deadline, progress)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        violations = result["violations"]
        review = []
        if any(not v["rule"]["has_solid_clause"] for v in violations):
            review.append("у части нарушений норма косвенная или не найдена")
        if not violations and any(o["confidence"] >= 0.5 for o in result["observations"]):
            review.append("есть наблюдения, не учтённые в вердикте")
        result["meta"]["processing_sec"] = round(time.time() - t_start, 2)
        if created_at:
            result["meta"]["since_upload_sec"] = round(time.time() - created_at, 2)
        progress(1.0, "done")
        return {
            **result,
            "verdict_ru": ("Обнаружены признаки возможных нарушений" if violations else "Нарушение не обнаружено"),
            "needs_manual_review": bool(review),
            "manual_review_reasons": review,
        }
