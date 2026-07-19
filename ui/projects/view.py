"""Project and lesson management UI.

This view is the main workflow hub: create/import projects, run Autopilot,
manage visual/voice settings, generate scripts, preview, synthesize audio,
render videos and inspect completed jobs.
"""

from __future__ import annotations

import os
import threading
import time
from collections import Counter

import flet as ft

from ui.theme import COLORS


_TTS_SAMPLE = {
    "vi": "Xin chào, đây là giọng đọc thử của TubeCraft.",
    "en": "Hello, this is a voice preview from TubeCraft.",
    "es": "Hola, esta es una voz de prueba de TubeCraft.",
    "fr": "Bonjour, ceci est un aperçu vocal de TubeCraft.",
    "de": "Hallo, dies ist eine Hörprobe von TubeCraft.",
    "it": "Ciao, questa è un'anteprima vocale di TubeCraft.",
    "pt": "Olá, esta é uma prévia de voz do TubeCraft.",
    "nl": "Hallo, dit is een stemvoorbeeld van TubeCraft.",
    "ja": "こんにちは、これはTubeCraftの音声プレビューです。",
    "ko": "안녕하세요, TubeCraft 음성 미리듣기입니다.",
    "zh": "你好，这是 TubeCraft 的音频试听。",
    "hi": "नमस्ते, यह TubeCraft की आवाज़ का नमूना है।",
}
_AUTO_SUBTITLE_PRESET = "__auto_subtitle__"
_AUTO_BACKGROUND = "__auto_background__"
_MANUAL_TEMPLATE = "__manual_template__"
_INHERIT_TITLE_COLOR = "__inherit_title_color__"
_INHERIT_FONT = "__inherit_font__"


def _select_value(value, sentinel):
    return sentinel if not value else value


def _stored_value(value, sentinel):
    return "" if value == sentinel else value


