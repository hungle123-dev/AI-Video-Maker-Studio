"""ui/subtitle_picker.py — Dialog chọn PHỤ ĐỀ (cháy chữ) cho project.

Ba phần, đọc từ trái sang phải:
  • Trái  : XEM TRƯỚC step đang chọn — frame render THẬT bằng canvas_renderer.js,
            áp đúng preset + cỡ chữ + vị trí đang kéo. Đổi gì cũng thấy ngay.
  • Phải  : bật/tắt, 2 thanh trượt (cỡ chữ, vị trí dọc) và LƯỚI THẺ 16 preset,
            mỗi thẻ là dải ảnh render thật quanh vùng phụ đề (core/subtitle_thumbs).
  • Đáy   : Huỷ / Lưu → ghi thẳng project.json qua project_store.update_project.

Thẻ mẫu render NỀN (thread) + spinner, y như trang Template mẫu — mở dialog là
dùng được ngay, ảnh hiện dần. Lần sau mở lại: đã cache → hiện tức thì.

Dùng được cả khi project CHƯA có kịch bản (dựng kịch bản mẫu 1 step) và cả khi
chưa chạy TTS (subtitle_engine tự rải chữ theo độ dài câu).
"""
import base64
import os
import re
import threading

import flet as ft

from ui.theme import COLORS; _DEBOUNCE_S = 0.35; _SCALE_MIN, _SCALE_MAX = (0.8, 1.4); _Y_MIN, _Y_MAX = (0.7, 0.88)
_SAFE_CACHE_PART = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def _cache_part(value: object, fallback: str) -> str:
    text = str(value or "")
    return text if _SAFE_CACHE_PART.fullmatch(text) else fallback


