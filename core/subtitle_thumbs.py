"""core/subtitle_thumbs.py — Ảnh mẫu cho từng preset phụ đề (frame RENDER THẬT).

Thẻ chọn preset phải cho thấy ĐÚNG cái sẽ ra trong video, nên ảnh mẫu không vẽ
bằng Flet mà chạy hẳn engines/canvas_renderer.js (qua core/preview) rồi CẮT dải
quanh vùng phụ đề — nhìn thẻ nhỏ vẫn đọc được chữ.

Cache giống hệt core/templates.py (has_thumb / thumb_path / render_thumb):
  data/subtitle_thumbs/<preset>__<key>.png        frame đầy đủ
  data/subtitle_thumbs/<preset>__<key>_card.png   dải đã cắt (ảnh cho thẻ)
<key> băm từ NGỮ CẢNH ẢNH HƯỞNG TỚI HÌNH: tỉ lệ khung, phong cách, nền, câu
thoại mẫu. Đổi phong cách → key khác → tự render lại, không phải nhớ xoá cache.

Thẻ luôn dùng cỡ chữ & vị trí MẶC ĐỊNH của preset (fontScale 1.0, yPct của
preset): thẻ để so sánh "chất" preset với nhau. Cỡ/vị trí người dùng kéo được
xem ở khung preview lớn (render riêng, không đụng cache này).
"""
import hashlib, logging, time
from pathlib import Path; logger = logging.getLogger("TubeCraft.SubThumbs")
from config import DATA_DIR; THUMB_DIR = Path(DATA_DIR) / "subtitle_thumbs"; BAND_TOP, BAND_BOT = (0.6, 0.94); CARD_PX = 560; _SAMPLE_FALLBACK = "Mỗi ngày một thói quen nhỏ, một năm sau bạn sẽ thành một con người hoàn toàn khác."; _MAX_SAMPLE = 110; _CACHE_MAX_FILES = 160; _CACHE_MAX_AGE_SECONDS = 14 * 24 * 60 * 60
def sample_text(script: dict=None) -> str:
    for s in (script or {}).get("steps", []) or []:
        t = " ".join((s.get("voice_text") or "").split())
        if len(t) >= 30:
            return _trim(t)
    return _SAMPLE_FALLBACK

def _trim(t: str) -> str:
    if len(t) <= _MAX_SAMPLE:
        return t
    cut = t[:_MAX_SAMPLE]
    for sep in (". ", ", ", " "):
        i = cut.rfind(sep)
        if i > 40:
            return cut[:i + (1 if sep == ". " else 0)].strip(" ,")
    return cut.strip()

def context(project: dict, script: dict=None) -> dict:
    p = project or {}
    # Thumbnail cards are cached on disk.  They should demonstrate style and
    # subtitle timing, not retain a project title or narration after the
    # dialog is closed; the full left-hand preview remains temporary.
    return {"aspect": p.get("aspect_ratio") or "9:16", "art_style": p.get("art_style") or "default", "bg": p.get("bg") or "", "theme": p.get("theme") or "dark", "title_color": p.get("title_color") or "", "text_color": p.get("text_color") or "", "font_family": p.get("font_family") or "", "title": "Xem trước phụ đề", "text": _SAMPLE_FALLBACK}

def card_style(preset: dict) -> dict:
    font = preset.get("font") or {}
    layout = preset.get("layout") or {}
    try:
        y = float(layout.get("yPct") or 0.82)
    except (TypeError, ValueError):
        y = 0.82
    try:
        ml = int(font.get("maxLines") or 2)
    except (TypeError, ValueError):
        ml = 2
    return {"font_scale": 1.0, "y_pct": round(y, 3), "max_lines": max(1, min(4, ml))}

def _key(preset_id: str, ctx: dict) -> str:
    from core.subtitles import get_preset
    st = card_style(get_preset(preset_id) or {})
    raw = "|".join([preset_id, ctx["aspect"], ctx["art_style"], ctx["bg"], ctx["theme"], ctx["title_color"], ctx["text_color"], ctx["font_family"], ctx["text"], f'{st["font_scale"]}', f'{st["y_pct"]}', f'{st["max_lines"]}'])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]

def thumb_path(preset_id: str, ctx: dict) -> Path:
    return THUMB_DIR / f"{preset_id}__{_key(preset_id, ctx)}.png"

def card_path(preset_id: str, ctx: dict) -> Path:
    p = thumb_path(preset_id, ctx)
    return p.with_name((p.stem) + "_card.png")

