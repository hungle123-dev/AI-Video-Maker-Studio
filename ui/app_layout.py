"""ui/app_layout.py — Sidebar + vùng nội dung (mô hình t2login)."""
import flet as ft
from ui.theme import COLORS

NAV_ITEMS = [("dashboard", ft.Icons.DASHBOARD_ROUNDED,
    "Tổng quan"), ("projects", ft.Icons.VIDEO_LIBRARY_ROUNDED,
    "Projects"), ("templates", ft.Icons.STYLE_ROUNDED,
    "Template mẫu"), ("render_queue", ft.Icons.QUEUE_ROUNDED,
    "Hàng đợi Render"),
    
    ("keys", ft.Icons.VPN_KEY_ROUNDED,
    "Key AI Cloud"), ("settings", ft.Icons.SETTINGS_ROUNDED,
    "Cài đặt")]
class AppLayout(ft.Column):
    def __init__(self, page: ft.Page, on_nav, initial_content):
        super().__init__(spacing=0, expand=True)
        self.page = page; self.on_nav = on_nav; self._active = "dashboard"; self._nav_buttons = {}; nav_col = [self._brand()]
        for key, icon, label in NAV_ITEMS:
            btn = self._nav_button(key, icon, label)
            self._nav_buttons[key] = btn
            nav_col.append(btn)
        
        nav_col.append(ft.Container(expand=True)); nav_col.append(self._footer())
        
        self.sidebar = ft.Container(width=220, bgcolor=COLORS["bg_card"], border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])), padding=ft.padding.symmetric(vertical=14, horizontal=10), content=ft.Column(nav_col, spacing=4))
        try:
            from ui.theme import polish_tree
            polish_tree(initial_content)
        except Exception:
            pass
        self.content_area = ft.Container(expand=True, padding=24, alignment=ft.alignment.top_left, content=initial_content)
        body = ft.Row([self.sidebar, self.content_area], spacing=0, expand=True)
        self.controls = [self._titlebar(), body]
        self._highlight()
    
    def _titlebar(self):
        self._max_icon = ft.Icon(ft.Icons.CROP_SQUARE_ROUNDED, size=15, color=COLORS["text_secondary"])
        def win_btn(icon_ctrl, on_click, hover=COLORS["bg_hover"], danger=False):
            return ft.Container(width=46, height=34, border_radius=8, alignment=ft.alignment.center, content=icon_ctrl, on_click=on_click, ink=True, data={"hover": "#fee2e2" if danger else hover}, on_hover=self._btn_hover)
        
        def minimize(_):
            self.page.window.minimized = True; self.page.update()
        
        def toggle_max(_):
            self.page.window.maximized = not self.page.window.maximized
            
            self._max_icon.name = ft.Icons.FILTER_NONE_ROUNDED if self.page.window.maximized else ft.Icons.CROP_SQUARE_ROUNDED
            self.page.update()
        
        def close(_):
            self.page.window.close()
        
        return ft.Container(bgcolor=COLORS["bg_card"], height=40, border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])), content=ft.Row([ft.WindowDragArea(ft.Container(padding=ft.padding.only(left=16), alignment=ft.alignment.center_left, content=ft.Row([ft.Image(src="logo.png", width=20, height=20, fit=ft.ImageFit.CONTAIN),
    
    ft.Text("TubeCraft", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]), ft.Text("· TubeCreate Studio", size=11, color=COLORS["text_secondary"])], spacing=8)), expand=True, maximizable=True),
    
    win_btn(ft.Icon(ft.Icons.REMOVE_ROUNDED, size=16, color=COLORS["text_secondary"]), minimize), win_btn(self._max_icon, toggle_max),
    
    win_btn(ft.Icon(ft.Icons.CLOSE_ROUNDED, size=16, color=COLORS["text_secondary"]), close, danger=True), ft.Container(width=6)], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    
    def _btn_hover(self, e):
        e.control.bgcolor = e.control.data["hover"] if e.data == "true" else None
        e.control.update()
    
    def _brand(self):
        from config import APP_VERSION
        return ft.Container(padding=ft.padding.only(left=10, bottom=18, top=4), content=ft.Row([ft.Image(src="logo.png", width=34, height=34, fit=ft.ImageFit.CONTAIN),
    
    ft.Column([ft.Text("TubeCraft", size=17, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
    
    ft.Text(f"v{APP_VERSION}", size=10, color=COLORS["text_secondary"])], spacing=0)], spacing=8))
    
    def _nav_button(self, key, icon, label):
        return ft.Container(border_radius=8, padding=ft.padding.symmetric(vertical=10, horizontal=12), on_click=(lambda e, k=key: self._click(k)), content=ft.Row([ft.Icon(icon, size=18, color=COLORS["text_secondary"]),
    
    ft.Text(label, size=13, color=COLORS["text_secondary"])], spacing=10))
    
    def _meter(self, label: str):
        bar = ft.ProgressBar(value=0, bar_height=5, border_radius=3, color=COLORS["accent"], bgcolor=COLORS["bg_hover"]); pct = ft.Text("--", size=9, color=COLORS["text_secondary"], width=32, text_align=ft.TextAlign.RIGHT)
        
        row = ft.Row([ft.Text(label, size=9, color=COLORS["text_secondary"], width=26), ft.Container(content=bar, expand=True), pct], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return (row, bar, pct)
    
    def _footer(self):
        cpu_row, self._cpu_bar, self._cpu_pct = self._meter("CPU")
        ram_row, self._ram_bar, self._ram_pct = self._meter("RAM")
        gpu_row, self._gpu_bar, self._gpu_pct = self._meter("GPU")
        self._gpu_row = ft.Container(content=gpu_row, visible=False); self._sys_hint = ft.Text("", size=9, color=COLORS["text_secondary"]); self._monitor_started = False
        return ft.Container(padding=ft.padding.only(left=12, right=10, bottom=6, top=6), content=ft.Column([cpu_row, ram_row, self._gpu_row,
    self._sys_hint,
    ft.Text("TubeCreate © 2026", size=10, color=COLORS["text_secondary"])], spacing=4))
    
    def start_monitor(self):
        if self._monitor_started:
            return None
        self._monitor_started = True
        import threading
        from core import sysmon; sysmon.start()
        def _tick():
            while True:
                s = sysmon.snapshot()
                try:
                    self._cpu_bar.value = s["cpu"] / 100
                    self._cpu_pct.value = f'{s["cpu"]:.0f}%'
                    self._cpu_bar.color = self._load_color(s["cpu"])
                    self._ram_bar.value = s["ram"] / 100
                    self._ram_pct.value = f'{s["ram"]:.0f}%'
                    self._ram_bar.color = self._load_color(s["ram"])
                    if s["gpu"] is None:
                        self._gpu_row.visible = False
                    else:
                        self._gpu_row.visible = True
                        self._gpu_bar.value = s["gpu"] / 100
                        self._gpu_pct.value = f'{s["gpu"]:.0f}%'
                        self._gpu_bar.color = self._load_color(s["gpu"])
                    self._sys_hint.value = f'RAM {s["ram_used_gb"]:.1f}/{s["ram_total_gb"]:.0f} GB' + (f' · VRAM {s["gpu_mem_used_gb"]:.1f}/{s["gpu_mem_total_gb"]:.0f} GB' if s["gpu"] is not None else '')
                    self.update()
                except Exception:
                    pass
                sysmon._stop.wait(sysmon.POLL_SECONDS)
                if sysmon._stop.is_set():
                    break
        
        threading.Thread(target=_tick, daemon=True, name="TubeCraft-SysMonUI").start()
    
    @staticmethod
    def _load_color(pct: float) -> str:
        if pct >= 90:
            return COLORS["red"]
        elif pct >= 70:
            return COLORS["orange"]
        
        return COLORS["accent"]
    
    def _click(self, key):
        self._active = key; self._highlight(); self.on_nav(key)
    
    def _highlight(self):
        for key, btn in self._nav_buttons.items():
            active = key == self._active
            btn.bgcolor = COLORS["bg_hover"] if active else None
            row = btn.content
            row.controls[0].color = COLORS["accent"] if active else COLORS["text_secondary"]
            row.controls[1].color = COLORS["accent"] if active else COLORS["text_secondary"]
            row.controls[1].weight = ft.FontWeight.BOLD if active else ft.FontWeight.W_500
        try:
            self.update()
        except Exception:
            pass
    
    def navigate(self, key):
        self._click(key)
    
    def set_content(self, view):
        try:
            from ui.theme import polish_tree
            polish_tree(view)
        except Exception:
            pass
        self.content_area.content = view
        try:
            self.content_area.update()
        except Exception:
            pass
