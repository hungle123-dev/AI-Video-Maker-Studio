"""core/preview_demo.py — Ảnh/GIF xem trước THẬT của template.

Trước đây thumbnail template dựng bằng `hero_script()` (tiêu đề + 1 hiệu ứng
counter) → mọi mẫu nhìn y hệt nhau và KHÔNG giống video mà mẫu đó thực sự
sinh ra. Module này dựng kịch bản demo bằng CHÍNH bộ cảnh / exemplar của mẫu:

  · Mẫu SCENE-FIRST (math_noir / tech_explainer / paper_explainer): ghép
    [chrome_scene] + [1 cảnh chữ ký của bộ] qua custom_scenes.expand() với
    params `demo` của cảnh, đặt vị trí y hệt core/script_generator
    (no_headline / center_body / body_anchor) → frame giống hệt video thật.
  · Mẫu có `exemplars` (neon_sketch, light_news, tech_light): chạy CODE của
    exemplar đầu tiên như một element custom_js — đó chính là "look" premium
    mà AI được dạy bắt chước.
  · Mẫu có cảnh riêng nhưng không scene-first (ai_hotlist, tech_news): ghép
    cảnh nền + cảnh hero theo _CURATED.
  · Còn lại: quay về hero_script cũ.

GIF: render N frame bằng renderer ở mode=frames (MỘT tiến trình node cho cả
dải frame — rẻ hơn nhiều so với gọi preview từng frame) rồi ghép bằng Pillow
(loop=0, ~10fps, ~270px) → app phát khi hover thẻ mẫu.
"""
import json, os, shutil, subprocess, tempfile
from pathlib import Path; _SIGNATURE = {"math_noir": {"scene": "mn_unit_circle", "headline": ""}, "tech_explainer": {"scene": "td_pipeline", "headline": "MỖI VÒNG ĐI QUA 5 BƯỚC"}, "paper_explainer": {"scene": "wp_timeline", "headline": ""}}

_CURATED = {"ai_hotlist": {"title": "", "scenes": [("cosmic_backdrop", {}), ("hotlist_board", {"big": "AI HOT LIST", "pill": "AI HOTLIST", "head": "🔥", "items": [{"name": "Claude Opus", "desc": "agent · code · reasoning"},
    {"name": "Gemini Ultra", "desc": "đa phương thức"},
    {"name": "GPT Turbo", "desc": "hệ sinh thái rộng"},
    {"name": "Llama Open", "desc": "chạy máy cá nhân"},
    {"name": "Mistral Fast", "desc": "rẻ và nhanh"}]})]}, "tech_news": {"title": "", "scenes": [("news_backdrop", {}), ("breaking_pill", {"label": "BREAKING · 2026.07"}), ("gradient_title", {"lines": ["CHIP MỚI", "NHANH GẤP ĐÔI"], "size": 104}), ("metric_grid", {"metrics": [{"icon": "⚡", "v": 2, "suffix": "x", "label": "tốc độ xử lý", "color": "cyan"},
    {"icon": "🔋", "v": 40, "suffix": "%", "label": "tiết kiệm điện", "color": "green"}]})]}}

def _pack_def(tid: str):
    try:
        import pack_templates as PT
        for pack in PT.PACKS:
            d = (pack.get("defs") or {}).get(tid)
            if d:
                return d
    except Exception:
        pass
    return None

def template_def(tid: str, tdef: dict=None) -> dict:
    if tdef:
        return dict(tdef)
    from core import templates as T
    if tid in T._BY_ID:
        return T.get_template(tid)
    d = T._online_by_id(tid) or _pack_def(tid)
    if d:
        return dict(d)
    return T.get_template(tid)

def _scenes():
    from core.custom_scenes import _td_scenes
    return _td_scenes()

def _expand(name: str, params: dict, **pos) -> dict:
    from core import custom_scenes
    safe_params = params or {}
    el = custom_scenes.expand(name, safe_params)
    if el is None:
        return None
    el = dict(el); el.setdefault("template", name); el["params"] = safe_params
    for k, v in pos.items():
        el[k] = v
    
    return el

