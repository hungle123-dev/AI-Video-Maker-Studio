"""core/voices.py — Danh mục giọng đọc gộp của mọi engine, lọc theo ngôn ngữ.

Một chỗ duy nhất để UI hỏi "engine X, ngôn ngữ Y thì có giọng nào?", thay vì mỗi
dialog tự hardcode một danh sách.

  edge     — Microsoft Edge TTS, miễn phí, ~450 giọng / 90+ ngôn ngữ (có vi)
  gtts     — Google Translate TTS, miễn phí, một giọng theo ngôn ngữ
  deepgram — Aura-2, giọng rất tự nhiên, 7 ngôn ngữ (KHÔNG có vi)
  everai   — chỉ tiếng Việt
  vivibe   — 13 giọng tiếng Việt qua tài khoản Vivibe

Danh sách edge lấy động (có cache 7 ngày) để thêm giọng mới không phải sửa code.
"""
import json, logging, time
from typing import List, Tuple
from config import DATA_DIR; logger = logging.getLogger("TubeCraft.Voices")
LANGUAGES: List[Tuple[str, str]] = [("vi", "Tiếng Việt"), ("en", "English"), ("es", "Español (Spanish)"), ("fr", "Français (French)"), ("de", "Deutsch (German)"), ("it", "Italiano (Italian)"), ("ja", "日本語 (Japanese)"), ("nl", "Nederlands (Dutch)"), ("ko", "한국어 (Korean)"), ("zh", "中文 (Chinese)"), ("pt", "Português (Portuguese)"), ("hi", "हिन्दी (Hindi)")]
ENGINES = [("edge", "Edge TTS — miễn phí, nhiều ngôn ngữ"), ("gtts", "Google TTS — miễn phí, không cần key"), ("deepgram", "Deepgram Aura — tự nhiên nhất (cần key)"), ("everai", "EverAI — tiếng Việt chất lượng cao (cần key)"), ("vivibe", "Vivibe — 13 giọng Việt qua tài khoản")]; _EDGE_CACHE = DATA_DIR / "edge_voices.json"; _TTL = 604_800
def _edge_all() -> List[dict]:
    try:
        cached = json.loads(_EDGE_CACHE.read_text(encoding="utf-8"))
        if time.time() - cached.get("at", 0) < _TTL:
            return cached["voices"]
    except Exception:
        cached = None
    try:
        import asyncio
        import edge_tts
        voices = asyncio.run(edge_tts.list_voices())
        out = []
        for v in voices:
            short = v["ShortName"]
            lang = short.split("-")[0]
            person = short.split("-")[2].replace("Neural", "") if len(short.split("-")) > 2 else short
            gender = "nữ" if v.get("Gender") == "Female" else "nam"
            locale = "-".join(short.split("-")[:2])
            out.append({"id": short, "lang": lang, "display": f"{person} — {gender} ({locale})"})
        out.sort(key=lambda x: (x["lang"], x["display"]))
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            _EDGE_CACHE.write_text(json.dumps({"at": time.time(), "voices": out}, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        return out
    except Exception as e:
        logger.warning(f"Không lấy được danh sách giọng Edge: {e}")
        return (cached or {}).get("voices", []) if cached else []

def list_voices(engine: str, lang: str) -> List[dict]:
    base = (lang or "").split("-")[0]
    if engine == "edge":
        return [v for v in _edge_all() if v["lang"] == base]
    if engine == "gtts":
        try:
            from gtts.lang import tts_langs
            supported = tts_langs()
            if base not in supported:
                return []
            label = dict(LANGUAGES).get(base, supported[base])
            return [{"id": base, "lang": base, "display": f"Google TTS — {label}"}]
        except Exception as e:
            logger.warning(f"Google TTS: {e}")
            return []
    if engine == "deepgram":
        try:
            from core.tts_deepgram import list_voices as dg
            return dg(base)
        except Exception as e:
            logger.warning(f"Deepgram: {e}")
            return []
    if engine == "everai":
        if base != "vi":
            return []
        from core.tts_everai import EVERAI_VOICES
        return [{"id": v["id"], "display": v["name"]} for v in EVERAI_VOICES]
    if engine == "vivibe":
        if base != "vi":
            return []
        from core.tts_vivibe import VIVIBE_VOICES
        return [dict(voice, lang="vi") for voice in VIVIBE_VOICES]
    return []

def supports(engine: str, lang: str) -> bool:
    return bool(list_voices(engine, lang))

def unsupported_msg(engine: str, lang: str) -> str:
    name = dict(ENGINES).get(engine, engine); lang_name = dict(LANGUAGES).get(lang, lang)
    if engine == "deepgram":
        return f"⚠️ Deepgram Aura không có giọng {lang_name}. Hỗ trợ: English, Español, Français, Deutsch, Italiano, 日本語, Nederlands. Dùng Edge TTS cho ngôn ngữ khác."
    elif engine == "everai":
        return f"⚠️ EverAI chỉ có giọng tiếng Việt, không đọc được {lang_name}."
    elif engine == "vivibe":
        return f"⚠️ Vivibe chỉ có giọng tiếng Việt, không đọc được {lang_name}."
    
    return f"⚠️ {name} không có giọng {lang_name}."
