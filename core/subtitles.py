"""core/subtitles.py — Phụ đề (subtitle) cháy chữ: NGUỒN DỮ LIỆU DUY NHẤT.

Preset phụ đề nằm ở engines/subtitle_presets.json — file DỮ LIỆU THUẦN, KHÔNG
code, được ĐỌC BỞI CẢ HAI phía:
  • JS  : engines/subtitle_engine.js (vẽ trong canvas_renderer.js)
  • PY  : module này (UI chọn preset, dựng tham số truyền cho renderer)
Sửa preset = sửa MỘT file JSON, không phải sửa hai nơi rồi lệch nhau.

Module này lo 3 việc:
  1. Đọc/cache danh sách preset      → list_presets(), get_preset(id)
  2. Chọn preset mặc định theo phong cách hình ảnh → default_for_style()
     (nền tối dùng chữ trắng viền đen; nền SÁNG phải có hộp nền, không thì
      chữ trắng chìm hẳn vào nền giấy/pastel)
  3. Dựng payload + cờ CLI cho canvas_renderer.js → subtitle_config(),
     cli_args(). Đúng MỘT chỗ dựng cờ → preview và render thật không bao giờ
     lệch nhau (bài học từ --title-color: 5 chỗ dựng lệnh, sửa sót 1 là lệch).

TƯƠNG THÍCH NGƯỢC (quan trọng — đọc kỹ):
project.json ĐƯỢC GHI TRƯỚC khi có tính năng này thì KHÔNG có khoá
"subtitle_enabled". Những project đó phải render RA Y HỆT bản cũ → phụ đề TẮT.
Nếu để nó rơi về settings/_DEFAULTS (mặc định True) thì mở lại một bài học cũ
rồi render là tự nhiên chữ cháy đè lên video vốn không hề có phụ đề.

Vì vậy khoá "subtitle_enabled" là MỐC ĐÁNH DẤU:
  • project KHÔNG có khoá  → project ĐỜI CŨ → tắt, và settings toàn cục KHÔNG
    được phép bật hộ (xem has_subtitle_key / subtitle_config).
  • project CÓ khoá        → project đời mới (project_store.create_project luôn
    ghi subtitle_enabled=True, dialog phụ đề cũng ghi) → theo đúng giá trị đó.
Các khoá còn lại (preset/cỡ chữ/vị trí) vẫn rơi về settings như thường — chúng
chỉ đổi HÌNH DÁNG phụ đề, không bật/tắt nó.
"""
import json, logging, re
from pathlib import Path; logger = logging.getLogger("TubeCraft.Subtitles")
from config import ENGINES_DIR; PRESETS_FILE = Path(ENGINES_DIR) / "subtitle_presets.json"; ENABLED_KEY = "subtitle_enabled"; _DEFAULTS = {"subtitle_enabled": True, "subtitle_preset": "", "subtitle_font_scale": 1.0, "subtitle_y_pct": None, "subtitle_max_lines": None}; _STYLE_MAP = {"aurora": "paper_ink", "watercolor": "paper_ink", "sketch": "paper_ink", "sketchnote": "paper_ink", "inkwash": "paper_ink", "warmpaper": "paper_ink", "pastel": "bubble_box", "cartoon": "bubble_box", "cyberpunk": "neon_glow", "neonsketch": "neon_glow", "techdark": "tech_chip", "mathnoir": "minimal_mono", "default": "capcut_bold", "liquidglass": "capcut_bold", "pixel": "big_impact"}; _FALLBACK_PRESET = "capcut_bold"; _AUTO_LABELS = {"Tự động theo phong cách", "🤖 Tự động theo phong cách"}; _cache = {"mtime": None, "data": None}

def normalize_preset_id(value) -> str:
    preset = str(value or "").strip()
    return "" if preset in _AUTO_LABELS else preset
