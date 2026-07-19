"""ui/settings/view.py — Cài đặt chung: AI provider mặc định, TTS, render."""
import flet as ft
from ui.theme import COLORS

class SettingsView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(spacing=16, expand=True, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.page = page
        self._build()
    
    def _build(self):
        from config import load_settings
        from core.key_manager import PROVIDERS
        from core.tts_vivibe import load_credentials
        s = load_settings()
        vivibe_user, vivibe_password = load_credentials()
        self.ai_provider = ft.Dropdown(label="AI provider mặc định (sinh kịch bản)", value=s.get("ai_provider", "gemini"), width=340, options=[ft.dropdown.Option(pid, PROVIDERS[pid]["name"]) for pid in PROVIDERS if PROVIDERS[pid].get("kind", "llm") == "llm"])
        
        self.ai_model = ft.TextField(label="Model (bỏ trống = mặc định của provider)", value=s.get("ai_model", ""), width=340)
        
        self.tts_voice = ft.TextField(label="Giọng TTS mặc định", value=s.get("tts_voice", ""), width=340, hint_text="vi-VN-HoaiMyNeural / Giọng adam"); self.fps = ft.TextField(label="FPS render", value=str(s.get("render_fps", 30)), width=160)
        self.vivibe_user = ft.TextField(label="Tài khoản Vivibe", value=vivibe_user, hint_text="Email đăng nhập")
        self.vivibe_password = ft.TextField(label="Mật khẩu Vivibe", value="", password=True, can_reveal_password=True, hint_text="Để trống nếu không đổi")
        self.vivibe_status = ft.Text("✅ Đã lưu credential mã hóa" if vivibe_user and vivibe_password else "Chưa cấu hình Vivibe", size=11, color=COLORS["green"] if vivibe_user and vivibe_password else COLORS["text_secondary"])
        
        self.gpu = ft.Dropdown(label="Encoder", value=s.get("gpu_encoder", "auto"), width=200, options=[ft.dropdown.Option("auto"),
    
    ft.dropdown.Option("nvenc"), ft.dropdown.Option("cpu")])
        
        for c in (self.ai_provider,
            self.ai_model,
            self.tts_voice,
            self.vivibe_user,
            self.vivibe_password):
            c.width = None
            c.expand = True
        
        self.controls = [ft.Text("Cài đặt", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            
            ft.Row([ft.Column([self._section(ft.Icons.AUTO_AWESOME_ROUNDED, "AI TẠO NỘI DUNG", [self.ai_provider,
    self.ai_model,
    ft.Text("Provider & model mặc định khi tạo project mới.", size=11, color=COLORS["text_secondary"])]),
    
    self._section(ft.Icons.RECORD_VOICE_OVER_ROUNDED, "GIỌNG ĐỌC", [self.tts_voice,
    ft.Text("Mỗi project vẫn chọn engine và giọng riêng.", size=11, color=COLORS["text_secondary"]),
    ft.Divider(height=1, color=COLORS["border"]), self.vivibe_user, self.vivibe_password, self.vivibe_status])], spacing=16, expand=True),
    
    ft.Column([self._section(ft.Icons.MOVIE_FILTER_ROUNDED, "RENDER", [ft.Row([self.fps,
    self.gpu], spacing=12), ft.Text("Encoder auto: tự dùng GPU NVIDIA nếu có, không thì CPU.", size=11, color=COLORS["text_secondary"])]), self._about_card()], spacing=16, expand=True)], spacing=18, vertical_alignment=ft.CrossAxisAlignment.START),
            
            ft.FilledButton("Lưu cài đặt", icon=ft.Icons.SAVE_ROUNDED, on_click=self._save)]
    
    def _section(self, icon, title, controls):
        return ft.Container(bgcolor=COLORS["bg_card"], border_radius=14, padding=18, border=ft.border.all(1, COLORS["border"]), shadow=ft.BoxShadow(blur_radius=16, color="#1f40870d", offset=ft.Offset(0, 4)), content=ft.Column([ft.Row([ft.Icon(icon, size=16, color=COLORS["accent"]),
    ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"])], spacing=8), *controls], spacing=12))
    
    def _about_card(self):
        import os
        from config import APP_NAME, APP_VERSION, DATA_DIR
        
        def open_data(_):
            try:
                os.startfile(str(DATA_DIR))
            except Exception:
                pass
        
        def row(label, val, mono=False):
            return ft.Row([ft.Text(label, size=12, color=COLORS["text_secondary"], width=110), ft.Text(val, size=12, color=COLORS["text"], expand=True, selectable=True, font_family="Consolas" if mono else None)])
        
        return ft.Container(bgcolor=COLORS["bg_card"], border_radius=14, padding=18, border=ft.border.all(1, COLORS["border"]), shadow=ft.BoxShadow(blur_radius=16, color="#1f40870d", offset=ft.Offset(0, 4)), content=ft.Column([ft.Row([ft.Icon(ft.Icons.INFO_ROUNDED, size=16, color=COLORS["accent"]),
    
    ft.Text("THÔNG TIN ỨNG DỤNG", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"])], spacing=8),
    
    row("Ứng dụng", f"{APP_NAME}  by TubeCreate"), row("Phiên bản", f"v{APP_VERSION}"), row("Chế độ", "Local — đầy đủ tính năng"), row("Thư mục dữ liệu", str(DATA_DIR), mono=True), ft.Container(height=4),
    
    ft.OutlinedButton("Mở thư mục dữ liệu", icon=ft.Icons.FOLDER_OPEN_ROUNDED, on_click=open_data)], spacing=10))
    
    def _save(self, e):
        from config import load_settings, save_settings; s = load_settings()
        from core.tts_vivibe import load_credentials, save_credentials
        old_user, old_password = load_credentials()
        username = (self.vivibe_user.value or "").strip()
        new_password = self.vivibe_password.value or ""
        if username or new_password:
            try:
                save_credentials(username or old_user, new_password or old_password)
                self.vivibe_password.value = ""
                self.vivibe_status.value = "✅ Đã lưu credential mã hóa"
                self.vivibe_status.color = COLORS["green"]
            except ValueError as exc:
                self.page.open(ft.SnackBar(content=ft.Text(str(exc))))
                return
        s["ai_provider"] = self.ai_provider.value; s["ai_model"] = (self.ai_model.value or "").strip(); s["tts_voice"] = (self.tts_voice.value or "").strip()
        try:
            s["render_fps"] = max(10, min(60, int(self.fps.value)))
        except Exception:
            pass
        s["gpu_encoder"] = self.gpu.value
        save_settings(s)
        self.page.open(ft.SnackBar(content=ft.Text("Đã lưu cài đặt.")))
