"""core/script_generator.py — Sinh kịch bản lesson bằng AI.

Bản gọn lại của engines/script_generator.py cũ (2.600 dòng): một prompt
mô tả đúng schema lesson_script.json, gọi qua core.ai_client (đa provider,
tự xoay key), bóc JSON và validate bằng core.schema.
"""
import json, logging, re, time
from typing import Optional, List
from core import ai_client
from core.schema import check_custom_js, validate_script; logger = logging.getLogger("TubeCraft.ScriptGen"); _SCENE_GUARDS = {"mn_unit_circle": ("sin", "cos", "tan", "lượng giác", "luong giac", "vòng tròn", "vong tron", "đường tròn", "duong tron", "góc", "goc", "radian", "quay", "°"), "mn_sine_trace": ("sin", "cos", "sóng", "song", "dao động", "dao dong", "tuần hoàn", "tuan hoan", "chu kỳ", "chu ky", "quay", "lượng giác", "luong giac", "nhịp", "nhip"), "mn_graph": ("hàm", "ham so", "đồ thị", "do thi", "parabol", "tiếp tuyến", "tiep tuyen", "đạo hàm", "dao ham", "tăng", "tang", "giảm", "giam", "biến thiên", "bien thien", "đường cong", "duong cong", "mũ", "exp", "log", "trục", "truc", "tọa độ", "toạ độ", "toa do", "mặt phẳng", "mat phang", "cặp số", "cap so", "descartes"), "mn_number_line": ("trục số", "truc so", "số âm", "so am", "khoảng", "khoang", "đoạn", "doan", "bất phương trình", "bat phuong trinh", "lớn hơn", "lon hon", "nhỏ hơn", "nho hon", "nằm giữa", "nam giua", "liên tiếp", "lien tiep", "≤", "≥", "dãy", "day so"), "mn_triangle_anatomy": ("tam giác", "tam giac", "pythagore", "py-ta-go", "pytago", "cạnh", "canh", "đường cao", "duong cao", "huyền", "huyen", "góc", "goc"), "mn_integral_area": ("tích phân", "tich phan", "nguyên hàm", "nguyen ham", "diện tích", "dien tich", "đường cong", "duong cong", "∫", "cộng dồn", "cong don", "tích lũy", "tich luy", "tổng", "tong"), "mn_venn": ("tập hợp", "tap hop", "giao", "chung", "venn", "cả hai", "ca hai", "vừa", "vua", "phần tử", "phan tu", "chia hết", "chia het", "thuộc", "thuoc"), "mn_pendulum": ("con lắc", "con lac", "dao động", "dao dong", "chu kỳ", "chu ky", "đung đưa", "dung dua", "lặp lại", "lap lai", "tuần hoàn", "tuan hoan", "vật lý", "vat ly", "nhịp", "nhip"), "mn_spiral": ("xoắn", "xoan", "fibonacci", "fibonaci", "tỉ lệ vàng", "ti le vang", "tỷ lệ vàng", "ốc", "oc", "dãy", "day so", "hoa", "tự nhiên", "tu nhien", "φ", "phi"), "mn_light_trail": ("quỹ đạo", "quy dao", "ném", "nem", "rơi", "roi", "parabol", "chuyển động", "chuyen dong", "đường đi", "duong di", "bay", "vệt", "vet", "ánh sáng", "anh sang", "tốc độ", "toc do")}; _MATHISH = re.compile("[=<>±×÷√∫%^²³]|\\d")
def _guard_swap_params(params, voice):
    p = params if isinstance(params, dict) else {}
    title = str(p.get("title") or "").strip()
    cands = [str(p.get(k) or "").strip() for k in ("formula", "expr", "label", "hot_label", "range_label", "point_label", "note", "sub")]
    formula = next((c for c in cands if _MATHISH.search(c)), "")
    if not formula and title and _MATHISH.search(title):
        formula, title = title, ""
    if not formula:
        formula, title = title or "", ""
    if not formula:
        snip = re.split("[.!?…;:]", str(voice or ""), 1)[0].strip()
        formula = snip[:60] or "?"
    return {"title": title[:60], "formula": formula[:80], "accent_part": "", "note": ""}

SECONDS_PER_STEP = 12.0
def estimate_minutes(step_count: int) -> float:
    return round(max(1, step_count) * SECONDS_PER_STEP / 60.0, 1)

_SYSTEM = "Bạn là biên kịch video giáo dục ngắn (TikTok/Reels 9:16).\nBạn luôn trả về DUY NHẤT một object JSON hợp lệ, không markdown, không giải thích."
def _lang_rule(lang: str) -> str:
    name = lang_name(lang)
    return f"\n━━━ NGÔN NGỮ ĐẦU RA (BẮT BUỘC) ━━━\n- Viết TOÀN BỘ nội dung bằng {name}.\n- Áp dụng cho MỌI trường: title, description, brief, voice_text, mọi text/items\n  trong elements, mọi nhãn/chữ hiển thị bên trong code custom_js, VÀ MỌI text\n  trong params của cảnh dựng sẵn (stamp_done.text, progress_map.done_text/\n  remain_text, kicker, pill, label, verdict, sub, items...). KHÔNG để sót\n  chữ tiếng Việt mẫu nếu ngôn ngữ đầu ra khác.\n- Ý tưởng người dùng nhập có thể viết bằng ngôn ngữ KHÁC (ví dụ tiếng Việt) —\n  hãy HIỂU nó, rồi VIẾT RA bằng {name}. Không dịch máy móc, viết tự nhiên như\n  người bản ngữ.\n- Cách đánh số tập / cách gọi \"bài\", \"phần\" dùng lối diễn đạt tự nhiên của\n  {name} (KHÔNG bê nguyên \"Tập 1\" nếu ngôn ngữ không phải tiếng Việt).\n- Chỉ giữ nguyên gốc: tên riêng, thương hiệu, thuật ngữ kỹ thuật, đoạn code.\n- Tuyệt đối KHÔNG trộn hai ngôn ngữ trong cùng một câu.\n"

def _template_hint(template) -> str:
    t = template
    if isinstance(t, str):
        try:
            from core.templates import get_template
            t = get_template(t)
        except Exception:
            return ""
    if not isinstance(t, dict):
        return ""
    hint = (t.get("ai_hint") or t.get("vibe") or "").strip()
    effects = t.get("effects") or ([t["effect"]] if t.get("effect") else [])
    style = t.get("art_style") or ""
    if not hint and not effects:
        return ""
    lines = [f"━━━ PHONG CÁCH KÊNH — template \"{t.get('name', '')}\" (BÁM SÁT) ━━━"]
    if hint:
        lines.append(hint)
    if effects:
        lines.append("Ưu tiên các hiệu ứng custom_js sau (chọn cái hợp mỗi step): " + ", ".join(effects) + ".")
    if style and style != "default":
        lines.append(f"Giữ tông màu & không khí của phong cách '{style}' xuyên suốt series.")
    pal = t.get("palette") or []
    if pal:
        lines.append("🎨 TEMPLATE ACCENT PALETTE (locked — every accent/ui.* color must come from this set; pass the hex straight into ui.* color params): " + ", ".join(pal[:3]) + ".")
    return "\n" + "\n".join(lines) + "\n"

