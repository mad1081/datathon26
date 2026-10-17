"""Background job queue with on-disk persistence (DATA_DIR/jobs/<id>/job.json)."""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import traceback
import uuid
from pathlib import Path

log = logging.getLogger("jobs")


class JobStore:
    def __init__(self, root: Path):
        self.root = root / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def dir(self, job_id: str) -> Path:
        return self.root / job_id

    def create(self, filename: str) -> str:
        job_id = uuid.uuid4().hex
        self.dir(job_id).mkdir(parents=True)
        self.save(job_id, {"job_id": job_id, "status": "processing", "stage": "queued", "progress": 0.0,
                           "filename": filename, "created_at": time.time()})
        return job_id

    def load(self, job_id: str) -> dict | None:
        if not job_id.isalnum():
            return None
        p = self.dir(job_id) / "job.json"
        if not p.exists():
            return None
        with self._lock:
            return json.loads(p.read_text(encoding="utf-8"))

    def save(self, job_id: str, data: dict) -> None:
        p = self.dir(job_id) / "job.json"
        tmp = p.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, p)

    def update(self, job_id: str, **kw) -> dict:
        d = self.load(job_id) or {"job_id": job_id}
        d.update(kw)
        self.save(job_id, d)
        return d

    def pending(self) -> list[str]:
        out = []
        for d in sorted(self.root.iterdir(), key=lambda p: p.stat().st_mtime):
            j = self.load(d.name) if d.is_dir() else None
            if j and j.get("status") == "processing":
                out.append(d.name)
        return out


class Worker:
    def __init__(self, store: JobStore, analyzer_factory, n_workers: int = 1):
        self.store = store
        self.q: queue.Queue[tuple[str, str]] = queue.Queue()
        self.analyzer_factory = analyzer_factory
        self._analyzer = None
        self.threads = [threading.Thread(target=self._loop, daemon=True, name=f"worker-{i}")
                        for i in range(n_workers)]

    def start(self):
        for jid in self.store.pending():  # resume after restart
            vid = next((str(p) for p in self.store.dir(jid).glob("input.*")), None)
            if vid:
                self.q.put((jid, vid))
            else:
                self.store.update(jid, status="failed", error="input file missing after restart")
        for t in self.threads:
            t.start()

    def submit(self, job_id: str, video_path: str):
        self.q.put((job_id, video_path))

    def _get_analyzer(self):
        if self._analyzer is None:
            self._analyzer = self.analyzer_factory()
        return self._analyzer

    def _loop(self):
        while True:
            job_id, path = self.q.get()
            try:
                self.store.update(job_id, stage="started", started_at=time.time())

                def progress(p: float, stage: str, _jid=job_id):
                    self.store.update(_jid, progress=round(p, 3), stage=stage)

                result = self._get_analyzer().run(path, progress)
                self.store.update(job_id, status="done", stage="done", progress=1.0,
                                  finished_at=time.time(), **result)
            except Exception as e:  # noqa: BLE001
                log.exception("job %s failed", job_id)
                self.store.update(job_id, status="failed", stage="failed", error=str(e)[:500],
                                  traceback=traceback.format_exc()[-2000:], finished_at=time.time())
            finally:
                self.q.task_done()
