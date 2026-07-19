"""core/jobs.py — Job store bền vững trên đĩa.

Mỗi job là một file JSON trong data/jobs/, sống sót qua restart và tự dọn
job cũ quá 7 ngày.
"""
import os, json, time, uuid, threading
from pathlib import Path
from typing import List, Optional
from config import JOBS_DIR; _RETENTION_SECONDS = 604_800; _lock = threading.RLock()
def _path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"

def create_job(kind: str, meta: dict | None=None) -> dict:
    job = {"id": f"{kind}_{uuid.uuid4().hex[:8]}", "kind": kind, "status": "queued", "progress": 0, "message": "", "logs": [], "result": None, "meta": meta or {}, "created_at": time.time(), "updated_at": time.time()}; _save(job)
    return job

def _save(job: dict) -> None:
    with _lock:
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(_path(job["id"])) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False)
        os.replace(tmp, _path(job["id"]))

def update_job(job_id: str, **fields) -> Optional[dict]:
    with _lock:
        job = get_job(job_id)
        if not job:
            return None
        job.update(fields)
        job["updated_at"] = time.time()
        _save(job)
        return job

def append_job_log(job_id: str, message: object, limit: int = 200) -> Optional[dict]:
    """Persist the worker console shown by the render queue."""
    text = str(message).strip()
    if not text:
        return get_job(job_id)
    with _lock:
        job = get_job(job_id)
        if not job:
            return None
        logs = list(job.get("logs") or [])
        logs.append(text)
        job["logs"] = logs[-limit:]
        job["updated_at"] = time.time()
        _save(job)
        return job

def get_job(job_id: str) -> Optional[dict]:
    try:
        with open(_path(job_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def list_jobs(kind: str | None=None, limit: int=50) -> List[dict]:
    cleanup_old_jobs()
    jobs = []
    if not JOBS_DIR.is_dir():
        return jobs
    for p in JOBS_DIR.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                j = json.load(f)
            if kind and j.get("kind") != kind:
                continue
            jobs.append(j)
        except Exception:
            continue
    jobs.sort(key=(lambda j: j.get("created_at", 0)), reverse=True)
    return jobs[:limit]

def mark_stale_jobs_on_startup() -> None:
    for j in list_jobs():
        if not j.get("status") in ("queued", "running"):
            continue
        update_job(j["id"], status="error", message="Bị gián đoạn do app khởi động lại.")

def cleanup_old_jobs() -> None:
    try:
        now = time.time()
        if not JOBS_DIR.is_dir():
            return None
        for p in JOBS_DIR.glob("*.json"):
            if now - (p.stat().st_mtime) > _RETENTION_SECONDS:
                p.unlink(missing_ok=True)
    except Exception:
        pass
