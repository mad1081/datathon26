"""CPU integration validation: real backend + local HTTP stub, never a model.

Needs backend CPU dependencies, imageio-ffmpeg, and httpx for FastAPI TestClient.
Run from repo root. Artifacts are written to .validation and analysis/.
"""
from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.validation/cpu-deps'), str(ROOT / 'deploy/vllm'), str(ROOT / 'service')]

import cv2
import imageio_ffmpeg
import numpy as np

from smoke_multi_image import check_answer, run

OUT = ROOT / '.validation/cpu-integration'
OUT.mkdir(parents=True, exist_ok=True)
requests_seen = []


def dominant_color(image):
    return ['blue', 'green', 'red'][int(np.argmax(image.mean(axis=(0, 1))))]


def decode_video(data):
    with tempfile.NamedTemporaryFile(dir=OUT, suffix='.mp4', delete=False) as target:
        target.write(data)
        path = Path(target.name)
    cap = cv2.VideoCapture(str(path))
    colors, count, dimensions = [], 0, None
    try:
        while True:
            ok, image = cap.read()
            if not ok:
                break
            count += 1
            dimensions = [image.shape[1], image.shape[0]]
            color = dominant_color(image)
            if not colors or colors[-1] != color:
                colors.append(color)
    finally:
        cap.release()
        path.unlink()
    return {'colors': colors, 'frame_count': count, 'dimensions': dimensions}


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        assert self.path == '/v1/chat/completions'
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        content = body['messages'][-1]['content']
        images, dimensions, video = [], [], None
        for item in content:
            if item['type'] == 'image_url':
                data = base64.b64decode(item['image_url']['url'].split(',', 1)[1])
                image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                images.append(dominant_color(image))
                dimensions.append([image.shape[1], image.shape[0]])
            elif item['type'] == 'video_url':
                video = decode_video(base64.b64decode(item['video_url']['url'].split(',', 1)[1]))
        prompt = ' '.join(i['text'] for i in content if i['type'] == 'text')
        is_smoke = 'English color names' in prompt
        if is_smoke:
            answer = {}
            if images:
                answer.update(first=images[0], second=images[1])
            if video:
                answer['video_colors'] = video['colors']
        else:
            answer = {'scene': 'CPU transport stub; not a model', 'events': [], 'states': {}}
        requests_seen.append({'model': body['model'], 'image_count': len(images), 'video': video,
                              'image_dimensions': dimensions, 'smoke': is_smoke,
                              'authorization_header_present': bool(self.headers.get('Authorization'))})
        result = {'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(answer)}}]}
        encoded = json.dumps(result).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main():
    model = 'Qwen/Qwen3.5-9B'
    server = ThreadingHTTPServer(('127.0.0.1', 0), Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}/v1'
    try:
        smoke = run(model, base, OUT / 'smoke', mode='all', ffmpeg=imageio_ffmpeg.get_ffmpeg_exe())
        assert smoke['all_passed']
        fixture = decode_video((OUT / 'smoke/three-colors.mp4').read_bytes())
        assert fixture == {'colors': ['red', 'green', 'blue'], 'frame_count': 72, 'dimensions': [464, 848]}, fixture
        # A test that accepts reversed colors or token-truncated answers is unsafe as a gate.
        for answer, finish in [({'video_colors': ['blue', 'green', 'red']}, 'stop'),
                               ({'video_colors': ['red', 'green', 'blue']}, 'length')]:
            try:
                check_answer({'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(answer)}}]}, 'video')
            except ValueError:
                pass
            else:
                raise AssertionError('Smoke accepted incorrect/incomplete answer')
        with tempfile.TemporaryDirectory(dir=OUT, prefix='app-') as data_dir:
            os.environ.update(VLM_BACKEND='openai', OPENAI_BASE_URL=base, OPENAI_MODEL=model,
                              WINDOW_CONCURRENCY='6', FRAME_MAX_SIDE='1024',
                              API_KEY='cpu-transport-test-secret', DATA_DIR=data_dir)
            from app.main import app
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                health = client.get('/api/v1/health')
                assert health.status_code == 200 and health.json()['backend'] == 'openai'
                assert client.get('/api/v1/jobs/no-key').status_code == 401
                headers = {'X-API-Key': os.environ['API_KEY']}
                with (OUT / 'smoke/three-colors.mp4').open('rb') as source:
                    response = client.post('/api/v1/analyze', headers=headers,
                                           files={'file': ('three-colors.mp4', source, 'video/mp4')})
                assert response.status_code == 202, response.text
                job_id = response.json()['job_id']
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    job = client.get(f'/api/v1/jobs/{job_id}', headers=headers).json()
                    if job['status'] != 'processing':
                        break
                    time.sleep(0.1)
                assert job['status'] == 'done', job
        backend_requests = [r for r in requests_seen if not r['smoke']]
        assert backend_requests and all(r['model'] == model for r in backend_requests)
        assert all(r['video'] is None for r in backend_requests)
        assert all(d == [464, 848] for r in backend_requests for d in r['image_dimensions'])
        assert any(r['image_count'] > 1 for r in backend_requests)
        report = {'scope': 'CPU integration with local HTTP stub; no vLLM, model weights, GPU, or AWS',
                  'fixture': fixture, 'smoke_transport': smoke,
                  'backend_health_auth_upload_job': 'passed', 'backend_native_frame_dimensions': 'preserved',
                  'wrong_color_and_truncation_rejected': True, 'requests': requests_seen,
                  'gpu_inference_verified': False}
        (ROOT / 'analysis/vllm_cpu_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('PASS: 72 decoded frames; ordered RGB; images/video/mixed HTTP transports; wrong answers rejected; real backend auth/upload/job; frame dimensions preserved.')
        print('This used a CPU HTTP stub. It does not validate any model or vLLM inference.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