_DEFAULT_RICH = ["gradient_title", "big_word", "code_typing", "metric_grid", "journey_path", "data_river", "phone_hero", "web_window", "neuro_stream", "versus_split", "stairs_steps", "orbit_cycle"]

def _rotate(seq, seed):
    seq = list(seq or [])
    if not seq:
        return seq
    elif isinstance(seed, str):
        seed = sum((ord(c) for c in seed))
    off = int(seed or 0) % len(seq)
    return seq[off:] + seq[:off]

_PROMPT_TEMPLATE = "You are the visual director of a HIGH-QUALITY 9:16 short educational video (TikTok/Reels).\nWrite a step-by-step script; every step carries ONE beautiful ANIMATED bespoke illustration via custom_js.\n\nCONTENT/{mode}:\n{content}\n{template_hint}\n\nReturn JSON exactly in this schema:\n{{\n  \"title\": \"Catchy video title (in the OUTPUT LANGUAGE)\",\n  \"description\": \"One-sentence description\",\n  \"subject\": \"{subject}\",\n  \"total_steps\": {step_count},\n  \"steps\": [\n    {{\n      \"id\": 1,\n      \"voice_text\": \"Natural 2-4 sentence narration in the OUTPUT LANGUAGE, numbers spelled as words\",\n      \"clear\": true,\n      \"elements\": [\n        {{\"type\": \"text\", \"text\": \"Short step headline\", \"fontSize\": 46, \"color\": \"highlight\", \"align\": \"center\", \"bold\": true}},\n        {{\"type\": \"custom_js\", \"height\": 900, \"code\": \"<JS canvas drawing DESIGNED FOR THIS STEP — see the quality bar below>\", \"x_9_16\": 0.5, \"y_9_16\": 0.5}}\n      ]\n    }}\n  ]\n}}\n\n━━━ COLOR TONE (the system handles it — do NOT fight it) ━━━\n• Never insert backdrop scenes yourself — only use cosmic_backdrop/news_backdrop\n  if the CHANNEL STYLE section below names one explicitly.\n• Use named colors ('cyan','green','yellow','red','purple','pink','title') or\n  rc() — they auto-adapt to light/dark tone. Do not invent fixed hex colors\n  unless the template palette gives them.\n• Keep ONE consistent scene family for the whole video.\n\n━━━ BESPOKE ILLUSTRATION — THE SOUL OF THE VIDEO (MOST IMPORTANT) ━━━\nEVERY content step MUST have ONE hand-written custom_js drawing designed for\nTHAT step's exact idea — DRAW THE THING BEING SAID:\n• money → wallet + falling coins; security → shield + lock + scanning beam\n• speed → speedometer needle surging; cost → invoice torn / price arrow diving\n• app/web → phone/browser mockup with the step's REAL content inside\n• pipeline → stations connected by flowing particles; growth → chart drawing\n  itself with real milestone numbers\nNever reuse one visual pattern across steps. Never draw a generic %-bar/circle.\nA viewer must guess the step's meaning from the picture alone.\n\nMANDATORY QUALITY BAR for every illustration:\n• LAYOUT RECIPE (hard rule): the frame is 1080×1920 — content must OWN it.\n  Open with ONE full-width TALL card:\n  ui.glass(80, cursorY+8, W-160, 880, {{accent:'<primary>'}});\n  and FILL it top-to-bottom (dead empty areas = REJECTED):\n  kicker ui.chip at cursorY+70 → ui.title(W/2, cursorY+150, ..., {{size:54}})\n  → HERO DRAWING covering ≥45% of the card (roughly 400px tall) →\n  ui.kpi/ui.chip row near the card bottom. `return 900;`\n• ONE card per step — NEVER stack a second card/word-art/captions below it\n  (overflowing the 1920px frame = REJECTED). Step elements = exactly one\n  headline text + one custom_js. In step 1 an intro scene may REPLACE the\n  card, never stack with it.\n• TYPE SCALE (hard minimums on the 1080-wide canvas): card headline ≥54px,\n  hero number ≥110px, sub-labels/captions ≥34px, NOTHING below 30px. If text\n  does not fit, CUT WORDS — never shrink the font.\n• CHARTS must be real: axis baseline + data line/bars + peak marker + value\n  callout anchored to the data point. Decorative gradient rectangles behind\n  numbers = REJECTED.\n• PREMIUM KIT ui.* is REQUIRED for every frame/label/number/gauge:\n  ui.glass(x,y,w,h,{{accent}}) glass card · ui.title(cx,y,text,{{size,from,to}})\n  gradient headline · ui.chip(cx,cy,text,{{color}}) pill label ·\n  ui.kpi(cx,y,'75%','SAVED',{{color,size}}) big gradient number ·\n  ui.icon(cx,cy,'🚀',64,{{color}}) emoji on a glowing disc (NEVER a bare emoji) ·\n  ui.bar(x,y,w,16,p,{{color}}) gauge bar · ui.ring(cx,cy,r,p,{{color,text:'72%'}})\n  ring gauge · ui.flow([[x,y],[x,y],...],{{color,n:3}}) particle flow line ·\n  ui.divider(x1,x2,y).\n• The HERO subject is still hand-drawn with shapes (wallet, shield, clock,\n  mockup...) INSIDE the card — ui.* is the skeleton, your drawing is the soul.\n• COLOR DISCIPLINE: pick ONE primary + ONE accent for the WHOLE video (use the\n  template palette when given) — every title/card edge uses the primary, every\n  highlighted number the accent. green/red ONLY for semantic up/down or\n  pros/cons, never decoration. Main strokes/fills alpha ≥ 0.85; pale rgba\n  washes as primary color = REJECTED.\n• Animate: reveal with stepProgress (easing EZ(t)=1-Math.pow(1-t,3)), pulse\n  with time, ui.flow particles. NO static pictures.\n• `ctx.save()` ... `ctx.restore(); return <height>` (height 860–920).\n• NEVER use // line comments — the code lives on ONE JSON line, so // kills\n  every command after it. Use /* ... */ if you must comment.\n• EACH STEP picks a DIFFERENT layout family: bar-chart / versus twin cards /\n  flow stations / ring-hero / kpi-hero / mockup / timeline / orbit. No two\n  steps may share a family.\nVariables: ctx, W (1080), cursorY, stepProgress (0→1), time, ui (kit above),\nrc(name)→tone-aware text color, wrapText(text,maxW,font).\n\nREFERENCE SNIPPETS — copy the RICHNESS & TECHNIQUE, not the picture; draw THIS\nstep's own picture:\n{effects}\n\n━━━ PREBUILT SCENES ━━━\n  {{\"type\": \"custom_js\", \"template\": \"<scene name>\", \"params\": {{...}}}}\n{scene_rule}\n\n━━━ CONTENT RULES ━━━\n- {steps_rule} {hook_rule} {recap_rule}\n- Warm, practical, engaging narration.\n- Numbers/labels inside drawings must match that step's narration.\n- Alternate the text element color \"highlight\"/\"title\" between steps.\n{lang_rule}\nReturn ONLY the JSON, no markdown."
# The legacy prompt above asked a remote model to author executable canvas JS.
# Keep generation declarative: only this local source tree expands templates.
_PROMPT_TEMPLATE = """You are the visual director of a high-quality short educational video.

CONTENT/{mode}:
{content}
{template_hint}

Return one JSON object in this exact shape:
{{
  "title": "Catchy video title (in the OUTPUT LANGUAGE)",
  "description": "One-sentence description",
  "subject": "{subject}",
  "total_steps": {step_count},
  "steps": [
    {{
      "id": 1,
      "voice_text": "Natural two-to-four sentence narration in the OUTPUT LANGUAGE",
      "clear": true,
      "elements": [
        {{"type": "text", "text": "Short step headline", "fontSize": 46, "color": "highlight", "align": "center", "bold": true}},
        {{"type": "custom_js", "template": "<scene name from the catalog>", "params": {{"label": "content for the chosen scene"}}}}
      ]
    }}
  ]
}}

SECURITY AND FORMAT RULES (HARD):
- Every visual is a named local template plus JSON params. Choose a meaning-matched scene for EVERY step.
- NEVER return a `code` field, JavaScript, HTML, CSS, a function, an expression, or a renderer command.
- Use only names from the scene catalog below. Template params are display data only: short labels, items, numbers, icons, colors.
- Give each step a different fitting scene family. Keep labels concise; narration carries long explanations.
- Do not add a backdrop unless the channel rule explicitly asks for one.

AVAILABLE LOCAL SCENES:
{effects}

SCENE POLICY:
{scene_rule}

CONTENT RULES:
- {steps_rule} {hook_rule} {recap_rule}
- Warm, practical, engaging narration. Numbers and labels in params must match narration.
- Alternate outer text color \"highlight\" / \"title\" between steps.
{lang_rule}
Return ONLY the JSON object; no markdown or explanation."""


