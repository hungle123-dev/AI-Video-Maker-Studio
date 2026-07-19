"""core/templates.py — Hệ thống TEMPLATE MẪU (font + màu + style + background).

Mỗi template gói sẵn một "combo trình bày" đã phối đẹp:
  - art_style   → nền (bgGrad) + bảng màu + font gốc của phong cách
  - title_color → màu tiêu đề (override, để "" = theo phong cách)
  - text_color  → màu chữ thân (override)
  - font_family → font chữ (override; "" = font của phong cách)

Renderer (engines/canvas_renderer.js) đã hỗ trợ đủ 4 tham số này nên template
chỉ là preset — không cần thêm logic vẽ. Dùng cho: dialog tạo project /
autopilot (chọn 1 template là xong), và nút "Xem trước template".
"""
import json
import os
import tempfile
from pathlib import Path

from config import BASE_DIR
from core.effects_catalog import EFFECTS

# Bundled examples are immutable assets.  Generated/overridden thumbnails are
# cache data and must not be written into the app tree (portable releases may
# be read-only and moving them must retain user state).
_BUNDLED_THUMB_DIR = Path(BASE_DIR) / "samples" / "templates"

TEMPLATES = [{"id": "lux_finance", "name": "Tài Chính Vàng", "emoji": "💰", "desc": "Kiếm tiền, đầu tư, kinh doanh, làm giàu", "vibe": "Nền kính mờ tối sang trọng, số liệu vàng gold nổi bật", "art_style": "liquidglass", "title_color": "#FFD700", "text_color": "", "font_family": "", "effect": "counter_metric", "topic": "Tự Do Tài Chính"},
    {"id": "neon_tech", "name": "Công Nghệ Neon", "emoji": "🤖", "desc": "Công nghệ, AI, lập trình, crypto, gadget", "vibe": "Nền tối, chữ neon cyan/hồng, font Orbitron tương lai", "art_style": "cyberpunk", "title_color": "", "text_color": "", "font_family": "", "effect": "flow_pipeline", "topic": "Sức Mạnh Của AI"},
    {"id": "warm_edu", "name": "Giáo Dục Ấm", "emoji": "📚", "desc": "Kỹ năng, học thuật, phát triển bản thân", "vibe": "Giấy màu nước ấm, chữ serif cổ điển, dịu mắt", "art_style": "watercolor", "title_color": "", "text_color": "", "font_family": "Cambria", "effect": "step_reveal_list", "topic": "Học Nhanh Nhớ Lâu"},
    {"id": "kids_fun", "name": "Trẻ Em Vui Nhộn", "emoji": "🎈", "desc": "Trẻ em, mầm non, hoạt hình, giải trí nhẹ", "vibe": "Vàng–đỏ tươi, chữ Fredoka bo tròn, halftone vui", "art_style": "cartoon", "title_color": "", "text_color": "", "font_family": "", "effect": "orbit_ecosystem", "topic": "Vui Học Mỗi Ngày"},
    {"id": "clean_biz", "name": "Doanh Nghiệp Sạch", "emoji": "📊", "desc": "Marketing, khởi nghiệp, chuyên môn, thuyết trình", "vibe": "Nền giấy sáng, ghi chú xanh dương, gọn chuyên nghiệp", "art_style": "sketchnote", "title_color": "", "text_color": "", "font_family": "", "effect": "bar_compare", "topic": "Tăng Trưởng Doanh Số"},
    {"id": "calm_wellness", "name": "Thư Giãn Pastel", "emoji": "🌸", "desc": "Sức khoẻ, thiền, lifestyle, tâm lý", "vibe": "Pastel hồng–tím dịu nhẹ, nhẹ nhàng thư thái", "art_style": "pastel", "title_color": "", "text_color": "", "font_family": "", "effect": "growth_curve", "topic": "Chữa Lành Mỗi Ngày"},
    {"id": "ink_tradition", "name": "Mực Tàu Cổ", "emoji": "🖌️", "desc": "Lịch sử, văn hoá, triết lý, cổ phong", "vibe": "Nền giấy dó, mực tàu đen, nét thư pháp trầm mặc", "art_style": "inkwash", "title_color": "", "text_color": "", "font_family": "Times New Roman", "effect": "gauge_dial", "topic": "Trí Tuệ Cổ Nhân"},
    {"id": "retro_game", "name": "Retro Pixel", "emoji": "👾", "desc": "Game, Gen-Z, giải trí, nostalgia 8-bit", "vibe": "Nền tối pixel, neon cyan/hồng, chất 8-bit retro", "art_style": "pixel", "title_color": "", "text_color": "", "font_family": "", "effect": "leak_bucket", "topic": "Level Up Kỹ Năng"},
    {"id": "midnight_pro", "name": "Tối Gradient Chuẩn", "emoji": "🌌", "desc": "Đa dụng, an toàn cho mọi chủ đề", "vibe": "Nền tím than gradient, chữ trắng, cân bằng dễ đọc", "art_style": "default", "title_color": "", "text_color": "", "font_family": "", "effect": "quote_card", "topic": "Bí Quyết Thành Công"},
    {"id": "health_green", "name": "Sức Khoẻ Xanh", "emoji": "🥗", "desc": "Gym, dinh dưỡng, sống khoẻ, thể thao", "vibe": "Kính mờ tối, tiêu đề xanh lá tươi, cảm giác khoẻ khoắn", "art_style": "liquidglass", "title_color": "#22c55e", "text_color": "", "font_family": "", "effect": "donut_percent", "topic": "Sống Khoẻ Mỗi Ngày"},
    {"id": "news_hot", "name": "Bản Tin Nóng", "emoji": "📰", "desc": "Tin tức, thời sự, bản tin nhanh", "vibe": "Nền tối, tiêu đề đỏ dứt khoát, cảm giác khẩn cấp", "art_style": "default", "title_color": "#ef4444", "text_color": "", "font_family": "", "effect": "timeline_road", "topic": "Tin Nóng Trong Ngày"},
    {"id": "science_blue", "name": "Khoa Học Xanh Dương", "emoji": "🔬", "desc": "Khoa học, STEM, giải thích, tri thức", "vibe": "Nền tối, tiêu đề cyan, mạch lạc – học thuật", "art_style": "default", "title_color": "#22d3ee", "text_color": "", "font_family": "", "effect": "icon_grid", "topic": "Khám Phá Khoa Học"},
    {"id": "beauty_purple", "name": "Làm Đẹp Tím", "emoji": "💄", "desc": "Làm đẹp, thời trang, mỹ phẩm, lifestyle", "vibe": "Kính mờ tối, tiêu đề tím sang, nữ tính hiện đại", "art_style": "liquidglass", "title_color": "#a855f7", "text_color": "", "font_family": "", "effect": "star_rating", "topic": "Bí Quyết Làm Đẹp"},
    {"id": "food_orange", "name": "Ẩm Thực Cam", "emoji": "🍜", "desc": "Nấu ăn, công thức, review món ngon", "vibe": "Kính mờ tối, tiêu đề cam ấm, kích thích vị giác", "art_style": "liquidglass", "title_color": "#f97316", "text_color": "", "font_family": "", "effect": "flat_stat", "topic": "Công Thức Món Ngon"},
    {"id": "whiteboard", "name": "Bảng Trắng", "emoji": "🧑‍🏫", "desc": "Giảng bài, explainer, whiteboard, tư duy", "vibe": "Nền trắng phác thảo tay, gần gũi như dạy trên bảng", "art_style": "sketch", "title_color": "", "text_color": "", "font_family": "", "effect": "step_reveal_list", "topic": "Giảng Bài Dễ Hiểu"},
    {"id": "dev_code", "name": "Lập Trình Dev", "emoji": "💻", "desc": "Lập trình, tutorial code, tech tip", "vibe": "Cửa sổ editor gõ code từng ký tự, chuẩn dân dev", "art_style": "default", "title_color": "#22d3ee", "text_color": "", "font_family": "", "effect": "code_typing", "topic": "Học Code Cấp Tốc"},
    {"id": "series_course", "name": "Khoá Học Series", "emoji": "🎓", "desc": "Series nhiều tập, khoá học có lộ trình", "vibe": "Vòng số tập + cung tiến độ, nhất quán cả series", "art_style": "default", "title_color": "#FFD700", "text_color": "", "font_family": "", "effect": "episode_ring", "topic": "Khoá Học 10 Tập"},
    {"id": "review_scan", "name": "Review Sản Phẩm", "emoji": "🛍️", "desc": "Review, unbox, so sánh giá, mua sắm", "vibe": "Laser quét sản phẩm bật thẻ giá, vibe mua sắm", "art_style": "liquidglass", "title_color": "#f97316", "text_color": "", "font_family": "", "effect": "laser_scan", "topic": "Đáng Tiền Không?"},
    {"id": "ai_assistant", "name": "Trợ Lý AI", "emoji": "🧠", "desc": "AI, chatbot, công cụ thông minh, automation", "vibe": "Não neuron phát token vào bubble chat, rất AI", "art_style": "default", "title_color": "#22d3ee", "text_color": "", "font_family": "", "effect": "neuro_stream", "topic": "AI Làm Được Gì?"},
    {"id": "app_maker", "name": "Xây App", "emoji": "📲", "desc": "Làm app, no-code, sản phẩm số, indie hacker", "vibe": "Máy đóng gói file thành app hoàn chỉnh, chất builder", "art_style": "default", "title_color": "#22c55e", "text_color": "", "font_family": "", "effect": "forge_apk", "topic": "Tự Tay Làm App"},
    {"id": "mobile_ui", "name": "UI Điện Thoại", "emoji": "📱", "desc": "UX/UI, app mobile, thiết kế giao diện", "vibe": "Điện thoại neon tự dựng giao diện, icon bay quanh", "art_style": "liquidglass", "title_color": "#22d3ee", "text_color": "", "font_family": "", "effect": "phone_hero", "topic": "Thiết Kế App Đẹp"}]; _BY_ID = {t["id"]: t for t in TEMPLATES}; DEFAULT_TEMPLATE = "lux_finance"; EDITABLE = ("name", "art_style", "title_color", "text_color", "font_family", "effect", "topic"); STYLE_OPTIONS = [("liquidglass", "🪟 Liquid Glass — kính mờ sang"), ("default", "🌌 Gradient tối tím"), ("cyberpunk", "🌃 Cyberpunk neon"), ("aurora", "🌤 Aurora sáng"), ("watercolor", "🎨 Màu nước ấm"), ("inkwash", "🖌 Mực tàu"), ("pastel", "🌸 Pastel dịu"), ("cartoon", "😄 Cartoon halftone"), ("sketch", "✏️ Sketch phác thảo"), ("sketchnote", "📝 Sketchnote ghi chú"), ("pixel", "👾 Pixel 8-bit"), ("neonsketch", "✨ Neon Doodle"), ("techdark", "🔬 Tech Decode"), ("mathnoir", "➗ Math Noir"), ("warmpaper", "📜 Paper Brief")]; TITLE_COLOR_OPTIONS = [("", "Theo phong cách"), ("#FFD700", "🟡 Vàng gold"), ("#22d3ee", "🔵 Cyan"), ("#22c55e", "🟢 Xanh lá"), ("#f97316", "🟠 Cam"), ("#ec4899", "🌸 Hồng"), ("#ef4444", "🔴 Đỏ"), ("#a855f7", "🟣 Tím"), ("#ffffff", "⚪ Trắng")]; FONT_OPTIONS = [("", "Theo phong cách"), ("Arial", "Arial"), ("Verdana", "Verdana"), ("Tahoma", "Tahoma"), ("Trebuchet MS", "Trebuchet MS"), ("Georgia", "Georgia (serif)"), ("Times New Roman", "Times New Roman (serif)"), ("Impact", "Impact (đậm)"), ("Comic Sans MS", "Comic Sans (vui)")]; EFFECT_OPTIONS = [(e["name"], f"{e["name"]} — {e["when"][:40]}") for e in EFFECTS]

