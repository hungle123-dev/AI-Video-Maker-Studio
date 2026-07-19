"""
TubeCraft — Canvas video encoder.
Supports two modes: 'pipe' (fast, single step) and 'frames' (stable, PNG + FFmpeg).
"""
import os
import json
import copy
import asyncio
import shutil
import logging
import signal
import time
import contextlib
import tempfile
from typing import Optional, Callable, List
from pathlib import Path

logger = logging.getLogger("TubeCraft.VideoEncoder")

# Thư mục gốc app: khi đóng gói PyInstaller, __file__ nằm trong _internal/ còn
# engines/ + node_modules/ đặt cạnh .exe → phải lấy BASE_DIR từ config.
# Fallback __file__ để module vẫn chạy độc lập ngoài app.
try:
    from config import BASE_DIR as _APP_DIR
    _APP_DIR = Path(_APP_DIR)
except Exception:
    _APP_DIR = Path(__file__).resolve().parent.parent

CANVAS_RENDERER_JS = _APP_DIR / "engines" / "canvas_renderer.js"

# Bản đóng gói là GUI KHÔNG có console. Mỗi tiến trình console (node/ffmpeg)
# sinh ra sẽ tự bung một CỬA SỔ ĐEN đè lên app — render 8 worker = 8 cửa sổ.
# Chạy từ python.exe lúc dev thì con kế thừa console sẵn nên không lộ lỗi.
# CREATE_NO_WINDOW chặn hẳn; tiến trình cháu (ffmpeg do node gọi) cũng kế thừa.
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_CREATE_NEW_PROCESS_GROUP = 0x00000200 if os.name == "nt" else 0

# A render must always have a finite lifetime.  The estimate intentionally has
# generous headroom for CPU-only laptops, while an explicit caller deadline is
# still available for tests and future UI policy.
_MIN_RENDER_TIMEOUT_SECONDS = 120.0
_SECONDS_PER_MEDIA_SECOND = 30.0
_MAX_RENDER_TIMEOUT_SECONDS = 3600.0
_PROCESS_POLL_SECONDS = 0.25
_PROCESS_STOP_GRACE_SECONDS = 5.0
_RENDERER_IDLE_TIMEOUT_SECONDS = 90.0


class RenderCancelledError(RuntimeError):
    """Raised when the owning render job was cancelled."""


class RenderTimeoutError(RuntimeError):
    """Raised when a render exceeded its absolute deadline."""


class RendererSceneError(RuntimeError):
    """A trusted scene/template failed or was rejected by the Node renderer."""


class RendererProcessError(RuntimeError):
    """Node/FFmpeg exited unsuccessfully for a non-scene reason."""


async def _exec(*args, **kwargs):
    """asyncio.create_subprocess_exec + ẩn cửa sổ console trên Windows."""
    if os.name == "nt":
        # Every renderer has its own process group so cancellation can remove
        # Node *and* the ffmpeg child it spawns.
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW | _CREATE_NEW_PROCESS_GROUP
    else:
        kwargs.setdefault("start_new_session", True)
    return await asyncio.create_subprocess_exec(*args, **kwargs)


def _normalize_fps(value) -> int:
    """Return the supported renderer FPS range (the settings UI uses 10–60)."""
    try:
        fps = int(value)
    except (TypeError, ValueError):
        fps = 30
    return max(10, min(60, fps))


