"""Tiny OpenAI-compatible fake VLM server for local tests (streams a fixed JSON answer).

    python tests/fake_vlm.py --port 8011 --mode ok|garbage|error
"""
import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSWER = {
    "scenario": "Приём наличных от клиента",
    "timeline": [{"t": 0.0, "event": "кассир за столом"}, {"t": 5.0, "event": "клиент передаёт деньги"},
                 {"t": 12.0, "event": "кассир осматривает купюру"}],
    "violations": [
        {"type_id": "suspicious_note_returned", "timecode_sec": 12.0, "confidence": 0.85,
         "observed": "кассир возвращает клиенту осмотренную купюру"},
        {"type_id": "counting_without_controller", "timecode_sec": 3.0, "confidence": 0.9, "observed": "x"},
        {"type_id": "other", "timecode_sec": 4.0, "confidence": 0.9, "observed": "прочее"},
    ],
}


class Handler(BaseHTTPRequestHandler):
    mode = "ok"
    max_images = 0
    calls = 0

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._json(200, {"object": "list", "data": [{"id": "fake", "object": "model"}]})

    def do_POST(self):
        Handler.calls += 1
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        if self.mode == "error":
            return self._json(500, {"error": "boom"})
        texts = [p["text"] for m in req["messages"] if isinstance(m["content"], list)
                 for p in m["content"] if p.get("type") == "text"]
        n_img = sum(1 for m in req["messages"] if isinstance(m["content"], list)
                    for p in m["content"] if p.get("type") == "image_url")
        if self.max_images and n_img > self.max_images:
            return self._json(400, {"object": "error", "message": f"maximum context length exceeded ({n_img} images)"})
        last_t = max((float(m.group(1)) for t in texts for m in [re.match(r"\[t=([\d.]+)", t)] if m), default=0)
        answer = dict(ANSWER, scenario=f"{ANSWER['scenario']} ({n_img} кадров, до {last_t:.1f} с)")
        text = "I cannot help with that." if self.mode == "garbage" else "```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for i in range(0, len(text), 40):
            chunk = {"id": "x", "object": "chat.completion.chunk", "created": 0, "model": req.get("model"),
                     "choices": [{"index": 0, "delta": {"content": text[i:i + 40]}, "finish_reason": None}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8011)
    ap.add_argument("--mode", default="ok", choices=["ok", "garbage", "error"])
    ap.add_argument("--max-images", type=int, default=0, help="reject larger requests with HTTP 400")
    a = ap.parse_args()
    Handler.mode = a.mode
    Handler.max_images = a.max_images
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
