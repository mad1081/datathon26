"""Native video input: re-encode a clip to a small mp4 and build a video_url chat message."""
import base64
import json
import os
import shutil
import tempfile
from pathlib import Path

import cv2

import config
import prompt_v3b
from frames import _open, _resize, video_info

CACHE_DIR = Path(os.getenv("VIDEO_CACHE_DIR", config.HARNESS_DIR / "runs" / "_video_cache"))
FOURCCS = [c.strip() for c in os.getenv("VIDEO_FOURCC", "avc1,mp4v").split(",") if c.strip()]

FRAME_LINE = ("- Каждый кадр подписан временем от начала видео в виде [t=12.0 с]. "
              "Все таймкоды в ответе — в секундах от начала видео, по этим подписям.")
VIDEO_LINE = ("- Тебе передаётся видеозапись целиком. Все таймкоды в ответе — в секундах от начала видео "
              "(0 — первый кадр), по времени внутри видео.")


def _sample_fps(duration):
    return config.FPS_SHORT if duration < config.SHORT_VIDEO_SEC else config.FPS_LONG


def _write(frames, out_fps, size, fourcc):
    tmp_dir = tempfile.mkdtemp(prefix="venc_")
    tmp = os.path.join(tmp_dir, "out.mp4")
    try:
        w = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*fourcc), out_fps, size)
        if not w.isOpened():
            return None
        for img in frames:
            if (img.shape[1], img.shape[0]) != size:
                img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            w.write(img)
        w.release()
        data = Path(tmp).read_bytes()
        # verify it decodes
        cap = cv2.VideoCapture(tmp)
        ok = cap.isOpened() and cap.read()[0]
        cap.release()
        return data if ok and len(data) > 1000 else None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def encode(video_path, fourccs=None):
    """Return (mp4_bytes, meta). Cached on disk per video key."""
    video_path = Path(video_path)
    key = config.video_key(video_path.name)
    fourccs = fourccs or FOURCCS
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for fc in fourccs:
        mp, mj = CACHE_DIR / f"{key}.{fc}.mp4", CACHE_DIR / f"{key}.{fc}.json"
        if mp.exists() and mj.exists():
            return mp.read_bytes(), json.loads(mj.read_text(encoding="utf-8"))

    info = video_info(video_path)
    vfps, n = info["fps"], info["frame_count"]
    duration = n / vfps if vfps else 0.0
    fps = _sample_fps(duration)
    step = max(1, round(vfps / fps))
    while n and (n + step - 1) // step > config.MAX_FRAMES:
        step += 1
    wanted = set(range(0, max(n, 1), step))
    imgs, times = [], []
    cap, tmp = _open(video_path)
    try:
        idx = 0
        while True:
            if not cap.grab():
                break
            if idx in wanted:
                ok, img = cap.retrieve()
                if ok:
                    imgs.append(_resize(img, config.MAX_SIDE))
                    times.append(round(idx / vfps, 3))
            idx += 1
    finally:
        cap.release()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    h, w = imgs[0].shape[:2]
    size = (w - w % 2, h - h % 2)
    out_fps = vfps / step
    last_err = None
    for fc in fourccs:
        data = _write(imgs, out_fps, size, fc)
        if data is None:
            last_err = f"fourcc {fc} failed"
            continue
        meta = {"key": key, "fourcc": fc, "src_fps": vfps, "src_frames": n, "duration_sec": round(duration, 3),
                "sample_fps": fps, "out_fps": out_fps, "step": step, "n_frames": len(imgs),
                "size": list(size), "bytes": len(data), "timestamps": times}
        (CACHE_DIR / f"{key}.{fc}.mp4").write_bytes(data)
        (CACHE_DIR / f"{key}.{fc}.json").write_text(json.dumps(meta), encoding="utf-8")
        return data, meta
    raise RuntimeError(f"cannot encode {video_path.name}: {last_err}")


def build_system_prompt():
    s = prompt_v3b.build_system_prompt()
    s = s.replace("Тебе показывают кадры записи камеры", "Тебе показывают видеозапись камеры")
    if FRAME_LINE in s:
        s = s.replace(FRAME_LINE, VIDEO_LINE)
    return s.replace("что именно видно на кадрах", "что именно видно на видео")


def instruction(meta):
    d = meta["duration_sec"]
    return (f"Выше — видеозапись длительностью {d:.1f} с (показана с частотой {meta['sample_fps']:g} кадр/с). "
            f"Все таймкоды (t, timecode_sec) указывай в секундах от начала видео, от 0 до {d:.1f}.\n"
            + prompt_v3b.INSTRUCTION.replace(
                "Выше — кадры одного видео в хронологическом порядке с подписями времени.\n", ""))


def build_messages(mp4_bytes, meta, mime="video/mp4"):
    url = f"data:{mime};base64," + base64.b64encode(mp4_bytes).decode("ascii")
    content = [{"type": "video_url", "video_url": {"url": url}},
               {"type": "text", "text": instruction(meta)}]
    return [{"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": content}]


if __name__ == "__main__":
    import sys
    from eval import list_videos
    for v in list_videos():
        data, meta = encode(v)
        print(meta["key"], meta["fourcc"], meta["duration_sec"], meta["n_frames"], meta["size"], meta["bytes"],
              flush=True)
