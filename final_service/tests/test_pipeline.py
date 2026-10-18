"""Run: python -m pytest -q tests  (or python tests/test_pipeline.py). CPU only, no model needed."""
import base64
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["VLM_BASE_URL"] = "mock"
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="cc_data_"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app.pipeline.vlm import VLMError, check_local, extract_json  # noqa: E402
from app.pipeline.whole_video import normalize_violations, split, verdict_type_ids, vote  # noqa: E402

DATA = Path(tempfile.gettempdir()) / "cc_test_data"


def _video() -> Path:
    p = DATA / "synthetic.avi"
    if not p.exists():
        DATA.mkdir(exist_ok=True)
        vw = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"MJPG"), 10, (640, 360))
        for i in range(120):
            img = np.full((360, 640, 3), 200, np.uint8)
            cv2.putText(img, f"t={i / 10:.1f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            vw.write(img)
        vw.release()
    return p


def _analyzer():
    from app.config import Settings
    from app.pipeline.analyzer import Analyzer
    return Analyzer(Settings())


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Ответ: {"violations": [], "scenario": "x {y}"} спасибо') == {"violations": [], "scenario": "x {y}"}
    assert extract_json('{"v": [1,2,],}') == {"v": [1, 2]}
    assert extract_json("<think>долго думаю {</think>{\"a\": 2}") == {"a": 2}
    assert extract_json("no json") is None
    assert extract_json("<think>не закончил") is None


def test_local_guard():
    for ok in ("mock", "http://127.0.0.1:8001/v1", "http://localhost:8001/v1", "http://vllm:8000/v1",
               "http://10.1.2.3:8000/v1", "http://192.168.0.5/v1", "http://0.0.0.0:8001/v1"):
        check_local(ok)
    for bad in ("https://api.openai.com/v1", "https://xyz-8000.proxy.runpod.net/v1", "http://8.8.8.8/v1"):
        try:
            check_local(bad)
            raise AssertionError(bad)
        except ValueError:
            pass


def test_verdict_types_and_split():
    rb = _analyzer().rb
    allowed = verdict_type_ids(rb)
    assert "other" not in allowed and "safe_opened_with_client" not in allowed
    assert "counting_without_controller" not in allowed and "cash_unattended" in allowed
    items = normalize_violations({"violations": [
        {"type_id": "cash_unattended", "timecode_sec": "00:12", "confidence": 90, "observed": "a"},
        {"type_id": "cash_unattended", "timecode_sec": 13.5, "confidence": 0.7, "observed": "b"},
        {"type_id": "issue_without_count", "timecode_sec": 5, "confidence": 0.5},
        {"type_id": "other", "timecode_sec": 1, "confidence": 0.99},
        {"type_id": "counting_without_controller", "timecode_sec": 2, "confidence": 0.99},
        {"type_id": "made_up", "timecode_sec": 2, "confidence": 0.99},
    ]}, duration=60)
    kept, obs = split(rb, items, offset=0.0, merge_window=3.0)
    assert [(k["type_id"], k["timecode_sec"]) for k in kept] == [("cash_unattended", 12.0)]
    assert kept[0]["confidence"] == 0.9 and kept[0]["observed"] == "a; b"
    assert {o["type_id"] for o in obs} == {"issue_without_count", "other", "counting_without_controller", "made_up"}
    kept, _ = split(rb, items, offset=0.35, merge_window=3.0)
    assert kept == []


def test_vote_majority_and_median():
    a = {"type_id": "cash_unattended", "confidence": 0.9, "observed": "x"}
    b = {"type_id": "door_left_open", "confidence": 0.8, "observed": "y"}
    s = [([dict(a, timecode_sec=10.0)], []), ([dict(a, timecode_sec=14.0), dict(b, timecode_sec=3)], []),
         ([dict(a, timecode_sec=11.0)], [])]
    kept, obs, meta = vote(s)
    assert [k["type_id"] for k in kept] == ["cash_unattended"] and kept[0]["timecode_sec"] == 11.0
    assert kept[0]["votes"] == "3/3" and obs[0]["type_id"] == "door_left_open"
    kept, _, _ = vote([([dict(a, timecode_sec=1)], []), ([], []), ([], [])])
    assert kept == []
    kept, _, _ = vote([([dict(a, timecode_sec=1)], []), ([dict(b, timecode_sec=2)], []), ([], [])])
    assert len(kept) == 2  # verdict majority without a majority type keeps the most-voted types


def test_mock_end_to_end():
    r = _analyzer().run(str(_video()))
    assert r["verdict"] == "violation"
    v = r["violations"][0]
    assert v["type_id"] == "cash_unattended" and v["type"] != v["type_id"]
    assert 1 <= len(v["evidence_frames"]) <= 3
    for f in v["evidence_frames"]:
        assert base64.b64decode(f["image_base64"])[:3] == b"\xff\xd8\xff"
    assert "Основание" in v["description"] and v["rule_ref"]["url"].startswith("https://adilet.zan.kz")
    assert r["scenario"] and r["timeline"]


def test_garbage_model_output_fails_not_clean():
    a = _analyzer()

    class Garbage:
        name = "garbage"
        calls = 0

        def chat(self, *args, **kw):
            Garbage.calls += 1
            return "I cannot help with that"
    a.whole.client = Garbage()
    try:
        a.run(str(_video()))
        raise AssertionError("expected failure on unparsable output")
    except VLMError as e:
        assert "not valid JSON" in str(e) and Garbage.calls == 2 * max(1, a.s.n_samples)


def test_api_auth_and_flow():
    from fastapi.testclient import TestClient
    from app.main import app, settings
    with TestClient(app) as c:
        h = {"X-API-Key": settings.api_key}
        assert c.get("/api/v1/jobs/abc").status_code == 401
        assert c.get("/api/v1/jobs/abc", headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.get("/api/v1/jobs/deadbeef", headers=h).status_code == 404
        with open(_video(), "rb") as f:
            assert c.post("/api/v1/analyze", files={"file": ("v.avi", f, "video/avi")}).status_code == 401
            f.seek(0)
            r = c.post("/api/v1/analyze", headers=h, files={"file": ("v.avi", f, "video/avi")})
        assert r.status_code == 202
        jid = r.json()["job_id"]
        for _ in range(120):
            j = c.get(f"/api/v1/jobs/{jid}", headers=h).json()
            if j["status"] != "processing":
                break
            time.sleep(0.5)
        assert j["status"] == "done" and j["verdict"] == "violation", j
        for k in ("job_id", "status", "verdict", "violations", "scenario", "timeline"):
            assert k in j


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
