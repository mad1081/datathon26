"""eval.py with a higher frame rate for very short videos (FPS_VERY_SHORT below VERY_SHORT_SEC)."""
import sys

import analyze
import config
import eval as ev
import frames

FPS_VERY_SHORT = config.env_float("FPS_VERY_SHORT", 3.0)
VERY_SHORT_SEC = config.env_float("VERY_SHORT_SEC", 40.0)


def sample_frames(path, *a, **kw):
    if frames.video_info(path)["duration_sec"] < VERY_SHORT_SEC:
        return frames.sample_frames(path, fps=FPS_VERY_SHORT)
    return frames.sample_frames(path, *a, **kw)


analyze.sample_frames = sample_frames

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ev.main()
