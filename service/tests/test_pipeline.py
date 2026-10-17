"""Run: ../.venv/bin/python -m pytest -q tests  (or python tests/test_pipeline.py)"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("VLM_BACKEND", "mock")

from app.pipeline.parse import extract_json, normalize_states, normalize_window, states_to_tracks  # noqa: E402

DATA = Path(__file__).parent / "data"


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Ответ: {"events": [], "scene": "x {y}"} спасибо') == {"events": [], "scene": "x {y}"}
    assert extract_json('{"events": [1,2,],}') == {"events": [1, 2]}
    assert extract_json("no json") is None


def test_normalize_unknown_type_and_clamp():
    scene, evs = normalize_window({"events": [{"type": "weird", "confidence": "0.8", "start_sec": -5,
                                               "end_sec": 99, "peak_sec": 3}]}, {"other", "cash_unattended"}, 2, 6)
    assert evs[0]["type"] == "other" and evs[0]["start_sec"] == 2 and evs[0]["end_sec"] == 6
    assert abs(evs[0]["confidence"] - 0.8) < 1e-9


def _analyzer():
    from app.config import settings
    from app.pipeline.analyzer import Analyzer
    return Analyzer(settings)


def test_mock_end_to_end():
    if not (DATA / "violation.mov").exists():
        from tests.make_synthetic import make
        DATA.mkdir(exist_ok=True)
        make(DATA / "violation.mov", True)
        make(DATA / "no_violation.mov", False)
    a = _analyzer()
    r = a.run(str(DATA / "violation.mov"))
    assert r["verdict"] == "violation"
    v = r["violations"][0]
    assert abs(v["timecode_sec"] - 4.0) <= 0.5
    assert 1 <= len(v["evidence_frames"]) <= 3
    assert v["rule"]["citations"] and "п. 20" in v["description"]
    # ТЗ: type = «Название типа нарушения» (рус.), машинный ключ — в type_id
    assert v["type_id"] == "cash_unattended"
    assert v["type"] == a.rb.get("cash_unattended").name_ru and v["type"] != v["type_id"]
    assert any("а" <= ch.lower() <= "я" for ch in v["type"])
    # optional UI fields (required jury fields unchanged)
    assert set(v["rule_ref"]) == {"doc", "clause", "quote", "url"} and v["rule_ref"]["clause"].startswith("п.")
    assert 0 <= v["confidence"] <= 1 and len(v["window_sec"]) == 2 and v["window_sec"][0] <= v["timecode_sec"] + 0.5
    assert r["verdict"] in ("violation", "no_violation") and isinstance(r["needs_manual_review"], bool)
    assert r["unanalyzed_ranges"] == []
    labels = {t["label"] for t in r["tracks"]}
    assert {"cashier_at_desk", "cash_in_hands"} <= labels
    assert all(set(t) == {"label", "start_sec", "end_sec"} and t["start_sec"] <= t["end_sec"] for t in r["tracks"])
    r2 = a.run(str(DATA / "no_violation.mov"))
    assert r2["verdict"] == "no_violation" and "cash_in_hands" not in {t["label"] for t in r2["tracks"]}


def test_states_and_tracks():
    flags = ("client_at_window", "cashier_at_desk", "phone")
    assert normalize_states({"states": {"client_at_window": "да", "phone": 0}}, flags) == \
        {"client_at_window": True, "cashier_at_desk": False, "phone": False}
    assert normalize_states({"events": []}, flags) == {}
    tr = states_to_tracks([(0, 4, {"phone": True}), (3, 7, {"phone": True}), (10, 14, {"phone": True, "counting": False})])
    assert tr == [{"label": "phone", "start_sec": 0, "end_sec": 7}, {"label": "phone", "start_sec": 10, "end_sec": 14}]


def test_rule_ref_for_rule_without_clause():
    a = _analyzer()
    refs = a._rule_refs(a.rb.get("workstation_unlocked"))
    assert refs["rule_ref"] is None and refs["rule_status"] == "rule_not_found_manual_review"
    refs = a._rule_refs(a.rb.get("foreign_cash_on_desk"))
    assert refs["rule_ref"]["doc"].startswith("Правила") and len(refs["rule_refs_extra"]) == 1


def test_rules_include_counting_without_controller():
    from app.pipeline.prompts import window_system
    a = _analyzer()
    r = a.rb.rules["counting_without_controller"]
    assert r.strength == "medium" and r.has_solid_clause and abs(r.threshold - 0.8) < 1e-9
    assert r.count_in_verdict is False  # X-43/X-45 (cashier alone counting) are labelled clean
    c = r.citations[0]
    assert c["clause"] == "п. 42" and c["url"].endswith("V1900019680#z163")
    assert c["quote"].startswith("Кассовые операции по пересчету, сортировке и упаковке")
    assert '"counting_without_controller"' in window_system(a.rb)
    assert a.rb.ids()[-1] == "other"

def test_api_optional_fields_and_errors():
    import time
    from fastapi.testclient import TestClient
    from app.main import app, settings
    with TestClient(app) as c:
        h = {"X-API-Key": settings.api_key}
        assert c.get("/api/v1/jobs/abc").status_code == 401
        assert c.get("/api/v1/jobs/deadbeef", headers=h).status_code == 404
        with open(DATA / "violation.mov", "rb") as f:
            jid = c.post("/api/v1/analyze", headers=h, files={"file": ("v.mov", f, "video/quicktime")}).json()["job_id"]
        for _ in range(240):
            j = c.get(f"/api/v1/jobs/{jid}", headers=h).json()
            if j["status"] != "processing":
                break
            time.sleep(0.5)
        assert j["status"] == "done" and j["verdict"] == "violation"
        for k in ("job_id", "status", "verdict", "violations", "tracks", "unanalyzed_ranges", "needs_manual_review"):
            assert k in j
        assert "rule_ref" in j["violations"][0]


def test_garbage_model_output_is_reported_not_silent():
    a = _analyzer()

    class Garbage:
        name = "garbage"

        def generate(self, *args, **kw):
            return "I cannot help with that"
    a.backend = Garbage()
    try:
        a.run(str(DATA / "violation.mov"))
        raise AssertionError("expected failure when every window is unparsable")
    except RuntimeError as e:
        assert "all windows failed" in str(e)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
