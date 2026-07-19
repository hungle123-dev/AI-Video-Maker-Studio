"""core/render_service.py — Hàng đợi TTS + Render chạy nền.

Một worker thread duy nhất chạy event-loop asyncio riêng; UI đẩy việc vào
queue và theo dõi tiến trình qua core.jobs (bền vững trên đĩa).

Pipeline một lesson:  script → TTS (timing_map) → node canvas_renderer
→ ffmpeg → mp4 trong data/outputs/.
"""
import asyncio, logging, threading
from pathlib import Path
from config import OUTPUTS_DIR, load_settings
from core import jobs
from core.project_store import project_store; logger = logging.getLogger("TubeCraft.Render")


class JobCancelledError(RuntimeError):
    """A queued media job was cancelled before its current phase completed."""


class StaleMediaJobError(RuntimeError):
    """A job finished after its script, settings, or audio input changed."""


def _err_msg(e: Exception) -> str:
    name = type(e).__name__; text = str(e).strip() or "(không có mô tả)"
    return f"{name}: {text}"[:280]

def _err_detail(e: Exception) -> str:
    import traceback
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))[-2000:]

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None

_lock = threading.Lock(); _ready = threading.Event()
def _ensure_worker() -> asyncio.AbstractEventLoop:
    global _loop
    global _thread
    with _lock:
        if _thread and _thread.is_alive() and _loop is not None:
            _ready.wait(5)
            return _loop
        _ready.clear(); loop = asyncio.new_event_loop()
        def _run():
            asyncio.set_event_loop(loop); loop.call_soon(_ready.set); loop.run_forever()
        t = threading.Thread(target=_run, daemon=True, name="TubeCraft-Worker")
        _loop = loop; _thread = t; t.start()
    if not _ready.wait(10):
        logger.error("Worker thread không khởi động được sau 10s.")
    return loop

_sem: asyncio.Semaphore | None = None
_sem_loop: asyncio.AbstractEventLoop | None = None

def _max_concurrent() -> int:
    return 1

async def _guarded(coro):
    global _sem
    global _sem_loop
    loop = asyncio.get_running_loop()
    if _sem is None or _sem_loop is not loop:
        _sem = asyncio.Semaphore(_max_concurrent())
        _sem_loop = loop
    async with _sem:
        await coro

def _submit(job_id: str, coro) -> None:
    fut = asyncio.run_coroutine_threadsafe(_guarded(coro), _ensure_worker())
    def _on_done(f):
        try:
            f.result()
        except Exception as e:
            logger.exception("Job nền thất bại ngoài thân coroutine")
            j = jobs.get_job(job_id)
            if j and j.get("status") in ("queued", "running"):
                jobs.update_job(job_id, status="error", message=_err_msg(e))
    
    fut.add_done_callback(_on_done)

def _active_job_for(project_id: str, lesson_id: str, kinds=None):
    for j in jobs.list_jobs(limit=2000):
        if j.get("status") not in ("queued", "running"):
            continue
        m = j.get("meta", {})
        if m.get("project_id") != project_id:
            continue
        if m.get("lesson_id") != lesson_id:
            continue
        if kinds is not None and j.get("kind") not in kinds:
            continue
        return j
    return None


def _is_cancelled(job_id: str) -> bool:
    job = jobs.get_job(job_id)
    return bool(job and job.get("cancel"))


def _raise_if_cancelled(job_id: str) -> None:
    if _is_cancelled(job_id):
        raise JobCancelledError("Đã hủy theo yêu cầu người dùng.")


def cancel_job(job_id: str) -> dict | None:
    """Request cancellation for a queued/running media job."""
    job = jobs.get_job(job_id)
    if not job or job.get("kind") not in ("tts", "render", "pipeline"):
        return job
    if job.get("status") not in ("queued", "running"):
        return job
    fields = {"cancel": True, "message": "Đang dừng theo yêu cầu..."}
    if job.get("status") == "queued":
        fields.update(status="cancelled", message="Đã hủy trước khi bắt đầu.")
    return jobs.update_job(job_id, **fields)

def queue_tts(project_id: str, lesson_id: str) -> dict:
    # A pipeline already owns its TTS phase, but an active render does not.
    existing = _active_job_for(project_id, lesson_id, kinds=("tts", "pipeline"))
    if existing:
        return existing
    job = jobs.create_job("tts", {"project_id": project_id, "lesson_id": lesson_id}); _submit(job["id"], _run_tts(job["id"], project_id, lesson_id))
    return job