def _remove_temp_preview(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError:
        return


def show_subtitle_dialog(page: ft.Page, project: dict, script: dict=None, timing: dict=None, step_index: int=0, on_saved=None):
    """Open the project subtitle picker and return its dialog.

    The preview and preset thumbnails are rendered by the same canvas engine
    used for final videos, so a selection in this dialog is representative of
    the exported result.  Passing a project without an ``id`` is supported by
    the create-project dialog; in that case ``on_saved`` receives the values.
    """
    from core import subtitles as subs
    from core import subtitle_thumbs as thumbs

    presets = subs.list_presets()
    if not presets:
        page.open(ft.SnackBar(content=ft.Text("❌ Không đọc được engines/subtitle_presets.json — chưa có preset phụ đề.")))
        return None

    project = project if isinstance(project, dict) else {}
    cfg = subs.subtitle_config(project)
    art_style = project.get("art_style") or "default"
    auto_id = subs.default_for_style(art_style)
    steps = (script or {}).get("steps") or []
    ctx = thumbs.context(project, script)
    demo_mode = not steps
    if demo_mode:
        script = thumbs.demo_script(ctx)
        timing = thumbs.demo_timing(ctx)
        steps = script["steps"]

    step_index = max(0, min(int(step_index or 0), len(steps) - 1))
    selected_raw = subs.normalize_preset_id(project.get("subtitle_preset"))
    selected_effective = selected_raw or cfg.get("preset") or auto_id
    initial_y = cfg.get("yPct")
    if initial_y is None:
        initial_y = _preset_y(subs, selected_effective)
    state = {
        "enabled": bool(cfg.get("enabled")),
        "preset": selected_raw,
        "scale": _clamp(cfg.get("fontScale", 1.0), _SCALE_MIN, _SCALE_MAX),
        "y": _clamp(initial_y, _Y_MIN, _Y_MAX),
        "y_pinned": project.get("subtitle_y_pct") is not None,
        "idx": step_index,
        "token": 0,
        "closed": False,
        "preview_cancel": None,
        "thumb_cancel": threading.Event(),
    }
    timer = {"value": None}
    frames, images, spinners = {}, {}, {}

    def effective_preset():
        return state["preset"] or auto_id

    def update_page():
        try:
            page.update()
        except Exception:
            pass

    aspect = project.get("aspect_ratio") or "9:16"
    ratio = _ratio(aspect)
    preview_h = min(610, max(390, int((getattr(page, "height", 760) or 760) - 190)))
    preview_w = min(480, max(245, int(preview_h / ratio)))
    preview_image = ft.Image(width=preview_w, height=preview_h, fit=ft.ImageFit.CONTAIN,
                             border_radius=10, gapless_playback=True)
    preview_spinner = ft.ProgressRing(width=28, height=28, stroke_width=3, color=COLORS["accent"])
    caption = ft.Text("", size=11, color=COLORS["text_secondary"],
                      max_lines=2, text_align=ft.TextAlign.CENTER)
    step_label = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"])
    previous_button = ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED)
    next_button = ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED)

    def sync_step_labels():
        index = state["idx"]
        step_label.value = f"Step {index + 1}/{len(steps)}"
        caption.value = str(steps[index].get("voice_text") or "(không lời thoại)")[:150]
        caption.color = COLORS["text_secondary"]
        previous_button.disabled = index <= 0
        next_button.disabled = index >= len(steps) - 1

    def render_preview(token, cancel):
        if state["closed"] or cancel.is_set():
            return
        index = state["idx"]
        params = dict(project)
        params.update({
            "subtitle_enabled": state["enabled"],
            "subtitle_preset": effective_preset(),
            "subtitle_font_scale": state["scale"],
            "subtitle_y_pct": state["y"],
        })
        from config import DATA_DIR
        preview_dir = os.path.join(
            str(DATA_DIR),
            "previews",
            _cache_part(project.get("id"), "new-project"),
            "subtitle-dialog",
        )
        os.makedirs(preview_dir, exist_ok=True)
        out = os.path.join(preview_dir, f"{_cache_part(project.get('id'), 'new-project')}_{index}_{token}.png")
        from core.preview import render_step_preview
        result = render_step_preview(params, script, index, out, timing=timing, cancel_check=cancel.is_set)
        if token != state["token"] or state["closed"] or cancel.is_set():
            _remove_temp_preview(out)
            return
        preview_spinner.visible = False
        if result.get("ok"):
            try:
                with open(result["path"], "rb") as handle:
                    preview_image.src_base64 = base64.b64encode(handle.read()).decode("ascii")
                preview_image.src = None
            except Exception as exc:
                caption.value = f"⚠️ Không đọc được preview: {exc}"
                caption.color = COLORS["yellow"]
            finally:
                _remove_temp_preview(out)
        else:
            caption.value = "⚠️ " + str(result.get("error") or "Không render được preview")[:160]
            caption.color = COLORS["yellow"]
        update_page()

    def schedule_preview(delay=_DEBOUNCE_S):
        previous_cancel = state.get("preview_cancel")
        if previous_cancel is not None:
            previous_cancel.set()
        cancel = threading.Event()
        state["preview_cancel"] = cancel
        state["token"] += 1
        token = state["token"]
        old = timer.get("value")
        if old is not None:
            old.cancel()
        preview_spinner.visible = True
        update_page()
        pending = threading.Timer(delay, render_preview, args=(token, cancel))
        pending.daemon = True
        timer["value"] = pending
        pending.start()

    def go_step(delta):
        state["idx"] = max(0, min(len(steps) - 1, state["idx"] + delta))
        sync_step_labels()
        schedule_preview(0.05)

    previous_button.on_click = lambda _: go_step(-1)
    next_button.on_click = lambda _: go_step(1)

    enabled_switch = ft.Switch(label="Bật phụ đề cháy chữ", value=state["enabled"],
                               active_color=COLORS["accent"])
    scale_label = ft.Text("", size=11, color=COLORS["text_secondary"])
    y_label = ft.Text("", size=11, color=COLORS["text_secondary"])

    def sync_slider_labels():
        scale_label.value = f"Cỡ chữ: {state['scale']:.2f}×"
        y_label.value = f"Vị trí dọc: {state['y'] * 100:.0f}%"

    def on_scale(event, final=False):
        state["scale"] = _clamp(event.control.value, _SCALE_MIN, _SCALE_MAX)
        sync_slider_labels()
        if final:
            schedule_preview(0.05)
        else:
            update_page()

    def on_y(event, final=False):
        state["y"] = _clamp(event.control.value, _Y_MIN, _Y_MAX)
        state["y_pinned"] = True
        sync_slider_labels()
        if final:
            schedule_preview(0.05)
        else:
            update_page()

    scale_slider = ft.Slider(min=_SCALE_MIN, max=_SCALE_MAX, divisions=12,
                             value=state["scale"], on_change=on_scale,
                             on_change_end=lambda e: on_scale(e, True))
    y_slider = ft.Slider(min=_Y_MIN, max=_Y_MAX, divisions=18,
                         value=state["y"], on_change=on_y,
                         on_change_end=lambda e: on_y(e, True))

    grid = ft.GridView(expand=True, max_extent=190, child_aspect_ratio=1.25,
                       spacing=8, run_spacing=8, padding=4)

    def mark_selected():
        for key, frame in frames.items():
            selected = key == state["preset"]
            frame.border = ft.border.all(2 if selected else 1,
                                         COLORS["accent"] if selected else COLORS["border"])
            frame.bgcolor = COLORS["bg_hover"] if selected else COLORS["bg_card"]

    def select(key):
        state["preset"] = key
        if not state["y_pinned"]:
            state["y"] = _clamp(_preset_y(subs, effective_preset()), _Y_MIN, _Y_MAX)
            y_slider.value = state["y"]
            sync_slider_labels()
        mark_selected()
        schedule_preview(0.05)

    card_w, card_h = 170, 118

    def card(key, preset_id, name, description):
        exists = thumbs.has_thumb(preset_id, ctx)
        image = ft.Image(src=str(thumbs.card_path(preset_id, ctx)) if exists else None,
                         width=card_w, height=66, fit=ft.ImageFit.COVER,
                         border_radius=7, gapless_playback=True)
        spinner = ft.Container(width=card_w, height=66, alignment=ft.alignment.center,
                               visible=not exists,
                               content=ft.ProgressRing(width=20, height=20, stroke_width=2,
                                                       color=COLORS["accent"]))
        images[preset_id] = image
        spinners[preset_id] = spinner
        frame = ft.Container(
            width=card_w,
            height=card_h,
            border_radius=9,
            padding=5,
            ink=True,
            on_click=lambda _e, value=key: select(value),
            content=ft.Column([
                ft.Stack([image, spinner], width=card_w, height=66),
                ft.Text(name, size=11, weight=ft.FontWeight.BOLD, color=COLORS["text"],
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(description, size=9, color=COLORS["text_secondary"],
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=2, tight=True),
        )
        frames[key] = frame
        return frame

    auto_preset = subs.get_preset(auto_id) or presets[0]
    grid.controls.append(card("", auto_id, "✨ Tự động",
                              f"Theo phong cách · {auto_preset.get('name', auto_id)}"))
    for preset in presets:
        grid.controls.append(card(preset["id"], preset["id"],
                                  str(preset.get("name") or preset["id"]),
                                  str(preset.get("desc") or "")))

    def apply_thumb(preset_id, path):
        image = images.get(preset_id)
        spinner = spinners.get(preset_id)
        if image is not None and path:
            image.src = str(path)
            image.src_base64 = None
        if spinner is not None:
            spinner.visible = False
        update_page()

    def ensure_thumbs(force=False):
        cancel = state["thumb_cancel"]
        for preset in presets:
            if state["closed"] or cancel.is_set():
                return
            preset_id = preset["id"]
            if not force and thumbs.has_thumb(preset_id, ctx):
                apply_thumb(preset_id, thumbs.card_path(preset_id, ctx))
                continue
            apply_thumb(preset_id, thumbs.render_thumb(preset_id, ctx, force=force, cancel_check=cancel.is_set))

    def rerender_all(_=None):
        state["thumb_cancel"].set()
        state["thumb_cancel"] = threading.Event()
        for image in images.values():
            image.src = None
            image.src_base64 = None
        for spinner in spinners.values():
            spinner.visible = True
        update_page()
        threading.Thread(target=ensure_thumbs, kwargs={"force": True}, daemon=True).start()

    grid_wrap = ft.Container(content=grid, expand=True, opacity=1.0 if state["enabled"] else 0.45)

    def on_switch(event):
        state["enabled"] = bool(event.control.value)
        grid_wrap.opacity = 1.0 if state["enabled"] else 0.45
        schedule_preview(0.05)

    enabled_switch.on_change = on_switch
    sync_step_labels()
    sync_slider_labels()
    mark_selected()

    preview_panel = ft.Container(
        width=preview_w + 28,
        padding=10,
        border_radius=12,
        bgcolor="#000000",
        content=ft.Column([
            ft.Row([previous_button, step_label, next_button],
                   alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            ft.Stack([
                ft.Container(width=preview_w, height=preview_h, alignment=ft.alignment.center,
                             content=preview_image),
                ft.Container(width=preview_w, height=preview_h, alignment=ft.alignment.center,
                             content=preview_spinner),
            ], width=preview_w, height=preview_h),
            caption,
        ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    )

    controls_panel = ft.Container(
        width=590,
        height=preview_h + 64,
        padding=12,
        border=ft.border.all(1, COLORS["border"]),
        border_radius=12,
        content=ft.Column([
            ft.Row([enabled_switch, ft.Container(expand=True),
                    ft.TextButton("Render lại ảnh mẫu", icon=ft.Icons.REFRESH_ROUNDED,
                                  on_click=rerender_all)], spacing=8),
            ft.Row([
                ft.Column([scale_label, scale_slider], spacing=0, expand=True),
                ft.Column([y_label, y_slider], spacing=0, expand=True),
            ], spacing=16),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Text("Chọn kiểu phụ đề", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            grid_wrap,
        ], spacing=8, expand=True),
    )

    def cancel_workers():
        state["closed"] = True
        preview_cancel = state.get("preview_cancel")
        if preview_cancel is not None:
            preview_cancel.set()
        state["thumb_cancel"].set()
        pending = timer.get("value")
        if pending is not None:
            pending.cancel()

    def close(_=None):
        cancel_workers()
        page.close(dialog)

    def save(_=None):
        values = {
            "subtitle_enabled": bool(state["enabled"]),
            "subtitle_preset": state["preset"],
            "subtitle_font_scale": round(float(state["scale"]), 3),
            "subtitle_y_pct": round(float(state["y"]), 3),
        }
        project.update(values)
        result = project
        project_id = project.get("id")
        if project_id:
            from core.project_store import project_store
            result = project_store.update_project(project_id, **values) or project
        if on_saved:
            on_saved(result)
        close()
        page.open(ft.SnackBar(content=ft.Text("✅ Đã lưu cài đặt phụ đề.")))

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.SUBTITLES_ROUNDED, color=COLORS["accent"]),
                      ft.Text("Phụ đề cháy chữ", weight=ft.FontWeight.BOLD, color=COLORS["text"])],
                     spacing=10),
        content=ft.Container(
            width=preview_w + 650,
            height=preview_h + 84,
            content=ft.Row([preview_panel, controls_panel], spacing=16,
                           vertical_alignment=ft.CrossAxisAlignment.START),
        ),
        actions=[ft.TextButton("Huỷ", on_click=close),
                 ft.FilledButton("Lưu", icon=ft.Icons.SAVE_ROUNDED, on_click=save)],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda _e: cancel_workers(),
    )
    dialog.data = state
    page.open(dialog)
    schedule_preview(0.05)
    threading.Thread(target=ensure_thumbs, daemon=True).start()
    return dialog

def _clamp(v, lo, hi):
    return max(lo, min(hi, float(v)))

def _ratio(aspect: str) -> float:
    try:
        wr, hr = (int(x) for x in str(aspect).split(":"))
        return hr / wr
    except Exception:
        return 16 / 9

def _preset_y(subs, preset_id: str) -> float:
    p = subs.get_preset(preset_id) or {}
    try:
        return float((p.get("layout") or {}).get("yPct") or 0.82)
    except (TypeError, ValueError):
        return 0.82
