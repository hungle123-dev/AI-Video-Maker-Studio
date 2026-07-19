"""ui/components.py — Thành phần UI dùng chung: progress bar chuyên nghiệp +
màn "khoe thành quả" khi render xong (vibe premium)."""
import os, flet as ft
from ui.theme import COLORS, RADIUS

def pro_progress(value: float, stage: str="", pct_text: bool=True):
    value = max(0.0, min(1.0, value or 0)); pct = int(value * 100)
    
    bar = ft.Stack([ft.Container(height=10, border_radius=6, bgcolor=COLORS["border"]),
    
    ft.Row([ft.Container(expand=max(1, pct), height=10, border_radius=6, gradient=ft.LinearGradient(begin=ft.alignment.center_left, end=ft.alignment.center_right, colors=[COLORS["accent"], COLORS["accent_2"]])),
    
    ft.Container(expand=max(1, 100 - pct))], spacing=0)]); row = [ft.Container(content=bar, expand=True)]
    if pct_text:
        row.append(ft.Text(f"{pct}%", size=13, weight=ft.FontWeight.BOLD, color=COLORS["accent_2"], width=46, text_align=ft.TextAlign.RIGHT))
    
    col = [ft.Row(row, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)]
    if stage:
        col.append(ft.Row([ft.ProgressRing(width=13, height=13, stroke_width=2, color=COLORS["accent"]), ft.Text(stage, size=11, color=COLORS["text_secondary"], max_lines=2, expand=True)], spacing=8))
    return ft.Column(col, spacing=6)

def show_result(page: ft.Page, project: dict, lesson: dict, video_path: str):
    exists = bool(video_path) and os.path.isfile(video_path)
    size_mb = round(os.path.getsize(video_path) / (1024 * 1024), 1) if exists else 0
    timing = lesson.get("timing") if isinstance(lesson.get("timing"), dict) else {}
    duration = float(timing.get("total_duration") or 0)
    if duration > 0:
        minutes, seconds = divmod(int(round(duration)), 60)
        dur_txt = f"{minutes}:{seconds:02d}"
    else:
        dur_txt = "—"
    aspect = project.get("aspect_ratio", "9:16")

    def open_video(_=None):
        if exists:
            try:
                os.startfile(video_path)
            except Exception:
                try:
                    import subprocess
                    subprocess.Popen([video_path])
                except Exception:
                    pass
    
    def reveal(_):
        if exists:
            import subprocess
            subprocess.Popen(["explorer", "/select,", os.path.normpath(video_path)])

    if aspect == "16:9":
        pw, ph = (400, 225)
    elif aspect == "1:1":
        pw, ph = (300, 300)
    else:
        pw, ph = (210, 373)
    player = None
    if exists:
        try:
            player = ft.Video(width=pw, height=ph, playlist=[ft.VideoMedia(resource=video_path)], autoplay=True, show_controls=True, muted=False, fit=ft.ImageFit.CONTAIN, fill_color="#000000", aspect_ratio=pw / ph)
        except Exception:
            player = None

    empty = ft.Column([
        ft.Icon(ft.Icons.MOVIE_ROUNDED, size=40,
                color=COLORS["accent"] if exists else COLORS["text_secondary"]),
        ft.Text("Bấm để mở video" if exists else "Không tìm thấy video", size=11,
                color=COLORS["text_secondary"]),
    ], alignment=ft.MainAxisAlignment.CENTER,
       horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    poster = ft.Container(
        width=pw, height=ph, border_radius=RADIUS, bgcolor="#000000",
        alignment=ft.alignment.center, border=ft.border.all(1.5, COLORS["accent"]),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS, content=player or empty,
        on_click=None if player else open_video,
    )

    def meta(icon, label, value):
        return ft.Row([
            ft.Icon(icon, size=15, color=COLORS["accent_2"]),
            ft.Text(label, size=12, color=COLORS["text_secondary"]),
            ft.Text(value, size=12, color=COLORS["text"], weight=ft.FontWeight.BOLD),
        ], spacing=6)

    def close_dialog(_=None):
        if player:
            try:
                player.pause()
            except Exception:
                pass
        page.close(dialog)

    dialog = ft.AlertDialog(
        content=ft.Container(
            width=620, padding=6,
            content=ft.Column([
                ft.Row([
                    ft.Container(width=40, height=40, border_radius=20,
                                 bgcolor=COLORS["green"] + "22", alignment=ft.alignment.center,
                                 content=ft.Icon(ft.Icons.CELEBRATION_ROUNDED,
                                                 color=COLORS["green"], size=24)),
                    ft.Column([
                        ft.Text("🎉 Render hoàn tất!", size=18,
                                weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        ft.Text(lesson.get("title", "")[:60], size=12,
                                color=COLORS["text_secondary"]),
                    ], spacing=1),
                ], spacing=12),
                ft.Container(height=8),
                ft.Row([
                    poster,
                    ft.Column([
                        meta(ft.Icons.ASPECT_RATIO_ROUNDED, "Tỉ lệ:", aspect),
                        meta(ft.Icons.SCHEDULE_ROUNDED, "Thời lượng:", dur_txt),
                        meta(ft.Icons.SD_CARD_ROUNDED, "Dung lượng:", f"{size_mb} MB"),
                        ft.Container(height=10),
                        ft.Text("▶ Có thể tua và xem ngay trong cửa sổ này." if player
                                else "Mở video bằng trình phát mặc định.",
                                size=11, color=COLORS["text_secondary"]),
                        ft.FilledButton("Mở toàn màn hình", icon=ft.Icons.FULLSCREEN_ROUNDED,
                                        on_click=open_video, width=210, disabled=not exists),
                        ft.OutlinedButton("Mở thư mục", icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                                          on_click=reveal, width=210, disabled=not exists),
                    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER, expand=True),
                ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6, tight=True),
        ),
        actions=[ft.TextButton("Đóng", on_click=close_dialog)],
    )
    dialog.on_dismiss = lambda _e: player.pause() if player else None
    page.open(dialog)
    return dialog
