"""Generate synthetic .mov test videos (top-down 'cash room' cartoon).

violation.mov    : red 'cash stack' left on the desk from 4.0 s to 9.0 s while the 'cashier' walks out at ~4 s
no_violation.mov : same scene without the red object
"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np


def make(path: Path, with_cash: bool, seconds=12, fps=30, w=1280, h=720):
    raw = path.with_suffix(".avi")
    vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    for i in range(seconds * fps):
        t = i / fps
        img = np.full((h, w, 3), (200, 205, 210), np.uint8)
        cv2.rectangle(img, (300, 200), (980, 480), (90, 120, 150), -1)       # desk
        cv2.rectangle(img, (1050, 150), (1200, 350), (60, 60, 60), -1)       # safe
        cv2.rectangle(img, (40, 560), (200, 700), (40, 90, 140), -1)         # door
        x = 640 if t < 4 else int(640 - (t - 4) * 250)                       # cashier walks out
        if x > -60:
            cv2.circle(img, (x, 540), 55, (40, 40, 40), -1)
        if with_cash and 4.0 <= t < 9.0:
            cv2.rectangle(img, (560, 300), (720, 380), (30, 30, 220), -1)    # red 'cash'
        cv2.putText(img, f"t={t:5.2f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        vw.write(img)
    vw.release()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-an", str(path)], check=True)
    raw.unlink()


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/data")
    out.mkdir(parents=True, exist_ok=True)
    make(out / "violation.mov", True)
    make(out / "no_violation.mov", False)
    print("written to", out)
