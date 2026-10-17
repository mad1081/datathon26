"""VLM backends. All return raw text; parsing is shared (parse.py).

- mock:          CPU-only deterministic stand-in (detects a saturated red marker; for pipeline tests only)
- transformers:  local HF model (default Qwen/Qwen2.5-VL-7B-Instruct, fallback Qwen/Qwen3-VL-4B-Instruct)
- openai:        local OpenAI-compatible server (e.g. `vllm serve Qwen/Qwen2.5-VL-7B-Instruct`) on localhost.
                 Must point to a LOCAL server — cloud AI APIs are forbidden by the case rules.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
from typing import Protocol

import cv2
import numpy as np

from .video import bgr_to_pil

log = logging.getLogger("backends")

Frame = tuple[float, np.ndarray]  # (t_sec, BGR image)


class VLMBackend(Protocol):
    name: str

    def generate(self, system: str, prompt: str, frames: list[Frame], kind: str) -> str: ...


# ----------------------------------------------------------------------------- mock
class MockBackend:
    """Flags frames with a large saturated-red area as `cash_unattended`.
    Only meant to exercise the full pipeline on CPU with synthetic videos."""

    name = "mock"

    @staticmethod
    def _red_fraction(img: np.ndarray) -> float:
        b, g, r = img[..., 0].astype(int), img[..., 1].astype(int), img[..., 2].astype(int)
        mask = (r > 150) & (g < 90) & (b < 90)
        return float(mask.mean())

    def __init__(self):
        import os
        self.delay = float(os.environ.get("MOCK_DELAY", "0"))  # simulate model latency

    def generate(self, system: str, prompt: str, frames: list[Frame], kind: str) -> str:
        if self.delay:
            import time
            time.sleep(self.delay)
        hits = [(t, self._red_fraction(img)) for t, img in frames]
        pos = [t for t, f in hits if f > 0.01]
        if kind == "verify":
            t, f = hits[0]
            return json.dumps({"visible": f > 0.01, "confidence": 0.9 if f > 0.01 else 0.1,
                               "evidence": "mock: красный маркер" if f > 0.01 else "mock: маркера нет"})
        scene = "mock: синтетическая сцена"
        t0 = frames[0][0] if frames else 0.0
        # plausible, deterministic scene-state flags for the UI tracks (mock only, not a detector)
        states = {"client_at_window": int(t0 // 10) % 2 == 0, "cashier_at_desk": True,
                  "cash_in_hands": bool(pos), "counting": bool(pos) and int(t0 // 5) % 2 == 0,
                  "second_employee": False, "phone": False}
        if not pos:
            return json.dumps({"scene": scene, "events": [], "states": states}, ensure_ascii=False)
        ev = {"type": "cash_unattended", "confidence": 0.9, "start_sec": min(pos), "end_sec": max(pos),
              "peak_sec": min(pos), "evidence": "mock: на столе виден красный объект без присмотра"}
        return "```json\n" + json.dumps({"scene": scene, "events": [ev], "states": states}, ensure_ascii=False) + "\n```"


# ----------------------------------------------------------------------------- transformers
class TransformersBackend:
    def __init__(self, model_id: str, fallback_id: str | None, max_new_tokens: int = 512):
        self.model_id, self.fallback_id = model_id, fallback_id
        self.max_new_tokens = max_new_tokens
        self.model = self.processor = None
        self.name = f"transformers:{model_id}"
        self._lock = threading.Lock()

    def _load(self):
        if self.model is not None:
            return
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        last_err = None
        for mid in [self.model_id, self.fallback_id]:
            if not mid:
                continue
            try:
                log.info("loading %s", mid)
                kw = dict(dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                          device_map="auto")
                try:
                    import flash_attn  # noqa: F401
                    kw["attn_implementation"] = "flash_attention_2"
                except Exception:
                    pass
                self.model = AutoModelForImageTextToText.from_pretrained(mid, **kw).eval()
                self.processor = AutoProcessor.from_pretrained(mid)
                self.name = f"transformers:{mid}"
                return
            except Exception as e:  # OOM, missing weights, unsupported arch...
                last_err = e
                log.exception("failed to load %s", mid)
                self.model = None
        raise RuntimeError(f"no VLM could be loaded: {last_err}")

    def generate(self, system: str, prompt: str, frames: list[Frame], kind: str) -> str:
        import torch
        with self._lock:
            self._load()
            content = []
            for t, img in frames:
                content.append({"type": "text", "text": f"[кадр t={t:.2f} с]"})
                content.append({"type": "image", "image": bgr_to_pil(img)})
            content.append({"type": "text", "text": prompt})
            messages = [{"role": "system", "content": [{"type": "text", "text": system}]},
                        {"role": "user", "content": content}]
            inputs = self.processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt"
            ).to(self.model.device)
            with torch.inference_mode():
                out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens if kind == "window" else 128,
                                          do_sample=False)
            gen = out[:, inputs["input_ids"].shape[1]:]
            return self.processor.batch_decode(gen, skip_special_tokens=True)[0]


# ----------------------------------------------------------------------------- openai-compatible local server
class OpenAICompatBackend:
    def __init__(self, base_url: str, model: str, max_new_tokens: int = 512):
        import requests  # noqa: F401
        host = base_url.split("//", 1)[-1].split("/", 1)[0].split(":")[0]
        if host not in ("127.0.0.1", "localhost", "0.0.0.0") and not host.startswith(("10.", "192.168.", "172.")) \
                and "." in host:
            raise ValueError(f"OPENAI_BASE_URL must point to a LOCAL inference server, got {host}")
        self.base_url, self.model, self.max_new_tokens = base_url.rstrip("/"), model, max_new_tokens
        self.name = f"openai-local:{model}"

    def generate(self, system: str, prompt: str, frames: list[Frame], kind: str) -> str:
        import requests
        content = []
        for t, img in frames:
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            content.append({"type": "text", "text": f"[кадр t={t:.2f} с]"})
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()}})
        content.append({"type": "text", "text": prompt})
        r = requests.post(f"{self.base_url}/chat/completions", timeout=120, json={
            "model": self.model, "temperature": 0,
            "max_tokens": self.max_new_tokens if kind == "window" else 128,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


_backend = None
_backend_lock = threading.Lock()


def get_backend(settings) -> VLMBackend:
    global _backend
    with _backend_lock:
        if _backend is None:
            kind = settings.vlm_backend.lower()
            if kind == "mock":
                _backend = MockBackend()
            elif kind == "transformers":
                _backend = TransformersBackend(settings.vlm_model, settings.vlm_fallback_model,
                                               settings.max_new_tokens)
            elif kind == "openai":
                _backend = OpenAICompatBackend(settings.openai_base_url, settings.openai_model,
                                               settings.max_new_tokens)
            else:
                raise ValueError(f"unknown VLM_BACKEND={settings.vlm_backend}")
        return _backend
