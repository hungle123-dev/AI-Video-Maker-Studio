"""TubeCraft — Studio local tạo video dạy học + quản lý key AI cloud."""

import asyncio
import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


_SCENE_MODULES = (
    "core.scenes_td_1",
    "core.scenes_td_2",
    "core.scenes_td_3",
    "core.scenes_td_4",
    "core.scenes_td_5",
    "core.scenes_wp_1",
    "core.scenes_wp_2",
    "core.scenes_wp_3",
    "core.scenes_wp_4",
    "core.scenes_mn_1",
    "core.scenes_mn_2",
    "core.scenes_mn_3",
    "core.scenes_mn_4",
    "core.scenes_mn_5",
    "core.scenes_mn_6",
    "core.scenes_mn_7",
    "core.scenes_mn_8",
)
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run_scene_catalog_smoke() -> None:
    """Prove every dynamically-loaded shipped scene is available in this build."""
    expected = {}
    for module_name in _SCENE_MODULES:
        module = importlib.import_module(module_name)
        scenes = getattr(module, "SCENES", None)
        if not isinstance(scenes, dict) or not scenes:
            raise RuntimeError(f"Scene module không có catalog hợp lệ: {module_name}")
        expected.update(scenes)

    from core.custom_scenes import _td_scenes

    catalog = _td_scenes()
    missing = sorted(set(expected).difference(catalog))
    if missing:
        raise RuntimeError("Catalog scene thiếu: " + ", ".join(missing[:8]))
    print(f"[scene-catalog-smoke] OK: {len(_SCENE_MODULES)} modules, {len(expected)} scenes")


