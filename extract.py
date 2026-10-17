"""Sample frames from each video and cache object detections (RT-DETRv2, Apache-2.0).

Usage: uv run extract.py [video ...]   (default: all of open/videos)
Output: cache/dets/<video>.json -> {"fps": .., "duration": .., "frames": [{"t": sec, "dets": [[label, score, x1, y1, x2, y2], ...]}]}
Boxes are normalized to [0, 1] so rules survive resolution / angle changes.
"""
import json
import sys
from pathlib import Path

import cv2
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForObjectDetection

MODEL_ID = "PekingU/rtdetr_v2_r50vd"
SAMPLE_FPS = 2
SCORE_THRESHOLD = 0.3
VIDEO_DIR = Path("open/videos")
OUT_DIR = Path("cache/dets")
DEVICE = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


def sample_frames(path: Path, sample_fps: float):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, round(fps / sample_fps))
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            yield i / fps, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        i += 1
    cap.release()


@torch.inference_mode()
def detect(model, processor, image: Image.Image):
    inputs = processor(images=image, return_tensors="pt").to(DEVICE)
    outputs = model(**inputs)
    w, h = image.size
    res = processor.post_process_object_detection(
        outputs, target_sizes=[(h, w)], threshold=SCORE_THRESHOLD
    )[0]
    return [
        [model.config.id2label[int(l)], round(float(s), 3),
         *[round(v, 4) for v in (b[0] / w, b[1] / h, b[2] / w, b[3] / h)]]
        for s, l, b in zip(res["scores"].tolist(), res["labels"].tolist(), res["boxes"].tolist())
    ]


def main(paths):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForObjectDetection.from_pretrained(MODEL_ID).to(DEVICE).eval()
    for path in paths:
        out = OUT_DIR / f"{path.stem}.json"
        if out.exists():
            continue
        frames = [{"t": round(t, 2), "dets": detect(model, processor, img)}
                  for t, img in sample_frames(path, SAMPLE_FPS)]
        out.write_text(json.dumps({"video": path.stem, "frames": frames}, ensure_ascii=False))
        print(f"{path.name}: {len(frames)} frames", flush=True)


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]] or sorted(VIDEO_DIR.glob("*.mov"))
    main(args)
