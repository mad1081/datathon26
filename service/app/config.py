"""Runtime configuration (all via environment variables)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


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
    workers: int = field(default_factory=lambda: int(_env("WORKERS", "1")))
    max_upload_mb: int = field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "300")))

    # model backend: mock | transformers | openai
    vlm_backend: str = field(default_factory=lambda: _env("VLM_BACKEND", "mock"))
    vlm_model: str = field(default_factory=lambda: _env("VLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct"))
    # NB: Qwen2.5-VL-3B is under the non-commercial "Qwen Research" licence -> do NOT use it.
    vlm_fallback_model: str = field(default_factory=lambda: _env("VLM_FALLBACK_MODEL", "Qwen/Qwen3-VL-4B-Instruct"))
    openai_base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", "http://127.0.0.1:8001/v1"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct"))
    max_new_tokens: int = field(default_factory=lambda: int(_env("MAX_NEW_TOKENS", "512")))

    # pipeline
    sample_fps: float = field(default_factory=lambda: float(_env("SAMPLE_FPS", "2")))
    window_sec: float = field(default_factory=lambda: float(_env("WINDOW_SEC", "4")))
    stride_sec: float = field(default_factory=lambda: float(_env("STRIDE_SEC", "2")))
    window_concurrency: int = field(default_factory=lambda: int(_env("WINDOW_CONCURRENCY", "1")))  # >1 useful with vLLM
    max_windows: int = field(default_factory=lambda: int(_env("MAX_WINDOWS", "60")))
    frame_max_side: int = field(default_factory=lambda: int(_env("FRAME_MAX_SIDE", "640")))
    refine: bool = field(default_factory=lambda: _env("REFINE", "1") == "1")
    refine_fps: float = field(default_factory=lambda: float(_env("REFINE_FPS", "4")))
    refine_span_sec: float = field(default_factory=lambda: float(_env("REFINE_SPAN_SEC", "2.5")))
    low_threshold: float = field(default_factory=lambda: float(_env("LOW_THRESHOLD", "0.35")))
    threshold_offset: float = field(default_factory=lambda: float(_env("THRESHOLD_OFFSET", "0")))
    max_violations: int = field(default_factory=lambda: int(_env("MAX_VIOLATIONS", "5")))
    time_budget_sec: float = field(default_factory=lambda: float(_env("TIME_BUDGET_SEC", "270")))
    evidence_max_side: int = field(default_factory=lambda: int(_env("EVIDENCE_MAX_SIDE", "1280")))
    type_field: str = field(default_factory=lambda: _env("TYPE_FIELD", "name"))  # name | id

    def ensure_dirs(self) -> None:
        (self.data_dir / "jobs").mkdir(parents=True, exist_ok=True)


settings = Settings()
