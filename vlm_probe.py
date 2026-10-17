"""Ask a local VLM (Qwen3-VL, Apache-2.0, via MLX) what happens around a timestamp.

Usage: uv run vlm_probe.py [video ...]   (default: all labeled violations at their label time)
Output: cache/probe/<video>.txt
"""
import sys
from pathlib import Path

import cv2
from PIL import Image
from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template

from evaluate import load_labels

MODEL_ID = "mlx-community/Qwen3-VL-8B-Instruct-4bit"
VIDEO_DIR = Path("open/videos")
OUT_DIR = Path("cache/probe")
WINDOW_OFFSETS_SEC = (-4, -3, -2, -1, 0, 1, 2, 3)
FRAME_HEIGHT = 560
CLEAN_VIDEO_PROBE_SEC = 10

PROMPT = (
    "These are {n} frames, 1 second apart, from an overhead CCTV camera in a bank cash room. "
    "Scene layout: a wooden cashier desk with a laptop/monitor and a banknote counting machine; "
    "the grey metal box/cabinet standing next to the desk is the CASH SAFE; the glass wall with a glass "
    "door at the back is the entrance to the cash room. Describe chronologically and factually what each person does: "
    "cashier, clients, cash-in-transit collectors. Pay attention to: handling of cash or bags, the safe "
    "(open/closed), the door, who enters or leaves, whether the cashier leaves the workstation, phones, "
    "personal items. Then state whether anything looks like a breach of cash-handling security procedures, "
    "and which frame shows it best. Do not identify people."
)


def frames_at(path: Path, center: float):
    cap = cv2.VideoCapture(str(path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30)
    images = []
    for off in WINDOW_OFFSETS_SEC:
        t = min(max(center + off, 0), duration - 0.1)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        images.append(img.resize((round(img.width * FRAME_HEIGHT / img.height), FRAME_HEIGHT)))
    cap.release()
    return images


def main(videos):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    labels = load_labels()
    model, processor = load(MODEL_ID)
    for video in videos:
        out = OUT_DIR / f"{video}.txt"
        if out.exists():
            continue
        t = labels[video]["t"] if labels[video]["verdict"] else CLEAN_VIDEO_PROBE_SEC
        images = frames_at(VIDEO_DIR / f"{video}.mov", t)
        prompt = apply_chat_template(processor, model.config, PROMPT.format(n=len(images)), num_images=len(images))
        result = generate(model, processor, prompt, image=images, max_tokens=500, temperature=0.0, verbose=False)
        text = result.text if hasattr(result, "text") else str(result)
        out.write_text(f"{video} label={labels[video]} center={t}\n{text}\n")
        print(f"== {video} @ {t}\n{text}\n", flush=True)


if __name__ == "__main__":
    labels = load_labels()
    main(sys.argv[1:] or [v for v, l in labels.items() if l["verdict"]])