async def _run_tts(job_id: str, project_id: str, lesson_id: str):
    audio_job_dir = None
    committed_audio = False
    try:
        _raise_if_cancelled(job_id)
        jobs.update_job(job_id, status="running", message="Chuẩn bị TTS...")
        from engines.audio_engine import generate_tts_for_script
        from core.project_store import script_has_content
        lesson = project_store.get_lesson(project_id, lesson_id)
        project = project_store.get_project(project_id)
        if not lesson or not project:
            raise RuntimeError("Không tìm thấy lesson/project.")
        if lesson.get("script_validation_errors"):
            raise RuntimeError("Kịch bản có dữ liệu không hợp lệ; hãy mở và lưu lại trước khi tạo giọng.")
        if not script_has_content(lesson.get("script")):
            raise RuntimeError("Bài này chưa có kịch bản thực (script rỗng) — hãy tạo lại kịch bản bằng AI trước khi tạo giọng.")
        revisions = project_store.begin_tts_generation(project_id, lesson_id)
        if not revisions:
            raise RuntimeError("Không khóa được revision media an toàn cho TTS.")
        expected_audio_revision = revisions["audio_source_revision"]
        # Capture the current inputs after reserving their versions. A later
        # edit may continue the worker, but it cannot publish its old bundle.
        lesson = project_store.get_lesson(project_id, lesson_id)
        project = project_store.get_project(project_id)
        if not lesson or not project:
            raise RuntimeError("Không tìm thấy lesson/project sau khi chuẩn bị TTS.")
        paths = project_store.lesson_paths(project_id, lesson_id)
        audio_job_dir = str(Path(paths["dir"]) / f".audio-job-{job_id}")
        jobs.append_job_log(job_id, "🚀 [HỆ THỐNG] Khởi tạo Vivibe/TTS...")
        def cb(pct, msg):
            _raise_if_cancelled(job_id)
            jobs.update_job(job_id, progress=int(pct), message=str(msg))
        def log_cb(message):
            _raise_if_cancelled(job_id)
            jobs.append_job_log(job_id, message)
        timing = await generate_tts_for_script(lesson["script"], audio_job_dir, voice=project.get("voice", "vi-VN-HoaiMyNeural"), tts_engine=project.get("tts_engine", "edge"), lang=project.get("lang", "vi"), progress_callback=cb, log_callback=log_cb)
        _raise_if_cancelled(job_id)
        if not project_store.commit_audio_bundle(
            project_id,
            lesson_id,
            audio_job_dir,
            timing,
            expected_audio_revision=expected_audio_revision,
        ):
            raise StaleMediaJobError("Nội dung hoặc cấu hình giọng đã đổi khi TTS đang chạy.")
        committed_audio = True
        jobs.update_job(job_id, status="done", progress=100, message="TTS hoàn tất.", result={"timing": True})
        return None
    except JobCancelledError:
        jobs.update_job(job_id, status="cancelled", message="Đã hủy tạo giọng đọc.", result={"cancelled": True})
    except StaleMediaJobError:
        jobs.update_job(job_id, status="cancelled", message="Nội dung đã đổi; đã bỏ audio của job cũ.", result={"stale": True})
    except Exception as e:
        logger.exception("TTS lỗi")
        jobs.update_job(job_id, status="error", message=_err_msg(e), result={"error": _err_msg(e), "error_detail": _err_detail(e)})
    finally:
        if audio_job_dir and not committed_audio:
            project_store.discard_audio_bundle(project_id, lesson_id, audio_job_dir)

def queue_render(project_id: str, lesson_id: str) -> dict:
    # TTS is allowed to finish first in the single worker.  Returning a TTS
    # job here used to make a Render click silently do nothing.
    existing = _active_job_for(project_id, lesson_id, kinds=("render", "pipeline"))
    if existing:
        return existing
    job = jobs.create_job("render", {"project_id": project_id, "lesson_id": lesson_id}); _submit(job["id"], _run_render(job["id"], project_id, lesson_id))
    return job

