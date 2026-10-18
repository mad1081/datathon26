"""Synthetic images, MP4, and mixed modalities in single OpenAI-compatible requests.

CPU-only --dry-run generates fixtures/payloads; it does NOT prove model support.
Live mode saves responses before checking ordered colors and exits nonzero on failure.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import time
import urllib.error
import urllib.request
import zlib

from serve import select_model


def color_png(rgb, side=224):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    pixels = (b'\x00' + bytes(rgb) * side) * side
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', side, side, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


def make_video(path, ffmpeg='ffmpeg'):
    """Six seconds, three two-second segments, 464x848, 12 FPS, H.264/yuv420p."""
    path.parent.mkdir(parents=True, exist_ok=True)
    argv = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y']
    for color in ['0xFF0000', '0x00FF00', '0x0000FF']:
        argv += ['-f', 'lavfi', '-i', f'color=c={color}:s=464x848:r=12:d=2']
    argv += ['-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]', '-map', '[v]',
             '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)]
    subprocess.run(argv, check=True, timeout=60, capture_output=True)
    return path.read_bytes()


def make_payload(model_id, mode='images', video=None):
    _, spec, _ = select_model({'VLM_MODEL': model_id})
    if mode not in {'images', 'video', 'mixed'}:
        raise ValueError(f'Unknown smoke mode: {mode}')
    prompts = []
    content = []
    if mode in {'images', 'mixed'}:
        prompts.append('Identify the dominant colors of the two still images in input order. '
                       'Use keys "first" and "second" with English color names.')
        for rgb in [(255, 0, 0), (0, 0, 255)]:
            content.append({'type': 'image_url', 'image_url': {
                'url': 'data:image/png;base64,' + base64.b64encode(color_png(rgb)).decode('ascii')}})
    if mode in {'video', 'mixed'}:
        if not video:
            raise ValueError('Video bytes are required')
        prompts.append('Watch the video. Name its three dominant color segments in chronological order. '
                       'Use key "video_colors" with a list of three English color names.')
        content.append({'type': 'video_url', 'video_url': {
            'url': 'data:video/mp4;base64,' + base64.b64encode(video).decode('ascii')}})
    content.insert(0, {'type': 'text', 'text': ' '.join(prompts) + ' Return only one JSON object.'})
    payload = {'model': model_id, 'messages': [{'role': 'user', 'content': content}],
               'max_tokens': 512, 'temperature': 0, 'seed': 0, 'stream': False}
    payload.update(spec.get('request_defaults', {}))
    return payload


def check_answer(response, mode='images'):
    choice = response['choices'][0]
    if choice.get('finish_reason') == 'length':
        raise ValueError('Response hit token limit; smoke test is inconclusive')
    content = choice['message'].get('content') or ''
    for obj in re.findall(r'\{[^{}]*\}', content):
        try:
            answer = json.loads(obj)
        except json.JSONDecodeError:
            continue
        normalize = lambda s: s.strip().lower() if isinstance(s, str) else None
        images_ok = (normalize(answer.get('first')) == 'red' and normalize(answer.get('second')) == 'blue')
        colors = answer.get('video_colors')
        video_ok = isinstance(colors, list) and [normalize(c) for c in colors] == ['red', 'green', 'blue']
        if (mode == 'video' or images_ok) and (mode == 'images' or video_ok):
            return True
    raise ValueError(f'{mode}: incorrect/missing ordered colors; inspect saved raw response')


def run(model, base_url, output_dir, mode='all', dry_run=False, timeout=300, ffmpeg='ffmpeg'):
    output_dir.mkdir(parents=True, exist_ok=True)
    modes = ['images', 'video', 'mixed'] if mode == 'all' else [mode]
    video = make_video(output_dir / 'three-colors.mp4', ffmpeg) if any(m != 'images' for m in modes) else None
    summary = {'model': model, 'dry_run': dry_run, 'checks': [], 'gpu_inference_verified': False}
    for selected in modes:
        payload = make_payload(model, selected, video)
        (output_dir / f'{selected}.request.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        if dry_run:
            summary['checks'].append({'mode': selected, 'status': 'payload_generated_only'})
            continue
        start = time.monotonic()
        status = 'failed'
        error_text = None
        try:
            headers = {'Content-Type': 'application/json'}
            if os.environ.get('VLLM_API_KEY'):
                headers['Authorization'] = 'Bearer ' + os.environ['VLLM_API_KEY']
            request = urllib.request.Request(base_url.rstrip('/') + '/chat/completions',
                                            data=json.dumps(payload).encode(), headers=headers, method='POST')
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode('utf-8')
            (output_dir / f'{selected}.response.json').write_text(raw + '\n', encoding='utf-8')
            check_answer(json.loads(raw), selected)
            status = 'passed'
        except urllib.error.HTTPError as error:
            raw = error.read().decode('utf-8', errors='replace')
            (output_dir / f'{selected}.response.txt').write_text(raw, encoding='utf-8')
            error_text = f'HTTP {error.code}: {raw[:2000]}'
        except (ValueError, KeyError, IndexError, TypeError, urllib.error.URLError, TimeoutError) as error:
            error_text = str(error)
        summary['checks'].append({'mode': selected, 'status': status,
                                  'seconds': round(time.monotonic() - start, 3), 'error': error_text})
    # A responding endpoint could be a mock; this client cannot attest GPU execution.
    summary['all_passed'] = not dry_run and all(c['status'] == 'passed' for c in summary['checks'])
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default=os.environ.get('VLM_MODEL') or os.environ.get('OPENAI_MODEL', 'Qwen/Qwen3.5-9B'))
    parser.add_argument('--base-url', default='http://vlm:8000/v1')
    parser.add_argument('--output-dir', type=Path, default=Path('results/smoke'))
    parser.add_argument('--mode', choices=['images', 'video', 'mixed', 'all'], default='all')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    try:
        summary = run(args.model, args.base_url, args.output_dir, args.mode, args.dry_run, args.timeout, args.ffmpeg)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Fixture/configuration error: {error}\n')
    print(json.dumps(summary, indent=2))
    if not args.dry_run and not summary['all_passed']:
        parser.exit(1, 'Smoke failed; see saved raw responses.\n')


if __name__ == '__main__':
    main()
