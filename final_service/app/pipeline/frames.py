"""Video decoding: frame sampling for the model and full-resolution evidence frames."""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2


def _open(path):
    cap = cv2.VideoCapture(str(path))
    if cap.isOpened():
        return cap, None
    # OpenCV on Windows can fail on non-ASCII paths; fall back to an ASCII temp copy.
    tmp_dir = tempfile.mkdtemp(prefix="vid_")
    tmp = os.path.join(tmp_dir, "video" + os.path.splitext(str(path))[1])
    shutil.copyfile(path, tmp)
    cap = cv2.VideoCapture(tmp)
    if not cap.isOpened():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"cannot open video: {Path(path).name}")
    return cap, tmp_dir


def ensure_decodable(path: str, workdir: Path) -> str:
    """Return a path OpenCV can read; transcode with ffmpeg if needed (e.g. HEVC .mov)."""
    try:
        cap, tmp = _open(path)
        ok, _ = cap.read()
        cap.release()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    except RuntimeError:
        ok = False
    if ok:
        return path
    if not shutil.which("ffmpeg"):
        raise RuntimeError("OpenCV cannot decode the file and ffmpeg is not installed")
    out = str(workdir / "decoded.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "20", out], check=True, timeout=120)
    return out


def _resize(img, max_side):
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def _encode(img, quality):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return buf.tobytes()


def video_info(path) -> dict:
    cap, tmp = _open(path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        if fps <= 1e-3 or fps > 240:
            fps = 30.0
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if n <= 0:
            while cap.grab():
                n += 1
        return {"fps": fps, "frame_count": n, "duration_sec": n / fps, "width": w, "height": h}
    finally:
        cap.release()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def read_indices(path, wanted, max_side, quality) -> dict[int, bytes]:
    """Sequentially decode and return {frame_idx: jpeg_bytes} for the wanted indices."""
    wanted = sorted(set(int(w) for w in wanted))
    out: dict[int, bytes] = {}
    if not wanted:
        return out
    cap, tmp = _open(path)
    try:
        last = wanted[-1]
        wanted_set = set(wanted)
        idx = 0
        last_img = None
        while idx <= last:
            if not cap.grab():
                break
            if idx in wanted_set:
                ok, img = cap.retrieve()
                if ok:
                    last_img = img
                    out[idx] = _encode(_resize(img, max_side), quality)
            idx += 1
        # Frame count metadata can overshoot; pad tail requests with the last decoded frame.
        if last_img is not None:
            for w in wanted:
                if w not in out and w >= idx:
                    out[w] = _encode(_resize(last_img, max_side), quality)
    finally:
        cap.release()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return out


def sample_frames(path, info, fps_short, fps_long, short_video_sec, max_frames, max_side, quality):
    """Return [{"t", "idx", "jpeg"}]: fps_short for short videos, fps_long otherwise, capped at max_frames."""
    vfps, n = info["fps"], info["frame_count"]
    fps = fps_short if n / vfps < short_video_sec else fps_long
    step = max(1, round(vfps / fps))
    while n and (n + step - 1) // step > max_frames:
        step += 1
    indices = list(range(0, max(n, 1), step))
    jpegs = read_indices(path, indices, max_side, quality)
    return [{"t": round(i / vfps, 2), "idx": i, "jpeg": jpegs[i]} for i in indices if i in jpegs]


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
