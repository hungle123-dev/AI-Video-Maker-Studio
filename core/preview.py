"""core/preview.py — Preview canvas trước khi render bằng engine TubeCraft.

Thay vì render cả video, ta render MỘT frame PNG cho mỗi step bằng chính
engine canvas_renderer.js — nên preview chính xác 100% với video cuối.

Nếu chưa có timing (chưa chạy TTS), dựng timing tổng hợp: mỗi step một
khoảng thời gian ước từ độ dài lời thoại. previewTime lấy gần cuối step để
hình đã "settled" (stepProgress ≈ 1).
"""
import copy, os, json, shutil, subprocess, tempfile, logging, time
from pathlib import Path; logger = logging.getLogger("TubeCraft.Preview"); _CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
from config import ENGINES_DIR; RENDERER_JS = Path(ENGINES_DIR) / "canvas_renderer.js"
def _synth_timing(script: dict) -> dict:
    steps = script.get("steps", []); offset = 0.0; tsteps = []
    for i, s in enumerate(steps):
        text = (s.get("voice_text") or "").strip()
        dur = max(len(text) * 0.06, 2.5)
        tsteps.append({"id": s.get("id", i + 1), "start": round(offset, 3), "end": round(offset + dur, 3), "duration": round(dur, 3), "audio": "", "words": []})
        offset += dur
    return {"steps": tsteps, "total_duration": round(offset, 3), "merged_audio": None}

def _node_env():
    from engines.video_encoder import _find_node_modules
    from config import DATA_DIR, GALLERY_DIR, TEMPLATE_CACHE_DIR; env = dict(os.environ); nm = _find_node_modules()
    if nm:
        env["NODE_PATH"] = str(nm)
    
    env["TUBECRAFT_TEMPLATE_CACHE"] = str(TEMPLATE_CACHE_DIR)
    env["TUBECRAFT_GALLERY_DIR"] = str(GALLERY_DIR)
    env["TUBECRAFT_FONTS_MANIFEST"] = str(Path(DATA_DIR) / "fonts.json")
    env["TUBECRAFT_FONTS_DIR"] = str(Path(DATA_DIR) / "fonts")
    return (env, nm)

def build_timing(script: dict, timing: dict=None) -> dict:
    return timing or _synth_timing(script)

def render_time_preview(project: dict, script: dict, preview_time: float, out_png: str, timing: dict=None, cancel_check=None) -> dict:
    from engines.video_encoder import _find_executable
    node = _find_executable("node")
    if not Path(node).is_file() and not shutil.which(node):
        return {"ok": False, "error": "Không tìm thấy Node.js — cài Node để preview."}
    env, nm = _node_env()
    if not nm:
        return {"ok": False, "error": "Chưa cài package 'canvas'. Bấm Render video một lần để tự cài, rồi preview lại."}
    timing = build_timing(script, timing)
    return _render(node, env, project, script, timing, float(preview_time), out_png, cancel_check=cancel_check)

def render_step_preview(project: dict, script: dict, step_index: int, out_png: str, timing: dict=None, cancel_check=None) -> dict:
    from engines.video_encoder import _find_executable
    node = _find_executable("node")
    if not Path(node).is_file() and not shutil.which(node):
        return {"ok": False, "error": "Không tìm thấy Node.js — cài Node để preview."}
    env, nm = _node_env()
    if not nm:
        return {"ok": False, "error": "Chưa cài package 'canvas'. Bấm Render video một lần để tự cài, rồi preview lại."}
    timing = build_timing(script, timing); steps = timing.get("steps", [])
    if not steps:
        return {"ok": False, "error": "Script chưa có step."}
    step_index = max(0, min(step_index, len(steps) - 1)); st = steps[step_index]; preview_time = max(st["start"], st["end"] - 0.15)
    return _render(node, env, project, script, timing, preview_time, out_png, cancel_check=cancel_check)

def _stop_preview_process(process) -> None:
    """Stop a local Node preview promptly when its dialog/request is obsolete."""
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _render(node, env, project, script, timing, preview_time, out_png, cancel_check=None) -> dict:
    # Preview is a renderer ingress too: never hand a caller's raw JS to Node.
    from core.schema import check_custom_js, validate_script
    script, validation_errors = validate_script(copy.deepcopy(script))
    security_errors = [
        error for error in validation_errors
        if any(
            marker in str(error).lower()
            for marker in ("custom_js", "template", "image src")
        )
    ] + check_custom_js(script)
    if security_errors:
        return {
            "ok": False,
            "error": "Cảnh không an toàn hoặc không được hỗ trợ: " + "; ".join(security_errors[:2]),
        }
    tmpdir = tempfile.mkdtemp(prefix="tubecraft_preview_")
    try:
        script_path = os.path.join(tmpdir, "script.json")
        timing_path = os.path.join(tmpdir, "timing.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False)
        with open(timing_path, "w", encoding="utf-8") as f:
            json.dump(timing, f, ensure_ascii=False)
        os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
        cmd = [node, str(RENDERER_JS), "--script", script_path, "--timing", timing_path, "--output", tmpdir, "--mode", "preview", "--previewTime", str(preview_time),
            
            "--outputFile", out_png, "--theme",
            
            project.get("theme", "dark"), "--aspect", project.get("aspect_ratio", "9:16"), "--style", project.get("art_style", "default")]
        if project.get("title_color"):
            cmd += ["--title-color", project["title_color"]]
        if project.get("text_color"):
            cmd += ["--text-color", project["text_color"]]
        if project.get("font_family"):
            cmd += ["--font", project["font_family"]]
        if project.get("bg"):
            from core.backgrounds import render_args
            cmd += render_args(project["bg"])
        from core.subtitles import cli_args as _sub_args
        try:
            cmd += _sub_args(project)
        except Exception as e:
            logger.warning(f"Phụ đề không áp được vào preview: {e}")
        if cancel_check and cancel_check():
            return {"ok": False, "cancelled": True, "error": "Đã hủy preview."}
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(RENDERER_JS.parent.parent),
            creationflags=_CREATE_NO_WINDOW,
        )
        deadline = time.monotonic() + 90.0
        stdout = b""
        stderr = b""
        while True:
            if cancel_check and cancel_check():
                _stop_preview_process(process)
                return {"ok": False, "cancelled": True, "error": "Đã hủy preview."}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_preview_process(process)
                return {"ok": False, "error": "Preview quá lâu (timeout 90s)."}
            try:
                stdout, stderr = process.communicate(timeout=min(0.25, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
        if process.returncode == 0 and os.path.exists(out_png):
            return {"ok": True, "path": out_png}
        raw_err = stderr.decode("utf-8", "replace")
        err = raw_err[-300:] or "Lỗi không rõ"
        for marker in ("image_asset_error:", "custom_scene_error:"):
            if marker in raw_err:
                err = raw_err[raw_err.index(marker):].splitlines()[0][:300]
                break
        logger.warning(f"Preview lỗi: {err}")
        return {"ok": False, "error": err}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
