"""ui/render_dialog.py — Xử lý render một bài, hỏi ý kiến nếu đã render rồi.

render_lesson(page, project_id, lesson_id, on_queued):
  - Chưa có giọng đọc  → chạy full pipeline (TTS + render).
  - Có giọng, chưa có video → chỉ render video (dùng lại audio, không tạo lại).
  - Đã có video → hỏi: Chỉ render video / Render lại audio + video / Bỏ qua.
"""
import flet as ft
from ui.theme import COLORS

def render_lesson(page: ft.Page, project_id: str, lesson_id: str, on_queued=None):
    from core.project_store import audio_is_current, project_store, video_is_current
    from core.render_service import queue_render, queue_full_pipeline
    lesson = project_store.get_lesson(project_id, lesson_id)
    if not lesson:
        page.open(ft.SnackBar(content=ft.Text("Không tìm thấy bài học.")))
        return None
    if lesson.get("script_validation_errors"):
        page.open(ft.SnackBar(content=ft.Text("Kịch bản có dữ liệu không hợp lệ; hãy mở và lưu lại trước.")))
        return None
    if not lesson.get("script", {}).get("steps"):
        page.open(ft.SnackBar(content=ft.Text("Bài chưa có kịch bản.")))
        return None
    paths = project_store.lesson_paths(project_id, lesson_id)
    has_audio = audio_is_current(lesson, lesson.get("timing"), paths["full_audio"])
    video_path = lesson.get("rendered_video_path", "")
    has_video = bool(video_path) and video_is_current(lesson, video_path)

    def _queue(full):
        job = (queue_full_pipeline(project_id, lesson_id) if full
               else queue_render(project_id, lesson_id))
        if on_queued:
            on_queued(job)
        return job
    
    if not has_video:
        full = not has_audio
        job = _queue(full=full)
        message = ("Đã xếp hàng tạo giọng đọc + render." if full
                   else "Đã xếp hàng render video (dùng audio hiện có).")
        page.open(ft.SnackBar(content=ft.Text(message)))
        return job

    def choose(full):
        page.close(dlg)
        _queue(full=full)
        message = ("Đã xếp hàng tạo lại audio + video." if full
                   else "Đã xếp hàng render lại video (dùng audio cũ).")
        page.open(ft.SnackBar(content=ft.Text(message)))
    
    opts = [ft.FilledButton("Chỉ render lại video", icon=ft.Icons.MOVIE_FILTER_ROUNDED, tooltip="Dùng lại giọng đọc hiện có, chỉ dựng lại video", disabled=not has_audio, on_click=(lambda _: choose(False))), ft.OutlinedButton("Render lại audio + video", icon=ft.Icons.RECORD_VOICE_OVER_ROUNDED, tooltip="Tạo lại giọng đọc rồi render", on_click=(lambda _: choose(True)))]
    
    dlg = ft.AlertDialog(title=ft.Row([ft.Icon(ft.Icons.HELP_OUTLINE_ROUNDED, color=COLORS["yellow"]),
    
    ft.Text("Bài này đã render", weight=ft.FontWeight.BOLD)], spacing=10), content=ft.Container(width=420, content=ft.Column([ft.Text(f"'{lesson.get("title", "")[:60]}' đã có video.", size=13, color=COLORS["text"]),
    
    ft.Text("Bạn muốn làm gì?", size=12, color=COLORS["text_secondary"]), ft.Container(height=4)], spacing=10, tight=True)), actions=opts + [ft.TextButton("Bỏ qua", on_click=(lambda _: page.close(dlg)))], actions_alignment=ft.MainAxisAlignment.END)
    
    page.open(dlg)
    return dlg
