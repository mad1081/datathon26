"""Client for a LOCAL OpenAI-compatible VLM server (vLLM). Cloud AI APIs are not allowed by the case rules."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import random
import re
import threading
import time

log = logging.getLogger("vlm")


class VLMError(RuntimeError):
    pass


class VLMRequestTooLarge(VLMError):
    """The server rejected the request (HTTP 400), typically prompt longer than --max-model-len."""


def check_local(base_url: str) -> None:
    """Allow only localhost, private IPs and docker service names (no dots)."""
    if base_url == "mock":
        return
    host = base_url.split("//", 1)[-1].split("/", 1)[0].rsplit("@", 1)[-1]
    host = host[1:].split("]", 1)[0] if host.startswith("[") else host.split(":", 1)[0]
    if host in ("localhost", "0.0.0.0") or "." not in host and ":" not in host:
        return
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (ip.is_loopback or ip.is_private or ip.is_unspecified):
        return
    raise ValueError(f"VLM_BASE_URL must point to a LOCAL inference server, got {host}")


def extract_json(text: str | None) -> dict | None:
    """Parse the first top-level JSON object from model output; None if impossible."""
    if not text:
        return None
    t = re.sub(r"<think>.*?</think>", "", text.strip(), flags=re.S).strip()
    if "<think>" in t and "</think>" not in t:  # unfinished reasoning, no answer
        return None
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, flags=re.S)
    candidates = [fence.group(1)] if fence else []
    candidates.append(t)
    for c in candidates:
        for s in (c, c[c.find("{"): c.rfind("}") + 1] if "{" in c else ""):
            if not s:
                continue
            for attempt in (s, re.sub(r",\s*([}\]])", r"\1", s)):
                try:
                    obj = json.loads(attempt)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(obj, dict):
                    return obj
    return None


def _mock_response(messages, seed: str) -> str:
    rng = random.Random(int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16))
    times = [float(p["text"][3:].split()[0]) for p in messages[-1]["content"]
             if p["type"] == "text" and p["text"].startswith("[t=")]
    duration = times[-1] if times else 30.0
    body = {
        "scenario": "тестовый сценарий (mock)",
        "timeline": [{"t": 0.0, "event": "начало записи"}, {"t": round(duration / 2, 1), "event": "середина"},
                     {"t": duration, "event": "конец записи"}],
        "violations": [{"type_id": "cash_unattended", "timecode_sec": round(rng.uniform(0, duration), 1),
                        "confidence": 0.9, "observed": "тестовое наблюдение (mock)"}],
    }
    return "```json\n" + json.dumps(body, ensure_ascii=False) + "\n```"


class VLMClient:
    def __init__(self, settings):
        self.s = settings
        check_local(settings.vlm_base_url)
        self.name = "mock" if settings.vlm_base_url == "mock" else f"vllm:{settings.vlm_model}"
        self._client = None
        self._lock = threading.Lock()

    def _get(self):
        with self._lock:
            if self._client is None:
                from openai import OpenAI
                self._client = OpenAI(base_url=self.s.vlm_base_url, api_key=self.s.vlm_api_key,
                                      timeout=self.s.vlm_timeout, max_retries=0)
            return self._client

    def _once(self, messages, temperature: float, timeout: float) -> str:
        extra = {"chat_template_kwargs": {"enable_thinking": False}} if self.s.disable_thinking else None
        stream = self._get().with_options(timeout=timeout).chat.completions.create(
            model=self.s.vlm_model, messages=messages, temperature=temperature,
            max_tokens=self.s.max_tokens, stream=True, extra_body=extra)
        chunks = []
        t_end = time.time() + timeout
        for ev in stream:
            if ev.choices:
                delta = ev.choices[0].delta
                if delta is not None and delta.content:
                    chunks.append(delta.content)
            if time.time() > t_end:
                stream.close()
                raise TimeoutError(f"generation exceeded {timeout:.0f} s")
        return "".join(chunks)

    def chat(self, messages, temperature: float, deadline: float, seed: str = "") -> str:
        """Return raw model text. Retries transport errors up to settings.vlm_retries times."""
        if self.s.vlm_base_url == "mock":
            return _mock_response(messages, seed)
        last = None
        for attempt in range(self.s.vlm_retries + 1):
            left = deadline - time.time()
            if attempt and left < 30:
                break
            timeout = max(30.0, min(self.s.vlm_timeout, left))
            try:
                return self._once(messages, temperature, timeout)
            except Exception as e:  # noqa: BLE001  network / server / timeout
                if getattr(e, "status_code", None) == 400:
                    raise VLMRequestTooLarge(f"model server rejected the request: {str(e)[:300]}") from e
                last = f"{type(e).__name__}: {str(e)[:300]}"
                log.warning("VLM call attempt %d failed: %s", attempt + 1, last)
                if attempt < self.s.vlm_retries:
                    time.sleep(min(2 + 3 * attempt, max(0.0, deadline - time.time() - 30)))
        raise VLMError(f"model call failed: {last or 'time budget exhausted'}")
