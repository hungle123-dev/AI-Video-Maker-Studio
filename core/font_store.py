"""Small, bounded Google Fonts helper for TubeCraft's optional font picker."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.request as urllib
import zipfile
from pathlib import Path


META_URL = "https://fonts.google.com/metadata/fonts"
GWFH_ZIP = "https://gwfh.mranftl.com/api/fonts/{fid}?download=zip&subsets={subs}&variants=regular&formats=ttf"
GWFH_JSON = "https://gwfh.mranftl.com/api/fonts/{}"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_MAX_HTTP_BYTES = 20 * 1024 * 1024
_MAX_FONT_BYTES = 16 * 1024 * 1024
_CACHE_MAX_FILES = 80
_CACHE_MAX_AGE_SECONDS = 14 * 24 * 60 * 60
REGIONS = [
    ("vietnamese", "🇻🇳 Tiếng Việt (đủ dấu)"),
    ("latin", "🌍 Latin (Anh, phổ thông)"),
    ("latin-ext", "🇪🇺 Latin mở rộng (Âu)"),
    ("cyrillic", "🇷🇺 Nga / Cyrillic"),
    ("greek", "🇬🇷 Hy Lạp"),
    ("thai", "🇹🇭 Thái"),
    ("arabic", "🇸🇦 Ả Rập"),
    ("hebrew", "🇮🇱 Do Thái"),
    ("devanagari", "🇮🇳 Ấn Độ (Devanagari)"),
    ("japanese", "🇯🇵 Nhật"),
    ("korean", "🇰🇷 Hàn"),
    ("chinese-simplified", "🇨🇳 Trung (giản thể)"),
]
_cache = {"fams": None}
_url_cache: dict[str, str] = {}


def _read_limited(response, limit: int = _MAX_HTTP_BYTES) -> bytes:
    size = response.headers.get("Content-Length")
    if size:
        try:
            if int(size) > limit:
                raise ValueError("Tài nguyên font quá lớn.")
        except ValueError:
            raise
        except Exception:
            pass
    chunks: list[bytes] = []
    total = 0
    while True:
        block = response.read(min(64 * 1024, limit + 1 - total))
        if not block:
            break
        total += len(block)
        if total > limit:
            raise ValueError("Tài nguyên font quá lớn.")
        chunks.append(block)
    return b"".join(chunks)


def _fetch(url: str, ua: str = _UA, timeout: int = 25) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _read_limited(response).decode("utf-8", "replace")


def _all_families(force: bool = False) -> list:
    if _cache["fams"] is not None and not force:
        return _cache["fams"]
    raw = _fetch(META_URL)
    start = raw.find("{")
    if start < 0:
        raise ValueError("Google Fonts metadata không chứa JSON hợp lệ.")
    data = json.loads(raw[start:])
    families = data.get("familyMetadataList", []) if isinstance(data, dict) else []
    _cache["fams"] = families if isinstance(families, list) else []
    return _cache["fams"]


def list_online(subset: str = "vietnamese", query: str = "", limit: int = 80, sort: str = "popularity") -> list:
    query = (query or "").strip().lower()
    try:
        limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        limit = 80
    output = []
    for family in _all_families():
        if not isinstance(family, dict):
            continue
        subsets = family.get("subsets") or []
        name = str(family.get("family") or "")
        if subset and subset not in subsets:
            continue
        if query and query not in name.lower():
            continue
        output.append({
            "family": name,
            "category": family.get("category", ""),
            "subsets": subsets,
            "vietnamese": "vietnamese" in subsets,
            "popularity": family.get("popularity", 99999),
        })
    output.sort(key=(lambda item: item["popularity"]) if sort == "popularity" else (lambda item: item["family"].lower()))
    return output[:limit]


def region_count(subset: str) -> int:
    return sum(1 for family in _all_families() if isinstance(family, dict) and subset in (family.get("subsets") or []))


def _slug(family: str) -> str:
    return re.sub("[^a-z0-9]+", "-", str(family).lower()).strip("-")[:100]


def preview_url(family: str) -> str:
    if family in _url_cache:
        return _url_cache[family]
    slug = _slug(family)
    if not slug:
        return ""
    try:
        data = json.loads(_fetch(GWFH_JSON.format(slug)))
        variants = data.get("variants", []) if isinstance(data, dict) else []
        regular = next((item for item in variants if isinstance(item, dict) and item.get("id") == "regular"), None)
        regular = regular or (variants[0] if variants else {})
        url = str(regular.get("ttf", "")) if isinstance(regular, dict) else ""
    except Exception:
        url = ""
    _url_cache[family] = url
    return url


def _download(url: str, timeout: int = 45) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _read_limited(response)


def _prune_cache(directory: Path) -> None:
    try:
        now = time.time()
        files = [path for path in directory.iterdir() if path.is_file()]
        for path in files:
            if now - path.stat().st_mtime > _CACHE_MAX_AGE_SECONDS:
                path.unlink(missing_ok=True)
        files = sorted((path for path in directory.iterdir() if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in files[_CACHE_MAX_FILES:]:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def _cache_dir() -> Path:
    from config import DATA_DIR

    directory = Path(DATA_DIR) / "font_cache"
    directory.mkdir(parents=True, exist_ok=True)
    _prune_cache(directory)
    return directory


def _preview_dir() -> Path:
    from config import DATA_DIR

    directory = Path(DATA_DIR) / "font_preview"
    directory.mkdir(parents=True, exist_ok=True)
    _prune_cache(directory)
    return directory


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".font.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _valid_cached_font(path: Path) -> bool:
    return path.is_file() and 0 < path.stat().st_size <= _MAX_FONT_BYTES


def fetch_font(family: str, subset: str = "vietnamese") -> str:
    slug = _slug(family)
    if not slug:
        raise ValueError("Tên font không hợp lệ.")
    safe_subset = _slug(subset) or "latin"
    destination = _cache_dir() / f"{slug}_{safe_subset}.ttf"
    if _valid_cached_font(destination):
        return str(destination)
    combinations: list[str] = []
    if subset and subset != "latin":
        combinations.extend([f"{subset},latin", subset])
    combinations.extend(["latin", ""])
    last_error: Exception | None = None
    for subsets in combinations:
        try:
            archive = _download(GWFH_ZIP.format(fid=slug, subs=subsets))
            with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                entries = [entry for entry in zipped.infolist() if entry.filename.lower().endswith(".ttf")]
                if not entries:
                    continue
                pick = next((entry for entry in entries if "regular" in entry.filename.lower()), entries[0])
                if pick.file_size <= 0 or pick.file_size > _MAX_FONT_BYTES:
                    raise ValueError("Font trong gói tải về quá lớn.")
                data = zipped.read(pick)
            if not 0 < len(data) <= _MAX_FONT_BYTES:
                raise ValueError("File font tải về không hợp lệ.")
            _atomic_bytes(destination, data)
            return str(destination)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Không tải được font '{family}': {last_error}")


def install_font(family: str, subset: str = "vietnamese") -> dict:
    from core.fonts import add_font

    return add_font(fetch_font(family, subset), display=family)


def render_sample(family: str, subset: str, text: str, fg=(30, 43, 74), size: int = 30) -> str:
    from PIL import Image, ImageDraw, ImageFont

    key = hashlib.sha256(
        (str(family) + "\0" + str(subset) + "\0" + str(text) + "\0" + repr(tuple(fg)) + "\0" + str(size)).encode("utf-8")
    ).hexdigest()[:24]
    output = _preview_dir() / f"{key}.png"
    if output.is_file() and output.stat().st_size > 0:
        return str(output)
    font = ImageFont.truetype(fetch_font(family, subset), max(8, min(int(size), 240)))
    canvas = Image.new("RGBA", (8, 8))
    bbox = ImageDraw.Draw(canvas).textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 10
    height = bbox[3] - bbox[1] + 10
    image = Image.new("RGBA", (max(width, 10), max(height, 10)), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((5 - bbox[0], 5 - bbox[1]), text, font=font, fill=tuple(fg) + (255,))
    temporary = output.with_suffix(".tmp.png")
    image.save(temporary)
    os.replace(temporary, output)
    return str(output)
