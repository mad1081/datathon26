import hashlib
import json
import random
import re
import time

import config

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(base_url=config.VLM_BASE_URL, api_key=config.VLM_API_KEY,
                         timeout=config.TIMEOUT, max_retries=0)
    return _client


def extract_json(text):
    """Parse the first top-level JSON object from model output; None if impossible."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, flags=re.S)
    candidates = [fence.group(1)] if fence else []
    candidates.append(t)
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        start = c.find("{")
        end = c.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(c[start:end + 1])
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass
    return None


def _mock_response(messages, seed):
    rng = random.Random(int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16))
    times = []
    for part in messages[-1]["content"]:
        if part["type"] == "text" and part["text"].startswith("[t="):
            times.append(float(part["text"][3:].split()[0]))
    duration = times[-1] if times else 30.0
    if rng.random() < 0.05:
        return "Не могу определить нарушение по кадрам."
    ids = [r["id"] for r in config.load_rules()["rules"]]
    violations = []
    if rng.random() < 0.55:
        for _ in range(rng.choice([1, 1, 2])):
            violations.append({
                "type_id": rng.choice(ids),
                "timecode_sec": round(rng.uniform(0, duration), 1),
                "confidence": round(rng.uniform(0.4, 0.95), 2),
                "observed": "тестовое наблюдение",
            })
    body = {
        "scenario": "тестовый сценарий",
        "timeline": [{"t": 0.0, "event": "начало"}, {"t": duration, "event": "конец"}],
        "violations": violations,
    }
    return "```json\n" + json.dumps(body, ensure_ascii=False) + "\n```"


def chat(messages, temperature=None, max_tokens=None, mock_seed=""):
    """Call the VLM endpoint. Returns dict(text, parsed, latency_sec, attempts, error, usage)."""
    temperature = config.TEMPERATURE if temperature is None else temperature
    max_tokens = max_tokens or config.MAX_TOKENS
    t0 = time.time()
    if config.VLM_BASE_URL == "mock":
        text = _mock_response(messages, mock_seed)
        return {"text": text, "parsed": extract_json(text), "latency_sec": round(time.time() - t0, 3),
                "attempts": 1, "error": None, "usage": None}

    extra = {}
    if config.DISABLE_THINKING:
        extra["chat_template_kwargs"] = {"enable_thinking": False}
    last_err = None
    for attempt in range(config.RETRIES + 1):
        t_attempt = time.time()
        try:
            stream = _get_client().chat.completions.create(
                model=config.VLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
                extra_body=extra or None,
            )
            chunks = []
            usage = None
            for ev in stream:
                if getattr(ev, "usage", None):
                    usage = ev.usage.model_dump() if hasattr(ev.usage, "model_dump") else dict(ev.usage)
                if ev.choices:
                    delta = ev.choices[0].delta
                    if delta is not None and delta.content:
                        chunks.append(delta.content)
            text = "".join(chunks)
            return {"text": text, "parsed": extract_json(text), "latency_sec": round(time.time() - t_attempt, 3),
                    "total_sec": round(time.time() - t0, 3), "attempts": attempt + 1, "error": None, "usage": usage}
        except Exception as e:  # network/proxy/server errors: retry
            last_err = f"{type(e).__name__}: {e}"
            if attempt < config.RETRIES:
                time.sleep(2 + 3 * attempt)
    return {"text": None, "parsed": None, "latency_sec": round(time.time() - t0, 3), "attempts": config.RETRIES + 1,
            "error": last_err, "usage": None}
