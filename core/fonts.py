"""User-font catalog for the portable TubeCraft runtime.

Mutable fonts belong to ``DATA_DIR``.  Keeping them beside the executable made
portable installs fragile (and failed outright in read-only locations), while
absolute paths in the manifest broke as soon as the app was moved.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from config import BASE_DIR, DATA_DIR


# ``STATIC_DIR`` remains a read-only asset location for older callers.  New
# user-provided files must always be stored below DATA_DIR instead.
STATIC_DIR = Path(BASE_DIR) / "static"
FONTS_DIR = Path(DATA_DIR) / "fonts"
_MAX_FONT_BYTES = 64 * 1024 * 1024
_VN_TEST = [7871, 7897, 7919, 417, 432, 273, 7841, 7879, 7857, 7895]
BUILTIN_FONTS = [
    ("", "Theo phong cách", True),
    ("Segoe UI", "Segoe UI (khuyên dùng)", True),
    ("Arial", "Arial", True),
    ("Tahoma", "Tahoma", True),
    ("Verdana", "Verdana", True),
    ("Calibri", "Calibri", True),
    ("Trebuchet MS", "Trebuchet MS", True),
    ("Georgia", "Georgia (serif)", True),
    ("Times New Roman", "Times New Roman (serif)", True),
    ("Comic Sans MS", "Comic Sans (vui)", True),
    ("Cambria", "Cambria (serif)", True),
    ("Impact", "Impact (đậm)", False),
    ("Courier New", "Courier New (mono)", True),
]
_WIN_FONT_FILES = {
    "Segoe UI": "segoeui.ttf",
    "Arial": "arial.ttf",
    "Tahoma": "tahoma.ttf",
    "Verdana": "verdana.ttf",
    "Calibri": "calibri.ttf",
    "Trebuchet MS": "trebuc.ttf",
    "Georgia": "georgia.ttf",
    "Times New Roman": "times.ttf",
    "Comic Sans MS": "comic.ttf",
    "Cambria": "cambria.ttc",
    "Impact": "impact.ttf",
    "Courier New": "cour.ttf",
}
_vn_cache: dict[str, bool] = {}


def _win_fonts_dir() -> Path:
    return Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"


def _builtin_vn(family: str, default: bool) -> bool:
    if not family:
        return default
    if family in _vn_cache:
        return _vn_cache[family]
    vietnamese = default
    filename = _WIN_FONT_FILES.get(family)
    if filename:
        candidate = _win_fonts_dir() / filename
        if candidate.exists():
            try:
                vietnamese = probe_font(str(candidate))["vietnamese"]
            except Exception:
                pass
    _vn_cache[family] = vietnamese
    return vietnamese


def _manifest_path() -> Path:
    return Path(DATA_DIR) / "fonts.json"


def _font_dir() -> Path:
    return Path(FONTS_DIR)


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _atomic_json_write(path: Path, payload: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".fonts.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _require_font_file(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError("Không thấy file font.")
    if candidate.suffix.lower() not in {".ttf", ".otf"}:
        raise ValueError("Chỉ hỗ trợ .ttf hoặc .otf")
    if candidate.stat().st_size <= 0 or candidate.stat().st_size > _MAX_FONT_BYTES:
        raise ValueError("File font phải có kích thước từ 1 byte đến 64 MB.")
    return candidate


def _portable_target(source: Path) -> Path:
    source = _require_font_file(source)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", source.stem).strip(".-") or "font"
    destination = _font_dir() / f"{stem[:72]}-{digest.hexdigest()[:16]}{source.suffix.lower()}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination.resolve()


def _relative_file(path: Path) -> str:
    return path.resolve().relative_to(_manifest_path().parent.resolve()).as_posix()


def resolve_user_font_path(record: dict) -> Path | None:
    """Resolve one manifest record only when it stays under DATA_DIR/fonts."""
    if not isinstance(record, dict) or not isinstance(record.get("file"), str):
        return None
    raw = record["file"].strip()
    if not raw or Path(raw).is_absolute():
        return None
    candidate = (_manifest_path().parent / raw).resolve()
    root = _font_dir().resolve()
    if not _inside(root, candidate) or not candidate.is_file():
        return None
    try:
        _require_font_file(candidate)
    except (FileNotFoundError, ValueError):
        return None
    return candidate


def _normalize_record(item: object) -> tuple[dict | None, bool]:
    """Validate an entry and migrate a usable legacy absolute path once."""
    if not isinstance(item, dict):
        return None, True
    family = str(item.get("family") or "").strip()[:160]
    if not family:
        return None, True
    display = str(item.get("display") or family).strip()[:200] or family
    original_file = item.get("file")
    resolved = resolve_user_font_path(item)
    migrated = False
    if resolved is None and isinstance(original_file, str) and Path(original_file).is_absolute():
        # Versions before the portable manifest stored static/fonts absolute
        # paths.  Copy a still-available legacy font into DATA_DIR once rather
        # than asking Node to trust an arbitrary absolute path.
        try:
            resolved = _portable_target(Path(original_file))
            migrated = True
        except (FileNotFoundError, ValueError, OSError):
            resolved = None
    if resolved is None:
        return None, True
    normalized = {
        "family": family,
        "display": display,
        "file": _relative_file(resolved),
        "vietnamese": bool(item.get("vietnamese")),
        "user": True,
    }
    return normalized, migrated or normalized != item


def _load_user() -> list[dict]:
    path = _manifest_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    normalized: list[dict] = []
    changed = False
    seen: set[str] = set()
    for item in raw:
        record, item_changed = _normalize_record(item)
        changed = changed or item_changed
        if record is None or record["family"] in seen:
            changed = True
            continue
        seen.add(record["family"])
        normalized.append(record)
    if changed:
        _atomic_json_write(path, normalized)
    return normalized


def _save_user(records: list[dict]) -> None:
    _atomic_json_write(_manifest_path(), records)


def probe_font(path: str) -> dict:
    missing: list[int] = []
    vietnamese = False
    family = ""
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(path, lazy=True, fontNumber=0)
        name = font["name"]
        family = (name.getDebugName(16) or name.getDebugName(1) or "").strip()
        cmap = font.getBestCmap() or {}
        missing = [codepoint for codepoint in _VN_TEST if codepoint not in cmap]
        vietnamese = len(missing) <= 1
        font.close()
        if not family:
            try:
                from PIL import ImageFont

                family = ImageFont.truetype(path).getname()[0]
            except Exception:
                family = Path(path).stem
    except Exception:
        family = Path(path).stem
    return {"family": family or Path(path).stem, "vietnamese": bool(vietnamese), "missing": missing}


def add_font(src_path: str, display: str = "", vietnamese=None) -> dict:
    source = _require_font_file(Path(src_path))
    info = probe_font(str(source))
    family = str(info["family"]).strip()[:160] or source.stem[:160]
    destination = _portable_target(source)
    record = {
        "family": family,
        "display": (display or family).strip()[:200] or family,
        "file": _relative_file(destination),
        "vietnamese": info["vietnamese"] if vietnamese is None else bool(vietnamese),
        "user": True,
    }
    users = [user for user in _load_user() if user.get("family") != family]
    users.append(record)
    _save_user(users)
    return record


def remove_font(family: str) -> None:
    users = _load_user()
    keep: list[dict] = []
    removed: list[Path] = []
    for user in users:
        if user.get("family") == family:
            path = resolve_user_font_path(user)
            if path is not None:
                removed.append(path)
            continue
        keep.append(user)
    _save_user(keep)
    still_used = {resolve_user_font_path(user) for user in keep}
    for path in removed:
        if path not in still_used:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def list_fonts() -> list[dict]:
    output = [
        {"family": family, "display": display, "vietnamese": _builtin_vn(family, vietnamese), "user": False}
        for family, display, vietnamese in BUILTIN_FONTS
    ]
    output.extend(
        {
            "family": record["family"],
            "display": record["display"],
            "vietnamese": bool(record["vietnamese"]),
            "user": True,
        }
        for record in _load_user()
    )
    return output


def _badge(vietnamese: bool) -> str:
    return "✓ Tiếng Việt" if vietnamese else "⚠ Thiếu dấu"


def font_options() -> list[tuple[str, str]]:
    options = []
    for font in list_fonts():
        if font["family"] == "":
            options.append(("", font["display"]))
            continue
        marker = " · 🖊️" if font.get("user") else ""
        options.append((font["family"], f"{font['display']}  ·  {_badge(font['vietnamese'])}{marker}"))
    return options


def is_vietnamese(family: str) -> bool:
    for font in list_fonts():
        if font["family"] == family:
            return bool(font["vietnamese"])
    return True
