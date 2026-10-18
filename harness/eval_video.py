"""Run prompt_v3b with native video input (video_url) against one vLLM server; cache in eval.py format.

python harness/eval_video.py --served qwen3vl-32b --base-url https://.../v1 --repeats 5 --concurrency 8
then: python harness/eval.py --name video-qwen3vl-32b-v3b --repeats 5 --score-only
"""
import argparse
import base64
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import video_mode
from client import extract_json
from eval import cache_path, list_videos, run_dir


def read_key():
    toks = (config.HARNESS_DIR / ".vlm_key").read_text(encoding="utf-8").split()
    return toks[1] if len(toks) > 1 else toks[0]


class Runner:
    def __init__(self, args):
        from openai import OpenAI
        self.args = args
        self.client = OpenAI(base_url=args.base_url, api_key=read_key(), timeout=args.timeout, max_retries=0)
        self.use_mm_kwargs = not args.no_mm_kwargs
        self.use_mov = args.mov
        self.lock = threading.Lock()
        self.notes = []

    def _payload(self, video):
        data, meta = video_mode.encode(video)
        if self.use_mov:
            return video_mode.build_messages(video.read_bytes(), meta, mime="video/quicktime"), meta, "mov"
        return video_mode.build_messages(data, meta), meta, meta["fourcc"]

    def call(self, video, k):
        messages, meta, fmt = self._payload(video)
        t0 = time.time()
        last_err = None
        attempts = 0
        for attempt in range(self.args.retries + 1):
            attempts = attempt + 1
            extra = {"mm_processor_kwargs": {"fps": meta["sample_fps"]}} if self.use_mm_kwargs else None
            ta = time.time()
            try:
                stream = self.client.chat.completions.create(
                    model=self.args.served, messages=messages, temperature=self.args.temperature,
                    max_tokens=self.args.max_tokens, stream=True, stream_options={"include_usage": True},
                    extra_body=extra)
                chunks, usage = [], None
                for ev in stream:
                    if getattr(ev, "usage", None):
                        usage = ev.usage.model_dump()
                    if ev.choices and ev.choices[0].delta is not None and ev.choices[0].delta.content:
                        chunks.append(ev.choices[0].delta.content)
                text = "".join(chunks)
                return self._result(video, k, meta, fmt, text, round(time.time() - ta, 3), attempts, None, usage)
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                msg = str(e)
                with self.lock:
                    if len(self.notes) < 20:
                        self.notes.append(last_err[:600])
                status = getattr(e, "status_code", None)
                if status == 400 and self.use_mm_kwargs and ("mm_processor_kwargs" in msg or "fps" in msg):
                    with self.lock:
                        self.use_mm_kwargs = False
                    print(f"  disabling mm_processor_kwargs: {msg[:300]}", flush=True)
                    continue
                if status == 400 and not self.use_mov and ("video" in msg.lower() or "decode" in msg.lower()
                                                           or "codec" in msg.lower()):
                    with self.lock:
                        self.use_mov = True
                    print(f"  switching to original .mov: {msg[:300]}", flush=True)
                    messages, meta, fmt = self._payload(video)
                    continue
                if attempt < self.args.retries:
                    time.sleep(2 + 3 * attempt)
        return self._result(video, k, meta, fmt, None, round(time.time() - t0, 3), attempts, last_err, None)

    def _result(self, video, k, meta, fmt, text, latency, attempts, err, usage):
        return {
            "video": video.name, "key": config.video_key(video.name), "repeat": k, "model": self.args.served,
            "params": {"input": "video", "format": fmt, "fps": meta["sample_fps"], "max_side": config.MAX_SIDE,
                       "temperature": self.args.temperature, "mm_processor_kwargs": self.use_mm_kwargs,
                       "duration_sec": meta["duration_sec"]},
            "n_frames": meta["n_frames"], "frames_sec": 0.0, "latency_sec": latency, "attempts": attempts,
            "error": err, "usage": usage, "raw_text": text, "parsed": extract_json(text) if text else None,
            "timestamps": meta["timestamps"],
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--served", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--max-tokens", type=int, default=2500)
    ap.add_argument("--timeout", type=float, default=280.0)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--mov", action="store_true", help="send the original .mov instead of the re-encoded mp4")
    ap.add_argument("--no-mm-kwargs", action="store_true")
    args = ap.parse_args()
    name = args.name or f"video-{args.served}-v3b"

    videos = list_videos(args.limit)
    rd = run_dir(name)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "config.json").write_text(json.dumps({
        "name": name, "base_url": args.base_url, "model": args.served, "input": "video_url",
        "temperature": args.temperature, "max_tokens": args.max_tokens, "fps_short": config.FPS_SHORT,
        "fps_long": config.FPS_LONG, "max_side": config.MAX_SIDE, "prompt_module": "video_mode(prompt_v3b)",
        "mov": args.mov}, ensure_ascii=False, indent=1), encoding="utf-8")
    (rd / "system_prompt.txt").write_text(video_mode.build_system_prompt(), encoding="utf-8")

    runner = Runner(args)
    jobs = [(v, k) for k in range(args.repeats) for v in videos if not cache_path(name, v, k).exists()]
    print(f"{name}: {len(jobs)} calls, concurrency {args.concurrency}", flush=True)
    t0 = time.time()
    done = fails = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(runner.call, v, k): (v, k) for v, k in jobs}
        for fut in as_completed(futs):
            v, k = futs[fut]
            try:
                raw = fut.result()
            except Exception as e:
                fails += 1
                print(f"  crash {v.name} r{k}: {type(e).__name__}: {e}", flush=True)
                continue
            done += 1
            if raw["error"]:
                fails += 1
                status = "ERR " + raw["error"][:300]
            else:
                p = cache_path(name, v, k)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".tmp")
                tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
                os.replace(tmp, p)
                nv = len((raw["parsed"] or {}).get("violations") or []) if raw["parsed"] else "-"
                pt = (raw["usage"] or {}).get("prompt_tokens")
                status = f"ok viol={nv} ptok={pt}" if raw["parsed"] is not None else f"BADJSON ptok={pt}"
            print(f"  [{done}/{len(jobs)}] {raw['key']} r{k} {raw['latency_sec']:.1f}s {status} "
                  f"(elapsed {time.time() - t0:.0f}s)", flush=True)
    print(f"done: {done} calls, {fails} failed, mm_kwargs={runner.use_mm_kwargs} mov={runner.use_mov}")
    if runner.notes:
        print("errors seen:")
        for n in dict.fromkeys(runner.notes):
            print("  " + n)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