def _load() -> dict:
    try:
        mtime = PRESETS_FILE.stat().st_mtime
        if _cache["mtime"] == mtime and _cache["data"] is not None:
            return _cache["data"]
        with open(PRESETS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("presets"), list):
            raise ValueError("thiếu mảng 'presets'")
        _cache["mtime"] = mtime
        _cache["data"] = data
        return data
    except OSError:
        logger.warning(f"Không thấy {PRESETS_FILE} — phụ đề sẽ không có preset.")
        return {"version": 0, "presets": []}
    except Exception as e:
        logger.error(f"subtitle_presets.json hỏng: {e}")
        return {"version": 0, "presets": []}

def list_presets() -> list:
    return [p for p in _load().get("presets", []) if isinstance(p, dict) and p.get("id")]

def preset_options() -> list:
    out = []
    for p in list_presets():
        desc = (p.get("desc") or "").strip()
        label = p.get("name") or p["id"]
        out.append((p["id"], f"{label} — {desc}" if desc else label))
    return out

def get_preset(preset_id: str):
    if not preset_id:
        return None
    for p in list_presets():
        if p.get("id") == preset_id:
            return p
    return None

def default_for_style(art_style: str) -> str:
    presets = list_presets()
    if not presets:
        return ""
    ids = {p["id"] for p in presets}
    for candidate in (_STYLE_MAP.get((art_style or "").strip().lower()), _FALLBACK_PRESET):
        if not candidate:
            continue
        if candidate in ids:
            return candidate
    return presets[0]["id"]

def _settings() -> dict:
    try:
        from config import load_settings
        return load_settings()
    except Exception:
        return {}

def _as_bool(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() not in ("", "0", "false", "off", "no", "none")
    
    return bool(v)

def _as_float(v, default: float) -> float:
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return default

def has_subtitle_key(project: dict) -> bool:
    return isinstance(project, dict) and ENABLED_KEY in project

def subtitle_config(project: dict, settings: dict=None) -> dict:
    project = project if isinstance(project, dict) else {}
    if settings is None:
        settings = _settings()
    settings = settings if isinstance(settings, dict) else {}

    def pick(key):
        for src in (project, settings):
            if src.get(key) is not None:
                return src[key]
        return _DEFAULTS[key]

    enabled = _as_bool(pick(ENABLED_KEY)) if has_subtitle_key(project) else False
    
    preset = normalize_preset_id(pick("subtitle_preset"))
    
    if preset and get_preset(preset) is None:
        logger.warning(f"Preset phụ đề '{preset}' không tồn tại → dùng mặc định.")
        preset = ""
    if not preset:
        preset = default_for_style(project.get("art_style", "default"))
    if not preset:
        enabled = False
    
    scale = min(2.0, max(0.6, _as_float(pick("subtitle_font_scale"), 1.0))); y_raw = pick("subtitle_y_pct"); y_pct = None
    if y_raw is not None and str(y_raw).strip() != "":
        y_pct = min(0.9, max(0.3, _as_float(y_raw, 0.82)))
    
    ml_raw = pick("subtitle_max_lines"); max_lines = None
    if ml_raw is not None and str(ml_raw).strip() != "":
        try:
            max_lines = min(4, max(1, int(ml_raw)))
        except (TypeError, ValueError):
            max_lines = None

    accent = project.get("subtitle_accent")
    if not accent and project.get("template"):
        try:
            from core.templates import get_template
            accent = (get_template(project["template"]) or {}).get("subtitle_accent")
        except Exception:
            accent = None
    accent = str(accent).strip() if accent else ""
    if not re.fullmatch("#[0-9a-fA-F]{6}", accent):
        accent = ""
    return {
        "enabled": enabled,
        "preset": preset,
        "fontScale": round(scale, 3),
        "yPct": y_pct,
        "maxLines": max_lines,
        "accent": accent or None,
    }

def to_json(cfg: dict) -> str:
    return json.dumps(cfg, ensure_ascii=False, separators=(",", ":"))

def cli_args(project: dict, settings: dict=None) -> list:
    cfg = subtitle_config(project, settings)
    if not cfg.get("enabled"):
        return []
    
    return ["--subtitle", to_json(cfg)]

def env_vars(project: dict, settings: dict=None) -> dict:
    cfg = subtitle_config(project, settings)
    if not cfg.get("enabled"):
        return {}
    
    return {"TUBECRAFT_SUBTITLE": to_json(cfg)}
