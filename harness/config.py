import json
import os
from functools import lru_cache
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
ROOT_DIR = HARNESS_DIR.parent
VIDEOS_DIR = Path(os.getenv("VIDEOS_DIR", ROOT_DIR / "open" / "videos"))
RULES_PATH = Path(os.getenv("RULES_PATH", HARNESS_DIR / "rules.json"))
RUNS_DIR = HARNESS_DIR / "runs"


def env_float(name, default):
    v = os.getenv(name)
    return float(v) if v not in (None, "") else default


def env_int(name, default):
    v = os.getenv(name)
    return int(v) if v not in (None, "") else default


def env_bool(name, default=False):
    v = os.getenv(name)
    if v in (None, ""):
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


FPS = env_float("FPS", 1.0)
# videos shorter than SHORT_VIDEO_SEC are sampled at FPS_SHORT, longer ones at FPS_LONG
FPS_ADAPTIVE = env_bool("FPS_ADAPTIVE", True)
FPS_SHORT = env_float("FPS_SHORT", 2.0)
FPS_LONG = env_float("FPS_LONG", 1.0)
SHORT_VIDEO_SEC = env_float("SHORT_VIDEO_SEC", 120.0)
MAX_FRAMES = env_int("MAX_FRAMES", 250)
MAX_SIDE = env_int("MAX_SIDE", 640)
JPEG_QUALITY = env_int("JPEG_QUALITY", 80)
EVIDENCE_MAX_SIDE = env_int("EVIDENCE_MAX_SIDE", 1280)

VLM_BASE_URL = os.getenv("VLM_BASE_URL", "mock")
VLM_API_KEY = os.getenv("VLM_API_KEY", "EMPTY")
VLM_MODEL = os.getenv("VLM_MODEL", "default")
TEMPERATURE = env_float("TEMPERATURE", 0.0)
MAX_TOKENS = env_int("MAX_TOKENS", 2500)
TIMEOUT = env_float("VLM_TIMEOUT", 280.0)
RETRIES = env_int("VLM_RETRIES", 2)
DISABLE_THINKING = env_bool("DISABLE_THINKING", False)
SYSTEM_IN_USER = env_bool("SYSTEM_IN_USER", False)

THRESHOLD_OFFSET = env_float("THRESHOLD_OFFSET", 0.0)
# "rules" = use count_in_verdict from rules.json, "all" = every known rule except "other"
VERDICT_MODE = os.getenv("VERDICT_MODE", "rules")
# organizer labels count these as violations although rules.json keeps them out of the verdict
EXTRA_VERDICT_TYPES = [t.strip() for t in os.getenv(
    "EXTRA_VERDICT_TYPES", "workstation_unlocked,seals_docs_unattended,eating_drinking").split(",") if t.strip()]
MERGE_WINDOW_SEC = env_float("MERGE_WINDOW_SEC", 3.0)


@lru_cache(maxsize=1)
def load_rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data


@lru_cache(maxsize=1)
def rules_by_id():
    return {r["id"]: r for r in load_rules()["rules"]}


def video_key(name):
    """Normalize 'Х-10.mov' / 'X-10' (Cyrillic or Latin X) to 'X-10'."""
    stem = Path(str(name)).stem.strip()
    return stem.replace("Х", "X").replace("х", "X").replace(" ", "")


def video_number(name):
    try:
        return int(video_key(name).split("-")[1])
    except (IndexError, ValueError):
        return 10**6
