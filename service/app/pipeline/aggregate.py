"""Merge per-window VLM events into candidates."""
from __future__ import annotations

from collections import defaultdict

from .timeline import Candidate


def aggregate(window_events: list[dict], windows: list[tuple[float, float]], merge_gap: float = 2.0) -> list[Candidate]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for e in window_events:
        by_type[e["type"]].append(e)
    cands: list[Candidate] = []
    for typ, evs in by_type.items():
        evs.sort(key=lambda e: e["start_sec"])
        clusters: list[list[dict]] = []
        for e in evs:
            if clusters and e["start_sec"] <= max(x["end_sec"] for x in clusters[-1]) + merge_gap:
                clusters[-1].append(e)
            else:
                clusters.append([e])
        for cl in clusters:
            s = min(e["start_sec"] for e in cl)
            en = max(e["end_sec"] for e in cl)
            wins_hit = {e["window"] for e in cl}
            covering = [i for i, (a, b) in enumerate(windows) if b >= s and a <= en] or list(wins_hit)
            support = len(wins_hit) / max(1, len(covering))
            best = max(cl, key=lambda e: e["confidence"])
            cmax = best["confidence"]
            # confidence-weighted earliest-strong peak: earliest peak among events within 0.15 of the max
            strong = [e for e in cl if e["confidence"] >= cmax - 0.15]
            peak = min(e["peak_sec"] for e in strong)
            score = cmax * (0.6 + 0.4 * support)
            cands.append(Candidate(type=typ, score=round(score, 3), start_sec=s, end_sec=en, peak_sec=peak,
                                   evidence=best["evidence"], support=round(support, 2),
                                   extra={"n_windows": len(wins_hit), "max_conf": cmax}))
    cands.sort(key=lambda c: -c.score)
    return cands