def _render_deadline(total_duration: float, timeout_seconds: Optional[float]) -> float:
    """One absolute monotonic deadline shared by every child process."""
    if timeout_seconds is None:
        seconds = max(
            _MIN_RENDER_TIMEOUT_SECONDS,
            min(_MAX_RENDER_TIMEOUT_SECONDS, _MIN_RENDER_TIMEOUT_SECONDS + max(0.0, total_duration) * _SECONDS_PER_MEDIA_SECOND),
        )
    else:
        try:
            seconds = float(timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("timeout_seconds phải là số giây hợp lệ.") from exc
        if seconds <= 0:
            raise ValueError("timeout_seconds phải lớn hơn 0.")
    return time.monotonic() + seconds


def _fallback_deadline(deadline: Optional[float], total_duration: float) -> Optional[float]:
    """Give one deliberate pipe→frames recovery its own bounded budget.

    Frames mode is a supported, slower recovery after a pipe/FFmpeg failure.
    It must not inherit a nearly-expired pipe deadline and be killed while it
    is still making progress.  User cancellation and the idle timeout remain
    active throughout the recovery.
    """
    if deadline is None:
        return None
    return max(deadline, _render_deadline(total_duration, None))


def _check_render_control(cancel_check: Optional[Callable[[], bool]], deadline: Optional[float]) -> None:
    if cancel_check and cancel_check():
        raise RenderCancelledError("Render đã bị hủy.")
    if deadline is not None and time.monotonic() >= deadline:
        raise RenderTimeoutError("Render quá thời gian cho phép.")


def _poll_timeout(deadline: Optional[float]) -> float:
    if deadline is None:
        return _PROCESS_POLL_SECONDS
    return max(0.0, min(_PROCESS_POLL_SECONDS, deadline - time.monotonic()))


async def _terminate_process_tree(proc) -> None:
    """Stop a renderer/FFmpeg process and any child it owns, best effort."""
    if getattr(proc, "returncode", None) is not None:
        return
    pid = getattr(proc, "pid", None)
    try:
        if pid and os.name == "nt":
            killer = await _exec(
                "taskkill", "/PID", str(pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(killer.wait(), timeout=_PROCESS_STOP_GRACE_SECONDS)
            except (asyncio.TimeoutError, Exception):
                if killer.returncode is None:
                    killer.kill()
        elif pid:
            os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass

    try:
        await asyncio.wait_for(proc.wait(), timeout=_PROCESS_STOP_GRACE_SECONDS)
        return
    except (asyncio.TimeoutError, Exception):
        pass

    try:
        if pid and os.name != "nt":
            os.killpg(pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError, OSError):
        pass
    with contextlib.suppress(Exception):
        await asyncio.wait_for(proc.wait(), timeout=_PROCESS_STOP_GRACE_SECONDS)


async def _wait_for_process(proc, *, cancel_check: Optional[Callable[[], bool]] = None,
                            deadline: Optional[float] = None) -> int:
    """Wait with cooperative cancellation and an absolute deadline."""
    try:
        while getattr(proc, "returncode", None) is None:
            _check_render_control(cancel_check, deadline)
            timeout = _poll_timeout(deadline)
            if timeout <= 0:
                _check_render_control(cancel_check, deadline)
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue
        return proc.returncode
    except BaseException:
        await _terminate_process_tree(proc)
        raise


async def _communicate_process(proc, *, cancel_check: Optional[Callable[[], bool]] = None,
                               deadline: Optional[float] = None):
    """Drain process pipes without allowing a hung child to outlive its job."""
    task = asyncio.create_task(proc.communicate())
    try:
        while not task.done():
            _check_render_control(cancel_check, deadline)
            timeout = _poll_timeout(deadline)
            if timeout <= 0:
                _check_render_control(cancel_check, deadline)
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
            except asyncio.TimeoutError:
                continue
        return task.result()
    except BaseException:
        await _terminate_process_tree(proc)
        with contextlib.suppress(Exception):
            await asyncio.wait_for(task, timeout=_PROCESS_STOP_GRACE_SECONDS)
        if not task.done():
            task.cancel()
        raise


async def _finish_reader(task: asyncio.Task) -> None:
    """A pipe reader should finish right after its process is reaped."""
    try:
        await asyncio.wait_for(task, timeout=_PROCESS_STOP_GRACE_SECONDS)
    except asyncio.TimeoutError:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def _scene_error(message: str) -> bool:
    text = message.lower()
    return "custom_scene" in text or "custom_js" in text or "trusted_template" in text


def _validated_renderer_script(script_path: str):
    """Return original and allowlisted script forms, rejecting unsafe ingress.

    ProjectStore already normalizes normal app edits, but this is the shared
    boundary for direct callers too.  Node only receives declarative local
    template code re-expanded by ``core.schema``; a raw imported/AI snippet is
    rejected before a child process is started.
    """
    try:
        with open(script_path, "r", encoding="utf-8-sig") as handle:
            source = json.load(handle)
    except Exception as exc:
        raise RendererSceneError(f"Không đọc được lesson script: {exc}") from exc

    from core.schema import check_custom_js, validate_script

    normalized, validation_errors = validate_script(copy.deepcopy(source))
    errors = list(validation_errors) + check_custom_js(normalized)
    if errors:
        raise RendererSceneError("Script/cảnh không hợp lệ: " + "; ".join(errors[:4]))
    return source, normalized


def _prepare_renderer_script(script_path: str, output_dir: str) -> tuple[str, Optional[Path]]:
    """Validate final renderer ingress and write normalization to a temp file."""
    source, normalized = _validated_renderer_script(script_path)
    if normalized == source:
        return script_path, None

    fd, temp_name = tempfile.mkstemp(prefix=".render-script-", suffix=".json", dir=output_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(normalized, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)
        raise
    return temp_name, Path(temp_name)


# ── Chọn số worker render theo SỨC MÁY ────────────────────────────────────
# Mỗi worker = 1 tiến trình node giữ một canvas full-res trong RAM + 1 ffmpeg.
# Trước đây cứ lấy cpu_count-1 (tối đa 8) → máy nhiều lõi ít RAM bị swap và
# TREO. Giờ lấy min(theo lõi, theo RAM trống) và cho phép người dùng ép cứng.
_RAM_PER_WORKER_MB = {          # ước lượng RAM một worker cần theo khung hình
    "9:16": 700,                # 1080x1920
    "16:9": 700,
    "1:1": 500,
}


def _free_ram_mb() -> int:
    """RAM khả dụng (MB). Trả 0 nếu không đo được → bỏ qua ràng buộc RAM."""
    try:
        import psutil
        return int(psutil.virtual_memory().available / 1048576)
    except Exception:
        pass
    if os.name == "nt":         # không cần psutil: hỏi thẳng Windows
        try:
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            ms = _MS()
            ms.dwLength = ctypes.sizeof(_MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
                return int(ms.ullAvailPhys / 1048576)
        except Exception:
            pass
    return 0


def _pick_workers(aspect_ratio: str = "9:16") -> int:
    """Số tiến trình render song song an toàn cho máy này.

    settings['render_workers']: 0 = tự động (mặc định), >0 = ép cứng.
    """
    try:
        from config import load_settings
        forced = int(load_settings().get("render_workers", 0) or 0)
    except Exception:
        forced = 0
    if forced > 0:
        return max(1, min(forced, 16))

    cpu = os.cpu_count() or 4
    # Trần 8 là điểm ngọt ĐO THỰC TẾ: nâng 11 worker trên máy 12 lõi còn CHẬM
    # hơn (mỗi worker = 1 node + 1 ffmpeg, quá 8 là tranh chấp CPU).
    by_cpu = max(1, min(cpu - 1, 8))          # chừa 1 lõi cho UI + hệ điều hành

    free = _free_ram_mb()
    if free <= 0:
        return by_cpu                          # không đo được RAM → theo lõi
    need = _RAM_PER_WORKER_MB.get(aspect_ratio, 700)
    # Chừa 1.5 GB cho app + hệ điều hành, phần còn lại chia cho worker
    by_ram = max(1, int((free - 1536) / need))

    n = max(1, min(by_cpu, by_ram))
    if n < by_cpu:
        logger.info(f"[Pipe] Giảm còn {n} worker (RAM trống {free} MB, "
                    f"mỗi worker ~{need} MB) thay vì {by_cpu} theo số lõi.")
    return n

# Encoder presets for ffmpeg
ENCODER_MAP = {
    "cpu":   {"codec": "libx264",    "preset": "fast",     "extra": ["-crf", "22", "-threads", "0"]},
    "nvenc": {"codec": "h264_nvenc", "preset": "p4",       "extra": ["-rc", "vbr", "-cq", "23", "-b:v", "8M", "-maxrate", "12M", "-bufsize", "16M"]},
    "qsv":   {"codec": "h264_qsv",  "preset": "veryfast", "extra": ["-global_quality", "23", "-look_ahead", "0"]},
    "amf":   {"codec": "h264_amf",  "preset": "speed",    "extra": ["-rc", "cqp", "-qp_i", "22", "-qp_p", "22", "-usage", "transcoding"]},
}


def _find_executable(name: str) -> str:
    """Tìm ffmpeg/ffprobe chạy được, tránh bản miniconda hỏng.

    Thứ tự: bản đóng gói cạnh .exe (BASE_DIR/tools|ffmpeg) → override/PATH cho
    môi trường dev → tên trần. KHÔNG hard-code đường dẫn theo máy dev (C:\\Users\\ADMIN…)
    vì máy người dùng khác username, ffmpeg sẽ không tìm thấy → render hỏng."""
    import os, shutil
    # 1. ffmpeg đóng gói cạnh app (nếu có) — ổn định nhất, không phụ thuộc máy
    for d in (_APP_DIR / "tools", _APP_DIR / "ffmpeg" / "bin", _APP_DIR):
        exe_path = d / f"{name}.exe"
        try:
            if exe_path.is_file():
                return str(exe_path)
        except Exception:
            pass
    # 2. env override tường minh
    env_dir = os.environ.get("TUBECRAFT_FFMPEG_DIR")
    if env_dir:
        p = os.path.join(env_dir, f"{name}.exe")
        if os.path.exists(p):
            return p
    # 3. PATH chỉ là fallback khi phát triển; bản portable luôn có tools/.
    found = shutil.which(name)
    if found:
        if "miniconda3" in found.lower():        # bản miniconda hay hỏng codec
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                if not path_dir or "miniconda3" in path_dir.lower():
                    continue
                exe_path = os.path.join(path_dir, f"{name}.exe")
                if os.path.exists(exe_path):
                    return exe_path
        return found
    return name


async def _require_audio_stream(
    video_path: str,
    *,
    cancel_check: Optional[Callable[[], bool]] = None,
    deadline: Optional[float] = None,
) -> None:
    """Refuse a nominally successful export that lost its required audio.

    The renderer has several FFmpeg paths (single pipe, chunk mux, frames,
    and optional intro/outro stitching).  An exit code alone is not proof that
    the final container still has an audio stream, so verify the artifact at
    the one shared publication boundary.
    """
    ffprobe_exe = _find_executable("ffprobe")
    if not Path(ffprobe_exe).is_file() and not shutil.which(ffprobe_exe):
        raise RendererProcessError("Thiếu tools/ffprobe.exe; không thể xác minh audio video.")
    proc = await _exec(
        ffprobe_exe,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await _communicate_process(
        proc, cancel_check=cancel_check, deadline=deadline,
    )
    stream_type = stdout.decode("utf-8", "replace").strip().lower()
    if proc.returncode != 0 or stream_type != "audio":
        detail = stderr.decode("utf-8", "replace")[-300:].strip()
        raise RendererProcessError(
            "Video cuối không có audio hợp lệ; từ chối xuất video câm"
            + (f": {detail}" if detail else ".")
        )


async def _concat_videos_ffmpeg(segments: List[str], output_path: str, aspect_ratio: str,
                                gpu_encoder: str = "nvenc", *,
                                cancel_check: Optional[Callable[[], bool]] = None,
                                deadline: Optional[float] = None,
                                fps: int = 30):
    """
    Concatenate video segments cleanly using FFmpeg complex filter.
    Ensures all segments are standardized to matching resolutions, 30 FPS, and resampled audio.
    """
    import asyncio
    
    ffmpeg_exe = _find_executable("ffmpeg")
    
    # Target resolution based on aspect ratio
    if aspect_ratio == "16:9":
        tw, th = 1920, 1080
    else:
        tw, th = 1080, 1920
        
    enc = ENCODER_MAP.get(gpu_encoder, ENCODER_MAP["nvenc"])
    
    # Build filter complex inputs
    filter_complex = ""
    inputs = []
    
    for i, seg in enumerate(segments):
        inputs.extend(["-i", seg])
        # scale each segment to exact target, pad to avoid skew, format yuv420p at 30 fps
        filter_complex += f"[{i}:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p[v{i}];"
        # Audio resample to standard 44100Hz stereo
        filter_complex += f"[{i}:a]aresample=44100,pan=stereo[a{i}];"
        
    # Now concatenate audio and video elements
    for i in range(len(segments)):
        filter_complex += f"[v{i}][a{i}]"
    filter_complex += f"concat=n={len(segments)}:v=1:a=1[outv][outa]"
    
    cmd = [
        ffmpeg_exe, "-y", "-threads", "0"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", enc["codec"], "-preset", enc["preset"]
    ]
    
    if enc.get("extra"):
        cmd.extend(enc["extra"])
        
    cmd.extend([
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ])
    
    logger.info(f"[Concat] Stitching {len(segments)} segments using {gpu_encoder}...")
    
    proc = await _exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await _communicate_process(proc, cancel_check=cancel_check, deadline=deadline)
    
    if proc.returncode != 0:
        # Fallback to CPU libx264 if GPU encoder fails during stitching
        if gpu_encoder != "cpu":
            logger.warning("[Concat] GPU encoding failed, falling back to CPU...")
            cpu_enc = ENCODER_MAP["cpu"]
            cpu_cmd = [
                ffmpeg_exe, "-y", "-threads", "0"
            ] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", cpu_enc["codec"], "-preset", cpu_enc["preset"]
            ] + cpu_enc.get("extra", []) + [
                "-c:a", "aac", "-b:a", "128k",
                output_path
            ]
            proc_fb = await _exec(
                *cpu_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr_fb = await _communicate_process(proc_fb, cancel_check=cancel_check, deadline=deadline)
            if proc_fb.returncode != 0:
                raise RuntimeError(f"FFmpeg concat fallback failed: {stderr_fb.decode()[:300]}")
        else:
            raise RuntimeError(f"FFmpeg concat failed: {stderr.decode()[:300]}")


def _find_node_modules():
    """Find this repository's canvas dependency or an explicit override."""
    here = Path(__file__).resolve()
    candidates = [
        _APP_DIR / "node_modules",             # cạnh .exe (bản đóng gói) / gốc project (dev)
        _APP_DIR / "engines" / "node_modules",
        here.parent / "node_modules",          # engines/node_modules
        here.parent.parent / "node_modules",   # repository root/node_modules
    ]
    # dò thêm vài cấp cha (an toàn nếu đóng gói khác cấu trúc)
    for up in range(2, min(6, len(here.parents))):
        candidates.append(here.parents[up] / "node_modules")
    # Explicit override is useful for portable/offline deployments.
    import os as _os
    if _os.environ.get("TUBECRAFT_NODE_MODULES"):
        candidates.insert(0, Path(_os.environ["TUBECRAFT_NODE_MODULES"]))
    for p in candidates:
        try:
            if (p / "canvas").is_dir():
                return p
        except Exception:
            continue
    return None


async def _ensure_canvas():
    """Return the bundled Canvas runtime or fail without mutating the machine."""
    nm = _find_node_modules()
    if nm:
        return nm
    raise RuntimeError("Thiếu node_modules/canvas; hãy khôi phục bundle TubeCraft đầy đủ.")


async def render_and_encode(
    script_path: str,
    timing_path: str,
    output_dir: str,
    project_id: str,
    theme: str = "dark",
    bg_color: str = "",
    bg: str = "",                       # id preset nền (core/backgrounds.py); "" = theo phong cách
    aspect_ratio: str = "9:16",
    art_style: str = "default",
    title_color: str = "",
    text_color: str = "",
    font_family: str = "",
    subtitle: Optional[dict] = None,    # core.subtitles.subtitle_config(project); None = không phụ đề
    render_mode: str = "pipe",
    gpu_encoder: str = "nvenc",
    intro_video_path: Optional[str] = None,
    outro_video_path: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
    fps: int = 30,
    cancel_check: Optional[Callable[[], bool]] = None,
    timeout_seconds: Optional[float] = None,
    require_audio: bool = False,
) -> str:
    """Render + encode video.

    ``fps`` is normalized to 10–60.  ``cancel_check`` is polled while child
    processes run; ``timeout_seconds`` is an optional absolute render budget.
    Neither a cancellation nor a timeout replaces an existing final MP4.
    ``require_audio`` is used by the project renderer: it refuses to publish a
    video if the canonical narration disappears or the encoded MP4 has no
    audio stream. Preview/test callers may intentionally render silent video.
    """
    from core.aspect_ratios import require_aspect_ratio

    aspect_ratio = require_aspect_ratio(aspect_ratio)
    os.makedirs(output_dir, exist_ok=True)
    fps = _normalize_fps(fps)
    try:
        with open(timing_path, "r", encoding="utf-8-sig") as timing_file:
            total_duration = float(json.load(timing_file).get("total_duration", 30.0) or 30.0)
    except Exception:
        total_duration = 30.0
    deadline = _render_deadline(total_duration, timeout_seconds)
    _check_render_control(cancel_check, deadline)

    # Validate caller-supplied content before looking up or starting any
    # renderer dependency.  ``_prepare_renderer_script`` validates again at
    # the final handoff so a file changed concurrently cannot bypass it.
    _validated_renderer_script(script_path)

    if progress_callback:
        progress_callback(5, "Preparing renderer...")

    node_modules = await _ensure_canvas()
    node_exe = _find_executable("node")
    if not Path(node_exe).is_file() and not shutil.which(node_exe):
        raise RuntimeError("Thiếu tools/node.exe; hãy khôi phục bundle TubeCraft đầy đủ.")
    if not CANVAS_RENDERER_JS.is_file():
        raise RuntimeError(f"Thiếu renderer: {CANVAS_RENDERER_JS}")
    ext_dir = _APP_DIR

    audio_path = os.path.join(os.path.dirname(script_path), "audio", "full_audio.mp3")
    # Once a caller begins with narration, it must not silently degrade to a
    # silent MP4 if that file disappears during a long render.  ``require_audio``
    # additionally protects the project workflow when its canonical file was
    # already absent at entry; previews without a source stay intentionally
    # silent and skip this verification.
    audio_present_at_start = os.path.isfile(audio_path)
    must_verify_audio = require_audio or audio_present_at_start
    if require_audio and not audio_present_at_start:
        raise RendererProcessError("Không tìm thấy audio hợp lệ để render video.")
    aspect_suffix = aspect_ratio.replace(":", "_")
    target_video = os.path.join(output_dir, f"edu_{project_id}_{aspect_suffix}.mp4")
    final_video = target_video + ".rendering.mp4"
    Path(final_video).unlink(missing_ok=True)

    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules)
    # Kho sprite của template (ui.sprite trong renderer)
    try:
        from config import DATA_DIR, GALLERY_DIR, TEMPLATE_CACHE_DIR
        env["TUBECRAFT_TEMPLATE_CACHE"] = str(TEMPLATE_CACHE_DIR)
        env["TUBECRAFT_GALLERY_DIR"] = str(GALLERY_DIR)
        env["TUBECRAFT_FONTS_MANIFEST"] = str(Path(DATA_DIR) / "fonts.json")
        env["TUBECRAFT_FONTS_DIR"] = str(Path(DATA_DIR) / "fonts")
    except Exception:
        pass
    # Override màu/font do người dùng chọn — renderer đọc từ env (fallback của args)
    if title_color:
        env["TUBECRAFT_TITLE_COLOR"] = title_color
    if text_color:
        env["TUBECRAFT_TEXT_COLOR"] = text_color
    if font_family:
        env["TUBECRAFT_FONT"] = font_family
    # Nền tuỳ biến (độc lập phong cách). Truyền qua env để MỌI worker chunk
    # song song đều nhận, không phải sửa 4 chỗ dựng lệnh.
    if bg:
        try:
            from core.backgrounds import get as _bg_get
            cfg = _bg_get(bg)
            if cfg:
                env["TUBECRAFT_BG_GRAD"] = ",".join(cfg["grad"])
                env["TUBECRAFT_BG_FX"] = cfg["fx"]
        except Exception as e:
            logger.warning(f"Nền '{bg}' không áp được: {e}")

    # ── Phụ đề cháy chữ ──────────────────────────────────────────────────
    # 'subtitle' là dict ĐÃ GIẢI QUYẾT (core.subtitles.subtitle_config): preset
    # đã chọn xong, không còn "" = auto. Truyền qua CẢ HAI kênh:
    #   • --subtitle <json>  : cờ CLI, thêm vào CẢ 4 chỗ dựng lệnh (pipe/frames
    #     × đơn/chunk) — thiếu 1 chỗ là chunk đó mất phụ đề, video nhấp nháy.
    #   • TUBECRAFT_SUBTITLE (env): lưới an toàn, mọi tiến trình con thừa kế.
    # subtitle=None hoặc enabled=False → sub_args=[] → renderer không thấy cờ
    # → vẽ y hệt bản chưa có phụ đề (tương thích ngược).
    sub_args: List[str] = []
    if isinstance(subtitle, dict) and subtitle.get("enabled"):
        try:
            from core.subtitles import to_json as _sub_json
            payload = _sub_json(subtitle)
        except Exception:
            payload = json.dumps(subtitle, ensure_ascii=False, separators=(",", ":"))
        sub_args = ["--subtitle", payload]
        env["TUBECRAFT_SUBTITLE"] = payload
        logger.info(f"[Subtitle] preset={subtitle.get('preset')} "
                    f"scale={subtitle.get('fontScale')}")

    # Prepend working ffmpeg directory to PATH so subprocesses spawned by node find the correct ffmpeg
    ffmpeg_exe = _find_executable("ffmpeg")
    if not Path(ffmpeg_exe).is_file() and not shutil.which(ffmpeg_exe):
        raise RuntimeError("Thiếu tools/ffmpeg.exe; hãy khôi phục bundle TubeCraft đầy đủ.")
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir:
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

    # 1. Render primary slide content video.  Only the temporary path is ever
    # touched before the final atomic replace below.
    safe_script_path, safe_script_temp = _prepare_renderer_script(script_path, output_dir)
    try:
        if render_mode == "pipe":
            await _render_pipe(
                node_exe, ext_dir, safe_script_path, timing_path, output_dir,
                theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, gpu_encoder,
                sub_args=sub_args, fps=fps, cancel_check=cancel_check, deadline=deadline,
            )
        else:
            await _render_frames(
                node_exe, ext_dir, safe_script_path, timing_path, output_dir,
                theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, gpu_encoder,
                sub_args=sub_args, fps=fps, cancel_check=cancel_check, deadline=deadline,
            )
    except BaseException:
        Path(final_video).unlink(missing_ok=True)
        raise
    finally:
        if safe_script_temp is not None:
            safe_script_temp.unlink(missing_ok=True)

    # 2. Perform FFmpeg stitching if custom video Intro or Outro template is selected
    if intro_video_path or outro_video_path:
        if progress_callback:
            progress_callback(97, "🎬 Nối ghép Intro/Outro video...")
            
        segments = []
        if intro_video_path:
            segments.append(intro_video_path)
        segments.append(final_video)
        if outro_video_path:
            segments.append(outro_video_path)
            
        stitched_temp = final_video + ".stitched.mp4"
        try:
            await _concat_videos_ffmpeg(
                segments, stitched_temp, aspect_ratio, gpu_encoder,
                cancel_check=cancel_check, deadline=deadline, fps=fps,
            )
            if os.path.exists(stitched_temp):
                os.replace(stitched_temp, final_video)
                logger.info(f"Stitching success! Combined video: {final_video}")
        except (RenderCancelledError, RenderTimeoutError):
            Path(stitched_temp).unlink(missing_ok=True)
            Path(final_video).unlink(missing_ok=True)
            raise
        except Exception as e:
            logger.error(f"FFmpeg concatenation failed: {e}")
            if os.path.exists(stitched_temp):
                try:
                    os.remove(stitched_temp)
                except Exception:
                    pass
            # We degrade gracefully: return the unstitched final_video instead of crashing
            if progress_callback:
                progress_callback(99, "⚠️ Lỗi ghép video, giữ lại video gốc...")

    try:
        _check_render_control(cancel_check, deadline)
        if not os.path.isfile(final_video):
            raise RendererProcessError("Renderer không tạo được file video cuối.")
        file_size = os.path.getsize(final_video)
        if file_size <= 1_000:
            raise RendererProcessError("Renderer tạo file video rỗng hoặc không hợp lệ.")
        if must_verify_audio:
            if not os.path.isfile(audio_path):
                raise RendererProcessError("Nguồn audio đã biến mất trong khi render; từ chối publish video.")
            await _require_audio_stream(
                final_video, cancel_check=cancel_check, deadline=deadline,
            )
        _check_render_control(cancel_check, deadline)
        os.replace(final_video, target_video)
    except BaseException:
        # Preserve the previous published target; a failed verification is
        # never a reason to leave a temporary, potentially silent MP4 behind.
        Path(final_video).unlink(missing_ok=True)
        raise
    if progress_callback:
        progress_callback(100, "Video export complete!")
    logger.info(f"Final: {target_video} ({file_size / 1024 / 1024:.1f} MB)")
    return target_video


def _renderer_failure(returncode, stderr_content: str, payload_error: Optional[dict], context: str):
    """Translate renderer JSON/stderr into an error the queue can classify."""
    payload_message = ""
    payload_code = ""
    if isinstance(payload_error, dict):
        payload_message = str(payload_error.get("message") or "")
        payload_code = str(payload_error.get("code") or "")
    if payload_message:
        message = payload_message
    else:
        error_lines = [
            line for line in stderr_content.split("\n")
            if line.strip() and not line.strip().startswith("[Renderer]")
        ]
        message = "\n".join(error_lines[-20:]) if error_lines else stderr_content[-2000:]
    message = message.strip() or "Lỗi renderer không có mô tả."
    prefix = f"{context}: " if context else ""
    if payload_code == "custom_scene_error" or _scene_error(message):
        return RendererSceneError(f"{prefix}{message[:2000]}")
    return RendererProcessError(f"{prefix}{message[:2000]} (exit code {returncode})")


async def _monitor_node_process(proc, *, on_progress: Optional[Callable[[dict], None]] = None,
                                cancel_check: Optional[Callable[[], bool]] = None,
                                deadline: Optional[float] = None):
    """Drain a Node renderer while retaining cancellation and stall control."""
    stderr_lines = []
    payload_error = None
    last_progress = time.monotonic()

    async def read_stderr():
        try:
            while True:
                line = await proc.stderr.readline()
                if not line:
                    return
                stderr_lines.append(line)
        except (asyncio.CancelledError, Exception):
            return

    async def read_stdout():
        nonlocal last_progress, payload_error
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    return
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str.startswith("{"):
                    continue
                try:
                    message = json.loads(line_str)
                except json.JSONDecodeError:
                    continue
                if message.get("type") == "error":
                    payload_error = message
                elif message.get("type") == "progress":
                    last_progress = time.monotonic()
                    if on_progress:
                        on_progress(message)
                elif message.get("type") == "done":
                    last_progress = time.monotonic()
                    logger.info(f"Renderer done: {message.get('totalFrames')} frames")
        except (asyncio.CancelledError, Exception):
            return

    stdout_task = asyncio.create_task(read_stdout())
    stderr_task = asyncio.create_task(read_stderr())
    try:
        while getattr(proc, "returncode", None) is None:
            _check_render_control(cancel_check, deadline)
            idle_remaining = _RENDERER_IDLE_TIMEOUT_SECONDS - (time.monotonic() - last_progress)
            if idle_remaining <= 0:
                raise RendererProcessError(
                    f"Renderer không có tiến độ trong {_RENDERER_IDLE_TIMEOUT_SECONDS:.0f} giây."
                )
            try:
                await asyncio.wait_for(proc.wait(), timeout=min(_poll_timeout(deadline), idle_remaining))
            except asyncio.TimeoutError:
                continue
        returncode = proc.returncode
    except BaseException:
        await _terminate_process_tree(proc)
        raise
    finally:
        await _finish_reader(stdout_task)
        await _finish_reader(stderr_task)
    return returncode, b"".join(stderr_lines).decode("utf-8", errors="replace"), payload_error


async def _run_node_renderer(node_exe, ext_dir, cmd, env, progress_callback, pct_range=(8, 96), *,
                             cancel_check: Optional[Callable[[], bool]] = None,
                             deadline: Optional[float] = None):
    """Run canvas_renderer.js and stream progress without unbounded waits."""
    _check_render_control(cancel_check, deadline)
    proc = await _exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(ext_dir),
        env=env,
    )
    pct_start, pct_end = pct_range

    def on_progress(message: dict) -> None:
        if not progress_callback:
            return
        pct = int(pct_start + message.get("percent", 0) / 100 * (pct_end - pct_start))
        progress_callback(pct, message.get("message", "Rendering..."))

    returncode, stderr_content, payload_error = await _monitor_node_process(
        proc, on_progress=on_progress, cancel_check=cancel_check, deadline=deadline,
    )
    if returncode != 0 or payload_error:
        error = _renderer_failure(returncode, stderr_content, payload_error, "Render failed")
        logger.error("Renderer error: %s", error)
        raise error
    return proc


async def _render_pipe(node_exe, ext_dir, script_path, timing_path, output_dir,
                       theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, gpu_encoder="nvenc",
                       sub_args=None, *, fps: int = 30,
                       cancel_check: Optional[Callable[[], bool]] = None,
                       deadline: Optional[float] = None):
    """PIPE MODE: render + encode in single step (fast). Uses multi-process chunk rendering."""
    import math
    sub_args = list(sub_args or [])      # ['--subtitle', '<json>'] hoặc []
    enc = ENCODER_MAP.get(gpu_encoder, ENCODER_MAP["nvenc"])
    encoder_label = {"cpu": "CPU", "nvenc": "NVIDIA GPU", "qsv": "Intel QSV", "amf": "AMD AMF"}.get(gpu_encoder, gpu_encoder)

    # 1. Determine total duration and total frames
    total_duration = 30.0
    try:
        with open(timing_path, "r", encoding="utf-8-sig") as f:
            timing_data = json.load(f)
            total_duration = timing_data.get("total_duration", 30.0)
    except Exception as e:
        logger.warning(f"[Pipe] Could not read timing map to determine duration: {e}")

    total_frames = math.ceil(total_duration * fps)

    # 2. Số worker theo SỨC MÁY THẬT (không chỉ số lõi)
    num_workers = _pick_workers(aspect_ratio)

    # Fallback to single worker if total duration is extremely short (under 5 seconds)
    if total_frames < 150:
        num_workers = 1

    logger.info(f"[Pipe] Rendering → {final_video} (encoder: {encoder_label}, workers: {num_workers}, frames: {total_frames})")

    if num_workers == 1:
        # Single process fallback
        cmd = [
            node_exe, str(CANVAS_RENDERER_JS),
            "--script", script_path,
            "--timing", timing_path,
            "--output", output_dir,
            "--theme", theme, "--bg-color", bg_color, "--aspect", aspect_ratio,
            "--style", art_style,
            "--fps", str(fps),
            "--mode", "pipe",
            "--outputFile", final_video,
            "--codec", enc["codec"],
            "--preset", enc["preset"],
        ] + sub_args
        if enc.get("extra"):
            cmd.extend(["--ffmpegExtra", " ".join(enc["extra"])])
        if os.path.isfile(audio_path):
            cmd.extend(["--audio", audio_path])

        if progress_callback:
            progress_callback(8, f"⚡ Pipe + {encoder_label}: rendering...")

        try:
            await _run_node_renderer(
                node_exe, ext_dir, cmd, env, progress_callback, (8, 96),
                cancel_check=cancel_check, deadline=deadline,
            )
        except (RenderCancelledError, RenderTimeoutError, RendererSceneError):
            raise
        except RendererProcessError as e:
            logger.warning(f"[Pipe] Failed ({e}), falling back to frames + CPU encoder...")
            if progress_callback:
                progress_callback(10, "⚠️ Pipe failed, switching to CPU frames mode...")
            return await _render_frames(
                node_exe, ext_dir, script_path, timing_path, output_dir,
                theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, "cpu",
                sub_args=sub_args, fps=fps, cancel_check=cancel_check,
                deadline=_fallback_deadline(deadline, total_duration),
            )
    else:
        # Multi-process parallel rendering
        temp_dir = os.path.join(output_dir, f"temp_chunks_{os.path.basename(final_video)}")
        os.makedirs(temp_dir, exist_ok=True)

        chunk_size = total_frames // num_workers
        workers_ranges = []
        for w in range(num_workers):
            start = w * chunk_size
            end = total_frames if w == num_workers - 1 else (w + 1) * chunk_size
            workers_ranges.append((start, end))

        procs = []
        try:
            for w, (start, end) in enumerate(workers_ranges):
                _check_render_control(cancel_check, deadline)
                chunk_path = os.path.join(temp_dir, f"chunk_{w}.mp4")
                cmd_w = [
                node_exe, str(CANVAS_RENDERER_JS),
                "--script", script_path,
                "--timing", timing_path,
                "--output", output_dir,
                "--theme", theme, "--bg-color", bg_color, "--aspect", aspect_ratio,
                "--style", art_style,
                "--fps", str(fps),
                "--mode", "pipe",
                "--outputFile", chunk_path,
                "--codec", "libx264",
                "--preset", "ultrafast",
                "--startFrame", str(start),
                "--endFrame", str(end)
                ] + sub_args  # Every chunk needs the same subtitle configuration.
                cmd_w.extend(["--ffmpegExtra", "-crf 22 -threads 2"])
                proc = await _exec(
                    *cmd_w,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(ext_dir),
                    env=env,
                )
                procs.append(proc)
        except BaseException:
            await asyncio.gather(*(_terminate_process_tree(p) for p in procs), return_exceptions=True)
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        worker_progress = [0] * num_workers

        async def monitor_worker(w_idx, proc):
            def on_progress(message: dict) -> None:
                frame = message.get("frame", 0)
                start = message.get("startFrame", 0)
                worker_progress[w_idx] = max(0, frame - start)
                total_done = sum(worker_progress)
                pct = int((total_done / total_frames) * 100)
                mapped_pct = int(8 + (pct / 100.0) * (96 - 8))
                if progress_callback:
                    progress_callback(mapped_pct, f"⚡ Pipe + {encoder_label}: rendering... {pct}% ({total_done}/{total_frames} frames)")

            returncode, stderr_content, payload_error = await _monitor_node_process(
                proc, on_progress=on_progress, cancel_check=cancel_check, deadline=deadline,
            )
            if returncode != 0 or payload_error:
                raise _renderer_failure(returncode, stderr_content, payload_error, f"Worker {w_idx} failed")

        tasks = [asyncio.create_task(monitor_worker(i, procs[i])) for i in range(num_workers)]
        try:
            await asyncio.gather(*tasks)
        except BaseException as exc:
            logger.error(f"[Pipe] Parallel rendering error: {exc}")
            await asyncio.gather(*(_terminate_process_tree(p) for p in procs), return_exceptions=True)
            await asyncio.gather(*tasks, return_exceptions=True)
            shutil.rmtree(temp_dir, ignore_errors=True)
            if isinstance(exc, (RenderCancelledError, RenderTimeoutError, RendererSceneError)):
                raise
            logger.warning("[Pipe] Parallel render failed, falling back to frames + CPU...")
            if progress_callback:
                progress_callback(10, "⚠️ Parallel render failed, switching to CPU frames mode...")
            return await _render_frames(
                node_exe, ext_dir, script_path, timing_path, output_dir,
                theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, "cpu",
                sub_args=sub_args, fps=fps, cancel_check=cancel_check,
                deadline=_fallback_deadline(deadline, total_duration),
            )

        # 3. Concatenate video chunks using FFmpeg demuxer
        if progress_callback:
            progress_callback(96, "🎬 Ghép các phân đoạn video...")

        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f_list:
            for w in range(num_workers):
                chunk_file = os.path.join(temp_dir, f"chunk_{w}.mp4").replace("\\", "/")
                f_list.write(f"file '{chunk_file}'\n")

        raw_video = os.path.join(temp_dir, "raw_video.mp4")
        ffmpeg_exe = _find_executable("ffmpeg")
        concat_cmd = [
            ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c", "copy", raw_video
        ]

        logger.info(f"[Pipe] Stitching chunks: {' '.join(concat_cmd)}")
        proc_concat = await _exec(
            *concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr_concat = await _communicate_process(
            proc_concat, cancel_check=cancel_check, deadline=deadline,
        )
        if proc_concat.returncode != 0:
            logger.error(f"[Pipe] FFmpeg concat failed: {stderr_concat.decode()[:500]}")
            # Try to copy first chunk or fallback
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            raise RuntimeError(f"FFmpeg chunk concat failed: {stderr_concat.decode()[:300]}")

        # 4. Mux audio bằng STREAM COPY — chunks đã là h264 (libx264 crf22),
        # encode lại lần 2 tốn ~10-15% tổng thời gian và còn GIẢM chất lượng.
        # Copy giữ nguyên video, chỉ ghép audio (gần như tức thì).
        if progress_callback:
            progress_callback(98, "🔊 Ghép âm thanh...")

        if os.path.isfile(audio_path):
            cmd_mux = [
                ffmpeg_exe, "-y",
                "-i", raw_video, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-shortest", final_video,
            ]
            logger.info(f"[Pipe] Mux (stream copy): {' '.join(cmd_mux)}")
            proc_mux = await _exec(
                *cmd_mux, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr_mux = await _communicate_process(
                proc_mux, cancel_check=cancel_check, deadline=deadline,
            )
            if proc_mux.returncode != 0:
                # Hiếm: copy lỗi → transcode như đường cũ
                logger.warning(f"[Pipe] Copy-mux failed: {stderr_mux.decode()[:200]}"
                               ", falling back to transcode")
                cmd_fb = [ffmpeg_exe, "-y", "-i", raw_video, "-i", audio_path,
                          "-c:v", enc["codec"], "-preset", enc["preset"]]
                if enc.get("extra"):
                    cmd_fb.extend(enc["extra"])
                cmd_fb.extend(["-c:a", "aac", "-b:a", "128k", "-shortest",
                               final_video])
                proc_fb = await _exec(
                    *cmd_fb, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr_fb = await _communicate_process(
                    proc_fb, cancel_check=cancel_check, deadline=deadline,
                )
                if proc_fb.returncode != 0:
                    raise RuntimeError(
                        f"FFmpeg audio mux failed: {stderr_fb.decode('utf-8', 'replace')[-300:]}"
                    )
        else:
            shutil.copy2(raw_video, final_video)

        # 5. Cleanup temp chunk files
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"[Pipe] Cleanup chunks error: {e}")

    if not os.path.isfile(final_video):
        logger.warning("[Pipe] No output file produced, falling back to frames + CPU...")
        if progress_callback:
            progress_callback(10, "⚠️ Không tìm thấy file kết quả, chuyển sang CPU frames mode...")
        return await _render_frames(
            node_exe, ext_dir, script_path, timing_path, output_dir,
            theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, "cpu",
            sub_args=sub_args, fps=fps, cancel_check=cancel_check,
            deadline=_fallback_deadline(deadline, total_duration),
        )

    if progress_callback:
        progress_callback(100, "Video export complete!")

    file_size = os.path.getsize(final_video)
    logger.info(f"Final: {final_video} ({file_size / 1024 / 1024:.1f} MB)")
    return final_video


async def _render_frames(node_exe, ext_dir, script_path, timing_path, output_dir,
                          theme, bg_color, aspect_ratio, art_style, audio_path, final_video, env, progress_callback, gpu_encoder="nvenc",
                          sub_args=None, *, fps: int = 30,
                          cancel_check: Optional[Callable[[], bool]] = None,
                          deadline: Optional[float] = None):
    """FRAMES MODE: render JPEGs then FFmpeg encode (stable). Uses multi-process parallel rendering."""
    import math
    sub_args = list(sub_args or [])      # ['--subtitle', '<json>'] hoặc []
    frames_dir = os.path.join(os.path.dirname(script_path), "frames")
    os.makedirs(frames_dir, exist_ok=True)

    # Clean old frames
    for f in os.listdir(frames_dir):
        if f.endswith(".png") or f.endswith(".jpg"):
            try:
                os.remove(os.path.join(frames_dir, f))
            except Exception:
                pass

    # 1. Determine total duration and total frames
    total_duration = 30.0
    try:
        with open(timing_path, "r", encoding="utf-8-sig") as f:
            timing_data = json.load(f)
            total_duration = timing_data.get("total_duration", 30.0)
    except Exception as e:
        logger.warning(f"[Frames] Could not read timing map: {e}")

    total_frames = math.ceil(total_duration * fps)

    # Keep frames-mode worker policy consistent with pipe mode and user settings.
    num_workers = _pick_workers(aspect_ratio)

    # Fallback to single worker if extremely short
    if total_frames < 150:
        num_workers = 1

    logger.info(f"[Frames] Rendering PNG/JPEGs (workers: {num_workers}, total frames: {total_frames})")

    # Step 1: Render frames (Single or Parallel)
    if num_workers == 1:
        cmd = [
            node_exe, str(CANVAS_RENDERER_JS),
            "--script", script_path,
            "--timing", timing_path,
            "--output", frames_dir,
            "--theme", theme, "--bg-color", bg_color, "--aspect", aspect_ratio,
            "--style", art_style,
            "--fps", str(fps),
            "--mode", "frames",
        ] + sub_args
        if progress_callback:
            progress_callback(5, "🖼️ Rendering frames...")
        await _run_node_renderer(
            node_exe, ext_dir, cmd, env, progress_callback, (5, 65),
            cancel_check=cancel_check, deadline=deadline,
        )
    else:
        chunk_size = total_frames // num_workers
        workers_ranges = []
        for w in range(num_workers):
            start = w * chunk_size
            end = total_frames if w == num_workers - 1 else (w + 1) * chunk_size
            workers_ranges.append((start, end))

        procs = []
        try:
            for w, (start, end) in enumerate(workers_ranges):
                _check_render_control(cancel_check, deadline)
                cmd_w = [
                node_exe, str(CANVAS_RENDERER_JS),
                "--script", script_path,
                "--timing", timing_path,
                "--output", frames_dir,
                "--theme", theme, "--bg-color", bg_color, "--aspect", aspect_ratio,
                "--style", art_style,
                "--fps", str(fps),
                "--mode", "frames",
                "--startFrame", str(start),
                "--endFrame", str(end)
                ] + sub_args  # Every chunk needs the same subtitle configuration.
                proc = await _exec(
                    *cmd_w,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(ext_dir),
                    env=env,
                )
                procs.append(proc)
        except BaseException:
            await asyncio.gather(*(_terminate_process_tree(p) for p in procs), return_exceptions=True)
            raise

        worker_progress = [0] * num_workers

        async def monitor_worker(w_idx, proc):
            def on_progress(message: dict) -> None:
                frame = message.get("frame", 0)
                start = message.get("startFrame", 0)
                worker_progress[w_idx] = max(0, frame - start)
                total_done = sum(worker_progress)
                pct = int((total_done / total_frames) * 100)
                mapped_pct = int(5 + (pct / 100.0) * (65 - 5))
                if progress_callback:
                    progress_callback(mapped_pct, f"🖼️ Rendering frames... {pct}% ({total_done}/{total_frames})")

            returncode, stderr_content, payload_error = await _monitor_node_process(
                proc, on_progress=on_progress, cancel_check=cancel_check, deadline=deadline,
            )
            if returncode != 0 or payload_error:
                raise _renderer_failure(returncode, stderr_content, payload_error, f"Worker {w_idx} failed")

        tasks = [asyncio.create_task(monitor_worker(i, procs[i])) for i in range(num_workers)]
        try:
            await asyncio.gather(*tasks)
        except BaseException as exc:
            logger.error(f"[Frames] Parallel rendering error: {exc}")
            await asyncio.gather(*(_terminate_process_tree(p) for p in procs), return_exceptions=True)
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    frame_count = len([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
    if frame_count != total_frames:
        raise RendererProcessError(f"Renderer tạo {frame_count}/{total_frames} frame; không thể xuất video không đầy đủ.")
    logger.info(f"Rendered {frame_count} frames")

    # Step 2: FFmpeg encode with selected encoder
    enc = ENCODER_MAP.get(gpu_encoder, ENCODER_MAP["nvenc"])
    encoder_label = {"cpu": "CPU", "nvenc": "NVIDIA GPU", "qsv": "Intel QSV", "amf": "AMD AMF"}.get(gpu_encoder, gpu_encoder)
    if progress_callback:
        progress_callback(68, f"🎬 Encoding ({encoder_label})...")

    ffmpeg_exe = _find_executable("ffmpeg")
    raw_video = os.path.join(output_dir, f"raw_{os.path.basename(final_video)}")
    frame_pattern = os.path.join(frames_dir, "frame_%06d.jpg")

    cmd_encode = [
        ffmpeg_exe, "-y",
        "-threads", "0",               # use all CPU threads for decode
        "-framerate", str(fps),
        "-i", frame_pattern,
        "-c:v", enc["codec"], "-preset", enc["preset"],
    ] + enc.get("extra", []) + [
        "-pix_fmt", "yuv420p",
        raw_video,
    ]
    proc2 = await _exec(
        *cmd_encode, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr2 = await _communicate_process(
        proc2, cancel_check=cancel_check, deadline=deadline,
    )
    if proc2.returncode != 0:
        # Fallback to CPU if GPU encoder fails
        if gpu_encoder != "cpu":
            logger.warning(f"{encoder_label} failed, falling back to CPU: {stderr2.decode()[:200]}")
            if progress_callback:
                progress_callback(70, "⚠️ GPU failed, falling back to CPU...")
            cpu_enc = ENCODER_MAP["cpu"]
            cmd_fallback = [
                ffmpeg_exe, "-y",
                "-threads", "0",
                "-framerate", str(fps),
                "-i", frame_pattern,
                "-c:v", cpu_enc["codec"], "-preset", cpu_enc["preset"],
            ] + cpu_enc.get("extra", []) + [
                "-pix_fmt", "yuv420p",
                raw_video,
            ]
            proc_fb = await _exec(
                *cmd_fallback, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_fb = await _communicate_process(
                proc_fb, cancel_check=cancel_check, deadline=deadline,
            )
            if proc_fb.returncode != 0:
                raise RuntimeError(f"FFmpeg encode failed (CPU fallback): {stderr_fb.decode()[:300]}")
        else:
            raise RuntimeError(f"FFmpeg encode failed: {stderr2.decode()[:300]}")
    # Step 3: Mux audio
    if os.path.isfile(audio_path):
        if progress_callback:
            progress_callback(85, "🔊 Muxing audio...")
        cmd_mux = [
            ffmpeg_exe, "-y",
            "-i", raw_video,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            final_video,
        ]
        proc3 = await _exec(
            *cmd_mux, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr3 = await _communicate_process(
            proc3, cancel_check=cancel_check, deadline=deadline,
        )
        if proc3.returncode != 0:
            detail = stderr3.decode("utf-8", "replace")[-500:]
            raise RendererProcessError(
                f"FFmpeg mux audio thất bại; từ chối xuất video câm: {detail}"
            )
    else:
        shutil.copy2(raw_video, final_video)

    # Cleanup
    try:
        os.remove(raw_video)
    except Exception:
        pass

    # Clean up intermediate JPEG/PNG frames to save disk space
    try:
        for f in os.listdir(frames_dir):
            if f.endswith(".png") or f.endswith(".jpg"):
                os.remove(os.path.join(frames_dir, f))
    except Exception as e:
        logger.warning(f"[Frames] Failed to clean up frames directory: {e}")

    if progress_callback:
        progress_callback(100, "Video export complete!")

    file_size = os.path.getsize(final_video)
    logger.info(f"Final: {final_video} ({file_size / 1024 / 1024:.1f} MB)")
    return final_video
