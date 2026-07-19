"""Fallback preview ảnh tĩnh khi WebView không dùng được."""

import base64
import os
import re
import threading

import flet as ft

from ui.theme import COLORS


_SAFE_CACHE_PART = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def _cache_part(value: object, fallback: str) -> str:
    text = str(value or "")
    return text if _SAFE_CACHE_PART.fullmatch(text) else fallback


def _preview_dir(project_id: str, lesson_id: str) -> str:
    from config import DATA_DIR

    directory = os.path.join(
        str(DATA_DIR),
        "previews",
        _cache_part(project_id, "project"),
        _cache_part(lesson_id, "lesson"),
    )
    os.makedirs(directory, exist_ok=True)
    return directory


def _remove_preview_file(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError:
        return
    try:
        directory = os.path.dirname(path)
        if directory and not os.listdir(directory):
            os.rmdir(directory)
            parent = os.path.dirname(directory)
            if parent and not os.listdir(parent):
                os.rmdir(parent)
    except OSError:
        pass


def show_static_preview(page: ft.Page, project: dict, lesson: dict):
    script = lesson.get("script") or {}
    steps = script.get("steps", [])
    if not steps:
        return

    project_id = project.get("id", "project")
    lesson_id = lesson.get("id", "preview")
    timing = lesson.get("timing")
    state = {"idx": 0, "request": 0, "closed": False, "cancel": None}

    img = ft.Image(fit=ft.ImageFit.CONTAIN, expand=True, border_radius=8)
    busy = ft.ProgressRing(width=26, height=26)
    stage = ft.Stack(
        [
            ft.Container(
                bgcolor="#000000",
                border_radius=8,
                expand=True,
                alignment=ft.alignment.center,
                content=img,
            ),
            ft.Container(alignment=ft.alignment.center, content=busy),
        ],
        expand=True,
    )
    caption = ft.Text(
        "", size=12, color=COLORS["text_secondary"], text_align=ft.TextAlign.CENTER
    )
    title_txt = ft.Text("", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"])
    prev_btn = ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED)
    next_btn = ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED)

    def render_current():
        i = state["idx"]
        previous_cancel = state.get("cancel")
        if previous_cancel is not None:
            previous_cancel.set()
        cancel = threading.Event()
        state["cancel"] = cancel
        state["request"] += 1
        request = state["request"]
        title_txt.value = f"Step {i + 1}/{len(steps)}"
        caption.value = steps[i].get("voice_text", "")[:110] or "(không lời thoại)"
        busy.visible = True
        prev_btn.disabled = True
        next_btn.disabled = True
        page.update()

        def work():
            out = os.path.join(_preview_dir(project_id, lesson_id), f"s_{i}_{request}.png")
            # A cancelled request may have removed an otherwise-empty cache
            # directory while this worker was waiting to start.
            os.makedirs(os.path.dirname(out), exist_ok=True)
            from core.preview import render_step_preview

            res = render_step_preview(project, script, i, out, timing=timing, cancel_check=cancel.is_set)
            # A slower previous render must never overwrite the currently
            # selected scene, nor touch a dialog that has already closed.
            if state["closed"] or state["request"] != request or state["idx"] != i:
                _remove_preview_file(out)
                return
            busy.visible = False
            caption.color = COLORS["text_secondary"]
            prev_btn.disabled = i == 0
            next_btn.disabled = i == len(steps) - 1
            if res["ok"]:
                try:
                    with open(res["path"], "rb") as file:
                        img.src_base64 = base64.b64encode(file.read()).decode()
                    img.src = None
                except Exception as ex:
                    caption.value = f"Lỗi đọc ảnh: {ex}"
                finally:
                    _remove_preview_file(out)
            else:
                caption.value = f"⚠️ {res['error'][:120]}"
                caption.color = COLORS["yellow"]
            try:
                page.update()
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def go(delta):
        state["idx"] = max(0, min(len(steps) - 1, state["idx"] + delta))
        render_current()

    prev_btn.on_click = lambda _: go(-1)
    next_btn.on_click = lambda _: go(1)

    def invalidate_preview(_=None):
        state["closed"] = True
        state["request"] += 1
        cancel = state.get("cancel")
        if cancel is not None:
            cancel.set()

    def close_preview(_=None):
        invalidate_preview()
        page.close(dlg)

    dlg = ft.AlertDialog(
        title=ft.Text("Preview theo renderer cuối", weight=ft.FontWeight.BOLD),
        content=ft.Container(
            width=430,
            height=640,
            content=ft.Column(
                [
                    ft.Row(
                        [prev_btn, title_txt, next_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    stage,
                    caption,
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        actions=[ft.TextButton("Đóng", on_click=close_preview)],
        on_dismiss=invalidate_preview,
    )
    page.open(dlg)
    render_current()
    return dlg
