"""Editor bài học: sửa step, sinh script AI, chạy TTS và render."""

import json
import threading
import time

import flet as ft

from ui.theme import COLORS


class EditorView(ft.Column):
    def __init__(self, page: ft.Page, project_id: str, lesson_id: str, on_back):
        super().__init__(spacing=12, expand=True)
        self.page = page
        self.project_id = project_id
        self.lesson_id = lesson_id
        self.on_back = on_back
        self._watch_job_id = None
        self._load()

    def deactivate(self):
        """Stop updating a detached editor; completed work remains in the project."""
        self._watch_job_id = None

    dispose = deactivate

    def _load(self):
        from core.project_store import project_store

        self.lesson = project_store.get_lesson(self.project_id, self.lesson_id)
        if not self.lesson:
            self.controls = [ft.Text("Không tìm thấy bài học.", color=COLORS["red"])]
            return
        self.script = self.lesson.get("script") or {}
        self._build()

    def _build(self):
        self.title_field = ft.TextField(
            label="Tiêu đề bài học",
            value=self.script.get("title", ""),
            text_size=14,
            dense=True,
        )
        self.progress_bar = ft.ProgressBar(
            value=0, visible=False, color=COLORS["accent"]
        )
        self.progress_text = ft.Text("", size=12, color=COLORS["text_secondary"])
        self.steps_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        self._rebuild_steps()

        tools = [
            ft.OutlinedButton(
                "Sinh script AI",
                icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                on_click=self._ai_dialog,
            ),
            ft.OutlinedButton(
                "Phụ đề", icon=ft.Icons.SUBTITLES_ROUNDED, on_click=self._subtitle_dialog
            ),
            ft.OutlinedButton(
                "Preview",
                icon=ft.Icons.VISIBILITY_ROUNDED,
                on_click=self._preview_dialog,
            ),
            ft.OutlinedButton(
                "Tạo giọng đọc",
                icon=ft.Icons.RECORD_VOICE_OVER_ROUNDED,
                on_click=self._run_tts,
            ),
            ft.FilledButton(
                "Render video",
                icon=ft.Icons.MOVIE_FILTER_ROUNDED,
                on_click=self._run_render,
            ),
        ]

        action_row = [
            ft.Text(
                f"{len(self.script.get('steps', []))} step",
                size=12,
                color=COLORS["text_secondary"],
            )
        ]
        action_row.append(
            ft.TextButton(
                "Thêm step", icon=ft.Icons.ADD_ROUNDED, on_click=self._add_step
            )
        )
        action_row += [
            ft.Container(expand=True),
            ft.TextButton("Lưu", icon=ft.Icons.SAVE_ROUNDED, on_click=self._save),
        ]

        lesson_title = self.lesson.get("title") or self.script.get("title", "")
        controls = [
            ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ARROW_BACK_ROUNDED,
                        tooltip="Quay lại Projects",
                        on_click=lambda _: self.on_back(),
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "Đang chỉnh sửa bài học",
                                        size=11,
                                        color=COLORS["text_secondary"],
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Text(
                                lesson_title or "Editor",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text"],
                                max_lines=1,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            self.title_field,
            ft.Row(action_row),
        ]
        controls += [
            self._media_bar(),
            ft.Row(tools, spacing=8, wrap=True),
            self.progress_bar,
            self.progress_text,
            self.steps_col,
        ]
        self.controls = controls

    def _media_bar(self):
        """Nghe thử audio và mở video đã render."""
        paths = None
        lesson = self.lesson
        try:
            from core.project_store import audio_is_current, project_store, video_is_current

            paths = project_store.lesson_paths(self.project_id, self.lesson_id)
            fresh_lesson = project_store.get_lesson(self.project_id, self.lesson_id)
            if fresh_lesson:
                lesson = fresh_lesson
        except Exception:
            audio_is_current = lambda *_args: False
            video_is_current = lambda *_args: False

        has_audio = bool(paths) and audio_is_current(
            lesson, lesson.get("timing"), paths["full_audio"]
        )
        video_path = lesson.get("rendered_video_path", "")
        has_video = bool(video_path) and video_is_current(lesson, video_path)
        items = []

        if has_audio:
            duration = (lesson.get("timing") or {}).get("total_duration", 0)
            minutes = f"{duration / 60:.1f} phút" if duration else ""
            items.append(
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.GRAPHIC_EQ_ROUNDED,
                            size=16,
                            color=COLORS["green"],
                        ),
                        ft.Text(
                            f"Đã có giọng đọc {minutes}",
                            size=12,
                            color=COLORS["green"],
                        ),
                        ft.TextButton(
                            "Nghe thử",
                            icon=ft.Icons.PLAY_ARROW_ROUNDED,
                            on_click=lambda _: self._open_file(paths["full_audio"]),
                        ),
                        ft.IconButton(
                            ft.Icons.FOLDER_OPEN_ROUNDED,
                            tooltip="Mở thư mục audio",
                            on_click=lambda _: self._reveal(paths["full_audio"]),
                        ),
                    ],
                    spacing=6,
                )
            )
        else:
            items.append(
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.VOLUME_OFF_ROUNDED,
                            size=16,
                            color=COLORS["text_secondary"],
                        ),
                        ft.Text(
                            "Chưa có giọng đọc — bấm '🔊 Tạo giọng đọc'.",
                            size=12,
                            color=COLORS["text_secondary"],
                        ),
                    ],
                    spacing=6,
                )
            )

        if has_video:
            items.append(
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.MOVIE_ROUNDED,
                            size=16,
                            color=COLORS["accent_2"],
                        ),
                        ft.Text(
                            "Đã render video", size=12, color=COLORS["accent_2"]
                        ),
                        ft.TextButton(
                            "Xem video",
                            icon=ft.Icons.PLAY_CIRCLE_ROUNDED,
                            on_click=lambda _: self._open_file(video_path),
                        ),
                        ft.IconButton(
                            ft.Icons.FOLDER_OPEN_ROUNDED,
                            tooltip="Mở thư mục",
                            on_click=lambda _: self._reveal(video_path),
                        ),
                    ],
                    spacing=6,
                )
            )

        return ft.Container(
            bgcolor=COLORS["bg_card"],
            border_radius=10,
            padding=12,
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Row(items, spacing=24, wrap=True),
        )

    def _rebuild_steps(self):
        self.steps_col.controls.clear()
        for index, step in enumerate(self.script.get("steps", [])):
            self.steps_col.controls.append(self._step_card(index, step))

    def _step_card(self, idx, step):
        card = ft.Container(
            bgcolor=COLORS["bg_card"],
            border_radius=10,
            padding=14,
            border=ft.border.all(1, COLORS["border"]),
        )

        def on_focus(_):
            card.border = ft.border.all(2, COLORS["accent"])
            card.bgcolor = COLORS["accent"] + "0e"
            card.shadow = ft.BoxShadow(
                blur_radius=14, color="#1f408722", offset=ft.Offset(0, 4)
            )
            try:
                card.update()
            except Exception:
                pass

        def on_blur(_):
            card.border = ft.border.all(1, COLORS["border"])
            card.bgcolor = COLORS["bg_card"]
            card.shadow = None
            try:
                card.update()
            except Exception:
                pass

        voice = ft.TextField(
            value=step.get("voice_text", ""),
            multiline=True,
            min_lines=2,
            max_lines=6,
            text_size=13,
            dense=True,
            label=f"Lời thoại · Step {idx + 1}",
            on_focus=on_focus,
            on_blur=on_blur,
            on_change=lambda e, target=step: target.__setitem__(
                "voice_text", e.control.value
            ),
        )
        number = ft.Container(
            width=30,
            height=30,
            border_radius=15,
            bgcolor=COLORS["accent"] + "33",
            alignment=ft.alignment.center,
            content=ft.Text(
                str(idx + 1),
                size=13,
                color=COLORS["accent"],
                weight=ft.FontWeight.BOLD,
            ),
        )
        summary = ", ".join(
            element.get("type", "?") for element in step.get("elements", [])
        ) or "trống"
        head = [
            number,
            ft.Text(
                f"Elements: {summary}",
                size=11,
                color=COLORS["text_secondary"],
                expand=True,
                max_lines=1,
            ),
            ft.IconButton(
                ft.Icons.DATA_OBJECT_ROUNDED,
                icon_size=17,
                tooltip="Sửa elements (JSON)",
                on_click=lambda _, target=step: self._edit_elements(target),
            ),
            ft.IconButton(
                ft.Icons.DELETE_OUTLINE,
                icon_size=17,
                icon_color=COLORS["red"],
                tooltip="Xoá step",
                on_click=lambda _, index=idx: self._del_step(index),
            ),
        ]
        card.content = ft.Column(
            [
                ft.Row(
                    head,
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                voice,
            ],
            spacing=8,
        )
        return card

    def _add_step(self, e):
        steps = self.script.setdefault("steps", [])
        steps.append(
            {"id": len(steps) + 1, "voice_text": "", "clear": True, "elements": []}
        )
        self._renumber_steps()
        self._rebuild_steps()
        self.update()

    def _del_step(self, idx):
        steps = self.script.get("steps", [])
        if 0 <= idx < len(steps):
            steps.pop(idx)
        self._renumber_steps()
        self._rebuild_steps()
        self.update()

    def _renumber_steps(self):
        for index, step in enumerate(self.script.get("steps", []), start=1):
            if isinstance(step, dict):
                step["id"] = index

    def _edit_elements(self, step):
        editor = ft.TextField(
            value=json.dumps(step.get("elements", []), ensure_ascii=False, indent=2),
            multiline=True,
            min_lines=14,
            max_lines=22,
            text_size=12,
            text_style=ft.TextStyle(font_family="Consolas"),
        )
        error = ft.Text("", size=12, color=COLORS["red"])

        def save(_):
            try:
                data = json.loads(editor.value)
                if not isinstance(data, list):
                    raise ValueError("Elements phải là mảng JSON.")
            except Exception as ex:
                error.value = f"JSON lỗi: {ex}"
                self.page.update()
                return
            step["elements"] = data
            self.page.close(dlg)
            self._rebuild_steps()
            self.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Sửa elements (JSON)"),
            content=ft.Column(
                [editor, error], tight=True, width=700, scroll=ft.ScrollMode.AUTO
            ),
            actions=[
                ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dlg)),
                ft.FilledButton("Lưu", on_click=save),
            ],
        )
        self.page.open(dlg)

    def _snack(self, msg):
        self.page.open(ft.SnackBar(content=ft.Text(msg)))

    def _save(self, e=None) -> bool:
        from core.project_store import project_store

        self._renumber_steps()
        self.script["title"] = (self.title_field.value or "").strip()
        ok, errors = project_store.save_script(
            self.project_id, self.lesson_id, self.script
        )
        if errors:
            self._snack("Đã lưu, có cảnh báo: " + "; ".join(errors[:3]))
        elif ok:
            self._snack("Đã lưu script.")
        return ok

    def _ai_dialog(self, e):
        from core.project_store import project_store
        from core.script_generator import estimate_minutes

        project = project_store.get_project(self.project_id) or {}
        default_steps = str(project.get("min_steps", 12))
        content = ft.TextField(
            label="Nội dung / chủ đề bài học",
            multiline=True,
            min_lines=5,
            max_lines=10,
            hint_text="VD: Giải thích quy luật lãi kép và cách áp dụng...",
        )
        estimate = ft.Text("", size=11, color=COLORS["accent_2"])

        def _upd_est(_=None):
            try:
                estimate.value = f"⏱ ~{estimate_minutes(int(steps_n.value))} phút"
            except Exception:
                estimate.value = ""
            self.page.update()

        steps_n = ft.TextField(
            label="Số step", value=default_steps, width=100, on_change=_upd_est
        )
        provider = project.get("ai_provider", "gemini")
        model = project.get("ai_model") or "(model mặc định)"
        info = ft.Text(
            f"AI: {provider} {model} — key lấy từ tab Key AI Cloud.",
            size=11,
            color=COLORS["text_secondary"],
        )
        busy = ft.ProgressRing(width=18, height=18, visible=False)

        def run(_):
            if not content.value.strip():
                return
            busy.visible = True
            self.page.update()

            def work():
                try:
                    from core.project_store import project_store
                    from core.script_generator import generate_lesson_script

                    current = project_store.get_project(self.project_id) or {}
                    script, errors = generate_lesson_script(
                        content.value.strip(),
                        step_count=int(steps_n.value or 10),
                        lang=current.get("lang", "vi"),
                        provider=current.get("ai_provider", ""),
                        model=current.get("ai_model", ""),
                        template=current.get("template") or "",
                    )
                    self.script = script
                    self.title_field.value = script.get("title", "")
                    self._save()
                    self._rebuild_steps()
                    self.page.close(dlg)
                    self.update()
                    message = "Đã sinh script."
                    if errors:
                        message += " Cảnh báo: " + "; ".join(errors[:2])
                    self._snack(message)
                except Exception as ex:
                    busy.visible = False
                    info.value = f"Lỗi: {ex}"
                    info.color = COLORS["red"]
                    self.page.update()

            threading.Thread(target=work, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Sinh kịch bản bằng AI"),
            content=ft.Column(
                [
                    content,
                    ft.Row(
                        [steps_n, estimate],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    info,
                ],
                tight=True,
                width=520,
            ),
            actions=[
                busy,
                ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dlg)),
                ft.FilledButton("Sinh script", on_click=run),
            ],
        )
        self.page.open(dlg)
        _upd_est()

    def _preview_dialog(self, e):
        if not self._save():
            return
        from core.project_store import project_store
        from ui.preview_dialog import show_preview

        project = project_store.get_project(self.project_id) or {}
        lesson = {
            "id": self.lesson_id,
            "title": self.script.get("title", ""),
            "script": self.script,
            "timing": self.lesson.get("timing"),
        }
        show_preview(self.page, project, lesson)

    def _subtitle_dialog(self, e):
        if not self._save():
            return
        from core.project_store import project_store
        from ui.subtitle_picker import show_subtitle_dialog

        project = project_store.get_project(self.project_id) or {}
        if not project:
            self._snack("Không tải được project.")
            return
        show_subtitle_dialog(
            self.page,
            project,
            script=self.script,
            timing=self.lesson.get("timing"),
            step_index=0,
            on_saved=lambda _: self._snack(
                "✓ Đã lưu phụ đề. Preview/Render mới sẽ áp dụng."
            ),
        )

    def _run_tts(self, e):
        if not self._save():
            return
        from core.project_store import script_has_content
        if not script_has_content(self.script):
            self._snack("Bài học chưa có nội dung để tạo giọng đọc.")
            return
        from core.render_service import queue_tts

        job = queue_tts(self.project_id, self.lesson_id)
        self._watch(job["id"], "TTS")

    def _run_render(self, e):
        if not self._save():
            return
        from core.project_store import script_has_content
        if not script_has_content(self.script):
            self._snack("Bài học chưa có nội dung để render.")
            return
        from ui.render_dialog import render_lesson

        render_lesson(
            self.page,
            self.project_id,
            self.lesson_id,
            on_queued=lambda job: self._watch(job["id"], "Render"),
        )

    def _watch(self, job_id, label):
        self._watch_job_id = job_id
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.progress_text.value = f"{label}: đang xếp hàng..."
        self.update()

        def poll():
            from core import jobs

            while self._watch_job_id == job_id:
                job = jobs.get_job(job_id)
                if not job:
                    return
                try:
                    self.progress_bar.value = (job.get("progress") or 0) / 100
                    self.progress_text.value = f"{label}: {job.get('message', '')}"
                    self.update()
                except Exception:
                    pass

                if job["status"] in ("done", "error", "cancelled"):
                    if job["status"] == "done":
                        result = job.get("result") or {}
                        try:
                            from core.project_store import project_store

                            current = project_store.get_lesson(
                                self.project_id, self.lesson_id
                            )
                            if current:
                                self.lesson = current
                                self.script = current.get("script") or self.script
                                self._build()
                                self.update()
                        except Exception:
                            pass
                        if result.get("video"):
                            try:
                                from ui.components import show_result

                                project = project_store.get_project(self.project_id)
                                show_result(
                                    self.page, project, self.lesson, result["video"]
                                )
                            except Exception:
                                pass
                        else:
                            self._snack(f"{label}: ✅ hoàn tất")
                    else:
                        self.progress_text.value = (
                            f"{label}: ❌ {job.get('message', '')}"
                        )
                    self.progress_bar.visible = job["status"] == "running"
                    self._watch_job_id = None
                    try:
                        self.update()
                    except Exception:
                        pass
                    return
                time.sleep(1.0)

        threading.Thread(target=poll, daemon=True).start()

    def _open_file(self, path):
        """Mở file bằng trình phát mặc định của hệ điều hành."""
        import os

        if not path or not os.path.exists(path):
            self._snack("Chưa thấy file.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess

                subprocess.Popen(["xdg-open", path])
        except Exception as ex:
            self._snack(f"Không mở được: {ex}")

    def _reveal(self, path):
        """Mở File Explorer và chọn file."""
        import os
        import subprocess

        if path and os.path.exists(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            return
        self._snack("Chưa thấy file.")
