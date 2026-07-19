"""Final-renderer preview entry point.

The former browser preview used a separate JavaScript renderer whose layout
and scene API diverged from the MP4 renderer.  Keep one trustworthy preview:
the static step viewer renders each frame with canvas_renderer.js.
"""

import flet as ft


def show_preview(page: ft.Page, project: dict, lesson: dict):
    """Open a per-step preview rendered by the same Node engine as MP4 output."""
    script = lesson.get("script") or {}
    if not script.get("steps"):
        page.open(ft.SnackBar(content=ft.Text("Bài này chưa có step để preview.")))
        return None

    from ui.preview_static import show_static_preview

    return show_static_preview(page, project, lesson)
