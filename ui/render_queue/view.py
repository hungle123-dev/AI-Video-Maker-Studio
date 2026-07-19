"""ui/render_queue/view.py — Danh sách job TTS/render, tự làm mới."""
import threading, flet as ft
from ui.theme import COLORS, STATUS_COLORS

class RenderQueueView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(spacing=14, expand=True, alignment=ft.MainAxisAlignment.START); self.page = page; self.jobs_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True); self._active = True; self._stopped = threading.Event()
        
        self.controls = [ft.Row([ft.Text("Hàng đợi Render", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]), ft.Container(expand=True),
    
    ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="Làm mới", on_click=(lambda e: self._reload()))]), self.jobs_col]; self._reload(); self._auto_refresh()
    
    def _reload(self):
        from core import jobs; self.jobs_col.controls.clear(); all_jobs = jobs.list_jobs(limit=40)
        if not all_jobs:
            self.jobs_col.controls.append(ft.Text("Chưa có job nào.", color=COLORS["text_secondary"]))
        for j in all_jobs:
            self.jobs_col.controls.append(self._job_card(j))
        try:
            self.update()
        except Exception:
            pass
    
    def _job_card(self, j):
        c = STATUS_COLORS.get(j["status"], COLORS["text_secondary"])
        meta = j.get("meta", {})
        running = j["status"] == "running"
        is_error = j["status"] == "error"
        result = j.get("result") if isinstance(j.get("result"), dict) else {}
        logs = [str(line) for line in (j.get("logs") or []) if str(line).strip()]
        
        head = [ft.ProgressRing(width=14, height=14, stroke_width=2, color=c)
                if running else ft.Container(width=10, height=10, border_radius=5, bgcolor=c),
            
            ft.Text(j["kind"].upper(), size=12, weight=ft.FontWeight.BOLD, color=c, width=80),
            
            ft.Text(f"{meta.get("project_id", "")}/{meta.get("lesson_id", "")}", size=12, color=COLORS["text_secondary"], expand=True),
            
            ft.Text(j["status"], size=12, color=c), ft.Text(f"{j.get("progress", 0)}%", size=12, color=COLORS["text"])]
        
        if is_error and result.get("error_detail"):
            head.append(ft.TextButton("Xem log", icon=ft.Icons.BUG_REPORT_OUTLINED, on_click=(lambda e, jj=j: self._show_error(jj))))
        if j.get("status") in ("queued", "running") and j.get("kind") in ("tts", "render", "pipeline"):
            head.append(ft.TextButton("Dừng", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=(lambda e, jj=j: self._cancel(jj))))
        
        if result.get("video"):
            head.append(ft.TextButton("▶ Xem", on_click=(lambda e, p=result["video"]: self._open(p))))
        body = [ft.Row(head, spacing=10), ft.Text(j.get("message", ""), size=11, color=COLORS["red"] if is_error else COLORS["text_secondary"], max_lines=3, selectable=True)]
        if logs:
            body.append(ft.Container(
                bgcolor=COLORS["bg_glass"], border_radius=6, padding=8, height=132,
                content=ft.Column([
                    ft.Text("Nhật ký Vivibe", size=11, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"]),
                    ft.Text("\n".join(logs[-14:]), size=10, selectable=True,
                            font_family="Consolas", color=COLORS["text_secondary"]),
                ], spacing=4, scroll=ft.ScrollMode.AUTO),
            ))
        return ft.Container(bgcolor=COLORS["bg_card"], border_radius=10, padding=14, border=ft.border.all(1, COLORS["red"] if is_error else COLORS["border"]), content=ft.Column(body, spacing=8))
    
    def _open(self, path):
        import os
        if path and os.path.exists(path):
            try:
                os.startfile(path)
                return None
            except Exception as exc:
                self.page.open(ft.SnackBar(content=ft.Text(f"Không mở được file: {exc}")))
                return None
        self.page.open(ft.SnackBar(content=ft.Text("Chưa thấy file.")))

    def _cancel(self, job):
        from core.render_service import cancel_job
        updated = cancel_job(job.get("id", ""))
        if updated:
            self.page.open(ft.SnackBar(content=ft.Text("Đã yêu cầu dừng job.")))
        self._reload()
    
    def _show_error(self, j):
        result = j.get("result") if isinstance(j.get("result"), dict) else {}
        detail = str(result.get("error_detail") or j.get("message") or "Không có chi tiết lỗi.")
        txt = ft.TextField(value=detail, multiline=True, min_lines=14, max_lines=22,
                           read_only=True, text_size=11,
                           text_style=ft.TextStyle(font_family="Consolas"))
        def open_log(_):
            import os
            from config import LOGS_DIR; log = os.path.join(str(LOGS_DIR), "app.log")
            if os.path.exists(log):
                os.startfile(log)
                return None
        
        dlg = ft.AlertDialog(title=ft.Row([ft.Icon(ft.Icons.BUG_REPORT_ROUNDED, color=COLORS["red"]),
    
    ft.Text("Chi tiết lỗi", weight=ft.FontWeight.BOLD)], spacing=10), content=ft.Container(width=680, content=txt), actions=[ft.TextButton("Mở app.log", icon=ft.Icons.DESCRIPTION_OUTLINED, on_click=open_log), ft.FilledButton("Đóng", on_click=(lambda _: self.page.close(dlg)))])
        
        self.page.open(dlg)
    
    def _auto_refresh(self):
        def loop():
            while not self._stopped.wait(2.5):
                if not self._active:
                    continue
                try:
                    if not self.page:
                        return None
                    self._reload()
                except Exception:
                    pass
        
        threading.Thread(target=loop, daemon=True).start()

    def activate(self):
        self._active = True
        self._reload()

    def deactivate(self):
        self._active = False

    def dispose(self):
        self._active = False
        self._stopped.set()