# All pack definitions and their preview assets ship with the reconstructed
# repository, so they are first-class local templates instead of paid stubs.
from pack_templates import PACKS as _BUNDLED_PACKS

_known_template_ids = set(_BY_ID)
for _pack in _BUNDLED_PACKS:
    for _definition in (_pack.get("defs") or {}).values():
        _template = dict(_definition)
        if _template.get("id") in _known_template_ids:
            continue
        _template["_pack"] = _pack.get("pack_id", "")
        TEMPLATES.append(_template)
        _known_template_ids.add(_template["id"])
_BY_ID = {template["id"]: template for template in TEMPLATES}
_MANUAL_LABELS = {"✋ Tuỳ chỉnh thủ công", "— Không —"}


def normalize_id(value) -> str:
    template_id = str(value or "").strip()
    if template_id in _MANUAL_LABELS:
        return ""
    return template_id if template_id in _BY_ID else ""


def style_options():
    return list(STYLE_OPTIONS)


def normalize_style(value) -> str:
    style = str(value or "").strip()
    return style if style in {item[0] for item in STYLE_OPTIONS} else "default"

# Pack publishing appends the scene catalog to ``ai_hint``.  The desktop app
# imports the bundled definitions directly, so do the same enrichment here at
# runtime; otherwise an AI sees the catalog heading but not the parameter
# schema and invents React-like props that a canvas scene cannot render.
from core.custom_scenes import td_prompt_doc as _scene_prompt_doc

