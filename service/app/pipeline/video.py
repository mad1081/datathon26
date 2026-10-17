"""Video decoding helpers (OpenCV, ffmpeg fallback for exotic .mov)."""
from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class VideoInfo:
    path: str
    fps: float
    n_frames: int
    duration: float
    width: int
    height: int


def _open(path: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    return cap


def ensure_decodable(path: str, workdir: Path) -> str:
    """Return a path OpenCV can read; transcode with ffmpeg if needed (e.g. HEVC .mov)."""
    cap = cv2.VideoCapture(path)
    ok, _ = cap.read() if cap.isOpened() else (False, None)
    cap.release()
    if ok:
        return path
    if not shutil.which("ffmpeg"):
        raise RuntimeError("OpenCV cannot decode the file and ffmpeg is not installed")
    out = str(workdir / "decoded.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "20", out], check=True)
    return out


def probe(path: str) -> VideoInfo:
    cap = _open(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if fps <= 1e-3 or fps > 240:
        fps = 30.0
    if n <= 0:  # count manually
        cap = _open(path)
        n = 0
        while cap.grab():
            n += 1
        cap.release()
    return VideoInfo(path, fps, n, n / fps if fps else 0.0, w, h)


def resize_max(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    s = max(h, w)
    if s <= max_side:
        return img
    k = max_side / s
    return cv2.resize(img, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)


def sample_frames(info: VideoInfo, fps: float, max_side: int) -> list[tuple[float, int, np.ndarray]]:
    """Sequentially decode, keep ~`fps` frames per second. Returns (t_sec, frame_idx, BGR image)."""
    step = max(1, int(round(info.fps / fps)))
    cap = _open(info.path)
    out, idx = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                out.append((idx / info.fps, idx, resize_max(frame, max_side)))
        idx += 1
    cap.release()
    return out


def read_range(info: VideoInfo, t0: float, t1: float, max_side: int | None = None,
               every: int = 1) -> list[tuple[float, int, np.ndarray]]:
    """Decode all frames (or every n-th) in [t0, t1] at native fps."""
    i0 = max(0, int(t0 * info.fps))
    i1 = min(info.n_frames - 1, int(t1 * info.fps))
    cap = _open(info.path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, i0)
    out = []
    for idx in range(i0, i1 + 1):
        ok, frame = cap.read()
        if not ok:
            break
        if (idx - i0) % every == 0:
            out.append((idx / info.fps, idx, resize_max(frame, max_side) if max_side else frame))
    cap.release()
    return out


def read_frame(info: VideoInfo, idx: int) -> np.ndarray | None:
    cap = _open(info.path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(idx, info.n_frames - 1)))
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def to_jpeg_b64(img: np.ndarray, max_side: int = 1280, quality: int = 88) -> str:
    img = resize_max(img, max_side)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def bgr_to_pil(img: np.ndarray):
    from PIL import Image
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def tmpdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="vid_"))