def _scene_first_script(t: dict) -> dict:
    reg = _scenes(); chrome = t.get("chrome_scene") or "td_chrome"
    sig = _SIGNATURE.get(t["id"]) or {}
    name = sig.get("scene") or t.get("effect") or ""
    if name not in reg:
        cands = [e for e in (t.get("effects") or [])
                 if e in reg and e != chrome and not e.endswith("_title")]
        name = cands[0] if cands else t.get("effect")

    cparams = dict((reg.get(chrome) or {}).get("demo") or {})
    cparams.update(t.get("chrome_params") or {})
    params = sig.get("params") or dict((reg.get(name) or {}).get("demo") or {})
    els = []; ch = _expand(chrome, cparams)
    if ch:
        els.append(ch)
    
    head_anchor = float(t.get("head_anchor", 0.26)); body_anchor = float(t.get("body_anchor", 0.335))
    
    headline = "" if t.get("no_headline") else sig.get("headline") or ""
    if headline:
        els.append({"type": "text", "text": headline, "fontSize": 52, "color": "title", "align": "center", "bold": True, "x_9_16": 0.5, "y_9_16": head_anchor})
    body = _expand(name, params, x_9_16=0.5)
    if body:
        if t.get("center_body"):
            h = int(body.get("height") or 800)
            body["y_9_16"] = round(min(0.45, max(0.06, (1920 - h) / 2 / 1920)), 4)
        else:
            body["y_9_16"] = body_anchor
        els.append(body)
    return _one_step(t, els)

_EXEMPLAR_IDX = {"light_news": 0, "tech_light": 1}
def _exemplar_script(t: dict) -> dict:
    # Exemplars are prompt/reference material, not executable template input.
    # Render the matching shipped scene instead so a downloaded template never
    # gains the ability to run arbitrary Node code during thumbnail generation.
    names = [str(t.get("effect") or "").strip().lower()]
    names.extend(str(item).strip().lower() for item in (t.get("effects") or []))
    scene = next(
        (candidate for name in names if name
         for candidate in [_expand(name, {}, x_9_16=0.5, y_9_16=0.12)]
         if candidate),
        None,
    )
    if scene is None:
        scene = _expand("counter_metric", {}, x_9_16=0.5, y_9_16=0.12)
    els = [scene] if scene else []
    return _one_step(t, els)

def _curated_script(t: dict, cur: dict) -> dict:
    els = []
    for name, params in cur["scenes"]:
        el = _expand(name, params)
        if not el:
            continue
        els.append(el)
    return _one_step(t, els)

def _one_step(t: dict, els: list) -> dict:
    topic = t.get("topic") or t.get("name") or "Demo"
    return {"title": topic, "description": "Xem trước mẫu", "subject": "general", "total_steps": 1, "steps": [{"id": 1, "clear": True, "voice_text": "Xem trước phong cách của mẫu này.", "elements": els}]}

def demo_script(tid: str, tdef: dict=None) -> dict:
    t = template_def(tid, tdef)
    try:
        if t.get("scene_first"):
            s = _scene_first_script(t)
            if s["steps"][0]["elements"]:
                return s
        elif t.get("exemplars"):
            return _exemplar_script(t)
        elif t["id"] in _CURATED:
            s = _curated_script(t, _CURATED[t["id"]])
            if s["steps"][0]["elements"]:
                return s
    except Exception as e:
        print(f"  ⚠ demo_script({tid}) lỗi: {e} → hero_script")
    from core.templates import hero_script
    return hero_script(t.get("topic") or t.get("name") or "Demo",
                       t.get("effect") or "counter_metric")

def _render_params(t: dict, aspect: str) -> dict:
    return {"theme": "dark", "aspect_ratio": aspect, "art_style": t.get("art_style") or "default", "title_color": t.get("title_color") or "", "text_color": t.get("text_color") or "", "font_family": t.get("font_family") or "", "subtitle_enabled": False}

def _timing(seconds: float) -> dict:
    return {"steps": [{"id": 1, "start": 0.0, "end": round(seconds, 3), "duration": round(seconds, 3), "audio": "", "words": []}], "total_duration": round(seconds, 3), "merged_audio": None}