for _template in TEMPLATES:
    if not _template.get("scene_first"):
        continue
    # The original Tech Decode pack omitted these two fields in its raw
    # definition.  They are required by the scene-first script contract.
    if _template.get("id") == "tech_explainer":
        _template.setdefault("scene_prefix", "td_")
        _template.setdefault("chrome_scene", "td_chrome")
    _catalog = _scene_prompt_doc(_template.get("scene_prefix") or "td_")
    _hint = str(_template.get("ai_hint") or "")
    if _catalog and _catalog not in _hint:
        _template["ai_hint"] = _hint + _catalog

def _store_path() -> Path:
    from config import DATA_DIR
    return Path(DATA_DIR) / "templates.json"


def _thumb_cache_dir() -> Path:
    from config import DATA_DIR

    return Path(DATA_DIR) / "template_thumbs"

def _load_store() -> dict:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_store(d: dict) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".templates.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(d if isinstance(d, dict) else {}, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass

def get_template(tid: str) -> dict:
    base = _BY_ID.get(normalize_id(tid)) or _BY_ID[DEFAULT_TEMPLATE]
    base = dict(base)
    ov = _load_store().get(tid)
    if isinstance(ov, dict):
        base.update({k: v for k, v in ov.items() if k in EDITABLE})
    return base

