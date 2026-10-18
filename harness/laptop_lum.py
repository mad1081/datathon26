"""Laptop screen brightness trace: VLM grounds the screen box once, OpenCV measures luminance over time."""
import json
import re

import cv2
import numpy as np

import config
from client import chat
from frames import _read_indices, b64, video_info

PROMPT = ('Найди на кадре экран ноутбука, стоящего на столе кассира (открытая крышка с экраном). '
          'Ответь только JSON: {"bbox_2d": [x1, y1, x2, y2]} — координаты экрана в шкале 0–1000 по ширине и высоте кадра. '
          'Если ноутбук не виден или крышка закрыта: {"bbox_2d": null}.')


def read_gray(path, times):
    info = video_info(path)
    vfps, n = info["fps"], max(info["frame_count"], 1)
    idx = {t: min(max(int(round(t * vfps)), 0), n - 1) for t in times}
    raw = _read_indices(path, idx.values(), 10_000, 95)
    out = {}
    for t, i in idx.items():
        if i in raw:
            out[t] = cv2.imdecode(np.frombuffer(raw[i], np.uint8), cv2.IMREAD_COLOR)
    return out


def ground(img):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    msgs = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64(buf.tobytes())}},
        {"type": "text", "text": PROMPT}]}]
    res = chat(msgs, temperature=0.0, max_tokens=100)
    box = (res["parsed"] or {}).get("bbox_2d")
    if box is None and res["text"]:
        m = re.search(r"\[(\s*\d+\s*,){3}\s*\d+\s*\]", res["text"])
        box = json.loads(m.group(0)) if m else None
    return box, res


def box_px(box, img):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in box]
    x1, x2 = sorted((x1 * w / 1000, x2 * w / 1000))
    y1, y2 = sorted((y1 * h / 1000, y2 * h / 1000))
    return int(x1), int(y1), max(int(x2), int(x1) + 1), max(int(y2), int(y1) + 1)


def luminance(img, px):
    x1, y1, x2, y2 = px
    roi = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    # bright-screen fraction is robust to a partly occluding hand/head
    return float(np.percentile(roi, 75)) if roi.size else 0.0