def _extract_json(text: str) -> dict:
    text = text.strip(); m = re.search("```(?:json)?\\s*(\\{.*\\})\\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    start = text.find("{"); end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Không tìm thấy JSON trong trả lời của AI.")
    raw = text[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # LLMs occasionally emit JS-style backslashes inside JSON strings.
        return json.loads(re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw))

_CUSTOM_LAYOUT_GUARD = r"""

━━━ COLLISION-SAFE TEXT CONTRACT (HARD RULE) ━━━
The normal `text` element is already the visible step headline ABOVE the card.
Inside custom_js, NEVER repeat that headline in ui.title/ui.chip/fillText.
Use the card's top area for a SHORT kicker (maximum 3 words) and start the
actual hero drawing immediately below it. One semantic label must appear only
once on screen.

Keep every literal passed to ui.chip at maximum 3 words / 18 characters.
When a row has 2 or 3 chips, centers must be at least 260px apart and each chip
must pass `{maxWidth:220}`. Keep ui.kpi values short; with 2 KPIs use centers
320 and 760 and `{maxWidth:300}`. Never put prose in a chip or KPI.
All drawing and labels must remain inside x=80..1000 and inside the 880px card.
Reserve cardY+170..cardY+650 for the complete hero, INCLUDING moving icons;
reserve cardY+760..cardY+840 for the bottom KPI/chip row. These zones must not
touch. Phone/browser mockups must end by cardY+680 and wrap every message.
For long explanations, DRAW a diagram and let narration/subtitles carry prose.
Before EVERY ctx.roundRect call, start a fresh path with ctx.beginPath().
Every literal longer than 30 characters must use wrapText; never let fillText
paint a long sentence directly because canvas does not wrap it.
NEVER pass absolute frame coordinates to ui.* while ctx.translate/scale/rotate
is active. Either restore first, or pass LOCAL coordinates such as (0,0);
reusing chartX/chartY after translate applies the offset twice and loses labels.
"""


def _without_repeated_custom_heading(code: str, headline: str) -> str:
    """Drop an AI-authored ui.title/ui.chip that duplicates the outer heading.

    The renderer already draws the text element above a bespoke card. Gemini
    frequently repeats the same literal inside the card, wasting vertical space
    and causing the two titles to collide. This is a narrow, deterministic
    repair; other labels and all drawing code remain untouched.
    """
    wanted = re.sub(r"\s+", " ", str(headline or "")).strip().casefold()
    if not wanted or not code:
        return code

    # Generated custom_js is a sequence of semicolon-terminated statements.
    # Match to that boundary instead of the first ')' because option values
    # commonly contain nested calls such as rc('cyan').
    call_re = re.compile(r"\bui\.(?:title|chip)\s*\([^;]*;", re.DOTALL)
    literal_re = re.compile(r"(['\"])(.*?)\1", re.DOTALL)

    def keep_or_drop(match):
        call = match.group(0)
        for _quote, value in literal_re.findall(call):
            normalized = re.sub(r"\s+", " ", value).strip().casefold()
            if normalized == wanted:
                return ""
        return call

    return call_re.sub(keep_or_drop, code)


def _ui_called_inside_transform(code: str) -> bool:
    """Detect a likely double translation of absolute ui.* coordinates.

    Local calls such as ``translate(iconX, iconY); ui.icon(0, 0, ...)`` are
    valid. The broken pattern reuses the translation origin in ui arguments,
    e.g. ``translate(chartX, chartY); ui.chip(chartX + x, chartY + y, ...)``.
    """
    if not code:
        return False
    token_re = re.compile(
        r"ctx\.(?P<state>save|restore)\s*\("
        r"|ctx\.translate\s*\((?P<tx>[^,;]+),(?P<ty>[^);]+)\)"
        r"|ctx\.(?P<other>scale|rotate)\s*\("
        r"|\bui\.\w+\s*\((?P<ux>[^,;]+),(?P<uy>[^,;]+),"
    )
    saved = []
    transformed = False
    origins = []

    def names(expression):
        return set(re.findall(r"[A-Za-z_$][\w$]*", expression or ""))

    def compact(expression):
        return re.sub(r"\s+", "", expression or "")

    for match in token_re.finditer(code):
        state = match.group("state")
        if state == "save":
            saved.append((transformed, list(origins)))
        elif state == "restore":
            transformed, origins = saved.pop() if saved else (False, [])
        elif match.group("tx") is not None:
            transformed = True
            origins.append((match.group("tx"), match.group("ty")))
        elif match.group("other") is not None:
            transformed = True
        elif transformed:
            ux, uy = match.group("ux"), match.group("uy")
            ui_names = names(ux) | names(uy)
            for tx, ty in origins:
                if compact(ux) in (compact(tx), compact(ty)) or compact(uy) in (
                    compact(tx),
                    compact(ty),
                ):
                    return True
                if ui_names & (names(tx) | names(ty)):
                    return True
    return False


def _custom_layout_issues(code: str) -> list[str]:
    """Reject the small set of generated-JS mistakes that visibly collide."""
    if not code:
        return []
    issues = []
    for match in re.finditer(
        r"\bui\.chip\s*\([^,;]+,[^,;]+,\s*(['\"])(.*?)\1", code, re.DOTALL
    ):
        text = re.sub(r"\s+", " ", match.group(2)).strip()
        if len(text) > 18 or len(text.split()) > 3:
            issues.append(f"chip quá dài: {text[:24]}")
    for match in re.finditer(
        r"\bui\.kpi\s*\([^,;]+,[^,;]+,\s*(['\"])(.*?)\1", code, re.DOTALL
    ):
        text = re.sub(r"\s+", " ", match.group(2)).strip()
        if len(text) > 12:
            issues.append(f"KPI quá dài: {text[:24]}")
    for match in re.finditer(r"\bctx\.fillText\s*\(\s*(['\"])(.*?)\1\s*,", code, re.DOTALL):
        text = re.sub(r"\s+", " ", match.group(2)).strip()
        if len(text) > 30:
            issues.append(f"fillText không wrap: {text[:24]}")

    fresh_path = False
    path_tokens = re.compile(
        r"\bctx\.(?P<begin>beginPath)\s*\("
        r"|\bctx\.(?P<paint>fill|stroke|clip)\s*\("
        r"|\bui\.\w+\s*\("
        r"|\bctx\.(?P<round>roundRect)\s*\("
    )
    for match in path_tokens.finditer(code):
        if match.group("begin"):
            fresh_path = True
        elif match.group("round"):
            if not fresh_path:
                issues.append("ctx.roundRect thiếu ctx.beginPath")
        else:
            fresh_path = False
    return issues


def _height_at_least(element: dict, minimum: int) -> bool:
    """Treat malformed AI height values as non-tall instead of aborting scrub."""
    try:
        return int(element.get("height") or 0) >= minimum
    except (TypeError, ValueError):
        return False


class QuotaWaitError(RuntimeError):
    """Quota model còn lâu mới hồi (reset after nhiều phút) — retry cùng model
        là vô ích. Caller nên ĐỔI provider/model khác thay vì chờ."""
    def __init__(self, msg: str, reset_seconds: int):
        super().__init__(msg)
        self.reset_seconds = reset_seconds

def _parse_reset_seconds(text: str):
    m = re.search("reset after\\s+((?:\\d+\\s*[hms]?\\s*)+)", text, re.I)
    if not m:
        return None
    total, plain = (0, None)
    for num, unit in re.findall("(\\d+)\\s*([hms]?)", m.group(1)):
        n = int(num)
        if unit == "h":
            total += n * 3600
            continue
        elif unit == "m":
            total += n * 60
            continue
        elif unit == "s":
            total += n
            continue
        plain = n
    if total:
        return total
    
    return plain

_QUOTA_SWITCH_THRESHOLD = 120; _JS_STMT = re.compile("ctx\\.|ctx\\[|ui\\.|const\\s|let\\s|var\\s|function\\s|if\\s*\\(|for\\s*\\(|while\\s*\\(|return\\s")
def _fix_inline_comments(code: str) -> str:
    if "//" not in code or code.count("\n") >= 2 or len(code) < 200:
        return code
    out, i, n, q = ([],
        0, len(code),
        None)
    while i < n:
        c = code[i]
        if q:
            if c == "\\" and i + 1 < n:
                out.append(code[i:i + 2])
                i += 2
                continue
            elif c == q:
                q = None
            out.append(c)
            i += 1
            continue
        elif c in "\"'`":
            q = c
            out.append(c)
            i += 1
            continue
        elif c == "/" and i + 1 < n and code[i + 1] == "/":
            j = code.find("\n", i)
            end = j if j != -1 else n
            m = _JS_STMT.search(code, i + 2, end)
            if m:
                out.append(code[i:m.start()] + "\n")
                i = m.start()
                continue
            out.append(code[i:end])
            i = end
            continue
        out.append(c)
        i += 1
    return "".join(out)

def _fallback_providers(primary: str):
    try:
        from core.key_manager import key_manager, PROVIDERS
        order = ["deepseek", "gemini", "claude", "openai", "openrouter", "9router"]
        out = []
        for p in order:
            if p == primary:
                continue
            info = PROVIDERS.get(p) or {}
            if info.get("kind", "llm") != "llm":
                continue
            if info.get("local"):
                st = key_manager.probe_local(p)
                if st.get("running") and st.get("models"):
                    out.append(p)
            elif key_manager.acquire_key(p):
                out.append(p)
        return out
    except Exception:
        return []

def _with_failover(provider: str, model: str, run):
    chain = [(provider, model)] + [(p, "") for p in _fallback_providers(provider)]
    last = None
    for i, (pv, md) in enumerate(chain):
        try:
            return run(pv, md)
        except QuotaWaitError as ex:
            last = ex
            logger.warning("Quota %s còn ~%d phút mới hồi — đổi provider khác (%d/%d).", pv, max(1, ex.reset_seconds // 60), i + 1, len(chain))
        except ai_client.AIError as ex:
            last = ex
            logger.warning("%s lỗi — thử provider kế: %s", pv, str(ex)[:100])
    if last:
        raise last
    raise RuntimeError("AI không phản hồi.")

def _retry_gen(fn, tries: int=4):
    last = None
    for attempt in range(tries):
        try:
            return fn()
        except Exception as ex:
            last = ex
            reset = _parse_reset_seconds(str(ex))
            if reset is not None and reset > _QUOTA_SWITCH_THRESHOLD:
                raise QuotaWaitError(str(ex), reset) from ex
            if attempt >= tries - 1:
                break
            wait = 2.0 * (attempt + 1)
            logger.warning("AI lỗi tạm thời (thử %d/%d), chờ %.0fs: %s", attempt + 1, tries, wait, str(ex)[:120])
            time.sleep(min(wait, 130))
    if last:
        raise last
    raise RuntimeError("AI không phản hồi.")

_OUTLINE_PROMPT = 'Từ ý tưởng sau, hãy lên khung một series video giáo dục ngắn.\n\nÝ TƯỞNG:\n{idea}\n\nTrả về DUY NHẤT JSON:\n{{\n  "project_title": "Tên series hấp dẫn",\n  "description": "Mô tả 1 câu",\n  "subject": "creator_economy | general | tech | science | ...",\n  "lessons": [\n    {{"title": "<số thứ tự tập + tiêu đề cụ thể, viết bằng ngôn ngữ đầu ra>", "brief": "Nội dung chính cần dạy trong tập này (2-3 câu để AI viết kịch bản)"}}\n  ]\n}}\n\nYÊU CẦU:\n- Đúng {lesson_count} tập. Mỗi tập một góc nhìn/khía cạnh riêng, không trùng lặp.\n- Sắp xếp logic: cơ bản → nâng cao. Tập cuối tổng kết.\n- brief đủ chi tiết để viết được kịch bản 12 step.\n{lang_rule}\nTrả về DUY NHẤT JSON.'; _LANG_NAMES = {"vi": "Vietnamese (tiếng Việt)", "en": "English", "es": "Spanish (Español)", "fr": "French (Français)", "de": "German (Deutsch)", "it": "Italian (Italiano)", "ja": "Japanese (日本語)", "nl": "Dutch (Nederlands)", "ko": "Korean (한국어)", "zh": "Chinese (中文)", "pt": "Portuguese (Português)", "hi": "Hindi (हिन्दी)"}
def lang_name(code: str) -> str:
    return _LANG_NAMES.get((code or "vi").split("-")[0], code)

def generate_outline(idea: str, lesson_count: int=5, lang: str="vi", provider: str="", model: str="") -> dict:
    from config import load_settings
    settings = load_settings()
    provider = provider or settings.get("ai_provider", "gemini")
    model = model or settings.get("ai_model", "")
    lesson_count = max(1, int(lesson_count or 1))
    prompt = _OUTLINE_PROMPT.format(idea=idea.strip(), lesson_count=lesson_count, lang_rule=_lang_rule(lang))
    def _gen(pv, md):
        def _once():
            text = ai_client.generate(prompt, system=_SYSTEM, provider=pv, model=md, max_tokens=8000); data = _extract_json(text)
            if not isinstance(data.get("lessons"), list) or len(data["lessons"]) < lesson_count:
                raise ValueError("AI không trả về danh sách tập hợp lệ.")
            data["lessons"] = data["lessons"][:lesson_count]
            return data
        
        return _retry_gen(_once)
    
    return _with_failover(provider, model, _gen)

_LONG_PLAN_PROMPT = 'You are planning ONE long educational video (9:16) about:\n\n{idea}\n\nBreak it into a step-by-step teaching plan. RULES:\n- Total steps: YOU decide from the content, between {lo} and {hi}.\n- Every step teaches exactly ONE idea (2-4 spoken sentences worth). Dense\n  ideas must be SPLIT (do not cram); thin content must NOT be padded with\n  filler or mid-video recaps.\n- Steps flow as one continuous video: step 1 hooks, the final step concludes.\n- Write title/brief in the OUTPUT LANGUAGE below.\n{lang_rule}\nReturn ONLY JSON:\n{{\n  "title": "Video title",\n  "description": "One sentence",\n  "subject": "tech | science | math | general | ...",\n  "steps": [\n    {{"title": "Step headline (short)", "brief": "What exactly this step teaches (1-2 sentences)"}}\n  ]\n}}'

def generate_long_plan(idea: str, lang: str="vi", provider: str="", model: str="", lo: int=15, hi: int=40) -> dict:
    from config import load_settings
    settings = load_settings()
    provider = provider or settings.get("ai_provider", "gemini")
    model = model or settings.get("ai_model", "")
    prompt = _LONG_PLAN_PROMPT.format(idea=idea.strip(), lo=lo, hi=hi, lang_rule=_lang_rule(lang))
    def _gen(pv, md):
        def _once():
            text = ai_client.generate(prompt, system=_SYSTEM, provider=pv, model=md, max_tokens=8000); data = _extract_json(text); steps = data.get("steps")
            if not isinstance(steps, list) or len(steps) < max(6, lo // 2):
                raise ValueError("Dàn ý video dài quá ngắn — sinh lại.")
            data["steps"] = steps[:hi]; return data
        
        return _retry_gen(_once)
    
    return _with_failover(provider, model, _gen)

def generate_lesson_script(content: str, subject: str="general", step_count: int=10,
                           lang: str="vi", provider: str="", model: str="",
                           images: Optional[List[bytes]]=None, template=None,
                           variety_seed=None, avoid_effects=None, part_info=None,
                           series_info=None) -> tuple:
    """Generate, normalize and validate one lesson script.

    Besides validating the JSON schema, this function enforces TubeCraft's
    visual contract: scene-first templates get their channel chrome, foreign
    scenes are replaced, semantic scene guards are applied, elements are
    positioned away from subtitles, and repetitive/empty AI output is retried.
    """
    from config import load_settings

    settings = load_settings()
    provider = provider or settings.get("ai_provider", "gemini")
    model = model or settings.get("ai_model", "")

    tpl = template
    if isinstance(template, str) and template:
        try:
            from core.templates import get_template
            tpl = get_template(template)
        except Exception:
            tpl = None
    if not isinstance(tpl, dict):
        tpl = {}

    structural = {
        "big_word", "stamp_done", "episode_ring", "progress_map",
        "breaking_pill", "news_backdrop", "rocket_finale",
        "light_backdrop", "cosmic_backdrop",
    }
    avoid = [name for name in (avoid_effects or []) if name not in structural]
    prefer = tpl.get("effects") or ([tpl["effect"]] if tpl.get("effect") else _DEFAULT_RICH)
    filtered = [name for name in prefer if name not in set(avoid)]
    prefer = _rotate(filtered or prefer, variety_seed if variety_seed is not None else content)

    try:
        auto_steps = int(step_count) <= 0
    except (TypeError, ValueError):
        auto_steps = False
    if auto_steps:
        step_count = 12
    try:
        step_count = max(1, int(step_count))
    except (TypeError, ValueError):
        step_count = 10

    part = part_info if isinstance(part_info, dict) and int(part_info.get("count", 1) or 1) > 1 else None
    is_first = part is None or int(part.get("index", 1) or 1) == 1
    is_last = part is None or int(part.get("index", 1) or 1) == int(part.get("count", 1) or 1)
    try:
        series = series_info if isinstance(series_info, dict) and int(series_info.get("total", 0) or 0) > 1 else None
    except (TypeError, ValueError):
        series = None

    avoid_note = ""
    if auto_steps:
        avoid_note += (
            "\n⚖️ PACING RULE — YOU choose the step count (8-16) from the content itself: "
            "every step teaches exactly ONE idea in 2-4 spoken sentences. Dense idea → "
            "SPLIT into more steps; thin content → FEWER steps. Never pad or cram.\n"
        )
    if part:
        k, count = int(part["index"]), int(part["count"])
        offset = int(part.get("offset", 0) or 0)
        total = int(part.get("total", step_count) or step_count)
        role = ("This part OPENS the video." if is_first else
                "This is the FINAL part — the video's ONLY recap/outro belongs to its last step."
                if is_last else "This is a MIDDLE part — flow continues on both sides.")
        prev = str(part.get("prev") or "").strip()
        avoid_note += (
            f"\n🎬 ONE LONG VIDEO — PART {k}/{count} (you are writing steps "
            f"{offset + 1}..{offset + step_count} of {total} total). {role} "
            "Do NOT restart the topic, do NOT re-introduce the series."
            + (f" Previous parts already covered: {prev}." if prev else "")
            + " Keep narration flowing as one continuous video.\n"
        )
    if avoid:
        avoid_note += (
            "\n⚠️ SCENES OVERUSED IN PREVIOUS EPISODES — reuse at most 2 of these; "
            "prefer OTHER scenes from the catalog: " + ", ".join(avoid[:10]) + "\n"
        )

    art_directions = [
        "everyday-object metaphor (draw the actual thing discussed, big close-up)",
        "app/web screen mockup with the step's real content inside",
        "stick-figure characters acting out the idea",
        "flow diagram: stations connected by lines with running light particles",
        "symmetric two-column comparison (before/after, do/don't)",
        "horizontal timeline/journey with milestones lighting up in sequence",
        "data chart drawing itself (bars/line/ring) with bold real numbers",
        "mini storytelling scenery (sky, room, road)",
        "dashboard of several small metric tiles",
        "orbit circle: subject at center, factors revolving around it",
    ]
    if not tpl.get("scene_first"):
        chosen = _rotate(art_directions, variety_seed if variety_seed is not None else content)[:3]
        avoid_note += "\n🎨 ART DIRECTIONS FOR THIS EPISODE: " + " · ".join(chosen) + ".\n"

    families = tpl.get("variations") or [
        "flow stations diagram with running particles", "versus twin cards comparison",
        "bar/line chart with real axis + peak callout", "ring-gauge hero with big % in the middle",
        "kpi-hero: one huge number + supporting chips", "phone/browser mockup with real content",
        "horizontal timeline with lighting milestones", "orbit: subject at center, factors revolving",
        "dashboard of small metric tiles", "mini scenery storytelling (room/road/sky)",
    ]
    families = _rotate(families, variety_seed if variety_seed is not None else content)
    plan = [f"  Step {i}: {families[(i - 2) % len(families)]}" for i in range(2, step_count)]
    if plan:
        heading = "VARIETY SUGGESTIONS" if tpl.get("scene_first") else "LAYOUT PLAN — MANDATORY"
        avoid_note += f"\n🗺️ {heading}:\n" + "\n".join(plan) + "\n"

    from core.effects_catalog import effects_menu
    from core.custom_scenes import PROMPT_DOC as scenes_doc
    effects_blob = effects_menu()

    scene_first = bool(tpl.get("scene_first"))
    if scene_first:
        chrome_name = tpl.get("chrome_scene") or "td_chrome"
        prefix = str(tpl.get("scene_prefix") or "").strip()
        headline = "" if tpl.get("no_headline") else (
            '    {"type":"text","text":"HEADLINE","fontSize":52,'
            '"color":"title","align":"center","bold":true},\n'
        )
        effects_blob = "(This channel is SCENE-FIRST; use its prebuilt scenes as the visual backbone.)"
        scene_rule = (
            "THIS CHANNEL IS SCENE-FIRST. Every step uses channel chrome, an optional headline, "
            "and one meaning-matched content scene in this order:\n"
            f'  [{{"type":"custom_js","template":"{chrome_name}","params":{{...}}}},\n'
            + headline +
            '    {"type":"custom_js","template":"<content scene>","params":{...}} ]\n'
            "Use only named templates and params. Never return a code field or raw JavaScript. "
            "Never repeat the same content scene in adjacent steps.\n"
        )
        if prefix:
            scene_rule += f"Only '{prefix}*' content scenes plus {chrome_name} are valid."
        else:
            scene_rule += "Scene catalog: " + scenes_doc + "\nScene menu: " + effects_menu()
    else:
        scene_rule = (
            "Every step must use one named local scene template with JSON params. "
            "Pick a scene that literally fits the narration; do not return raw code.\nScene catalog: "
            + scenes_doc
        )

    if not is_last:
        recap_rule = "Do NOT write any recap/outro step; the final step is normal content."
    elif scene_first:
        recap_rule = "Last step uses the channel's outro scene; do not add a duplicate recap."
    else:
        recap_rule = (
            "Last step is one recap using a result box, title text, and one three-item list; "
            "do not add another custom_js summary card."
        )
    hook_rule = ("Step 1 = strong hook + welcome." if is_first else
                 "Step 1 continues the previous part directly; no hook, welcome, or intro scene.")
    steps_rule = ("Choose the RIGHT number of steps yourself — 8 to 16." if auto_steps
                  else f"Exactly {step_count} steps.")

    prompt = _PROMPT_TEMPLATE.format(
        mode="ẢNH ĐÍNH KÈM" if images else "TEXT",
        content=content or "(xem ảnh đính kèm)",
        subject=subject,
        step_count='"<count you chose>"' if auto_steps else step_count,
        lang_rule=_lang_rule(lang),
        template_hint=_template_hint(tpl) + avoid_note,
        effects=effects_blob,
        scene_rule=scene_rule,
        recap_rule=recap_rule,
        hook_rule=hook_rule,
        steps_rule=steps_rule,
    )
    if not scene_first:
        prompt += _CUSTOM_LAYOUT_GUARD

    def inject_chrome(script: dict) -> dict:
        steps = script.get("steps") or []
        if not scene_first or not steps:
            return script
        chrome_name = tpl.get("chrome_scene") or "td_chrome"
        base = dict(tpl.get("chrome_params") or {})
        for step in steps:
            for element in step.get("elements") or []:
                if isinstance(element, dict) and element.get("template") == chrome_name:
                    base.update(element.get("params") or {})
                    break
        colors = ["cyan", "green", "yellow", "orange", "red"]
        offset = int(part.get("offset", 0) or 0) if part else 0
        total = int(part.get("total", len(steps)) or len(steps)) if part else len(steps)
        chapters = int(base.get("chaps") or min(4, max(2, total // 2)))
        for index, step in enumerate(steps):
            elements = step.get("elements")
            if not isinstance(elements, list):
                continue
            global_index = offset + index + 1
            fill = dict(base)
            title = str(script.get("title") or "")[:40]
            if title:
                fill.setdefault("brand", title)
            fill.setdefault("progress", round(global_index / max(1, total), 3))
            if chrome_name == "td_chrome":
                chapter_no = 1 + (global_index - 1) * chapters // max(1, total)
                fill.setdefault("series", str(script.get("title") or "")[:44])
                fill.update({
                    "ep": global_index,
                    "total": total,
                    "clock": f"{((global_index - 1) * 22) // 60:02d}:{((global_index - 1) * 22) % 60:02d}",
                    "chap_no": chapter_no,
                    "chaps": chapters,
                })
                fill.setdefault("chap", f"PHẦN {chapter_no}")
                fill.setdefault("color", colors[(chapter_no - 1) % len(colors)])
            current = next((e for e in elements if isinstance(e, dict)
                            and e.get("template") == chrome_name), None)
            if current is None:
                elements.insert(0, {"type": "custom_js", "template": chrome_name, "params": fill})
                continue
            params = current.get("params") or {}
            template_name = str(tpl.get("name") or "").strip().lower()
            for key in ("brand", "series"):
                if template_name and isinstance(params.get(key), str) and params[key].strip().lower() == template_name:
                    params.pop(key)
            for key, value in fill.items():
                params.setdefault(key, value)
            current["params"] = params
        return script

    def center_layout(script: dict) -> dict:
        has_anchor = tpl.get("head_anchor") is not None or tpl.get("body_anchor") is not None
        if not scene_first and not has_anchor:
            return script
        chrome_name = tpl.get("chrome_scene") or "td_chrome"
        head_anchor = float(tpl.get("head_anchor", 0.26))
        body_anchor = float(tpl.get("body_anchor", 0.335))
        for step in script.get("steps") or []:
            elements = step.get("elements")
            if not isinstance(elements, list):
                continue
            head = next((e for e in elements if isinstance(e, dict)
                         and e.get("type") == "text"), None)
            body = next((e for e in elements if isinstance(e, dict)
                         and e.get("type") == "custom_js"
                         and e.get("template") != chrome_name), None)
            if head is not None:
                head["x_9_16"], head["y_9_16"] = 0.5, head_anchor
            if body is None:
                continue
            body["x_9_16"] = 0.5
            try:
                height = int(body.get("height") or 800)
            except Exception:
                height = 800
            if tpl.get("center_body"):
                body["y_9_16"] = round(min(0.45, max(0.06, (1920 - height) / 2 / 1920)), 4)
            else:
                body["y_9_16"] = body_anchor
            bottom = float(body["y_9_16"]) * 1920 + height
            # The caption preset is already bottom-anchored at 82%.  Match
            # the original scene contract: only move it when a tall body
            # actually enters that caption band, and leave the minimum gap
            # proportional to the scene bottom.
            if bottom > 1470:
                step["subtitle_y_pct_9_16"] = round(
                    min(0.88, max(0.84, (bottom + 90) / 1920)), 3
                )
        return script

    light_styles = {"watercolor", "inkwash", "sketch", "pastel", "aurora", "sketchnote"}
    backdrops = {"light_backdrop", "news_backdrop", "cosmic_backdrop"}

    def safe_template_for(step_index: int) -> str:
        from core import custom_scenes

        prefix_name = str(tpl.get("scene_prefix") or "").strip()
        candidates = (
            ([prefix_name + "formula", prefix_name + "title", prefix_name + "outro"] if prefix_name else [])
            + list(prefer)
            + ["counter_metric", "bar_compare", "flow_pipeline", "orbit_ecosystem", "big_word"]
        )
        for name in _rotate(candidates, step_index):
            if custom_scenes.expand(name, {}) is not None:
                return name
        return "big_word"

    def normalize_ai_visuals(script: dict) -> dict:
        """Discard model-authored code and keep every generated step renderable."""
        from core import custom_scenes

        for step_index, step in enumerate(script.get("steps") or []):
            elements = step.get("elements")
            if not isinstance(elements, list):
                continue
            headline = next(
                (str(item.get("text") or "").strip() for item in elements
                 if isinstance(item, dict) and item.get("type") == "text"),
                "",
            )
            has_visual = False
            for element in elements:
                if not isinstance(element, dict) or element.get("type") != "custom_js":
                    continue
                name = str(element.get("template") or "").strip().lower()
                if name and custom_scenes.expand(name, element.get("params")) is not None:
                    element.pop("code", None)
                    element.pop("trusted_template", None)
                    has_visual = True
                    continue
                name = safe_template_for(step_index)
                params = {"word": headline[:60], "sub": ""} if name == "big_word" else {}
                element.clear()
                element.update({"type": "custom_js", "template": name, "params": params})
                has_visual = True
            if not has_visual:
                name = safe_template_for(step_index)
                params = {"word": headline[:60], "sub": ""} if name == "big_word" else {}
                elements.append({"type": "custom_js", "template": name, "params": params})
            if not scene_first:
                visuals = [
                    element for element in elements
                    if isinstance(element, dict) and element.get("type") == "custom_js"
                ]
                if len(visuals) > 1:
                    hero_name = str(tpl.get("effect") or "").strip().lower()
                    hero = next(
                        (element for element in visuals
                         if str(element.get("template") or "").strip().lower() == hero_name),
                        visuals[0],
                    )
                    step["elements"] = [
                        element for element in elements
                        if not (isinstance(element, dict) and element.get("type") == "custom_js")
                        or element is hero
                    ]
        return script

    def scrub(script: dict) -> dict:
        normalize_ai_visuals(script)
        inject_chrome(script)
        template_name = str(tpl.get("name") or "").strip()
        video_title = str(script.get("title") or "").strip()
        if scene_first and template_name and video_title and template_name.lower() != video_title.lower():
            pattern = re.compile(re.escape(template_name), re.IGNORECASE)
            for step in script.get("steps") or []:
                voice = step.get("voice_text")
                if isinstance(voice, str) and pattern.search(voice):
                    step["voice_text"] = pattern.sub(video_title, voice)
                for element in step.get("elements") or []:
                    if not isinstance(element, dict) or element.get("type") != "custom_js":
                        continue
                    params = element.get("params")
                    if not isinstance(params, dict):
                        continue
                    for key in ("brand", "name", "series", "term"):
                        value = params.get(key)
                        if isinstance(value, str) and value.strip().lower() == template_name.lower():
                            params[key] = video_title

        chrome_name = tpl.get("chrome_scene") or "td_chrome"
        if scene_first:
            for step in script.get("steps") or []:
                elements = step.get("elements")
                if not isinstance(elements, list):
                    continue
                kept, has_body = [], False
                for element in elements:
                    is_body = (isinstance(element, dict)
                               and element.get("type") == "custom_js"
                               and element.get("template") != chrome_name)
                    if is_body and has_body:
                        continue
                    has_body = has_body or is_body
                    kept.append(element)
                step["elements"] = kept

        prefix = str(tpl.get("scene_prefix") or "").strip()
        if scene_first and prefix:
            from core.custom_scenes import has_scene
            intro_name, fallback_name, outro_name = prefix + "title", prefix + "formula", prefix + "outro"
            steps = script.get("steps") or []
            last_index = len(steps) - 1
            for step_index, step in enumerate(steps):
                voice = str(step.get("voice_text") or "")
                for element in step.get("elements") or []:
                    if not isinstance(element, dict) or element.get("type") != "custom_js":
                        continue
                    name = str(element.get("template") or "")
                    if not name or name == chrome_name or name.startswith(prefix) or str(element.get("code") or "").strip():
                        continue
                    params = element.get("params") if isinstance(element.get("params"), dict) else {}
                    if step_index == 0 and is_first and has_scene(intro_name):
                        element["template"] = intro_name
                        element["params"] = {
                            "kicker": str(params.get("kicker") or ""),
                            "word": str(params.get("word") or params.get("title") or params.get("text") or ""),
                            "sub": str(params.get("sub") or params.get("subtitle") or params.get("line") or ""),
                        }
                    elif step_index == last_index and is_last and has_scene(outro_name):
                        line = str(params.get("line") or params.get("sub") or params.get("tagline") or params.get("text") or "")
                        element["template"] = outro_name
                        element["params"] = {"brand": str(script.get("title") or ""),
                                             "name": str(script.get("title") or ""),
                                             "line": line, "tagline": line}
                    elif has_scene(fallback_name):
                        element["template"] = fallback_name
                        element["params"] = _guard_swap_params(params, voice)
                    logger.warning("Cảnh %s ngoài bộ %s* — đổi sang %s.",
                                   name, prefix, element.get("template"))

        if scene_first:
            for step in script.get("steps") or []:
                voice = str(step.get("voice_text") or "")
                for element in step.get("elements") or []:
                    if not isinstance(element, dict) or element.get("type") != "custom_js":
                        continue
                    if str(element.get("code") or "").strip():
                        continue
                    if prefix and element.get("template") == prefix + "title":
                        params = element.get("params") if isinstance(element.get("params"), dict) else {}
                        if not str(params.get("word") or "").strip():
                            params["word"] = str(script.get("title") or "")[:30]
                        kicker = str(params.get("kicker") or "").strip()
                        if series:
                            labels = {"vi": "TẬP", "en": "EPISODE"}
                            label = labels.get(str(lang or "vi")[:2].lower(), "EP.")
                            params["kicker"] = f"{label} {int(series.get('index', 1))}"
                        elif re.match(r"^(tập|tap|ep(isode)?|bài|bai|part|phần|phan)\W*\d+$",
                                      kicker, re.IGNORECASE):
                            params["kicker"] = ""
                        element["params"] = params
                        continue
                    keywords = _SCENE_GUARDS.get(element.get("template"), ())
                    if not keywords:
                        continue
                    params = element.get("params") if isinstance(element.get("params"), dict) else {}
                    parts = [voice, str(step.get("title") or "")]
                    for key, value in params.items():
                        if key in ("kind", "fn", "mode", "accent"):
                            continue
                        if isinstance(value, str):
                            parts.append(value)
                        elif isinstance(value, list):
                            parts.extend(str(item) for item in value if isinstance(item, str))
                    haystack = " ".join(parts).lower()
                    if any(keyword in haystack for keyword in keywords):
                        continue
                    logger.warning("Guard ngữ nghĩa: cảnh %s không khớp nội dung step — đổi sang mn_formula.",
                                   element.get("template"))
                    element["params"] = _guard_swap_params(params, voice)
                    element["template"] = "mn_formula"

        if scene_first and prefix:
            import zlib
            seed_base = zlib.crc32(str(script.get("title") or "").encode("utf-8"))
            for step_index, step in enumerate(script.get("steps") or []):
                for element in step.get("elements") or []:
                    if not isinstance(element, dict) or element.get("type") != "custom_js":
                        continue
                    name = str(element.get("template") or "")
                    if not name.startswith(prefix) or name == chrome_name or str(element.get("code") or "").strip():
                        continue
                    params = element.get("params") if isinstance(element.get("params"), dict) else {}
                    params.setdefault("seed", int((seed_base + step_index * 97) % 9973))
                    element["params"] = params

        if scene_first and tpl.get("no_headline"):
            for step in script.get("steps") or []:
                elements = step.get("elements")
                if not isinstance(elements, list):
                    continue
                texts = [e for e in elements if isinstance(e, dict) and e.get("type") == "text"
                         and str(e.get("text") or "").strip()]
                if texts:
                    body = next((e for e in elements if isinstance(e, dict)
                                 and e.get("type") == "custom_js"
                                 and e.get("template") != chrome_name), None)
                    if body is not None:
                        params = body.get("params") if isinstance(body.get("params"), dict) else {}
                        if not str(params.get("title") or "").strip():
                            params["title"] = str(texts[0].get("text", "")).strip()[:60]
                        body["params"] = params
                    step["elements"] = [e for e in elements
                                        if not (isinstance(e, dict) and e.get("type") == "text")]

        for step in script.get("steps") or []:
            elements = step.get("elements")
            if not isinstance(elements, list):
                continue
            headline = next(
                (str(e.get("text") or "").strip() for e in elements
                 if isinstance(e, dict) and e.get("type") == "text"
                 and str(e.get("text") or "").strip()),
                "",
            )
            for element in elements:
                if not isinstance(element, dict) or element.get("type") != "custom_js":
                    continue
                element.pop("fontSize", None)
                if element.get("code"):
                    code = _fix_inline_comments(element["code"])
                    if not scene_first:
                        code = _without_repeated_custom_heading(code, headline)
                    element["code"] = code
                    try:
                        tall_center_anchor = (
                            not scene_first
                            and int(element.get("height") or 0) >= 800
                            and float(element.get("x_9_16")) == 0.5
                            and float(element.get("y_9_16")) == 0.5
                        )
                    except (TypeError, ValueError):
                        tall_center_anchor = False
                    if tall_center_anchor:
                        element.pop("x_9_16", None)
                        element.pop("y_9_16", None)
            if not scene_first and any(
                isinstance(element, dict)
                and element.get("type") == "custom_js"
                and not element.get("template")
                and _height_at_least(element, 800)
                and "y_9_16" not in element
                for element in elements
            ):
                step.setdefault("subtitle_y_pct_9_16", 0.86)
            if (tpl.get("art_style") or "") in light_styles:
                step["elements"] = [e for e in elements if not
                                    (isinstance(e, dict) and e.get("template") in backdrops)]
        return script

    def generate_with(pv, md):
        def once():
            text = ai_client.generate(prompt, system=_SYSTEM, provider=pv, model=md,
                                      images=images, max_tokens=32_000)
            script = _extract_json(text)
            if not script.get("steps"):
                raise ValueError("Kịch bản rỗng.")
            output, errors = validate_script(scrub(script))
            steps = output.get("steps") or []
            if auto_steps:
                if not 8 <= len(steps) <= 16:
                    raise ValueError(
                        f"AI chọn {len(steps)} step; chế độ tự động yêu cầu 8–16 step."
                    )
            elif len(steps) != step_count:
                raise ValueError(
                    f"AI trả {len(steps)} step; yêu cầu chính xác {step_count} step."
                )
            visual = sum(any(isinstance(e, dict) and e.get("type") == "custom_js"
                             and (str(e.get("code") or "").strip() or e.get("template"))
                             for e in (step.get("elements") or [])) for step in steps)
            allowance = 1 if is_last else 0
            if visual < max(1, len(steps) - allowance):
                raise ValueError(f"Kịch bản nghèo hình ({visual}/{len(steps)} step có hình) — sinh lại.")
            transformed_ui = sum(
                _ui_called_inside_transform(str(element.get("code") or ""))
                for step in steps
                for element in (step.get("elements") or [])
                if isinstance(element, dict)
                and element.get("type") == "custom_js"
                and not element.get("template")
            )
            if transformed_ui:
                raise ValueError(
                    f"Có {transformed_ui} cảnh gọi ui.* khi canvas đang transform — "
                    "sinh lại để tránh nhãn trôi khỏi card."
                )
            layout_issues = [
                issue
                for step in steps
                for element in (step.get("elements") or [])
                if isinstance(element, dict)
                and element.get("type") == "custom_js"
                and not element.get("template")
                for issue in _custom_layout_issues(str(element.get("code") or ""))
            ]
            if layout_issues:
                raise ValueError(
                    "Cảnh có nguy cơ chồng lấn: " + "; ".join(layout_issues[:4])
                )
            js_errors = check_custom_js(output)
            if js_errors:
                raise ValueError("Custom JS lỗi cú pháp: " + "; ".join(js_errors[:4]))
            signatures = {}
            for step in steps:
                for element in step.get("elements") or []:
                    if not isinstance(element, dict) or element.get("type") != "custom_js":
                        continue
                    code = str(element.get("code") or "").strip()
                    if not code or element.get("template"):
                        continue
                    signature = re.sub(r"'[^']*'|\"[^\"]*\"|\d+", "", code)
                    signature = re.sub(r"\s+", "", signature)[:400]
                    signatures[signature] = signatures.get(signature, 0) + 1
            if signatures:
                duplicate = max(signatures.values())
                if duplicate > max(2, len(steps) // 3):
                    raise ValueError(
                        f"Kịch bản rập khuôn ({duplicate}/{len(steps)} step cùng một khối hình) — "
                        "sinh lại theo LAYOUT PLAN."
                    )
            center_layout(output)
            return output, errors
        return _retry_gen(once)

    return _with_failover(provider, model, generate_with)