def list_templates() -> list:
    return [get_template(template["id"]) for template in TEMPLATES]

def is_customized(tid: str) -> bool:
    return bool(_load_store().get(tid))

def update_template(tid: str, **fields) -> dict:
    store = _load_store(); cur = dict(store.get(tid, {}))
    for k, v in fields.items():
        if not k in EDITABLE:
            continue
        cur[k] = v
    
    store[tid] = cur
    
    _save_store(store)
    return get_template(tid)

def reset_template(tid: str) -> dict:
    store = _load_store(); store.pop(tid, None); _save_store(store)
    return get_template(tid)

def template_options():
    return [(t["id"], f"{t["emoji"]} {t["name"]} — {t["desc"]}") for t in list_templates()]

def apply_to_project(project: dict, tid: str) -> dict:
    t = get_template(tid)
    project["template"] = t["id"]; project["art_style"] = t["art_style"]; project["title_color"] = t["title_color"]; project["text_color"] = t["text_color"]; project["font_family"] = t["font_family"]; return project

def render_params(tid: str) -> dict:
    t = get_template(tid)
    return {"art_style": t["art_style"], "title_color": t["title_color"], "text_color": t["text_color"], "font_family": t["font_family"]}

def _effect(name: str) -> str:
    for e in EFFECTS:
        if e["name"] == name:
            return e["code"]
    return EFFECTS[0]["code"]

ASPECTS = ["9:16", "16:9", "1:1"]
def _aspect_suffix(aspect: str) -> str:
    return {"9:16": "", "16:9": "_16x9", "1:1": "_1x1"}.get(aspect, "_" + aspect.replace(":", "x"))

def _cache_thumb_path(tid: str, aspect: str="9:16") -> Path:
    return _thumb_cache_dir() / f"{tid}{_aspect_suffix(aspect)}.png"


def _bundled_thumb_path(tid: str, aspect: str="9:16") -> Path:
    return _BUNDLED_THUMB_DIR / f"{tid}{_aspect_suffix(aspect)}.png"


