"""config.py — Đường dẫn, phiên bản và cấu hình chung của TubeCraft.

Mô hình giống t2login: BASE_DIR trỏ về nơi đặt .exe khi đóng gói (PyInstaller),
data/ nằm cạnh executable để dễ backup và không đụng Program Files.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

APP_NAME = "TubeCraft"
APP_VERSION = "0.1.61"
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


def _data_dir() -> Path:
    """Keep portable ``data`` by default; allow an explicit durable location."""
    override = os.environ.get("TUBECRAFT_DATA_DIR", "").strip()
    if not override:
        return BASE_DIR / "data"
    candidate = Path(override).expanduser()
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    return candidate.resolve()


DATA_DIR = _data_dir()
PROJECTS_DIR = DATA_DIR / "projects"

OUTPUTS_DIR = DATA_DIR / "outputs"; JOBS_DIR = DATA_DIR / "jobs"; GALLERY_DIR = DATA_DIR / "gallery"; LOGS_DIR = DATA_DIR / "logs"; SETTINGS_FILE = DATA_DIR / "settings.json"; KEYS_FILE = DATA_DIR / "keys.enc.json"; ENGINES_DIR = BASE_DIR / "engines"; TEMPLATE_CACHE_DIR = DATA_DIR / "template_packs"
def ensure_directories():
    for d in (PROJECTS_DIR, OUTPUTS_DIR, JOBS_DIR, GALLERY_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)

ensure_directories(); _DEFAULT_SETTINGS = {"lang": "vi", "theme": "dark", "tts_engine": "edge", "tts_voice": "vi-VN-HoaiMyNeural", "aspect_ratio": "9:16", "render_fps": 30, "render_workers": 0, "gpu_encoder": "auto", "ai_provider": "gemini", "ai_model": "", "subtitle_enabled": True, "subtitle_preset": "", "subtitle_font_scale": 1.0, "subtitle_y_pct": None}
def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    merged = dict(_DEFAULT_SETTINGS)
    merged.update(data if isinstance(data, dict) else {})
    return merged

def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".settings.", suffix=".tmp", dir=str(DATA_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, SETTINGS_FILE)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
