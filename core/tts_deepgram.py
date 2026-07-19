"""core/tts_deepgram.py — Engine giọng đọc Deepgram Aura.

Vì sao thêm: Aura-2 cho giọng rất tự nhiên ở 7 ngôn ngữ (en/es/fr/de/it/ja/nl).
KHÔNG có tiếng Việt — dùng Edge TTS hoặc EverAI cho tiếng Việt.

Điểm khó: /v1/speak CHỈ trả audio, không có timing từng chữ, trong khi renderer
cần timing để highlight chữ theo lời đọc. Giải: cho chính Deepgram STT (/v1/listen)
nghe lại audio vừa sinh — nó trả word-level timestamps. Cùng một API key, và
transcript khớp gần như tuyệt đối vì audio do chính nó đọc.

Danh mục giọng lấy động từ GET /v1/models (102 giọng lúc viết) và cache trên đĩa,
nên thêm giọng mới ở phía Deepgram là app tự thấy.
"""
import json, logging, time
from pathlib import Path
from typing import List, Tuple
import requests
from config import DATA_DIR
from core.key_manager import key_manager; logger = logging.getLogger("TubeCraft.Deepgram"); BASE = "https://api.deepgram.com/v1"; SPEAK_URL = f"{BASE}/speak"; LISTEN_URL = f"{BASE}/listen"; MODELS_URL = f"{BASE}/models"; LANGUAGES = {"en": "English", "es": "Español (Spanish)", "fr": "Français (French)", "de": "Deutsch (German)", "it": "Italiano (Italian)", "ja": "日本語 (Japanese)", "nl": "Nederlands (Dutch)"}; _STT_MODEL = {"en": "nova-3"}; _STT_DEFAULT = "nova-2"; _CACHE_FILE = DATA_DIR / "deepgram_voices.json"; _CACHE_TTL = 604_800
class DeepgramError(Exception):
    pass

def _auth_header() -> dict:
    entry = key_manager.acquire_key("deepgram")
    if not entry:
        raise DeepgramError("Chưa có key Deepgram — thêm ở tab Key AI Cloud (mục API TTS).")
    return {"Authorization": f"Token {entry["key"]}"}

def _fetch_voices() -> List[dict]:
    try:
        headers = _auth_header()
    except DeepgramError:
        # The public model catalogue can be queried without a token.  Keeping
        # this fallback lets the voice picker work before a key is configured.
        headers = {}

    r = requests.get(MODELS_URL, headers=headers, timeout=30)
    if r.status_code != 200:
        raise DeepgramError(f"GET /models lỗi HTTP {r.status_code}: {r.text[:120]}")

    out = []
    for model in r.json().get("tts") or []:
        name = model.get("canonical_name") or model.get("name")
        languages = model.get("languages") or []
        if not name or not languages:
            continue
        metadata = model.get("metadata") or {}
        base_lang = next(
            (value for value in languages if "-" not in value),
            languages[0].split("-")[0],
        )
        out.append(
            {
                "id": name,
                "lang": base_lang,
                "arch": model.get("architecture", ""),
                "accent": metadata.get("accent", ""),
                "tags": metadata.get("tags", []) or [],
                "display": _display_name(name, metadata),
            }
        )
    out.sort(key=lambda voice: (voice["lang"], voice["arch"] != "aura-2", voice["id"]))
    return out

def _display_name(model_id: str, meta: dict) -> str:
    parts = model_id.split("-")
    person = parts[2].capitalize() if len(parts) > 2 else model_id
    tags = [tag for tag in (meta.get("tags") or [])]
    gender = "nữ" if "feminine" in tags else ("nam" if "masculine" in tags else "")
    traits = ", ".join(tag for tag in tags if tag not in ("feminine", "masculine"))[:34]
    bits = [value for value in (gender, meta.get("accent", ""), traits) if value]
    return f"{person} — {' · '.join(bits)}" if bits else person

def list_voices(lang: str="", refresh: bool=False) -> List[dict]:
    data = None
    if not refresh:
        try:
            cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - cached.get("at", 0) < _CACHE_TTL:
                data = cached.get("voices")
        except Exception:
            data = None

    if data is None:
        data = _fetch_voices()
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_text(
                json.dumps({"at": time.time(), "voices": data}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    if lang:
        base = lang.split("-")[0]
        data = [voice for voice in data if voice["lang"] == base]
    return data

def supports(lang: str) -> bool:
    return (lang or "").split("-")[0] in LANGUAGES

def synthesize(text: str, voice: str, output_path: str, with_words: bool=True, lang: str="en") -> Tuple[(bool, list)]:
    headers = dict(_auth_header())
    api_key = headers["Authorization"].removeprefix("Token ")
    headers["Content-Type"] = "application/json"
    
    url = f"{SPEAK_URL}?model={voice}&encoding=mp3&bit_rate=48000"; r = requests.post(url, headers=headers, json={"text": text}, timeout=120)
    if r.status_code != 200:
        if r.status_code in (401, 402, 429):
            key_manager.report_error("deepgram", api_key, quota=r.status_code == 429)
        raise DeepgramError(f"Deepgram /speak HTTP {r.status_code}: {r.text[:160]}")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "wb") as f:
        f.write(r.content)
    
    if Path(output_path).stat().st_size <= 100:
        raise DeepgramError("Deepgram trả file rỗng.")
    elif not with_words:
        return (True,
            [])
    
    return (True, word_timings(output_path, lang=lang))

def word_timings(audio_path: str, lang: str="en") -> list:
    base = (lang or "en").split("-")[0]
    model = _STT_MODEL.get(base, _STT_DEFAULT)
    try:
        headers = dict(_auth_header())
        headers["Content-Type"] = "audio/mpeg"
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                f"{LISTEN_URL}?model={model}&language={base}&smart_format=false&punctuate=false",
                headers=headers,
                data=audio_file.read(),
                timeout=120,
            )
        if response.status_code != 200:
            logger.warning(
                f"Deepgram STT HTTP {response.status_code}: {response.text[:120]}"
            )
            return []

        alternative = response.json()["results"]["channels"][0]["alternatives"][0]
        from engines.audio_engine import _normalize_word

        return [
            {
                "word": word["word"],
                "norm": _normalize_word(word["word"]),
                "start": round(float(word["start"]), 3),
                "end": round(float(word["end"]), 3),
            }
            for word in alternative.get("words", [])
        ]
    except Exception as exc:
        logger.warning(f"Deepgram không lấy được word timing: {exc}")
        return []

def test_key() -> dict:
    try:
        r = requests.get(f"{BASE}/auth/token", headers=_auth_header(), timeout=20)
    except DeepgramError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"Không kết nối được: {exc}"}

    if r.status_code == 200:
        try:
            n = len(list_voices())
        except Exception:
            n = 0
        return {"ok": True, "error": "", "voice_count": n}
    return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:120]}"}
