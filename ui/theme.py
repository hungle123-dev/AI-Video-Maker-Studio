"""ui/theme.py — Theme SÁNG glass xanh (vibe quanlythuoc):
nền xanh nhạt, card trắng mờ, chữ ink đậm, accent #3b7cf6."""
import flet as ft; COLORS = {"bg_dark": "#eef1fb", "bg_card": "#ffffff", "bg_glass": "#f5f7fe", "bg_hover": "#e7edfb", "border": "#dbe3f4", "border_soft": "#e8edf9", "accent": "#3b7cf6", "accent_deep": "#2563eb", "accent_2": "#0ea5e9", "green": "#16a34a", "yellow": "#d97706", "orange": "#ea580c", "red": "#dc2626", "purple": "#9333ea", "pink": "#db2777", "text": "#1e2b4a", "text_secondary": "#5b6b8c"}; STATUS_COLORS = {"draft": "#5b6b8c", "queued": "#d97706", "running": "#3b7cf6", "done": "#16a34a", "error": "#dc2626", "cancelled": "#5b6b8c"}; RADIUS = 16; RADIUS_LG = 22; RADIUS_FIELD = 14; RADIUS_SECTION = 22; RADIUS_DIALOG = 28; RADIUS_BTN = 18; FIELD_BG = "#ffffff"; SECTION_BG = "#f7f8fd"; FIELD_BORDER = "#e6eaf6"; PLACEHOLDER = "#8c9ac0"; SHADOW_GLASS = "#1f408714"; SHADOW_BTN = "#3b6ef659"; BTN_GRADIENT = ["#5b8ef8", "#3b6ef6", "#345ff0"]
def soft_shadow(blur=32, dy=8):
    return ft.BoxShadow(blur_radius=blur, spread_radius=0, color=SHADOW_GLASS, offset=ft.Offset(0, dy))

def round_field(ctrl):
    ctrl.filled = True; ctrl.fill_color = FIELD_BG; ctrl.bgcolor = FIELD_BG; ctrl.focused_bgcolor = FIELD_BG; ctrl.border_radius = RADIUS_FIELD; ctrl.border_color = FIELD_BORDER; ctrl.focused_border_color = COLORS["accent"]
    if getattr(ctrl, "hint_style", None) is None:
        ctrl.hint_style = ft.TextStyle(color=PLACEHOLDER)
    return ctrl

def round_btn_style(radius=RADIUS_BTN, pad_h=18, pad_v=14):
    return ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=radius), padding=ft.padding.symmetric(horizontal=pad_h, vertical=pad_v))

def _btn_theme(theme_type, radius=RADIUS_BTN):
    return theme_type(shape=ft.RoundedRectangleBorder(radius=radius))

def build_theme() -> ft.Theme:
    return ft.Theme(color_scheme_seed=COLORS["accent"], dialog_theme=ft.DialogTheme(bgcolor=COLORS["bg_card"], shape=ft.RoundedRectangleBorder(radius=RADIUS_DIALOG), elevation=8, shadow_color=SHADOW_GLASS), card_theme=ft.CardTheme(color=COLORS["bg_card"], elevation=1, shape=ft.RoundedRectangleBorder(radius=RADIUS_SECTION)), snackbar_theme=ft.SnackBarTheme(shape=ft.RoundedRectangleBorder(radius=14), elevation=4), filled_button_theme=_btn_theme(ft.FilledButtonTheme), elevated_button_theme=_btn_theme(ft.ElevatedButtonTheme), outlined_button_theme=_btn_theme(ft.OutlinedButtonTheme), text_button_theme=_btn_theme(ft.TextButtonTheme, 12))

_SNACK_KINDS = {"ok": (ft.Icons.CHECK_CIRCLE_ROUNDED,
    "#16a34a", "#dcfce7"), "err": (ft.Icons.CANCEL_ROUNDED,
    "#dc2626", "#fee2e2"), "warn": (ft.Icons.WARNING_AMBER_ROUNDED,
    "#d97706", "#fef3c7"), "info": (ft.Icons.INFO_ROUNDED,
    "#2563eb", "#dbeafe")}
