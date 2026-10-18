"""Runtime configuration (all via environment variables)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return default if v in (None, "") else v


def _bool(name: str, default: str = "0") -> bool:
    return _env(name, default).strip().lower() in ("1", "true", "yes", "on")


def _default_rules() -> str:
    for p in (_HERE.parent / "rules.json", _HERE.parent.parent / "rules.json"):
        if p.exists():
            return str(p)
    return str(_HERE.parent / "rules.json")


@dataclass
class Settings:
    api_key: str = field(default_factory=lambda: _env("API_KEY", "change-me"))
    ui_api_key: str = field(default_factory=lambda: _env("UI_API_KEY", ""))  # optional: prefill key in UI
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(_HERE.parent / "var"))))
    rules_path: str = field(default_factory=lambda: _env("RULES_PATH", _default_rules()))
    workers: int = field(default_factory=lambda: int(_env("WORKERS", "2")))
    max_upload_mb: int = field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "500")))

    # local OpenAI-compatible VLM server (vLLM); "mock" = built-in random stand-in for pipeline tests
    vlm_base_url: str = field(default_factory=lambda: _env("VLM_BASE_URL", "http://127.0.0.1:8001/v1"))
    vlm_api_key: str = field(default_factory=lambda: _env("VLM_API_KEY", "EMPTY"))
    vlm_model: str = field(default_factory=lambda: _env("VLM_MODEL", "default"))
    temperature: float = field(default_factory=lambda: float(_env("TEMPERATURE", "0")))
    max_tokens: int = field(default_factory=lambda: int(_env("MAX_TOKENS", "2500")))
    vlm_timeout: float = field(default_factory=lambda: float(_env("VLM_TIMEOUT", "240")))
    vlm_retries: int = field(default_factory=lambda: int(_env("VLM_RETRIES", "2")))
    disable_thinking: bool = field(default_factory=lambda: _bool("DISABLE_THINKING"))
    system_in_user: bool = field(default_factory=lambda: _bool("SYSTEM_IN_USER"))

    # self-consistency
    n_samples: int = field(default_factory=lambda: int(_env("N_SAMPLES", "5")))
    sample_temperature: float = field(default_factory=lambda: float(_env("SAMPLE_TEMPERATURE", "0.6")))
    # below this many seconds left in the budget, sampling falls back to a single call
    min_sec_for_sampling: float = field(default_factory=lambda: float(_env("MIN_SEC_FOR_SAMPLING", "150")))

    # targeted object-state checks after the main call (comma list: laptop, desk, safe; empty = off)
    state_checks: list = field(default_factory=lambda: [c.strip() for c in _env("STATE_CHECKS", "laptop,desk,safe").split(",")
                                                        if c.strip()])
    state_votes: int = field(default_factory=lambda: int(_env("STATE_VOTES", "3")))
    state_temperature: float = field(default_factory=lambda: float(_env("STATE_TEMPERATURE", "0.6")))
    state_crop_top: float = field(default_factory=lambda: float(_env("STATE_CROP_TOP", "0.65")))
    state_upscale: float = field(default_factory=lambda: float(_env("STATE_UPSCALE", "1.6")))

    # frame sampling (whole video in one request)
    fps_short: float = field(default_factory=lambda: float(_env("FPS_SHORT", "2")))
    fps_long: float = field(default_factory=lambda: float(_env("FPS_LONG", "1")))
    short_video_sec: float = field(default_factory=lambda: float(_env("SHORT_VIDEO_SEC", "120")))
    max_frames: int = field(default_factory=lambda: int(_env("MAX_FRAMES", "250")))
    frame_max_side: int = field(default_factory=lambda: int(_env("MAX_SIDE", "640")))
    jpeg_quality: int = field(default_factory=lambda: int(_env("JPEG_QUALITY", "80")))
    evidence_max_side: int = field(default_factory=lambda: int(_env("EVIDENCE_MAX_SIDE", "1280")))

    # decision
    threshold_offset: float = field(default_factory=lambda: float(_env("THRESHOLD_OFFSET", "0")))
    merge_window_sec: float = field(default_factory=lambda: float(_env("MERGE_WINDOW_SEC", "3")))
    max_violations: int = field(default_factory=lambda: int(_env("MAX_VIOLATIONS", "6")))
    max_observations: int = field(default_factory=lambda: int(_env("MAX_OBSERVATIONS", "5")))
    # measured from upload (job created_at); the jury limit is 300 s
    time_budget_sec: float = field(default_factory=lambda: float(_env("TIME_BUDGET_SEC", "285")))
    evidence_reserve_sec: float = field(default_factory=lambda: float(_env("EVIDENCE_RESERVE_SEC", "15")))

    def ensure_dirs(self) -> None:
        (self.data_dir / "jobs").mkdir(parents=True, exist_ok=True)


settings = Settings()