def _run_checked_smoke_process(command: list[str], label: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[-600:]
        raise RuntimeError(f"{label} thất bại (exit {result.returncode}): {detail}")
    return result


def _run_renderer_smoke() -> None:
    """Render a tiny narrated MP4 using only the bundled Node/FFmpeg runtime."""
    configured_root = os.environ.get("TUBECRAFT_RENDER_SMOKE_DIR", "").strip()
    owned_root = not configured_root
    root = Path(configured_root).resolve() if configured_root else Path(
        tempfile.mkdtemp(prefix="tubecraft-render-smoke-")
    )
    root.mkdir(parents=True, exist_ok=True)
    # This diagnostic must never initialize a release's real data directory.
    os.environ["TUBECRAFT_DATA_DIR"] = str(root / "data")

    try:
        from engines.video_encoder import _find_executable, render_and_encode

        script_path = root / "lesson_script.json"
        timing_path = root / "timing_map.json"
        audio_path = root / "audio" / "full_audio.mp3"
        output_dir = root / "output"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(
            json.dumps(
                {
                    "title": "Portable runtime smoke",
                    "description": "",
                    "subject": "general",
                    "total_steps": 1,
                    "steps": [{
                        "id": 1,
                        "clear": True,
                        "voice_text": "TubeCraft runtime smoke.",
                        "elements": [{
                            "type": "text",
                            "text": "TubeCraft OK",
                            "fontSize": 56,
                            "align": "center",
                            "bold": True,
                        }],
                    }],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        timing_path.write_text(
            json.dumps(
                {
                    "steps": [{"id": 1, "start": 0.0, "end": 0.25, "duration": 0.25, "words": []}],
                    "total_duration": 0.25,
                }
            ),
            encoding="utf-8",
        )
        ffmpeg = _find_executable("ffmpeg")
        ffprobe = _find_executable("ffprobe")
        _run_checked_smoke_process(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t",
                "0.25",
                "-c:a",
                "libmp3lame",
                str(audio_path),
            ],
            "FFmpeg tạo audio smoke",
            root,
        )
        final_video = Path(
            asyncio.run(
                render_and_encode(
                    str(script_path),
                    str(timing_path),
                    str(output_dir),
                    "runtime-smoke",
                    aspect_ratio="1:1",
                    gpu_encoder="cpu",
                    require_audio=True,
                    timeout_seconds=120,
                )
            )
        )
        if not final_video.is_file() or final_video.stat().st_size <= 1_000:
            raise RuntimeError("Renderer smoke không tạo được MP4 hợp lệ.")
        probe = _run_checked_smoke_process(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(final_video),
            ],
            "FFprobe xác minh audio smoke",
            root,
        )
        if probe.stdout.strip().lower() != "audio":
            raise RuntimeError("MP4 smoke không có audio stream.")
        print(f"[renderer-smoke] OK: {final_video}")
    finally:
        if owned_root:
            shutil.rmtree(root, ignore_errors=True)


if os.environ.get("TUBECRAFT_RUNTIME_SMOKE") == "1":
    try:
        from core.runtime_checks import check_packaged_runtime

        check_packaged_runtime()
    except Exception as exc:
        print(f"[runtime-smoke] FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("[runtime-smoke] OK")
    raise SystemExit(0)

if os.environ.get("TUBECRAFT_SCENE_CATALOG_SMOKE") == "1":
    try:
        _run_scene_catalog_smoke()
    except Exception as exc:
        print(f"[scene-catalog-smoke] FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(0)

if os.environ.get("TUBECRAFT_RENDER_SMOKE") == "1":
    try:
        _run_renderer_smoke()
    except Exception as exc:
        print(f"[renderer-smoke] FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(0)


def _run_startup_import_smoke() -> None:
    """Import the complete desktop startup surface without opening a window.

    Packaging failures are often hidden until a lazily-loaded view is opened.
    Keep these imports explicit so PyInstaller analyzes them and the portable
    release can prove they are all available before it is published.
    """

    import flet as smoke_flet
    import flet_desktop as smoke_flet_desktop

    from config import APP_VERSION as smoke_version
    from core.jobs import mark_stale_jobs_on_startup
    from ui.app_layout import AppLayout
    from ui.dashboard.view import DashboardView
    from ui.editor.view import EditorView
    from ui.keys.view import KeysView
    from ui.preview_dialog import show_preview
    from ui.preview_static import show_static_preview
    from ui.projects.view import ProjectsView
    from ui.render_dialog import render_lesson
    from ui.render_queue.view import RenderQueueView
    from ui.settings.view import SettingsView
    from ui.templates.view import TemplatesView
    from ui.theme import build_theme

    imported = (
        smoke_flet,
        smoke_flet_desktop,
        smoke_version,
        mark_stale_jobs_on_startup,
        AppLayout,
        DashboardView,
        EditorView,
        KeysView,
        ProjectsView,
        RenderQueueView,
        SettingsView,
        TemplatesView,
        build_theme,
        show_preview,
        show_static_preview,
        render_lesson,
    )
    if any(value is None for value in imported):
        raise RuntimeError("Một module khởi động desktop không tải được.")


if os.environ.get("TUBECRAFT_STARTUP_IMPORT_SMOKE") == "1":
    try:
        _run_startup_import_smoke()
    except Exception as exc:
        print(f"[startup-import-smoke] FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("[startup-import-smoke] OK")
    raise SystemExit(0)

import flet as ft

from config import APP_VERSION, LOGS_DIR
from ui.app_layout import AppLayout
from ui.theme import COLORS


for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO)
logging.getLogger("flet").setLevel(logging.WARNING)
logging.getLogger("flet_core").setLevel(logging.WARNING)

try:
    from logging.handlers import RotatingFileHandler

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _fh = RotatingFileHandler(
        str(LOGS_DIR / "app.log"),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(_fh)
    logging.getLogger("TubeCraft").info("=== App khởi động ===")
except Exception as _e:
    print("[Log] Không tạo được app.log:", _e)


def main(page: ft.Page):
    page.title = f"TubeCraft v{APP_VERSION} — by TubeCreate"

    try:
        from config import BASE_DIR

        page.window.icon = str(BASE_DIR / "assets" / "icon.ico")
    except Exception:
        pass

    page.padding = 0
    page.spacing = 0
    page.window.min_width = 1100
    page.window.min_height = 700
    page.window.maximized = True
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLORS["bg_dark"]

    from ui.theme import build_theme, polish_tree

    page.theme = build_theme()

    _open = page.open

    def _offstage_controls():
        off = getattr(page, "_Page__offstage", None)
        return off.controls if off is not None else None

    def _open_polished(control):
        try:
            polish_tree(control)
        except Exception:
            pass

        if isinstance(control, ft.SnackBar):
            try:
                from ui.theme import polish_snackbar

                polish_snackbar(control, page.width)
            except Exception:
                pass

        if isinstance(control, ft.AlertDialog):
            controls = _offstage_controls()
            if controls is not None:
                for current in [c for c in controls if isinstance(c, ft.AlertDialog)]:
                    current.open = False
                    try:
                        controls.remove(current)
                    except ValueError:
                        pass

        return _open(control)

    page.open = _open_polished

    def _close_clean(control):
        control.open = False
        try:
            control.update()
        except Exception:
            page.update()

    page.close = _close_clean

    from core.jobs import mark_stale_jobs_on_startup
    from core.project_store import project_store

    mark_stale_jobs_on_startup()
    migrated_projects = project_store.migrate_legacy_preferences()
    if migrated_projects:
        logging.getLogger("TubeCraft").info("Đã chuẩn hoá cấu hình %s project cũ.", migrated_projects)

    views_cache = {}
    active_view = None

    def show_view(view):
        """Swap views without leaving background UI workers behind."""
        nonlocal active_view
        if active_view is not view and active_view is not None:
            deactivate = getattr(active_view, "deactivate", None)
            if callable(deactivate):
                deactivate()
        layout.set_content(view)
        active_view = view
        activate = getattr(view, "activate", None)
        if callable(activate):
            activate()

    def get_view(key: str, **kwargs):
        if key == "dashboard" and key not in views_cache:
            from ui.dashboard.view import DashboardView

            views_cache[key] = DashboardView(page, on_nav)
        elif key == "projects" and key not in views_cache:
            from ui.projects.view import ProjectsView

            views_cache[key] = ProjectsView(page, open_editor)
        elif key == "templates" and key not in views_cache:
            from ui.templates.view import TemplatesView

            views_cache[key] = TemplatesView(page)
        elif key == "render_queue" and key not in views_cache:
            from ui.render_queue.view import RenderQueueView

            views_cache[key] = RenderQueueView(page)
        elif key == "keys" and key not in views_cache:
            from ui.keys.view import KeysView

            views_cache[key] = KeysView(page)
        elif key == "settings" and key not in views_cache:
            from ui.settings.view import SettingsView

            views_cache[key] = SettingsView(page)
        elif key == "editor":
            from ui.editor.view import EditorView

            pid, lid = kwargs["project_id"], kwargs["lesson_id"]
            return EditorView(page, pid, lid, on_back=lambda: _back_to_projects(pid, lid))
        if key == "projects" and kwargs.get("focus"):
            views_cache[key].focus(*kwargs["focus"])
        return views_cache.get(key)

    def on_nav(key: str):
        view = get_view(key)
        if view is not None:
            show_view(view)

    def _back_to_projects(pid, lid):
        view = get_view("projects", focus=(pid, lid))
        if view is not None:
            show_view(view)

    def open_editor(project_id: str, lesson_id: str):
        view = get_view("editor", project_id=project_id, lesson_id=lesson_id)
        show_view(view)

    layout = AppLayout(page, on_nav, get_view("dashboard"))
    active_view = views_cache["dashboard"]
    page.app_layout = layout
    page.add(layout)
    page.update()
    layout.start_monitor()


if __name__ == "__main__":
    from config import BASE_DIR

    ft.app(target=main, assets_dir=str(BASE_DIR / "assets"))
