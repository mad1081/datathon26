"""FastAPI app: UI + API (POST /api/v1/analyze, GET /api/v1/jobs/{job_id})."""
from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .config import settings
from .jobs import JobStore, Worker
from .pipeline.analyzer import Analyzer
from .pipeline.rules import load_rulebook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

ALLOWED_EXT = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}
PUBLIC_FIELDS = ("job_id", "status", "verdict", "violations")

settings.ensure_dirs()
store = JobStore(settings.data_dir)
worker = Worker(store, lambda: Analyzer(settings), settings.workers)
app = FastAPI(title="Cash discipline video analyzer", version="0.1.0")


@app.on_event("startup")
def _startup():
    if settings.api_key == "change-me":
        log.warning("API_KEY is not set — using insecure default 'change-me'")
    load_rulebook(settings.rules_path)  # fail fast on broken rules.json
    worker.start()


def require_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


@app.get("/api/v1/health")
def health():
    model = {"transformers": settings.vlm_model, "openai": settings.openai_model}.get(settings.vlm_backend, "mock (no model)")
    return {"status": "ok", "backend": settings.vlm_backend, "model": model}


@app.post("/api/v1/analyze", dependencies=[Depends(require_key)])
async def analyze(file: UploadFile = File(...)):
    name = file.filename or "upload.mov"
    ext = Path(name).suffix.lower() or ".mov"
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"unsupported file type {ext}; expected .mov/.mp4")
    job_id = store.create(name)
    dst = store.dir(job_id) / f"input{ext}"
    size, limit = 0, settings.max_upload_mb * 1024 * 1024
    with open(dst, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                f.close()
                store.update(job_id, status="failed", error="file too large")
                raise HTTPException(status_code=413, detail="file too large")
            f.write(chunk)
    if size == 0:
        store.update(job_id, status="failed", error="empty file")
        raise HTTPException(status_code=400, detail="empty file")
    store.update(job_id, size_bytes=size)
    worker.submit(job_id, str(dst))
    return JSONResponse({"job_id": job_id, "status": "processing"}, status_code=202)


@app.get("/api/v1/jobs/{job_id}", dependencies=[Depends(require_key)])
def get_job(job_id: str, full: bool = True):
    j = store.load(job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job not found")
    if j["status"] == "processing":
        return {"job_id": job_id, "status": "processing", "stage": j.get("stage"), "progress": j.get("progress", 0)}
    if j["status"] == "failed":
        return {"job_id": job_id, "status": "failed", "error": j.get("error", "")}
    out = {k: j.get(k) for k in PUBLIC_FIELDS}
    if full:
        for k in ("verdict_ru", "observations", "unanalyzed_ranges", "needs_manual_review",
                  "manual_review_reasons", "tracks", "meta", "filename"):
            out[k] = j.get(k)
    return out


@app.get("/", response_class=HTMLResponse)
def index():
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return html.replace("__UI_API_KEY__", settings.ui_api_key.replace('"', ""))