def thumb_path(tid: str, aspect: str="9:16") -> Path:
    cache = _cache_thumb_path(tid, aspect)
    if cache.is_file() and cache.stat().st_size > 0:
        return cache
    bundled = _bundled_thumb_path(tid, aspect)
    if not is_customized(tid) and bundled.is_file() and bundled.stat().st_size > 0:
        return bundled
    return cache

def has_thumb(tid: str, aspect: str="9:16") -> bool:
    p = thumb_path(tid, aspect)
    return p.is_file() and p.stat().st_size > 0

def clear_thumbs(tid: str) -> None:
    try:
        for a in ASPECTS:
            _cache_thumb_path(tid, a).unlink(missing_ok=True)
    except Exception:
        pass

def render_thumbnail(tid: str, aspect: str="9:16", force: bool=False):
    p = _cache_thumb_path(tid, aspect)
    if p.exists() and p.stat().st_size > 0 and not force:
        return str(p)
    bundled = _bundled_thumb_path(tid, aspect)
    if not force and not is_customized(tid) and bundled.is_file() and bundled.stat().st_size > 0:
        return str(bundled)
    from core import preview_demo
    p.parent.mkdir(parents=True, exist_ok=True)
    return preview_demo.render_preview_png(tid, str(p), aspect)

def hero_script(topic: str, effect: str="counter_metric") -> dict:
    return {"title": topic, "description": "Mẫu template", "subject": "general", "total_steps": 1, "steps": [{"id": 1, "clear": True, "voice_text": "Đây là hình minh hoạ phong cách trình bày của mẫu.", "elements": [{"type": "text", "text": topic, "fontSize": 54, "color": "title", "align": "center", "bold": True},
    {"type": "custom_js", "template": effect, "params": {}, "x_9_16": 0.5, "y_9_16": 0.54, "x_16_9": 0.5, "y_16_9": 0.42, "fontSize": 50}]}]}

def demo_script(topic: str="Làm Chủ Chủ Đề Của Bạn") -> dict:
    return {"title": topic, "description": "Video mẫu minh hoạ template", "subject": "general", "total_steps": 4, "steps": [{"id": 1, "clear": True, "voice_text": "Chỉ với ba bước đơn giản, bạn có thể tăng kết quả lên tới một trăm phần trăm.", "elements": [{"type": "text", "text": topic, "fontSize": 54, "color": "title", "align": "center", "bold": True},
    {"type": "text", "text": "Tăng trưởng thấy rõ sau mỗi tập", "fontSize": 30, "color": "highlight", "align": "center"},
    {"type": "custom_js", "height": 520, "code": _effect("counter_metric"), "x_9_16": 0.5, "y_9_16": 0.5, "fontSize": 50}]},
    {"id": 2, "clear": True, "voice_text": "So với cách làm cũ, phương pháp mới cho hiệu quả vượt trội và tiết kiệm thời gian.", "elements": [{"type": "text", "text": "Cũ và Mới — Khác Biệt Rõ Rệt", "fontSize": 48, "color": "highlight", "align": "center", "bold": True},
    {"type": "custom_js", "height": 540, "code": _effect("bar_compare"), "x_9_16": 0.5, "y_9_16": 0.5, "fontSize": 50}]},
    {"id": 3, "clear": True, "voice_text": "Bốn bước cốt lõi giúp bạn đi từ mục tiêu tới kết quả một cách nhất quán.", "elements": [{"type": "text", "text": "Lộ Trình Bốn Bước", "fontSize": 50, "color": "title", "align": "center", "bold": True},
    {"type": "custom_js", "height": 560, "code": _effect("step_reveal_list"), "x_9_16": 0.5, "y_9_16": 0.5, "fontSize": 50}]},
    {"id": 4, "clear": True, "voice_text": "Tổng kết lại, hãy ghi nhớ ba điều quan trọng nhất để áp dụng ngay hôm nay.", "elements": [{"type": "box", "style": "result"},
    {"type": "text", "text": "Tổng Kết Toàn Tập", "fontSize": 50, "color": "highlight", "align": "center", "bold": True},
    {"type": "list", "items": ["✅ Bắt đầu với mục tiêu rõ ràng", "✅ Chọn đúng phương pháp hiệu quả", "✅ Thực thi và đo lường mỗi ngày"], "bullet": "", "fontSize": 30, "color": "green"}]}]}
