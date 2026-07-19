"""core/schema.py — Validate lesson_script.json tại biên lưu trữ/render.

Định dạng script chuẩn của TubeCraft:
{
  title, description, subject, total_steps,
  steps: [ { id, voice_text, clear, elements: [ {type: text|list|box|image|custom_js, ...} ] } ]
}

validate_script() sửa những lỗi vô hại (thiếu id, total_steps lệch) và trả
danh sách lỗi thật sự thay vì để hỏng lúc render.
"""
import re
from typing import List, Tuple
from urllib.parse import unquote


ELEMENT_TYPES = {"box", "list", "text", "arrow", "image", "latex", "spacer", "custom_js"}
def default_script(title: str="") -> dict:
    return {"title": title or "Bài học mới", "description": "", "subject": "general", "total_steps": 1, "steps": [{"id": 1, "voice_text": "", "clear": True, "elements": []}]}

_LIGHT_INK = {"": "#0f172a", "title": "#0f172a", "text": "#1e2b4a", "white": "#0f172a", "highlight": "#1d4ed8", "yellow": "#b45309", "cyan": "#0e7490", "green": "#15803d", "red": "#dc2626", "blue": "#1d4ed8", "muted": "#5b6478"}; _LIGHT_MARKER = "#f3f6ff"
def _fix_light_contrast(steps: list) -> None:
    for step in steps:
        if not isinstance(step, dict):
            continue
        els = step.get("elements")
        if not isinstance(els, list):
            continue
        is_light = any(
            _LIGHT_MARKER in (element.get("code") or "")
            for element in els
            if isinstance(element, dict)
        )
        if not is_light:
            continue
        for e in els:
            if not isinstance(e, dict):
                continue
            elif not e.get("type") in ("text", "list"):
                continue
            c = e.get("color") or ""
            if str(c).startswith("#"):
                continue
            e["color"] = _LIGHT_INK.get(c, "#0f172a")

_LAYOUT_KEYS = ("x_9_16", "y_9_16", "x_16_9", "y_16_9", "x_1_1", "y_1_1")
_GALLERY_PREFIX = "gallery:"
_LEGACY_GALLERY_PREFIXES = (
    "/api/v1/edu_video/gallery/file/",
    "/api/v1/edu_video_studio/gallery/file/",
)
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
_GALLERY_SEGMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def normalize_gallery_src(value: object) -> str | None:
    """Accept only a small, local gallery reference; never a renderer URL/path."""
    if not isinstance(value, str):
        return None
    source = value.strip()
    if not source or len(source) > 512 or any(ord(char) < 32 for char in source):
        return None
    relative = None
    if source.startswith(_GALLERY_PREFIX):
        relative = source[len(_GALLERY_PREFIX):]
    else:
        for prefix in _LEGACY_GALLERY_PREFIXES:
            if source.startswith(prefix):
                relative = source[len(prefix):]
                break
    if relative is None:
        return None
    # Decode exactly once so encoded slash/backslash/traversal cannot become a
    # filesystem path later. A remaining '%' is rejected to avoid double-decode
    # ambiguity across Python/Node layers.
    relative = unquote(relative)
    if (
        not relative
        or len(relative) > 240
        or "%" in relative
        or any(char in relative for char in ("\\", "?", "#", ":", "\x00"))
    ):
        return None
    parts = relative.split("/")
    if any(
        not part
        or part in (".", "..")
        or part.strip() != part
        # Keep the Python boundary exactly aligned with the renderer's
        # cross-platform filename allowlist.  A rejected name is preferable
        # to accepting it here and failing after a render job has begun.
        or not _GALLERY_SEGMENT_RE.fullmatch(part)
        for part in parts
    ):
        return None
    filename = parts[-1]
    if "." not in filename or ("." + filename.rsplit(".", 1)[1].lower()) not in _IMAGE_EXTENSIONS:
        return None
    return _GALLERY_PREFIX + "/".join(parts)


def _trusted_scene(expanded: dict, template: str, source: dict, params: dict) -> dict:
    """Attach provenance after *local* expansion, never accept it from input."""
    scene = dict(expanded)
    scene["template"] = template
    scene["params"] = params
    scene["trusted_template"] = template
    for key in _LAYOUT_KEYS:
        if key in source:
            scene.setdefault(key, source[key])
    return scene