def polish_snackbar(sb, page_width=None):
    import re
    if not isinstance(getattr(sb, "content", None), ft.Text):
        return
    msg = sb.content.value or ""; low = msg.lower()
    if msg.startswith(("✓", "✅")):
        kind = "ok"
    elif msg.startswith("❌") or low.startswith("lỗi") or "lỗi:" in low:
        kind = "err"
    elif msg.startswith(("⚠", "!")):
        kind = "warn"
    else:
        kind = "info"
    icon, col, tint = _SNACK_KINDS[kind]
    
    text = re.sub("^[✓✅❌⚠️\\s]+", "", msg) or msg
    
    sb.content = ft.Row([ft.Container(width=34, height=34, border_radius=17, bgcolor=tint, alignment=ft.alignment.center, content=ft.Icon(icon, size=20, color=col)), ft.Text(text, size=14, weight=ft.FontWeight.W_600, color=COLORS["text"], expand=True, max_lines=3)], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER); sb.bgcolor = COLORS["bg_card"]; sb.behavior = ft.SnackBarBehavior.FLOATING
    
    sb.shape = ft.RoundedRectangleBorder(radius=16); sb.elevation = 12
    
    w = int(page_width or 0)
    left = max(20, w - 560) if w else 20
    sb.margin = ft.margin.only(left=left, right=18, bottom=16)
    sb.duration = 6000 if kind == "err" else 3500
    sb.show_close_icon = kind == "err"
    sb.close_icon_color = COLORS["text_secondary"]

def polish_tree(ctrl, _seen=None):
    if ctrl is None or isinstance(ctrl, (str, int, float, bool)):
        return ctrl
    if _seen is None:
        _seen = set()
    if id(ctrl) in _seen:
        return ctrl
    _seen.add(id(ctrl))
    if isinstance(ctrl, (list, tuple)):
        for c in ctrl:
            polish_tree(c, _seen)
        return ctrl
    if isinstance(ctrl, (ft.TextField, ft.Dropdown)):
        round_field(ctrl)
    
    for attr in ("controls", "content", "actions", "title", "leading", "trailing"):
        child = getattr(ctrl, attr, None)
        if child is not None:
            polish_tree(child, _seen)
    return ctrl

def primary_button(text, icon=None, on_click=None, width=180, height=46):
    row = ft.Row(
        [c for c in (
            ft.Icon(icon, size=18, color="white") if icon else None,
            ft.Text(text, size=15, weight=ft.FontWeight.W_600, color="white"),
        ) if c],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
    )
    return ft.Container(content=row, width=width, height=height, on_click=on_click, ink=True, border_radius=RADIUS_BTN, alignment=ft.alignment.center, padding=ft.padding.symmetric(horizontal=20), gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=BTN_GRADIENT), shadow=ft.BoxShadow(blur_radius=24, color=SHADOW_BTN, offset=ft.Offset(0, 10)))
def card(content, padding=16, radius=RADIUS, accent=False, **kw):
    return ft.Container(content=content, bgcolor=COLORS["bg_card"], border_radius=radius, padding=padding, border=ft.border.all(1.5, COLORS["accent"] if accent else COLORS["border"]), shadow=ft.BoxShadow(blur_radius=24, spread_radius=0, color="#1f40871a", offset=ft.Offset(0, 6)), **kw)

def tile_icon(icon, color, size=44):
    return ft.Container(width=size, height=size, border_radius=size / 3.4, bgcolor=color + "1f", alignment=ft.alignment.center, content=ft.Icon(icon, color=color, size=size * 0.5))

def gradient_bg():
    return ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=["#e6ecfb", "#eef1fb"])