class ProjectsView(ft.Column):
    _PREFS_KEY = "last_config"
    _DIALOG_CHROME_H = 190
    _DIALOG_SIDE_PAD = 96

    def __init__(self, page: ft.Page, open_editor, focus=None):
        super().__init__(
            spacing=16,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.page = page
        self.open_editor = open_editor
        self.selected_project = None
        self._focus = focus
        self._focus_lid = focus[1] if focus else None
        self._shown_results = set()
        self._ai_gen_active = set()
        self._polling = False
        self._active = True
        self._stopped = threading.Event()
        try:
            from core import jobs
            for job in jobs.list_jobs(limit=500):
                result = job.get("result") if isinstance(job.get("result"), dict) else {}
                if job.get("status") == "done" and result.get("video"):
                    self._shown_results.add(job["id"])
        except Exception:
            pass
        self._build()

    def _safe_update(self, control=None):
        try:
            if control is not None:
                control.update()
            elif self.page is not None:
                # Autopilot/create dialogs live in page.overlay, outside this
                # ProjectsView subtree. Updating self cannot repaint them.
                self.page.update()
            else:
                self.update()
        except Exception:
            try:
                if self.page is not None:
                    self.page.update()
            except Exception:
                pass

    def _snack(self, message, color=None):
        if not self.page:
            return
        text = ft.Text(str(message), color=color)
        self.page.open(ft.SnackBar(content=text))

    @property
    def _compact(self) -> bool:
        return (getattr(self.page, "height", None) or 720) < 820

    def _cv(self, small, normal):
        return small if self._compact else normal

    def _build(self):
        self.project_list = ft.ListView(spacing=8, expand=True)
        self.lesson_panel = ft.Column([
            ft.Container(alignment=ft.alignment.center, expand=True,
                         content=ft.Text("Chọn một project để xem bài học",
                                         color=COLORS["text_secondary"]))
        ], expand=True)
        self.controls = [
            ft.Row([
                ft.Text("Projects", size=24, weight=ft.FontWeight.BOLD,
                        color=COLORS["text"]),
                ft.Container(expand=True),
                ft.OutlinedButton("Import project cũ", icon=ft.Icons.DRIVE_FOLDER_UPLOAD,
                                  on_click=self._import_dialog),
                ft.OutlinedButton("Project mới", icon=ft.Icons.ADD_ROUNDED,
                                  on_click=self._create_dialog),
                ft.FilledButton("Tạo tự động (AI)", icon=ft.Icons.AUTO_AWESOME,
                                on_click=self._autopilot_dialog),
            ]),
            ft.Row([
                ft.Container(width=360, content=self.project_list),
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                ft.Container(expand=True, content=self.lesson_panel),
            ], expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        ]
        self._reload_projects()
        if self._focus:
            from core.project_store import project_store
            project = project_store.get_project(self._focus[0])
            if project:
                self.selected_project = project
                self._reload_projects()
                self._reload_lessons()

    def focus(self, project_id, lesson_id=None):
        """Return to a cached Projects view and restore the edited lesson."""
        from core.project_store import project_store

        project = project_store.get_project(project_id)
        if not project:
            return
        self._focus = (project_id, lesson_id) if lesson_id else None
        self._focus_lid = lesson_id
        self.selected_project = project
        self._reload_projects()
        self._reload_lessons()

    def activate(self):
        """Resume project-only refresh work after this cached view is shown."""
        if self._stopped.is_set():
            return
        self._active = True
        if self.selected_project:
            self._ensure_poll()

    def deactivate(self):
        """Never let a hidden Projects view update controls or open a result modal."""
        self._active = False

    def dispose(self):
        self._active = False
        self._stopped.set()

    def _reload_projects(self):
        from core.project_store import project_store
        selected_id = self.selected_project.get("id") if self.selected_project else None
        projects = project_store.list_projects()
        self.project_list.controls.clear()
        if not projects:
            self.project_list.controls.append(
                ft.Container(padding=20,
                             content=ft.Text("Chưa có project. Bấm “Project mới” hoặc “Tạo tự động”.",
                                             color=COLORS["text_secondary"], size=12))
            )
        for project in projects:
            self.project_list.controls.append(self._project_card(project))
            if project.get("id") == selected_id:
                self.selected_project = project
        self._safe_update(self.project_list)

    def _project_card(self, project):
        from ui.theme import FIELD_BORDER, RADIUS_SECTION, soft_shadow
        selected = bool(self.selected_project and
                        project["id"] == self.selected_project.get("id"))
        count = project.get("lesson_count_actual", 0)
        return ft.Container(
            bgcolor=COLORS["accent"] + "12" if selected else COLORS["bg_card"],
            border=ft.border.all(1, COLORS["accent"] if selected else FIELD_BORDER),
            border_radius=RADIUS_SECTION, padding=14,
            on_click=lambda _e, value=project: self._select_project(value),
            shadow=soft_shadow(18 if selected else 10, 5 if selected else 2),
            content=ft.Row([
                ft.Container(width=42, height=42, border_radius=12,
                             bgcolor=COLORS["accent"] + "1f", alignment=ft.alignment.center,
                             content=ft.Icon(ft.Icons.VIDEO_LIBRARY_ROUNDED,
                                             color=COLORS["accent"], size=22)),
                ft.Column([
                    ft.Text(project.get("title", "?"), size=14,
                            weight=ft.FontWeight.BOLD, color=COLORS["text"], max_lines=2),
                    ft.Row([
                        ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, size=12,
                                color=COLORS["text_secondary"]),
                        ft.Text(f"{count} bài", size=11, color=COLORS["text_secondary"]),
                        ft.Text("·", size=11, color=COLORS["text_secondary"]),
                        ft.Text(project.get("aspect_ratio", ""), size=11,
                                color=COLORS["text_secondary"]),
                    ], spacing=5),
                ], spacing=4, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _select_project(self, project):
        self.selected_project = project
        self._reload_projects()
        self._reload_lessons()

    def _active_jobs_map(self):
        from core import jobs
        output = {}
        project_id = self.selected_project.get("id") if self.selected_project else None
        if not project_id:
            return output
        for job in jobs.list_jobs(limit=150):
            meta = job.get("meta") or {}
            if meta.get("project_id") != project_id:
                continue
            if job.get("status") not in ("queued", "running"):
                continue
            lesson_id = meta.get("lesson_id")
            if lesson_id:
                output[lesson_id] = job
        return output

    def _error_jobs_map(self):
        from core import jobs
        output = {}
        project_id = self.selected_project.get("id") if self.selected_project else None
        if not project_id:
            return output
        ordered = sorted(jobs.list_jobs(limit=250), key=lambda item: item.get("updated_at", 0))
        for job in ordered:
            meta = job.get("meta") or {}
            if meta.get("project_id") != project_id:
                continue
            lesson_id = meta.get("lesson_id")
            if not lesson_id:
                continue
            if job.get("status") == "error":
                output[lesson_id] = str(job.get("message") or "Lỗi")
            elif job.get("status") in ("done", "running", "queued"):
                output.pop(lesson_id, None)
        return output

    def _reload_lessons(self):
        from core.project_store import project_store
        project = self.selected_project
        if not project:
            return
        fresh = project_store.get_project(project["id"])
        if fresh:
            self.selected_project = project = fresh
        lessons = project_store.list_lessons(project["id"])

        from core.templates import normalize_id as normalize_template, style_options
        style_options = style_options()
        from ui.theme import round_btn_style, round_field
        style_dropdown = round_field(ft.Dropdown(
            value=project.get("art_style", "default"), width=190, dense=True,
            label="Phong cách",
            options=[ft.dropdown.Option(key, label) for key, label in style_options],
            on_change=lambda e: self._change_style(project["id"], e.control.value),
        ))
        from core.backgrounds import normalize_id as normalize_background, options as background_options
        background_dropdown = round_field(ft.Dropdown(
            value=_select_value(normalize_background(project.get("bg")), _AUTO_BACKGROUND), width=210, dense=True, label="Nền",
            options=[ft.dropdown.Option(_AUTO_BACKGROUND if not key else key, label)
                     for key, label in background_options()],
            on_change=lambda e: self._change_bg(project["id"], e.control.value),
        ))
        from core.templates import list_templates
        template_options = [ft.dropdown.Option(_MANUAL_TEMPLATE, "— Không —")]
        template_options.extend(ft.dropdown.Option(
            template["id"], f"{template.get('emoji', '')} {template['name']}"
        ) for template in list_templates())
        template_dropdown = round_field(ft.Dropdown(
            value=_select_value(normalize_template(project.get("template")), _MANUAL_TEMPLATE), width=220, dense=True, label="Template",
            options=template_options,
            on_change=lambda e: self._change_template(project["id"], e.control.value),
        ))

        project_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_HORIZ_ROUNDED, tooltip="Cấu hình project",
            items=[
                ft.PopupMenuItem(text="🎨  Màu tiêu đề & font",
                                 on_click=lambda _e: self._color_font_dialog(project)),
                ft.PopupMenuItem(text="🗑  Xoá project",
                                 on_click=lambda _e: self._delete_project(project["id"])),
            ],
        )
        rows = [
            ft.Text(project["title"], size=20, weight=ft.FontWeight.BOLD,
                    color=COLORS["text"], max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS, tooltip=project["title"]),
            ft.Row([
                template_dropdown, style_dropdown, background_dropdown,
                ft.OutlinedButton("Phụ đề", icon=ft.Icons.SUBTITLES_ROUNDED,
                                  tooltip="Chọn kiểu, cỡ và vị trí phụ đề",
                                  style=round_btn_style(radius=14, pad_h=14, pad_v=16),
                                  on_click=lambda _e: self._subtitle_dialog(project)),
                ft.OutlinedButton("Xuất Excel", icon=ft.Icons.TABLE_VIEW_ROUNDED,
                                  style=round_btn_style(radius=14, pad_h=14, pad_v=16),
                                  on_click=lambda _e: self._export_excel(project)),
                project_menu,
                ft.FilledButton("Bài học", icon=ft.Icons.ADD_ROUNDED,
                                style=round_btn_style(radius=14, pad_h=16, pad_v=16),
                                on_click=self._create_lesson_dialog),
            ], spacing=10, wrap=True, run_spacing=8,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ]
        if lessons:
            total = len(lessons)
            script_count = sum(1 for lesson in lessons if lesson.get("has_script"))
            audio_count = sum(1 for lesson in lessons if lesson.get("has_audio"))
            video_count = sum(1 for lesson in lessons if lesson.get("has_video"))

            def stat(label, count, color):
                return ft.Row([ft.Text(f"{count}/{total}", size=15,
                                       weight=ft.FontWeight.BOLD,
                                       color=color if count else COLORS["text_secondary"]),
                               ft.Text(label, size=12, color=COLORS["text_secondary"])],
                              spacing=5)

            from ui.theme import FIELD_BORDER, RADIUS_SECTION, soft_shadow
            rows.append(ft.Container(
                bgcolor=COLORS["bg_card"], border_radius=RADIUS_SECTION, padding=14,
                border=ft.border.all(1, FIELD_BORDER), shadow=soft_shadow(16, 4),
                content=ft.Row([
                    stat("có kịch bản", script_count, COLORS["green"]),
                    ft.Container(width=1, height=20, bgcolor=FIELD_BORDER),
                    stat("có giọng đọc", audio_count, COLORS["green"]),
                    ft.Container(width=1, height=20, bgcolor=FIELD_BORDER),
                    stat("đã render", video_count, COLORS["accent_2"]),
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
            rows.append(ft.Row([
                ft.OutlinedButton("Tạo giọng tất cả",
                                  icon=ft.Icons.RECORD_VOICE_OVER_OUTLINED,
                                  on_click=lambda _e: self._batch("tts")),
                ft.FilledButton("Render tất cả", icon=ft.Icons.MOVIE_FILTER_ROUNDED,
                                on_click=lambda _e: self._batch("pipeline")),
            ], spacing=10, wrap=True))
        else:
            rows.append(ft.Text("Chưa có bài học nào.", color=COLORS["text_secondary"]))

        active = self._active_jobs_map()
        errors = self._error_jobs_map()
        for lesson in lessons:
            rows.append(self._lesson_row(lesson, active.get(lesson["id"]),
                                         errors.get(lesson["id"])))
        self._lesson_scroll = ft.Column(rows, spacing=8, scroll=ft.ScrollMode.AUTO,
                                        expand=True)
        self.lesson_panel.controls = [
            ft.Container(padding=ft.padding.only(left=16), expand=True,
                         content=self._lesson_scroll)
        ]
        self._safe_update(self.lesson_panel)
        if self._focus_lid:
            focus_id = self._focus_lid
            self._focus_lid = None
            try:
                self._lesson_scroll.scroll_to(key=focus_id, duration=350)
            except Exception:
                pass
        if active:
            self._ensure_poll()

    def _chip(self, label, done):
        color = COLORS["green"] if done else COLORS["text_secondary"]
        return ft.Container(
            border_radius=6, padding=ft.padding.symmetric(vertical=3, horizontal=8),
            bgcolor=color + "22" if done else COLORS["bg_dark"],
            border=ft.border.all(1, color if done else COLORS["border"]),
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if done
                        else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                        size=13, color=color),
                ft.Text(label, size=11, color=color),
            ], spacing=4, tight=True),
        )

    def _lesson_row(self, lesson, active_job=None, error_msg=None):
        index = lesson.get("index", 0) + 1
        lesson_id = lesson["id"]
        has_script = bool(lesson.get("has_script"))
        has_audio = bool(lesson.get("has_audio"))
        has_video = bool(lesson.get("has_video"))
        show_error = bool(error_msg) and not active_job and not has_video
        generating = lesson_id in self._ai_gen_active
        from ui.theme import FIELD_BORDER, RADIUS_SECTION, round_btn_style, soft_shadow
        button_style = round_btn_style(radius=14, pad_h=14, pad_v=14)
        if generating:
            primary = ft.Container(width=150, alignment=ft.alignment.center,
                                   content=ft.Row([
                                       ft.ProgressRing(width=16, height=16, stroke_width=2,
                                                       color=COLORS["accent"]),
                                       ft.Text("Đang viết...", size=13,
                                               weight=ft.FontWeight.W_600,
                                               color=COLORS["accent"]),
                                   ], spacing=8, tight=True,
                                      alignment=ft.MainAxisAlignment.CENTER))
        elif active_job:
            primary = ft.FilledButton("Đang xử lý...", disabled=True, width=140,
                                      style=button_style)
        elif show_error:
            primary = ft.FilledButton("Thử lại", icon=ft.Icons.REFRESH_ROUNDED,
                                      width=140, on_click=lambda _e: self._render_lesson(lesson_id))
        elif has_video:
            primary = ft.FilledButton("Xem video", icon=ft.Icons.PLAY_CIRCLE_ROUNDED,
                                      width=140, style=button_style,
                                      on_click=lambda _e: self._play_lesson(lesson_id))
        elif has_script:
            primary = ft.FilledButton("Tạo video", icon=ft.Icons.MOVIE_FILTER_ROUNDED,
                                      width=140, style=button_style,
                                      on_click=lambda _e: self._render_lesson(lesson_id))
        else:
            primary = ft.FilledButton("Viết kịch bản AI", icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                                      width=155, style=button_style,
                                      on_click=lambda _e: self._ai_gen_lesson(lesson_id))
        menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT_ROUNDED, tooltip="Thao tác khác",
            items=[
                ft.PopupMenuItem(text="✨  Viết lại kịch bản (AI)",
                                 on_click=lambda _e: self._ai_gen_lesson(lesson_id)),
                ft.PopupMenuItem(text="👁  Xem trước (preview)",
                                 on_click=lambda _e: self._preview_lesson(lesson_id)),
                ft.PopupMenuItem(text="✏️  Chỉnh sửa nội dung",
                                 on_click=lambda _e: self.open_editor(
                                     self.selected_project["id"], lesson_id)),
                ft.PopupMenuItem(text="🔊  Tạo/làm lại giọng đọc",
                                 on_click=lambda _e: self._tts_lesson(lesson_id)),
                ft.PopupMenuItem(text="🎬  Render lại video",
                                 on_click=lambda _e: self._render_lesson(lesson_id)),
                ft.PopupMenuItem(text="🗑  Xoá bài học",
                                 on_click=lambda _e: self._delete_lesson_confirm(lesson)),
            ],
        )
        top = ft.Row([
            ft.Container(width=30, height=30, border_radius=15,
                         bgcolor=COLORS["accent"] + "1f", alignment=ft.alignment.center,
                         content=ft.Text(str(index), size=13, color=COLORS["accent"],
                                         weight=ft.FontWeight.BOLD)),
            ft.Column([
                ft.Text(lesson.get("title", "?"), size=14,
                        weight=ft.FontWeight.W_600, color=COLORS["text"], max_lines=1),
                ft.Row([self._chip("Kịch bản", has_script),
                        self._chip("Giọng đọc", has_audio),
                        self._chip("Video", has_video)], spacing=6),
            ], spacing=6, expand=True),
            primary, menu,
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        column = [top]
        if active_job:
            from ui.components import pro_progress
            column.append(pro_progress((active_job.get("progress") or 0) / 100,
                                       str(active_job.get("message") or "")[:90]))
        elif show_error:
            column.append(ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, size=15, color=COLORS["red"]),
                ft.Text(f"Lỗi: {str(error_msg)[:100]} — bấm 'Thử lại'.", size=11,
                        color=COLORS["red"], expand=True, max_lines=2),
            ], spacing=6))
        focused = self._focus_lid == lesson_id
        border_color = COLORS["red"] if show_error else FIELD_BORDER
        return ft.Container(
            key=lesson_id,
            bgcolor=COLORS["accent"] + "0e" if focused else COLORS["bg_card"],
            border_radius=RADIUS_SECTION, padding=14,
            border=ft.border.all(1, border_color),
            shadow=soft_shadow(18 if focused else 12, 4 if focused else 3),
            content=ft.Column(column, spacing=10),
        )

    def _play_file(self, path):
        if not path or not os.path.isfile(path):
            self._snack("Không tìm thấy file audio.")
            return
        try:
            if os.name == "nt" and str(path).lower().endswith(".wav"):
                import winsound

                winsound.PlaySound(
                    os.path.abspath(path), winsound.SND_FILENAME | winsound.SND_ASYNC
                )
                return
            import shutil
            import subprocess
            from engines.video_encoder import _find_executable
            ffplay = _find_executable("ffplay")
            if ffplay and (os.path.isfile(ffplay) or shutil.which(ffplay)):
                subprocess.Popen([ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                                 creationflags=0x08000000 if os.name == "nt" else 0,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            else:
                os.startfile(path)
        except Exception as exc:
            self._snack(f"Không phát được audio: {exc}")

    def _load_prefs(self):
        try:
            from config import load_settings
            settings = load_settings()
            value = settings.get(self._PREFS_KEY)
            # Global settings are the defaults for a new project.  The last
            # project form only overrides fields the user actually chose.
            if isinstance(value, dict):
                settings.update(value)
            return settings
        except Exception:
            return {}

    def _save_prefs(self, values):
        try:
            from config import load_settings, save_settings
            settings = load_settings()
            settings[self._PREFS_KEY] = dict(values)
            save_settings(settings)
        except Exception:
            pass

    @staticmethod
    def _mark_required(field, message):
        field.error_text = message
        field.border_color = COLORS["red"]
        field.focused_border_color = COLORS["red"]

    @staticmethod
    def _clear_required(field):
        from ui.theme import FIELD_BORDER
        field.error_text = ""
        field.border_color = FIELD_BORDER
        field.focused_border_color = COLORS["accent"]

    def _polish(self, ctrl, compact: bool | None = None):
        from ui.theme import polish_tree
        return polish_tree(ctrl)

    def _dialog_box(self, body, max_width=880, max_height=None):
        width = max(360, min(max_width,
                             (getattr(self.page, "width", None) or 1280)
                             - self._DIALOG_SIDE_PAD))
        available = max(300, (getattr(self.page, "height", None) or 720)
                        - self._DIALOG_CHROME_H)
        height = min(max_height, available) if max_height else available
        return ft.Container(width=width, height=height,
                            content=ft.Column([body], scroll=ft.ScrollMode.AUTO,
                                              expand=True, spacing=0))

    def _two_col(self, left, right):
        narrow = (getattr(self.page, "width", None) or 1280) < 900
        spacing = self._cv(8, 12)
        if narrow:
            return ft.Column(left + right, spacing=spacing, tight=True)
        return ft.Row([
            ft.Column(left, spacing=spacing, expand=True, tight=True),
            ft.Column(right, spacing=spacing, expand=True, tight=True),
        ], spacing=self._cv(10, 14), vertical_alignment=ft.CrossAxisAlignment.START)

    def _section(self, icon, label, controls):
        from ui.theme import FIELD_BORDER, RADIUS_SECTION, SECTION_BG, soft_shadow
        return ft.Container(
            bgcolor=SECTION_BG, border_radius=RADIUS_SECTION,
            padding=self._cv(12, 16), border=ft.border.all(1, FIELD_BORDER),
            shadow=soft_shadow(self._cv(14, 20), self._cv(3, 5)),
            content=ft.Column([
                ft.Row([ft.Icon(icon, size=self._cv(14, 16), color=COLORS["accent"]),
                        ft.Text(label, size=self._cv(11, 12),
                                weight=ft.FontWeight.BOLD, color=COLORS["text"])],
                       spacing=7),
                *controls,
            ], spacing=self._cv(7, 10)),
        )

    def _config_block(self, on_steps_change=None):
        from core.key_manager import PROVIDERS, key_manager
        from core.script_generator import estimate_minutes
        from core.voices import ENGINES, LANGUAGES, list_voices, unsupported_msg
        from core.backgrounds import normalize_id as normalize_background, options as background_options, contrast_warning
        from core.fonts import font_options
        from core.subtitles import default_for_style, get_preset, normalize_preset_id, preset_options
        from core.templates import get_template, list_templates, normalize_id as normalize_template, normalize_style, style_options

        prefs = self._load_prefs()

        def pref(key, default):
            value = prefs.get(key)
            return default if value in (None, "") else value

        # The AI layout contract and regression suite currently cover the
        # vertical canvas only.  Do not advertise horizontal/square output
        # until all scene, subtitle and preview contracts are proven there.
        aspect = ft.Dropdown(label="Tỉ lệ", value="9:16", filled=True,
                             width=220, options=[
                                 ft.dropdown.Option("9:16", "9:16 — Dọc (được kiểm chứng)"),
                             ])
        lang = ft.Dropdown(label="Ngôn ngữ nội dung", value=pref("lang", "vi"),
                           filled=True,
                           options=[ft.dropdown.Option(code, name) for code, name in LANGUAGES])
        min_steps = ft.Dropdown(label="Step / tập", value=str(pref("min_steps", 12)),
                                filled=True, width=170,
                                options=[ft.dropdown.Option("0", "AI tự quyết")] + [
                                    ft.dropdown.Option(str(value))
                                    for value in (8, 10, 12, 15, 18, 20, 25, 30, 40)
                                ])
        estimate = ft.Text("", size=11, color=COLORS["accent_2"])

        def update_estimate(_=None):
            value = int(min_steps.value or 0)
            estimate.value = ("🤖 AI tự chọn số step theo nội dung."
                              if value <= 0 else
                              f"⏱ Ước lượng ~{estimate_minutes(value)} phút/tập ({value} step)")
            if on_steps_change:
                on_steps_change(value)
            self._safe_update()

        min_steps.on_change = update_estimate
        update_estimate()

        provider_states = {item["id"]: item for item in key_manager.list_providers()
                           if item.get("kind") == "llm"}
        if not provider_states:
            provider_states = {
                key: {"id": key, "name": value["name"], "ready": bool(value.get("local"))}
                for key, value in PROVIDERS.items() if value.get("kind", "llm") == "llm"
            }
        provider_id = pref("ai_provider", "gemini")
        if provider_id not in provider_states:
            provider_id = next(iter(provider_states), "gemini")
        ai_provider = ft.Dropdown(
            label="Nhà cung cấp AI", value=provider_id, filled=True, expand=True,
            options=[ft.dropdown.Option(pid,
                                        state.get("name", pid)
                                        + ("" if state.get("ready") else "  ⚠️ chưa có key"))
                     for pid, state in provider_states.items()],
        )
        ai_model = ft.Dropdown(label="Model", filled=True, expand=True)
        ai_hint = ft.Text("", size=11, color=COLORS["text_secondary"])

        def set_models(models, default=""):
            models = list(models or [])
            ai_model.options = [ft.dropdown.Option(model) for model in models]
            saved = str(prefs.get("ai_model") or "")
            ai_model.value = saved if saved in models else (default if default in models else
                                                            (models[0] if models else None))
            ai_model.disabled = not models

        def refresh_models(_=None):
            pid = ai_provider.value
            info = PROVIDERS.get(pid, {})
            if info.get("local"):
                ai_hint.value = "⏳ Đang lấy model từ dịch vụ local..."
                self._safe_update()

                def probe():
                    state = key_manager.probe_local(pid)
                    if ai_provider.value != pid:
                        return
                    set_models(state.get("models") or [])
                    if state.get("running") and state.get("models"):
                        ai_hint.value = f"✓ {state.get('model_count', len(state['models']))} model khả dụng."
                        ai_hint.color = COLORS["green"]
                    else:
                        ai_hint.value = "🔴 Dịch vụ local chưa chạy hoặc chưa có model."
                        ai_hint.color = COLORS["red"]
                    self._safe_update()

                threading.Thread(target=probe, daemon=True).start()
                return
            set_models(info.get("models") or [], info.get("default_model", ""))
            ready = provider_states.get(pid, {}).get("ready")
            ai_hint.value = ("✓ Sẵn sàng sinh kịch bản." if ready else
                             f"⚠️ Chưa có key {provider_states.get(pid, {}).get('name', pid)}.")
            ai_hint.color = COLORS["green"] if ready else COLORS["yellow"]

        ai_provider.on_change = refresh_models
        refresh_models()

        def check_model(_=None):
            pid, model = ai_provider.value, ai_model.value
            if not model:
                return
            ai_hint.value = f"⏳ Đang thử gọi {model}..."
            self._safe_update()

            def work():
                result = key_manager.probe_model(pid, model)
                if result.get("ok"):
                    ai_hint.value = f"✓ Model gọi được ({result.get('latency_ms', 0)} ms)."
                    ai_hint.color = COLORS["green"]
                else:
                    ai_hint.value = f"❌ {result.get('error') or 'Model không phản hồi.'}"
                    ai_hint.color = COLORS["red"]
                self._safe_update()

            threading.Thread(target=work, daemon=True).start()

        ai_check = ft.IconButton(ft.Icons.NETWORK_CHECK_ROUNDED,
                                 tooltip="Kiểm tra model", on_click=check_model)
        ai_reload = ft.IconButton(ft.Icons.REFRESH_ROUNDED,
                                  tooltip="Tải lại model", on_click=refresh_models)

        templates = list_templates()
        saved_template = normalize_template(prefs.get("template"))
        template = ft.Dropdown(
            label="Template mẫu", value=_select_value(saved_template, _MANUAL_TEMPLATE),
            filled=True, expand=True,
            options=[ft.dropdown.Option(_MANUAL_TEMPLATE, "✋ Tuỳ chỉnh thủ công")] + [
                ft.dropdown.Option(item["id"],
                                   f"{item.get('emoji', '')} {item['name']} — {item.get('desc', '')}")
                for item in templates
            ],
        )
        template_hint = ft.Text("", size=11, color=COLORS["text_secondary"])
        art_style = ft.Dropdown(label="Phong cách hình ảnh",
                                value=normalize_style(pref("art_style", "liquidglass")), filled=True,
                                expand=True,
                                options=[ft.dropdown.Option(key, label) for key, label in style_options()])
        background = ft.Dropdown(label="Nền", value=_select_value(normalize_background(prefs.get("bg")), _AUTO_BACKGROUND),
                                 filled=True, expand=True,
                                 options=[ft.dropdown.Option(_AUTO_BACKGROUND if not key else key, label)
                                          for key, label in background_options()])
        background_warning = ft.Text("", size=11, color=COLORS["yellow"], visible=False)
        title_colors = [
            ("", "Theo phong cách"), ("#FFD700", "🟡 Vàng gold"),
            ("#22d3ee", "🔵 Cyan"), ("#22c55e", "🟢 Xanh lá"),
            ("#f97316", "🟠 Cam"), ("#ec4899", "🌸 Hồng"),
            ("#ef4444", "🔴 Đỏ"), ("#a855f7", "🟣 Tím"),
            ("#ffffff", "⚪ Trắng"),
        ]
        saved_title_color = str(prefs.get("title_color") or "").strip()
        title_color = ft.Dropdown(label="Màu tiêu đề",
                                  value=_select_value(saved_title_color if saved_title_color in {key for key, _ in title_colors} else "", _INHERIT_TITLE_COLOR), filled=True,
                                  expand=True,
                                  options=[ft.dropdown.Option(_INHERIT_TITLE_COLOR if not key else key, label)
                                           for key, label in title_colors])
        fonts = font_options()
        font_value = str(prefs.get("font_family") or "")
        if font_value not in {key for key, _ in fonts}:
            font_value = ""
        font_family = ft.Dropdown(label="Font chữ", value=_select_value(font_value, _INHERIT_FONT), filled=True,
                                  expand=True,
                                  options=[ft.dropdown.Option(_INHERIT_FONT if not key else key, label) for key, label in fonts])

        subtitle_on = ft.Switch(value=bool(pref("subtitle_enabled", True)),
                                active_color=COLORS["accent"])
        saved_subtitle_preset = normalize_preset_id(prefs.get("subtitle_preset"))
        subtitle_preset = ft.Dropdown(
            label="Kiểu phụ đề", value=saved_subtitle_preset or _AUTO_SUBTITLE_PRESET,
            filled=True, expand=True,
            options=[ft.dropdown.Option(_AUTO_SUBTITLE_PRESET, "🤖 Tự động theo phong cách")] + [
                ft.dropdown.Option(key, label) for key, label in preset_options()
            ],
        )
        subtitle_hint = ft.Text("", size=11, color=COLORS["text_secondary"])

        def refresh_subtitle(_=None):
            subtitle_preset.disabled = not subtitle_on.value
            if subtitle_preset.value != _AUTO_SUBTITLE_PRESET:
                subtitle_hint.value = "Preset này áp dụng cho mọi bài của project."
            else:
                preset_id = default_for_style(art_style.value or "default")
                preset = get_preset(preset_id) or {}
                subtitle_hint.value = f"🤖 Tự động → {preset.get('name', preset_id)}"
            self._safe_update()

        subtitle_on.on_change = refresh_subtitle
        subtitle_preset.on_change = refresh_subtitle

        def check_contrast(_=None):
            message = contrast_warning(_stored_value(background.value, _AUTO_BACKGROUND), art_style.value or "")
            background_warning.value = message
            background_warning.visible = bool(message)
            refresh_subtitle()

        background.on_change = check_contrast
        art_style.on_change = check_contrast

        def on_template(_=None, apply=True):
            template_id = _stored_value(template.value, _MANUAL_TEMPLATE)
            if not template_id:
                template_hint.value = "Bạn tự chọn phong cách, màu và font."
                template_hint.color = COLORS["text_secondary"]
            else:
                item = get_template(template_id)
                if apply:
                    art_style.value = item.get("art_style", "default")
                    title_color.value = _select_value(item.get("title_color", ""), _INHERIT_TITLE_COLOR)
                    font_family.value = _select_value(item.get("font_family", ""), _INHERIT_FONT)
                    background.value = _AUTO_BACKGROUND
                template_hint.value = f"🎨 {item.get('vibe', '')}"
                template_hint.color = COLORS["accent_2"]
            check_contrast()

        template.on_change = on_template

        engine = ft.Dropdown(label="Engine giọng đọc",
                             value=pref("tts_engine", "edge"), filled=True, expand=True,
                             options=[ft.dropdown.Option(key, label) for key, label in ENGINES])
        saved_voice = str(prefs.get("voice") or prefs.get("tts_voice") or
                          ("vi-VN-HoaiMyNeural" if lang.value == "vi" else ""))
        voice = ft.Dropdown(label="Giọng đọc", value=saved_voice or None,
                            filled=True, expand=True,
                            options=[ft.dropdown.Option(saved_voice)] if saved_voice else [])
        voice_count = ft.Text("", size=11, color=COLORS["text_secondary"])
        tts_hint = ft.Text("", size=11, color=COLORS["text_secondary"])

        def refresh_voices(_=None, reset_voice=True):
            selected_engine, selected_lang = engine.value, lang.value
            voice.disabled = True
            voice_count.value = "⏳ Đang tải danh sách giọng..."
            self._safe_update()

            def work():
                load_error = ""
                try:
                    voices = list_voices(selected_engine, selected_lang)
                except Exception as exc:
                    voices = []
                    load_error = str(exc)
                if engine.value != selected_engine or lang.value != selected_lang:
                    return
                voice.options = [ft.dropdown.Option(item["id"], item["display"])
                                 for item in voices]
                ids = [item["id"] for item in voices]
                current = voice.value
                preferred = str(prefs.get("voice") or prefs.get("tts_voice") or "")
                if not reset_voice and preferred in ids:
                    voice.value = preferred
                elif current not in ids:
                    voice.value = ids[0] if ids else None
                voice.disabled = not voices
                voice_count.value = f"{len(voices)} giọng" if voices else ""
                if load_error:
                    tts_hint.value = f"Không tải được danh sách giọng: {load_error[:100]}"
                    tts_hint.color = COLORS["red"]
                elif voices:
                    if selected_engine == "edge":
                        tts_hint.value = "Edge TTS miễn phí, không cần key."
                    elif selected_engine == "gtts":
                        tts_hint.value = "Google TTS miễn phí, không cần key (cần mạng)."
                    elif selected_engine == "vivibe":
                        from core.tts_vivibe import credentials_ready
                        ready = credentials_ready()
                        tts_hint.value = "Vivibe đã sẵn sàng." if ready else "Chưa có tài khoản Vivibe — mở Cài đặt để nhập."
                        tts_hint.color = COLORS["green"] if ready else COLORS["red"]
                    else:
                        tts_hint.value = "Đã tải danh sách giọng."
                    if selected_engine != "vivibe":
                        tts_hint.color = COLORS["green"]
                else:
                    tts_hint.value = unsupported_msg(selected_engine, selected_lang)
                    tts_hint.color = COLORS["red"]
                self._safe_update()

            # Vivibe/EverAI/gTTS are local static catalogs. Updating them from a
            # worker thread can leave Flet showing the old Edge voice forever.
            if selected_engine in {"vivibe", "everai", "gtts"}:
                work()
            else:
                threading.Thread(target=work, daemon=True).start()

        engine.on_change = lambda _e: refresh_voices(reset_voice=True)

        def on_language(_e):
            refresh_voices(reset_voice=True)
            refresh_subtitle()

        lang.on_change = on_language
        tts_test = ft.OutlinedButton("Nghe thử", icon=ft.Icons.VOLUME_UP_ROUNDED)

        def test_tts(_=None):
            if not voice.value:
                self._snack("Chưa có giọng để nghe thử.")
                return
            if engine.value == "vivibe":
                from core.tts_vivibe import preview_path

                sample_path = preview_path(voice.value)
                if sample_path:
                    self._play_file(str(sample_path))
                else:
                    self._snack("Thiếu file nghe thử Vivibe trong bộ cài.")
                return
            tts_test.disabled = True
            tts_test.text = "Đang tạo..."
            self._safe_update()

            def work():
                import asyncio
                import tempfile
                try:
                    from engines.audio_engine import generate_tts_for_step
                    directory = tempfile.mkdtemp(prefix="tubecraft_voice_test_")
                    sample = _TTS_SAMPLE.get(lang.value) or _TTS_SAMPLE["en"]
                    ok, _duration, _words = asyncio.run(generate_tts_for_step(
                        1, sample, directory, voice.value, engine.value, lang.value
                    ))
                    path = os.path.join(directory, "step_001.mp3")
                    if ok and os.path.isfile(path):
                        self._play_file(path)
                    else:
                        self._snack("Không tạo được giọng thử.")
                except Exception as exc:
                    self._snack(f"Lỗi nghe thử: {str(exc)[:120]}")
                finally:
                    tts_test.disabled = False
                    tts_test.text = "Nghe thử"
                    self._safe_update()

            threading.Thread(target=work, daemon=True).start()

        tts_test.on_click = test_tts
        on_template(apply=True)
        refresh_subtitle()
        refresh_voices(reset_voice=False)

        sections = [
            self._section(ft.Icons.STYLE_ROUNDED, "TEMPLATE MẪU",
                          [template, template_hint]),
            self._section(ft.Icons.ASPECT_RATIO_ROUNDED, "ĐỊNH DẠNG",
                          [ft.Row([aspect, min_steps], spacing=8, wrap=True),
                           ft.Text("16:9 và 1:1 sẽ mở lại sau khi pass visual render test.",
                                   size=11, color=COLORS["text_secondary"]), estimate]),
            self._section(ft.Icons.AUTO_AWESOME_ROUNDED, "AI TẠO NỘI DUNG",
                          [ft.Row([ai_provider, ai_model, ai_check, ai_reload], spacing=4),
                           ai_hint]),
            self._section(ft.Icons.PALETTE_ROUNDED, "PHONG CÁCH & NỀN",
                          [art_style, background, background_warning]),
            self._section(ft.Icons.FORMAT_COLOR_TEXT_ROUNDED, "FONT & MÀU CHỮ",
                          [ft.Row([title_color, font_family], spacing=10)]),
            self._section(ft.Icons.RECORD_VOICE_OVER_ROUNDED, "GIỌNG ĐỌC",
                          [ft.Row([engine, voice], spacing=10),
                           ft.Row([tts_test, voice_count], spacing=10), tts_hint]),
            self._section(ft.Icons.SUBTITLES_ROUNDED, "PHỤ ĐỀ",
                          [ft.Row([subtitle_on, subtitle_preset], spacing=10),
                           subtitle_hint]),
        ]
        from ui.theme import FIELD_BORDER, RADIUS_SECTION
        language_bar = ft.Container(
            bgcolor=COLORS["accent"] + "16", border=ft.border.all(1, FIELD_BORDER),
            border_radius=RADIUS_SECTION, padding=self._cv(12, 16),
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.TRANSLATE_ROUNDED, color=COLORS["accent"], size=16),
                        ft.Text("NGÔN NGỮ VIDEO", size=12, weight=ft.FontWeight.BOLD,
                                color=COLORS["accent"])], spacing=7),
                lang,
                ft.Text("AI viết toàn bộ nội dung và lọc giọng đọc theo ngôn ngữ này.",
                        size=11, color=COLORS["text_secondary"]),
            ], spacing=8),
        )

        def values():
            return {
                "aspect_ratio": aspect.value or "9:16",
                "lang": lang.value or "vi",
                "ai_provider": ai_provider.value or "gemini",
                "ai_model": ai_model.value or "",
                "min_steps": int(min_steps.value or 12),
                "art_style": art_style.value or "default",
                "bg": _stored_value(background.value, _AUTO_BACKGROUND),
                "title_color": _stored_value(title_color.value, _INHERIT_TITLE_COLOR),
                "text_color": "",
                "font_family": _stored_value(font_family.value, _INHERIT_FONT),
                "template": _stored_value(template.value, _MANUAL_TEMPLATE),
                "tts_engine": engine.value or "edge",
                "voice": voice.value or "",
                "subtitle_enabled": bool(subtitle_on.value),
                "subtitle_preset": "" if subtitle_preset.value == _AUTO_SUBTITLE_PRESET else subtitle_preset.value,
                "subtitle_font_scale": 1.0,
                "subtitle_y_pct": None,
            }

        def validate():
            if not voice.value:
                return unsupported_msg(engine.value, lang.value)
            if engine.value == "vivibe":
                from core.tts_vivibe import credentials_ready
                if not credentials_ready():
                    return "Chưa cấu hình tài khoản Vivibe trong Cài đặt."
            if not ai_provider.value:
                return "Chưa chọn nhà cung cấp AI."
            return ""

        return sections, values, validate, language_bar

    def _create_dialog(self, _event=None):
        title = ft.TextField(label="Tên project *", filled=True,
                             prefix_icon=ft.Icons.MOVIE_CREATION_OUTLINED)
        sections, values, validate, language_bar = self._config_block()
        error = ft.Text("", size=12, color=COLORS["red"])
        body = ft.Column([
            title,
            self._two_col([language_bar, sections[0], sections[1], sections[2]],
                          [sections[3], sections[4], sections[6], sections[5]]),
            error,
        ], spacing=self._cv(8, 12), tight=True)

        def create(_=None):
            name = (title.value or "").strip()
            if not name:
                self._mark_required(title, "Bắt buộc — hãy đặt tên cho project.")
                self._safe_update()
                return
            message = validate()
            if message:
                error.value = message
                self._safe_update()
                return
            from core.project_store import project_store
            options = values()
            self._save_prefs(options)
            project = project_store.create_project(name, **options)
            self.page.close(dialog)
            self.selected_project = project
            self._reload_projects()
            self._reload_lessons()
            self._snack("✓ Đã tạo project.")

        title.on_change = lambda _e: self._clear_required(title)
        dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.VIDEO_SETTINGS_ROUNDED,
                                  color=COLORS["accent"]),
                          ft.Text("Tạo project mới", weight=ft.FontWeight.BOLD)], spacing=10),
            content=self._dialog_box(body, max_width=820),
            actions=[ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dialog)),
                     ft.FilledButton("Tạo project", icon=ft.Icons.ADD_ROUNDED,
                                     on_click=create)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dialog)
        return dialog

    def _autopilot_dialog(self, _event=None):
        idea = ft.TextField(label="Ý tưởng của bạn *", filled=True, multiline=True,
                            min_lines=3, max_lines=6,
                            hint_text="VD: Series dạy kiếm tiền online cho người mới...")
        count = ft.Dropdown(label="Số tập", value="5", width=160, filled=True,
                            options=[ft.dropdown.Option(str(value),
                                                        "1 — video dài" if value == 1 else str(value))
                                     for value in (1, 3, 5, 8, 10, 12)])
        auto_media = ft.Switch(value=False, label="Tự tạo giọng đọc + render")
        current_steps = {"value": 12}

        def steps_changed(value):
            current_steps["value"] = value

        sections, values, validate, language_bar = self._config_block(steps_changed)
        estimate = ft.Text("", size=12, color=COLORS["accent_2"])

        def update_total(_=None):
            episodes = int(count.value or 1)
            step_value = current_steps["value"]
            if episodes == 1:
                estimate.value = ("🎬 Một video dài; AI tự chia thành nhiều phần để viết."
                                  if step_value <= 0 else
                                  f"🎬 Một video khoảng {step_value} step.")
            else:
                estimate.value = f"🎞 {episodes} tập · {step_value or 'AI chọn'} step/tập."
            self._safe_update()

        count.on_change = update_total
        update_total()
        error = ft.Text("", size=12, color=COLORS["red"])
        progress = ft.ProgressBar(value=0, color=COLORS["accent"], bar_height=8,
                                  border_radius=5)
        status = ft.Text("Sẵn sàng", size=12, color=COLORS["text_secondary"])
        log = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
        progress_panel = ft.Container(
            visible=False, padding=12, border_radius=12,
            bgcolor=COLORS["bg_dark"], border=ft.border.all(1, COLORS["border"]),
            content=ft.Column([progress, status, log], spacing=8),
        )
        body = ft.Column([
            idea, ft.Row([count, auto_media], spacing=12), estimate,
            self._two_col([language_bar, sections[0], sections[1], sections[2]],
                          [sections[3], sections[4], sections[6], sections[5]]),
            error, progress_panel,
        ], spacing=10, tight=True)
        run_button = ft.FilledButton("Chạy Autopilot", icon=ft.Icons.AUTO_AWESOME)

        def run(_=None):
            prompt = (idea.value or "").strip()
            if not prompt:
                self._mark_required(idea, "Hãy nhập ý tưởng cho video/series.")
                self._safe_update()
                return
            message = validate()
            if message:
                error.value = message
                self._safe_update()
                return
            options = values()
            self._save_prefs(options)
            from core.autopilot import run_autopilot
            job = run_autopilot(
                prompt, int(count.value), aspect_ratio=options["aspect_ratio"],
                lang=options["lang"], ai_provider=options["ai_provider"],
                ai_model=options["ai_model"], tts_engine=options["tts_engine"],
                voice=options["voice"], min_steps=options["min_steps"],
                art_style=options["art_style"], title_color=options["title_color"],
                font_family=options["font_family"], bg=options["bg"],
                template=options["template"], auto_media=bool(auto_media.value),
                subtitle_enabled=options["subtitle_enabled"],
                subtitle_preset=options["subtitle_preset"],
                subtitle_font_scale=options["subtitle_font_scale"],
                subtitle_y_pct=options["subtitle_y_pct"],
            )
            progress_panel.visible = True
            run_button.disabled = True
            status.value = "Đang khởi động..."
            self._safe_update()
            self._watch_autopilot(job["id"], progress, status, log,
                                  on_done=lambda finished: self._autopilot_done(finished, dialog))

        run_button.on_click = run
        dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME, color=COLORS["accent"]),
                          ft.Text("Tạo tự động bằng AI", weight=ft.FontWeight.BOLD)], spacing=10),
            content=self._dialog_box(body, max_width=900),
            actions=[ft.TextButton("Đóng", on_click=lambda _: self.page.close(dialog)),
                     run_button], actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dialog)
        return dialog

    def _watch_autopilot(self, job_id, progress=None, status=None, log=None, on_done=None):
        def poll():
            last_message = None
            while True:
                from core import jobs
                job = jobs.get_job(job_id)
                if not job:
                    return
                if progress is not None:
                    progress.value = (job.get("progress") or 0) / 100
                message = str(job.get("message") or job.get("status") or "")
                if status is not None:
                    status.value = message
                    status.color = (COLORS["red"] if job.get("status") == "error"
                                    else COLORS["green"] if job.get("status") == "done"
                                    else COLORS["text_secondary"])
                if log is not None and message and message != last_message:
                    log.controls.append(ft.Text(message, size=11, color=COLORS["text"]))
                    last_message = message
                self._safe_update()
                if job.get("status") in ("done", "error", "cancelled"):
                    if on_done:
                        on_done(job)
                    return
                time.sleep(1.0)

        threading.Thread(target=poll, daemon=True).start()

    def _autopilot_done(self, job, dialog=None):
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        project_id = result.get("project_id")
        self._reload_projects()
        if project_id:
            from core.project_store import project_store
            project = project_store.get_project(project_id)
            if project:
                self.selected_project = project
                self._reload_projects()
                self._reload_lessons()
        if job.get("status") == "done":
            self._snack(job.get("message") or "✅ Autopilot hoàn tất.")
        elif job.get("status") == "error":
            self._snack("❌ " + str(job.get("message") or "Autopilot lỗi."))

    def _import_dialog(self, _event=None):
        path_field = ft.TextField(label="Thư mục project", filled=True,
                                  hint_text=r"C:\duong-dan\project")
        picker = None

        def picked(event):
            if getattr(event, "path", None):
                path_field.value = event.path
                self._safe_update()

        try:
            picker = ft.FilePicker(on_result=picked)
            if hasattr(self.page, "overlay"):
                self.page.overlay.append(picker)
                self.page.update()
        except Exception:
            picker = None

        def browse(_=None):
            if picker:
                picker.get_directory_path(dialog_title="Chọn thư mục project TubeCraft")

        error = ft.Text("", size=12, color=COLORS["red"])

        def do_import(_=None):
            source = (path_field.value or "").strip()
            if not source or not os.path.isfile(os.path.join(source, "project.json")):
                error.value = "Thư mục phải chứa project.json."
                self._safe_update()
                return
            from core.project_store import project_store
            try:
                project = project_store.import_external_project(source)
                if not project:
                    raise ValueError("project.json không hợp lệ")
                self.page.close(dialog)
                self.selected_project = project
                self._reload_projects()
                self._reload_lessons()
                self._snack("✓ Đã import project.")
            except Exception as exc:
                error.value = f"Import lỗi: {exc}"
                self._safe_update()

        dialog = ft.AlertDialog(
            title=ft.Text("Import project cũ", weight=ft.FontWeight.BOLD),
            content=ft.Container(width=520, content=ft.Column([
                ft.Row([path_field,
                        ft.IconButton(ft.Icons.FOLDER_OPEN_ROUNDED, on_click=browse)], spacing=8),
                error,
            ], spacing=10, tight=True)),
            actions=[ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dialog)),
                     ft.FilledButton("Import", icon=ft.Icons.DRIVE_FOLDER_UPLOAD,
                                     on_click=do_import)],
        )
        self.page.open(dialog)
        return dialog

    def _create_lesson_dialog(self, _event=None):
        if not self.selected_project:
            return
        project_id = self.selected_project["id"]
        mode = ft.Dropdown(label="Cách tạo", value="manual", filled=True,
                           options=[ft.dropdown.Option("manual", "Tạo bài trống"),
                                    ft.dropdown.Option("ai", "AI viết thêm bài")])
        title = ft.TextField(label="Tên bài học", filled=True)
        idea = ft.TextField(label="Ý tưởng / hướng mở rộng", filled=True,
                            multiline=True, min_lines=3, max_lines=5)
        count = ft.Dropdown(label="Số bài", value="1", width=140, filled=True,
                            options=[ft.dropdown.Option(str(value)) for value in (1, 2, 3, 5, 8)])
        auto_media = ft.Switch(label="Tự TTS + render", value=False)
        ai_group = ft.Column([idea, ft.Row([count, auto_media], spacing=12)],
                             spacing=10, visible=False)
        error = ft.Text("", size=12, color=COLORS["red"])
        progress = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        status = ft.Text("", size=11, color=COLORS["text_secondary"])

        def change_mode(_=None):
            title.visible = mode.value == "manual"
            ai_group.visible = mode.value == "ai"
            self._safe_update()

        mode.on_change = change_mode

        def create(_=None):
            from core.project_store import project_store
            if mode.value == "manual":
                name = (title.value or "").strip()
                if not name:
                    error.value = "Nhập tên bài học."
                    self._safe_update()
                    return
                project_store.create_lesson(project_id, name)
                self.page.close(dialog)
                self._reload_lessons()
                self._reload_projects()
                return
            from core.autopilot import add_ai_lessons
            job = add_ai_lessons(project_id, (idea.value or "").strip(),
                                 int(count.value), bool(auto_media.value))
            progress.visible = True
            create_button.disabled = True
            self._watch_autopilot(
                job["id"], progress, status, None,
                on_done=lambda finished: self._lesson_ai_done(finished, dialog),
            )

        create_button = ft.FilledButton("Tạo", icon=ft.Icons.ADD_ROUNDED,
                                        on_click=create)
        dialog = ft.AlertDialog(
            title=ft.Text("Thêm bài học", weight=ft.FontWeight.BOLD),
            content=ft.Container(width=520, content=ft.Column([
                mode, title, ai_group, error, progress, status,
            ], spacing=12, tight=True)),
            actions=[ft.TextButton("Đóng", on_click=lambda _: self.page.close(dialog)),
                     create_button],
        )
        self.page.open(dialog)
        return dialog

    def _lesson_ai_done(self, job, dialog=None):
        self._reload_lessons()
        self._reload_projects()
        if job.get("status") == "done":
            if dialog:
                self.page.close(dialog)
            self._snack(job.get("message") or "✓ Đã thêm bài học.")
        else:
            self._snack("❌ " + str(job.get("message") or "Không thêm được bài."))

    def _delete_project(self, project_id):
        def confirm(_=None):
            from core.project_store import project_store
            project_store.delete_project(project_id)
            self.page.close(dialog)
            self.selected_project = None
            self._reload_projects()
            self.lesson_panel.controls = [
                ft.Container(alignment=ft.alignment.center, expand=True,
                             content=ft.Text("Chọn một project để xem bài học",
                                             color=COLORS["text_secondary"]))
            ]
            self._safe_update(self.lesson_panel)

        dialog = ft.AlertDialog(
            title=ft.Text("Xoá project?"),
            content=ft.Text("Toàn bộ bài học, audio, video và script sẽ bị xoá vĩnh viễn."),
            actions=[ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dialog)),
                     ft.FilledButton("Xoá", on_click=confirm)],
        )
        self.page.open(dialog)

    def _delete_lesson(self, lesson_id):
        from core.project_store import project_store
        project_store.delete_lesson(self.selected_project["id"], lesson_id)
        self._reload_lessons()
        self._reload_projects()

    def _delete_lesson_confirm(self, lesson):
        def confirm(_=None):
            self.page.close(dialog)
            self._delete_lesson(lesson["id"])

        dialog = ft.AlertDialog(
            title=ft.Text("Xoá bài học?", weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Xoá '{lesson.get('title', '')[:60]}' cùng mọi file media?"),
            actions=[ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dialog)),
                     ft.FilledButton("Xoá", on_click=confirm)],
        )
        self.page.open(dialog)

    def _change_style(self, project_id, style):
        from core.project_store import project_store
        self.selected_project = project_store.update_project(project_id, art_style=style)
        self._snack(f"Đã đổi phong cách → {style}.")
        self._reload_lessons()

    def _change_bg(self, project_id, background):
        from core.backgrounds import contrast_warning, name_of, normalize_id
        from core.project_store import project_store
        background = normalize_id(_stored_value(background, _AUTO_BACKGROUND))
        self.selected_project = project_store.update_project(project_id, bg=background)
        warning = contrast_warning(background,
                                   self.selected_project.get("art_style", "default"))
        self._snack(warning or f"Đã đổi nền → {name_of(background)}.")
        self._reload_lessons()

    def _change_template(self, project_id, template_id):
        from core.project_store import project_store
        from core.templates import normalize_id
        template_id = normalize_id(_stored_value(template_id, _MANUAL_TEMPLATE))
        if not template_id:
            self.selected_project = project_store.update_project(project_id, template="")
            self._snack("Đã bỏ template. Bạn có thể tự chọn phong cách/màu/font.")
        else:
            from core.templates import get_template
            template = get_template(template_id)
            self.selected_project = project_store.update_project(
                project_id, template=template_id,
                art_style=template.get("art_style", "default"),
                title_color=template.get("title_color", ""),
                text_color=template.get("text_color", ""),
                font_family=template.get("font_family", ""),
            )
            self._snack(f"Đã áp template → {template.get('emoji', '')} {template['name']}.")
        self._reload_lessons()

    def _subtitle_dialog(self, project):
        from core.project_store import project_store
        from ui.subtitle_picker import show_subtitle_dialog
        script = timing = None
        for lesson in project_store.list_lessons(project["id"]):
            if not lesson.get("has_script"):
                continue
            full = project_store.get_lesson(project["id"], lesson["id"]) or {}
            candidate = full.get("script") or {}
            if candidate.get("steps"):
                script, timing = candidate, full.get("timing")
                break

        def saved(updated):
            self.selected_project = updated
            self._reload_lessons()

        return show_subtitle_dialog(self.page, project, script=script, timing=timing,
                                    on_saved=saved)

    def _ai_gen_lesson(self, lesson_id):
        if lesson_id in self._ai_gen_active or not self.selected_project:
            return
        from core.project_store import project_store
        project_id = self.selected_project["id"]
        project = project_store.get_project(project_id)
        lessons = project_store.list_lessons(project_id)
        lesson = next((item for item in lessons if item["id"] == lesson_id), None)
        if not project or not lesson:
            self._snack("Không tìm thấy bài học.")
            return
        position = lesson.get("index", 0) + 1
        self._ai_gen_active.add(lesson_id)
        self._snack(f"✨ AI đang viết kịch bản Tập {position}...")
        self._reload_lessons()

        def work():
            try:
                from core.script_generator import generate_lesson_script
                titles = "\n".join(
                    f"  {index + 1}. {item.get('title', '')}"
                    for index, item in enumerate(lessons)
                )
                content = (
                    f"Đây là series '{project.get('title', '')}'. Toàn bộ các tập:\n{titles}\n\n"
                    f"Viết kịch bản cho TẬP {position}: \"{lesson.get('title', '')}\". "
                    "Bám sát mạch tổng thể, không lặp nội dung của tập khác."
                )
                scene_counter = Counter()
                for other in lessons:
                    if other["id"] == lesson_id:
                        continue
                    full = project_store.get_lesson(project_id, other["id"]) or {}
                    scene_counter.update((full.get("script") or {}).get("scenes_used") or [])
                avoid = [name for name, count in scene_counter.most_common(16) if count >= 2][:8]
                script, _errors = generate_lesson_script(
                    content, subject=project.get("subject", "general"),
                    step_count=int(project.get("min_steps", 10)),
                    lang=project.get("lang", "vi"),
                    provider=project.get("ai_provider", ""),
                    model=project.get("ai_model", ""),
                    template=project.get("template") or "", variety_seed=position,
                    avoid_effects=avoid,
                    series_info={"index": position, "total": len(lessons)},
                )
                project_store.save_script(project_id, lesson_id, script)
                project_store.update_lesson_meta(project_id, lesson_id, status="ready")
                self._snack(f"✓ Đã viết xong kịch bản Tập {position}.")
            except Exception as exc:
                self._snack(f"❌ Không viết được kịch bản: {str(exc)[:180]}")
            finally:
                self._ai_gen_active.discard(lesson_id)
                self._reload_lessons()

        threading.Thread(target=work, daemon=True).start()

    def _export_excel(self, project):
        self._snack("📊 Đang xuất Excel...")

        def work():
            try:
                from core.export_excel import export_project_xlsx
                path = export_project_xlsx(project["id"])
                self._snack(f"✓ Đã xuất Excel: {path}")
                os.startfile(path)
            except Exception as exc:
                self._snack(f"❌ Xuất Excel lỗi: {exc}")

        threading.Thread(target=work, daemon=True).start()

    def _color_font_dialog(self, project):
        colors = [
            ("", "Theo phong cách"), ("#FFD700", "🟡 Vàng gold"),
            ("#22d3ee", "🔵 Cyan"), ("#22c55e", "🟢 Xanh lá"),
            ("#f97316", "🟠 Cam"), ("#ec4899", "🌸 Hồng"),
            ("#ef4444", "🔴 Đỏ"), ("#a855f7", "🟣 Tím"),
            ("#ffffff", "⚪ Trắng"),
        ]
        from core.fonts import font_options
        title_color = ft.Dropdown(label="Màu tiêu đề",
                                  value=_select_value(project.get("title_color", ""), _INHERIT_TITLE_COLOR), filled=True,
                                  options=[ft.dropdown.Option(_INHERIT_TITLE_COLOR if not key else key, label) for key, label in colors])
        font = ft.Dropdown(label="Font chữ", value=_select_value(project.get("font_family", ""), _INHERIT_FONT),
                           filled=True,
                           options=[ft.dropdown.Option(_INHERIT_FONT if not key else key, label) for key, label in font_options()])

        def save(_=None):
            from core.project_store import project_store
            self.selected_project = project_store.update_project(
                project["id"], title_color=_stored_value(title_color.value, _INHERIT_TITLE_COLOR),
                font_family=_stored_value(font.value, _INHERIT_FONT)
            )
            self.page.close(dialog)
            self._reload_lessons()
            self._snack("Đã lưu màu & font.")

        dialog = ft.AlertDialog(
            title=ft.Text("Màu tiêu đề & font", weight=ft.FontWeight.BOLD),
            content=ft.Container(width=400, content=ft.Column([
                title_color, font,
                ft.Text("Font Segoe UI xử lý dấu tiếng Việt tốt nhất.", size=11,
                        color=COLORS["text_secondary"]),
            ], spacing=12, tight=True)),
            actions=[ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dialog)),
                     ft.FilledButton("Lưu", on_click=save)],
        )
        self.page.open(dialog)

    def _preview_lesson(self, lesson_id):
        from core.project_store import project_store
        from ui.preview_dialog import show_preview
        project_id = self.selected_project["id"]
        lesson = project_store.get_lesson(project_id, lesson_id)
        project = project_store.get_project(project_id)
        if not lesson or not project:
            self._snack("Không tải được bài học.")
            return
        show_preview(self.page, project, lesson)

    def _render_lesson(self, lesson_id):
        from ui.render_dialog import render_lesson
        render_lesson(self.page, self.selected_project["id"], lesson_id,
                      on_queued=lambda _job: (self._reload_lessons(), self._ensure_poll()))

    def _play_lesson(self, lesson_id):
        from core.project_store import project_store
        project_id = self.selected_project["id"]
        lesson = project_store.get_lesson(project_id, lesson_id)
        project = project_store.get_project(project_id)
        video_path = lesson.get("rendered_video_path", "") if lesson else ""
        if lesson and project and video_path and os.path.isfile(video_path):
            from ui.components import show_result
            show_result(self.page, project, lesson, video_path)
        else:
            self._snack("Chưa có video — hãy render trước.")

    def _tts_lesson(self, lesson_id):
        from core.render_service import queue_tts
        queue_tts(self.selected_project["id"], lesson_id)
        self._snack("Đã xếp hàng tạo giọng đọc.")
        self._reload_lessons()
        self._ensure_poll()

    def _batch(self, kind):
        from core.project_store import project_store
        lessons = [lesson for lesson in project_store.list_lessons(
            self.selected_project["id"]) if lesson.get("has_script")]
        if not lessons:
            self._snack("Chưa bài nào có script để xử lý.")
            return
        if kind == "tts":
            todo = [lesson for lesson in lessons if not lesson.get("has_audio")]
            if not todo:
                self._show_batch_confirm("Tất cả bài đã có giọng đọc.",
                                         "Tạo lại giọng đọc cho tất cả?",
                                         lambda: self._do_batch(lessons, "tts"))
                return
            self._do_batch(todo, "tts")
            self._snack(f"Đã xếp hàng tạo giọng đọc cho {len(todo)} bài.")
            return
        todo = [lesson for lesson in lessons if not lesson.get("has_video")]
        if not todo:
            self._show_batch_confirm("Tất cả bài đã render.",
                                     "Render lại tất cả (dùng audio cũ nếu có)?",
                                     lambda: self._do_batch(lessons, "pipeline"))
            return
        self._do_batch(todo, "pipeline")
        skipped = len(lessons) - len(todo)
        message = f"Đã xếp hàng render {len(todo)} bài."
        if skipped:
            message += f" Bỏ qua {skipped} bài đã render."
        self._snack(message)

    def _do_batch(self, lessons, kind):
        from core.render_service import queue_full_pipeline, queue_render, queue_tts
        project_id = self.selected_project["id"]
        for lesson in lessons:
            if kind == "tts":
                queue_tts(project_id, lesson["id"])
            elif lesson.get("has_audio"):
                queue_render(project_id, lesson["id"])
            else:
                queue_full_pipeline(project_id, lesson["id"])
        self._reload_lessons()
        self._ensure_poll()

    def _show_batch_confirm(self, title, question, on_yes):
        def yes(_=None):
            self.page.close(dialog)
            on_yes()

        dialog = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD), content=ft.Text(question),
            actions=[ft.TextButton("Bỏ qua", on_click=lambda _: self.page.close(dialog)),
                     ft.FilledButton("Làm lại tất cả", on_click=yes)],
        )
        self.page.open(dialog)

    def _ensure_poll(self):
        if self._polling or not self._active or self._stopped.is_set():
            return
        self._polling = True

        def loop():
            try:
                while self._active and self.selected_project and not self._stopped.is_set():
                    if self._stopped.wait(2.0) or not self._active:
                        break
                    active = self._active_jobs_map()
                    if not self._active or self._stopped.is_set():
                        break
                    self._check_finished_renders()
                    if not self._active or self._stopped.is_set():
                        break
                    self._reload_lessons()
                    if not active:
                        self._reload_projects()
                        break
            finally:
                self._polling = False

        threading.Thread(target=loop, daemon=True).start()

    def _check_finished_renders(self):
        if not self._active or self._stopped.is_set():
            return
        from core import jobs
        from core.project_store import project_store
        project_id = self.selected_project.get("id") if self.selected_project else None
        if not project_id:
            return
        newly_finished = []
        for job in jobs.list_jobs(limit=150):
            if job.get("status") != "done" or job["id"] in self._shown_results:
                continue
            meta = job.get("meta") or {}
            result = job.get("result") if isinstance(job.get("result"), dict) else {}
            if meta.get("project_id") != project_id or not result.get("video"):
                continue
            self._shown_results.add(job["id"])
            newly_finished.append((meta.get("lesson_id"), result["video"]))
        if not newly_finished:
            return
        if self._active_jobs_map():
            self._snack(f"✅ Render xong {len(newly_finished)} bài.")
            return
        if self._has_open_dialog():
            self._snack(
                "✅ Render đã xong. Đóng form hiện tại rồi mở bài học hoặc Hàng đợi Render để xem video."
            )
            return
        lesson_id, video_path = newly_finished[-1]
        lesson = project_store.get_lesson(project_id, lesson_id)
        project = project_store.get_project(project_id)
        if lesson and project:
            from ui.components import show_result
            show_result(self.page, project, lesson, video_path)

    def _has_open_dialog(self) -> bool:
        """Avoid replacing an in-progress form with an asynchronous result modal."""
        roots = [getattr(self.page, "overlay", None)]
        offstage = getattr(self.page, "_Page__offstage", None)
        roots.append(getattr(offstage, "controls", None))
        for controls in roots:
            for control in controls or []:
                if isinstance(control, ft.AlertDialog) and bool(getattr(control, "open", False)):
                    return True
        return False