def render_preview_png(tid: str, out_path: str, aspect: str="9:16", tdef: dict=None, seconds: float=3.2) -> str:
    from core.preview import render_time_preview; t = template_def(tid, tdef); script = demo_script(tid, t); timing = _timing(seconds); r = render_time_preview(_render_params(t, aspect), script, seconds * 0.85, str(out_path), timing)
    if not r.get("ok"):
        print(f"  ✗ PNG {tid} {aspect}: {r.get("error")}")
        return None
    return str(out_path)

def _render_frames(t: dict, script: dict, timing: dict, aspect: str, fps: int, n_frames: int, outdir: str) -> bool:
    from core.preview import RENDERER_JS, _node_env, _CREATE_NO_WINDOW
    from engines.video_encoder import _find_executable
    from core.schema import check_custom_js, validate_script

    script, errors = validate_script(script)
    errors += check_custom_js(script)
    if errors:
        print("  ✗ script demo không an toàn:", "; ".join(errors[:2]))
        return False
    node = _find_executable("node")
    if not Path(node).is_file() and not shutil.which(node):
        print("  ✗ Không tìm thấy Node.js")
        return False
    env, nm = _node_env()
    if not nm:
        print("  ✗ Chưa cài package 'canvas'")
        return False
    sp = os.path.join(outdir, "script.json"); tp = os.path.join(outdir, "timing.json"); Path(sp).write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    
    Path(tp).write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8"); proj = _render_params(t, aspect); cmd = [node, str(RENDERER_JS), "--script", sp, "--timing", tp, "--output", outdir, "--mode", "frames", "--fps", str(fps), "--startFrame", "0", "--endFrame", str(n_frames), "--theme", "dark", "--aspect", aspect, "--style", proj["art_style"]]
    if proj["title_color"]:
        cmd += ["--title-color", proj["title_color"]]
    if proj["text_color"]:
        cmd += ["--text-color", proj["text_color"]]
    
    if proj["font_family"]:
        cmd += ["--font", proj["font_family"]]
    
    p = subprocess.run(cmd, capture_output=True, env=env, timeout=300, cwd=str(Path(RENDERER_JS).parent.parent), creationflags=_CREATE_NO_WINDOW)
    if p.returncode != 0:
        print("  ✗ frames:", p.stderr.decode("utf-8", "replace")[-300:])
        return False
    return True

def render_preview_gif(tid: str, out_path: str, aspect: str="9:16", seconds: float=3.2, fps: int=10, width: int=270, tdef: dict=None, colors: int=128) -> str:
    from PIL import Image; t = template_def(tid, tdef); script = demo_script(tid, t); n = max(2, int(round(seconds * fps))); timing = _timing(seconds); tmp = tempfile.mkdtemp(prefix=f"t2gif_{tid}_")
    try:
        print(f"  … render {n} frame ({fps}fps, {seconds}s) …")
        if not _render_frames(t, script, timing, aspect, fps, n, tmp):
            shutil.rmtree(tmp, ignore_errors=True)
            return None
        files = sorted(Path(tmp).glob("frame_*.jpg"))
        if len(files) < 2:
            print(f"  ✗ GIF {tid}: chỉ có {len(files)} frame")
            shutil.rmtree(tmp, ignore_errors=True)
            return None
        rgb = []
        for f in files:
            im = Image.open(f).convert("RGB")
            h = round((im.height) * width / (im.width))
            rgb.append(im.resize((width, h), Image.LANCZOS))
        pal = rgb[int(len(rgb) * 0.8)].quantize(colors=colors, method=Image.MEDIANCUT)
        frames = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in rgb]
        im = None
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(str(out_path), save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, optimize=True)
        kb = (Path(out_path).stat().st_size) / 1024
        print(f"  ✓ {Path(out_path).name}: {len(frames)} frame, {kb:.0f} KB")
        shutil.rmtree(tmp, ignore_errors=True)
        return str(out_path)
        im = None
    except Exception as e:
        print(f"  ✗ GIF {tid}: {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        return None
