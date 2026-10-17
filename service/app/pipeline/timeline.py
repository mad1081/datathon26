"""Extension point: detector/tracker signals + rules-on-timeline.

v0 ships only a cheap motion-energy signal (used for timecode refinement). Later:
- add SignalProvider implementations (e.g. RT-DETR / Grounding DINO person+object detection,
  MediaPipe pose/hands — all Apache-2.0) producing per-frame signals such as
  `n_persons`, `cashier_present`, `door_open`, `safe_open`, `cash_on_desk`, `hands_below_desk`;
- add TimelineRule implementations that turn signal sequences into Candidate objects
  (e.g. cash_on_desk & !cashier_present for > 2 s -> cash_unattended).
Candidates from timeline rules are merged with VLM candidates in analyzer.py (same format).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import cv2
import numpy as np


@dataclass
class Candidate:
    type: str
    score: float
    start_sec: float
    end_sec: float
    peak_sec: float
    evidence: str
    source: str = "vlm"
    support: float = 1.0
    extra: dict = field(default_factory=dict)


class SignalProvider(Protocol):
    name: str

    def compute(self, frames: list[tuple[float, int, np.ndarray]]) -> dict[str, list[float]]: ...


class TimelineRule(Protocol):
    rule_id: str

    def evaluate(self, times: list[float], signals: dict[str, list[float]]) -> list[Candidate]: ...


def motion_energy(frames: list[tuple[float, int, np.ndarray]]) -> list[float]:
    """Mean abs grayscale difference to the previous frame (first frame = 0)."""
    out, prev = [], None
    for _, _, img in frames:
        g = cv2.cvtColor(cv2.resize(img, (320, int(320 * img.shape[0] / img.shape[1]))), cv2.COLOR_BGR2GRAY)
        g = cv2.GaussianBlur(g, (5, 5), 0)
        out.append(0.0 if prev is None else float(np.abs(g.astype(int) - prev.astype(int)).mean()))
        prev = g
    return out


class MotionSignal:
    name = "motion"

    def compute(self, frames):
        return {"motion": motion_energy(frames)}


SIGNAL_PROVIDERS: list[SignalProvider] = []   # register detectors here later
TIMELINE_RULES: list[TimelineRule] = []       # register timeline rules here later