def _expand_scene_templates(steps: list, errors: List[str]) -> None:
    """Turn declarative scene data into locally-owned renderer code.

    ``custom_js.code`` crosses an AI/import trust boundary.  It is therefore
    never executable input: a known template is re-expanded from this source
    tree; an exact shipped legacy effect is migrated; all other raw code is
    removed and reported to the caller.
    """
    from core import custom_scenes

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        elements = step.get("elements")
        if not isinstance(elements, list):
            continue
        normalized = []
        for j, element in enumerate(elements):
            if not isinstance(element, dict) or element.get("type") != "custom_js":
                normalized.append(element)
                continue

            name = str(element.get("template") or "").strip().lower()
            params = custom_scenes.normalize_scene_params(name, element.get("params")) if name else {}
            expanded = custom_scenes.expand(name, params) if name else None
            if expanded is not None:
                supplied = element.get("code")
                expected = str(expanded.get("code") or "").strip()
                if isinstance(supplied, str) and supplied.strip() and supplied.strip() != expected:
                    errors.append(
                        f"Step {i + 1}, element {j + 1}: code custom_js ngoài template '{name}' đã bị bỏ qua."
                    )
                normalized.append(_trusted_scene(expanded, name, element, params))
                continue

            legacy = custom_scenes.legacy_template_for_code(element.get("code")) if not name else None
            if legacy:
                expanded = custom_scenes.expand(legacy, {})
                if expanded is not None:
                    normalized.append(_trusted_scene(expanded, legacy, element, {}))
                    continue

            if name:
                errors.append(
                    f"Step {i + 1}, element {j + 1}: template '{name}' không được hỗ trợ; cảnh đã bị bỏ qua."
                )
            else:
                errors.append(
                    f"Step {i + 1}, element {j + 1}: custom_js raw không được hỗ trợ; hãy chọn template mẫu."
                )
        step["elements"] = normalized


def _normalize_image_sources(steps: list, errors: List[str]) -> None:
    """Remove image elements that do not point to a local owned gallery asset."""
    for step_index, step in enumerate(steps):
        if not isinstance(step, dict) or not isinstance(step.get("elements"), list):
            continue
        normalized = []
        for element_index, element in enumerate(step["elements"]):
            if not isinstance(element, dict) or element.get("type") != "image":
                normalized.append(element)
                continue
            source = normalize_gallery_src(element.get("src"))
            if source is None:
                errors.append(
                    f"Step {step_index + 1}, element {element_index + 1}: image src không thuộc gallery local; ảnh đã bị bỏ qua."
                )
                continue
            item = dict(element)
            item["src"] = source
            normalized.append(item)
        step["elements"] = normalized

def validate_script(script: dict) -> Tuple[(dict, List[str])]:
    errors = []
    if not isinstance(script, dict):
        return (default_script(), ["Script không phải object JSON."])
    script.setdefault("title", "Bài học"); script.setdefault("description", ""); script.setdefault("subject", "general"); steps = script.get("steps")
    if not isinstance(steps, list):
        errors.append("Script không có steps.")
        script["steps"] = default_script()["steps"]
        script["total_steps"] = 1
        return (script, errors)
    used = []
    for st in steps:
        if not isinstance(st, dict):
            continue
        for e in st.get("elements") or []:
            if not isinstance(e, dict):
                continue
            elif not e.get("type") == "custom_js":
                continue
            elif not e.get("template"):
                continue
            used.append(e["template"])
    script["scenes_used"] = sorted(set(used))
    
    _expand_scene_templates(steps, errors)
    _normalize_image_sources(steps, errors)
    _fix_light_contrast(steps)
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"Step {i + 1} không phải object.")
            continue
        step["id"] = i + 1
        step.setdefault("clear", True)
        if not isinstance(step.get("voice_text"), str):
            step["voice_text"] = str(step.get("voice_text") or "")
        els = step.get("elements")
        if not isinstance(els, list):
            step["elements"] = []
            continue
        for j, el in enumerate(els):
            if not isinstance(el, dict):
                errors.append(f"Step {i + 1}, element {j + 1} không phải object.")
                continue
            etype = el.get("type", "")
            if etype not in ELEMENT_TYPES:
                errors.append(f"Step {i + 1}, element {j + 1}: type lạ '{etype}'.")
            if etype != "custom_js":
                continue
            if not isinstance(el.get("code"), str):
                errors.append(f"Step {i + 1}, element {j + 1}: custom_js thiếu code.")
                continue
            if el.get("template") != el.get("trusted_template"):
                errors.append(f"Step {i + 1}, element {j + 1}: custom_js chưa được xác thực từ template.")
    script["total_steps"] = len(steps); return (script, errors)

def check_custom_js(script: dict) -> List[str]:
    """Verify provenance without compiling untrusted JavaScript in Node."""
    from core import custom_scenes

    errors = []
    for step_index, step in enumerate(script.get("steps") or []):
        if not isinstance(step, dict):
            continue
        for element_index, element in enumerate(step.get("elements") or []):
            if not isinstance(element, dict) or element.get("type") != "custom_js":
                continue
            label = f"Step {step.get('id', step_index + 1)}, element {element_index + 1}"
            template = str(element.get("template") or "").strip().lower()
            if not template or element.get("trusted_template") != template:
                errors.append(f"{label}: custom_js không đến từ template tin cậy.")
                continue
            expected = custom_scenes.expand(template, element.get("params"))
            if expected is None:
                errors.append(f"{label}: template '{template}' không được hỗ trợ.")
                continue
            if str(element.get("code") or "").strip() != str(expected.get("code") or "").strip():
                errors.append(f"{label}: code custom_js đã bị thay đổi ngoài template.")
    return errors
