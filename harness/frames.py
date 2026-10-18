import base64
import os
import shutil
import tempfile
import threading
from collections import OrderedDict

import cv2

import config


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
        raise RuntimeError(f"cannot open video: {path}")
    return cap, tmp_dir


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


def video_info(path):
    cap, tmp = _open(path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        return {"fps": fps, "frame_count": n, "duration_sec": n / fps if fps else 0.0,
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}
    finally:
        cap.release()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _read_indices(path, wanted, max_side, quality):
    """Sequentially decode and return {frame_idx: jpeg_bytes} for the wanted indices."""
    wanted = sorted(set(wanted))
    out = {}
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


_cache = OrderedDict()
_cache_lock = threading.Lock()
_CACHE_SIZE = 12


def sample_frames(path, fps=None, max_frames=None, max_side=None, quality=None):
    """Return list of {"t": sec, "idx": frame_idx, "jpeg": bytes} sampled at `fps`."""
    fps = fps or config.FPS
    max_frames = max_frames or config.MAX_FRAMES
    max_side = max_side or config.MAX_SIDE
    quality = quality or config.JPEG_QUALITY
    key = (str(path), fps, max_frames, max_side, quality)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    info = video_info(path)
    vfps = info["fps"]
    n = info["frame_count"]
    if config.FPS_ADAPTIVE and fps == config.FPS:
        fps = config.FPS_SHORT if n / vfps < config.SHORT_VIDEO_SEC else config.FPS_LONG
    step = max(1, round(vfps / fps))
    while n and (n + step - 1) // step > max_frames:
        step += 1
    indices = list(range(0, max(n, 1), step))
    jpegs = _read_indices(path, indices, max_side, quality)
    frames = [{"t": round(i / vfps, 2), "idx": i, "jpeg": jpegs[i]} for i in indices if i in jpegs]

    with _cache_lock:
        _cache[key] = frames
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return frames


def frames_at_times(path, times, max_side=None, quality=90):
    """Return [{"timestamp_sec", "jpeg"}] from the original video at the given seconds."""
    max_side = max_side or config.EVIDENCE_MAX_SIDE
    info = video_info(path)
    vfps = info["fps"]
    n = max(info["frame_count"], 1)
    idx_for = {}
    for t in times:
        i = min(max(int(round(t * vfps)), 0), n - 1)
        idx_for[t] = i
    jpegs = _read_indices(path, idx_for.values(), max_side, quality)
    out = []
    for t, i in idx_for.items():
        if i in jpegs:
            out.append({"timestamp_sec": round(i / vfps, 2), "jpeg": jpegs[i]})
    return out


def b64(data):
    return base64.b64encode(data).decode("ascii")
