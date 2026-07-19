"""ui/dashboard/view.py — Tổng quan: số liệu + job gần đây."""
import flet as ft
from ui.theme import COLORS, STATUS_COLORS

def _stat_card(icon, label, value, color):
    from ui.theme import RADIUS, tile_icon
    return ft.Container(expand=True, bgcolor=COLORS["bg_card"], border_radius=RADIUS, padding=18, border=ft.border.all(1, COLORS["border"]), shadow=ft.BoxShadow(blur_radius=20, color="#00000044", offset=ft.Offset(0, 5)), content=ft.Row([tile_icon(icon, color, 46),
    
    ft.Column([ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]), ft.Text(label, size=12, color=COLORS["text_secondary"])], spacing=0)], spacing=14))

class DashboardView(ft.Column):
    def __init__(self, page: ft.Page, on_nav):
        super().__init__(spacing=20, expand=True, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.STRETCH); self.page = page; self.on_nav = on_nav; self._build()
    
    def _build(self):
        from core.project_store import project_store
        from core.key_manager import key_manager
        from core import jobs
        projects = project_store.list_projects()
        lesson_total = sum(p.get("lesson_count_actual", 0) for p in projects)
        providers = key_manager.list_providers()
        ready = sum(1 for provider in providers if provider.get("ready"))
        all_jobs = jobs.list_jobs(limit=8)
        running = sum(1 for job in all_jobs if job.get("status") in ("queued", "running"))
        self.scroll = ft.ScrollMode.AUTO
        
        self.controls = [ft.Text("Tổng quan", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            
            ft.Row([_stat_card(ft.Icons.VIDEO_LIBRARY_ROUNDED, "Projects", len(projects), COLORS["accent"]),
    
    _stat_card(ft.Icons.MENU_BOOK_ROUNDED, "Bài học", lesson_total, COLORS["accent_2"]),
    
    _stat_card(ft.Icons.BOLT_ROUNDED, "Job đang chạy", running, COLORS["yellow"]), _stat_card(ft.Icons.VPN_KEY_ROUNDED, "Provider sẵn sàng", f"{ready}/{len(providers)}", COLORS["green"])], spacing=14),
            
            ft.Text("Bắt đầu nhanh", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            
            ft.Row([self._quick(ft.Icons.AUTO_AWESOME, "Tạo tự động (AI)", "Nhập ý tưởng → cả series", COLORS["accent"], "projects"),
    
    self._quick(ft.Icons.VIDEO_LIBRARY_ROUNDED, "Projects", "Quản lý & render", COLORS["purple"], "projects"),
    
    self._quick(ft.Icons.QUEUE_ROUNDED, "Hàng đợi Render", "Theo dõi tiến trình", COLORS["orange"], "render_queue"), self._quick(ft.Icons.VPN_KEY_ROUNDED, "Key AI Cloud", "Nạp & xoay key", COLORS["green"], "keys")], spacing=14),
            
            ft.Column([ft.Text("Hoạt động gần đây", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
    
    self._jobs_list(all_jobs)], spacing=10)]
    
    def _quick(self, icon, title, desc, color, nav):
        from ui.theme import tile_icon
        return ft.Container(expand=True, bgcolor=COLORS["bg_card"], border_radius=14, padding=16, border=ft.border.all(1, COLORS["border"]), shadow=ft.BoxShadow(blur_radius=16, color="#1f40870d", offset=ft.Offset(0, 4)), on_click=(lambda e: self.on_nav(nav)), ink=True, content=ft.Column([tile_icon(icon, color, 42), ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"]), ft.Text(desc, size=11, color=COLORS["text_secondary"])], spacing=8))
    
    def _jobs_list(self, all_jobs):
        if not all_jobs:
            return ft.Container(bgcolor=COLORS["bg_card"], border_radius=12, padding=24, border=ft.border.all(1, COLORS["border"]), content=ft.Text("Chưa có hoạt động nào. Tạo project để bắt đầu!", color=COLORS["text_secondary"]))
        rows = []
        for j in all_jobs:
            c = STATUS_COLORS.get(j["status"], COLORS["text_secondary"])
            rows.append(ft.Row([ft.Container(width=8, height=8, border_radius=4, bgcolor=c),
    
    ft.Text(j["kind"].upper(), size=11, color=c, width=70),
    
    ft.Text(j.get("message", "")[:80] or j["status"], size=12, color=COLORS["text"], expand=True), ft.Text(f"{j.get("progress", 0)}%", size=12, color=COLORS["text_secondary"])], spacing=10))
        return ft.Container(bgcolor=COLORS["bg_card"], border_radius=12, padding=16, border=ft.border.all(1, COLORS["border"]), content=ft.Column(rows, spacing=10))
