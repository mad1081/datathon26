"""Load rules.json and render citations / descriptions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Rule:
    id: str
    name_ru: str
    visual_criteria: str
    vlm_hint: str
    negatives: str
    citations: list[dict]
    strength: str
    has_solid_clause: bool
    threshold: float
    count_in_verdict: bool
    note: str = ""


class RuleBook:
    def __init__(self, data: dict):
        self.acts: dict = data["acts"]
        self.rules: dict[str, Rule] = {}
        for r in data["rules"]:
            self.rules[r["id"]] = Rule(
                id=r["id"], name_ru=r["name_ru"], visual_criteria=r["visual_criteria"],
                vlm_hint=r.get("vlm_hint", ""), negatives=r.get("negatives", ""),
                citations=r.get("citations", []), strength=r.get("strength", "unknown"),
                has_solid_clause=bool(r.get("has_solid_clause", False)),
                threshold=float(r.get("threshold", 0.6)),
                count_in_verdict=bool(r.get("count_in_verdict", True)), note=r.get("note", ""))

    def get(self, rid: str) -> Rule:
        return self.rules.get(rid) or self.rules["other"]

    def ids(self) -> list[str]:
        return list(self.rules)

    def citation_objects(self, rule: Rule) -> list[dict]:
        out = []
        for c in rule.citations:
            act = self.acts[c["act"]]
            out.append({"document": act["title"], "act": act["number"], "short": act["short"],
                        "clause": c["clause"], "quote": c["quote"], "url": c.get("url", act["url"])})
        return out

    def citation_text(self, rule: Rule) -> str:
        if not rule.citations:
            return ("Норма: в проверенных актах РК прямой нормы не найдено — требуется ручная проверка "
                    "проверяющим.")
        parts = []
        for c in rule.citations:
            act = self.acts[c["act"]]
            parts.append(f"{act['short']} ({act['number']}), {c['clause']}: «{c['quote']}»")
        return "Норма: " + "; ".join(parts)


@lru_cache(maxsize=4)
def load_rulebook(path: str) -> RuleBook:
    with open(path, encoding="utf-8") as f:
        return RuleBook(json.load(f))