async def _run_render(job_id: str, project_id: str, lesson_id: str):
    try:
        _raise_if_cancelled(job_id)
        jobs.update_job(job_id, status="running", message="Chuẩn bị render...")
        from engines.video_encoder import render_and_encode
        from core.project_store import (
            audio_is_current,
            script_has_content,
        )
        snapshot = project_store.get_render_snapshot(project_id, lesson_id)
        if not snapshot:
            raise RuntimeError("Không tìm thấy lesson/project.")
        project = snapshot["project"]
        lesson = snapshot["lesson"]
        paths = snapshot["paths"]
        if lesson.get("script_validation_errors"):
            raise RuntimeError("Kịch bản có dữ liệu không hợp lệ; hãy mở và lưu lại trước khi render.")
        if not script_has_content(lesson.get("script")):
            raise RuntimeError("Bài này chưa có kịch bản thực (script rỗng) — hãy tạo lại kịch bản bằng AI trước khi render.")
        expected_render_revision = snapshot["render_source_revision"]
        expected_audio_revision = snapshot["audio_source_revision"]
        if not audio_is_current(lesson, lesson.get("timing"), paths["full_audio"]):
            raise RuntimeError("Chưa có audio hợp lệ — chạy TTS trước khi render.")
        settings = load_settings()
        try:
            render_fps = max(10, min(60, int(settings.get("render_fps", 30))))
        except (TypeError, ValueError):
            render_fps = 30
        aspect = project.get("aspect_ratio", "9:16")
        out_dir = OUTPUTS_DIR / project_id
        out_dir.mkdir(parents=True, exist_ok=True)
        def cb(pct, msg):
            jobs.update_job(job_id, progress=int(pct), message=str(msg))
        from core import subtitles as _subs
        subtitle_cfg = _subs.subtitle_config(project, settings)
        video_path = await render_and_encode(script_path=paths["script"], timing_path=paths["timing"], output_dir=str(out_dir), project_id=f"{project_id}_{lesson_id}_r{expected_render_revision}", theme=project.get("theme", "dark"), bg=project.get("bg", ""), aspect_ratio=aspect, art_style=project.get("art_style", "default"), title_color=project.get("title_color", ""), text_color=project.get("text_color", ""), font_family=project.get("font_family", ""), subtitle=subtitle_cfg, gpu_encoder=_resolve_encoder(settings.get("gpu_encoder", "auto")), progress_callback=cb, fps=render_fps, cancel_check=lambda: _is_cancelled(job_id), require_audio=True)
        _raise_if_cancelled(job_id)
        if not project_store.publish_rendered_video(
            project_id,
            lesson_id,
            video_path,
            aspect,
            expected_render_revision=expected_render_revision,
            expected_audio_revision=expected_audio_revision,
        ):
            Path(video_path).unlink(missing_ok=True)
            raise StaleMediaJobError("Nội dung, hình thức hoặc audio đã đổi khi render đang chạy.")
        jobs.update_job(job_id, status="done", progress=100, message="Render hoàn tất.", result={"video": video_path})
    except JobCancelledError:
        jobs.update_job(job_id, status="cancelled", message="Đã hủy render.", result={"cancelled": True})
    except StaleMediaJobError:
        jobs.update_job(job_id, status="cancelled", message="Nội dung đã đổi; đã bỏ video của job cũ.", result={"stale": True})
    except Exception as e:
        from engines.video_encoder import RenderCancelledError
        if isinstance(e, RenderCancelledError):
            jobs.update_job(job_id, status="cancelled", message="Đã hủy render.", result={"cancelled": True})
            return None
        logger.exception("Render lỗi")
        jobs.update_job(job_id, status="error", message=_err_msg(e), result={"error": _err_msg(e), "error_detail": _err_detail(e)})

def _resolve_encoder(pref: str) -> str:
    if pref in ("nvenc", "cpu"):
        return pref
    import os as _os, shutil as _sh, subprocess as _sp
    try:
        if _sh.which("nvidia-smi"):
            r = _sp.run(["nvidia-smi", "-L"], capture_output=True, timeout=5, creationflags=134_217_728 if _os.name == "nt" else 0)
            if r.returncode == 0 and b"GPU" in r.stdout:
                return "nvenc"
        return "cpu"
    except Exception:
        return "cpu"

def queue_full_pipeline(project_id: str, lesson_id: str) -> dict:
    existing = _active_job_for(project_id, lesson_id, kinds=("tts", "render", "pipeline"))
    if existing:
        return existing
    job = jobs.create_job("pipeline", {"project_id": project_id, "lesson_id": lesson_id}); _submit(job["id"], _run_pipeline(job["id"], project_id, lesson_id))
    return job

async def _run_pipeline(job_id: str, project_id: str, lesson_id: str):
    await _run_tts(job_id, project_id, lesson_id)
    j = jobs.get_job(job_id)
    if j and j.get("status") == "done" and not j.get("cancel"):
        jobs.update_job(job_id, status="running", progress=0, message="Bắt đầu render...")
        await _run_render(job_id, project_id, lesson_id)
    elif j and j.get("cancel") and j.get("status") == "done":
        jobs.update_job(job_id, status="cancelled", message="Đã hủy trước khi render.", result={"cancelled": True})
