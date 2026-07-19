from __future__ import annotations

import os
import time

from core import jobs


def test_jobs_survive_restart_mark_stale_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    queued = jobs.create_job("tts", {"project_id": "p", "lesson_id": "l"})
    running = jobs.create_job("render")
    done = jobs.create_job("pipeline")
    jobs.update_job(running["id"], status="running")
    jobs.update_job(done["id"], status="done")

    jobs.mark_stale_jobs_on_startup()
    assert jobs.get_job(queued["id"])["status"] == "error"
    assert jobs.get_job(running["id"])["status"] == "error"
    assert jobs.get_job(done["id"])["status"] == "done"

    old_path = jobs._path(queued["id"])
    old_time = time.time() - jobs._RETENTION_SECONDS - 60
    os.utime(old_path, (old_time, old_time))
    jobs.cleanup_old_jobs()
    assert not old_path.exists()
    assert jobs.get_job(done["id"]) is not None