def has_thumb(preset_id: str, ctx: dict) -> bool:
    p = card_path(preset_id, ctx)
    return p.exists() and p.stat().st_size > 0

def band_ratio(aspect: str) -> float:
    try:
        wr, hr = (int(x) for x in str(aspect).split(":"))
        return (BAND_BOT - BAND_TOP) * hr / wr
    except Exception:
        return (BAND_BOT - BAND_TOP) * 16 / 9

def _script(ctx: dict) -> dict:
    title = ctx.get("title") or "Xem trước phụ đề"
    return {"title": title, "description": "Mẫu phụ đề", "subject": "general", "total_steps": 1, "steps": [{"id": 1, "clear": True, "voice_text": ctx["text"], "elements": [{"type": "text", "text": title, "fontSize": 46, "color": "title", "align": "center", "bold": True}]}]}

def _timing(ctx: dict) -> dict:
    dur = max(len(ctx["text"]) * 0.06, 3.0)
    return {"steps": [{"id": 1, "start": 0.0, "end": round(dur, 3), "duration": round(dur, 3), "audio": "", "words": []}], "total_duration": round(dur, 3), "merged_audio": None}

def demo_script(ctx: dict) -> dict:
    return _script(ctx)

def demo_timing(ctx: dict) -> dict:
    return _timing(ctx)

def _params(preset_id: str, ctx: dict, preset: dict) -> dict:
    st = card_style(preset)
    return {"theme": ctx["theme"], "aspect_ratio": ctx["aspect"], "art_style": ctx["art_style"], "bg": ctx["bg"], "title_color": ctx["title_color"], "text_color": ctx["text_color"], "font_family": ctx["font_family"], "subtitle_enabled": True, "subtitle_preset": preset_id, "subtitle_font_scale": st["font_scale"], "subtitle_y_pct": st["y_pct"], "subtitle_max_lines": st["max_lines"]}

def _crop_card(full_png: Path) -> str:
    try:
        from PIL import Image
    except Exception:
        return str(full_png)
    try:
        with Image.open(full_png) as im:
            W, H = im.size
            band = im.crop((0, int(H * BAND_TOP), W, int(H * BAND_BOT)))
            if band.width > CARD_PX:
                h = max(1, round((band.height) * CARD_PX / (band.width)))
                band = band.resize((CARD_PX, h), Image.LANCZOS)
            out = full_png.with_name((full_png.stem) + "_card.png")
            band.convert("RGB").save(out, "PNG")
        full_png.unlink(missing_ok=True)
        return str(out)
    except Exception as e:
        logger.warning(f"Cắt dải phụ đề lỗi: {e}")
        return str(full_png)

def _prune_cache() -> None:
    try:
        if not THUMB_DIR.is_dir():
            return
        now = time.time()
        for file in THUMB_DIR.glob("*.png"):
            if now - file.stat().st_mtime > _CACHE_MAX_AGE_SECONDS:
                file.unlink(missing_ok=True)
        files = sorted(THUMB_DIR.glob("*.png"), key=lambda file: file.stat().st_mtime, reverse=True)
        for file in files[_CACHE_MAX_FILES:]:
            file.unlink(missing_ok=True)
    except OSError:
        pass


def render_thumb(preset_id: str, ctx: dict, force: bool=False, cancel_check=None):
    card = card_path(preset_id, ctx)
    if not force and card.exists() and card.stat().st_size > 0:
        return str(card)
    if cancel_check and cancel_check():
        return None
    from core.subtitles import get_preset; preset = get_preset(preset_id)
    if not preset:
        logger.warning(f"Không có preset phụ đề '{preset_id}'.")
        return None
    THUMB_DIR.mkdir(parents=True, exist_ok=True); _prune_cache(); full = thumb_path(preset_id, ctx); tm = _timing(ctx); t = tm["steps"][0]["duration"] * 0.32
    from core.preview import render_time_preview
    
    res = render_time_preview(_params(preset_id, ctx, preset), _script(ctx), t, str(full), timing=tm, cancel_check=cancel_check)
    if not res.get("ok"):
        full.unlink(missing_ok=True)
        logger.warning(f"Render thẻ phụ đề '{preset_id}' lỗi: {res.get("error")}")
        return None
    return _crop_card(full)

def clear_cache() -> int:
    n = 0
    if not THUMB_DIR.is_dir():
        return 0
    for f in THUMB_DIR.glob("*.png"):
        try:
            f.unlink()
            n += 1
        except OSError:
            continue
    return n
