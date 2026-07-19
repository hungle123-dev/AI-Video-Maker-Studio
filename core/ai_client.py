"""core/ai_client.py — Gọi LLM đa provider qua KeyManager.

Một hàm duy nhất `generate(prompt, ...)` cho toàn app:
  - Lấy key round-robin từ key_manager (local → env).
  - 429/quota → báo key_manager cho key nghỉ, tự thử key kế tiếp.
  - 401/403 → tắt key, thử key kế tiếp.
  - Claude đi qua SDK `anthropic` chính thức; Gemini qua REST;
    OpenAI/DeepSeek/OpenRouter qua REST chuẩn OpenAI.

Hỗ trợ ảnh đầu vào (vision) cho Gemini / Claude / OpenAI-compatible.
"""
import base64, json, logging
from typing import Optional, List
import requests
from core.key_manager import key_manager, PROVIDERS; logger = logging.getLogger("TubeCraft.AI"); MAX_KEY_ATTEMPTS = 4
class AIError(Exception):
    pass

def generate(prompt: str, system: str="", provider: str="gemini", model: str="", images: Optional[List[bytes]]=None, max_tokens: int=16_000, timeout: int=300) -> str:
    if provider not in PROVIDERS:
        raise AIError(f"Provider không hỗ trợ: {provider}")
    elif PROVIDERS[provider].get("kind") != "llm":
        raise AIError(f"{PROVIDERS[provider]["name"]} là API TTS, không dùng để sinh nội dung.")
    model = model or PROVIDERS[provider]["default_model"]
    if provider == "gemini" and model in {"gemini-2.5-flash", "gemini-2.5-pro"}:
        model = PROVIDERS[provider]["default_model"]
    if not model and PROVIDERS[provider].get("local"):
        st = key_manager.probe_local(provider)
        if not st["running"]:
            raise AIError(f'{PROVIDERS[provider]["name"]} không chạy tại {PROVIDERS[provider]["base_url"]} — mở 9Router rồi thử lại.')
        if not st["models"]:
            raise AIError(f'{PROVIDERS[provider]["name"]} chưa có model nào.')
        model = st["models"][0]
    if not model:
        raise AIError(f"Chưa chọn model cho {provider} (xem Cài đặt).")
    last_err = "Không có key khả dụng."
    attempted = set()
    for _ in range(MAX_KEY_ATTEMPTS):
        entry = key_manager.acquire_key(provider)
        if not entry:
            break
        key = entry["key"]
        identity = (entry.get("source"), key)
        if identity in attempted:
            break
        attempted.add(identity)
        try:
            if provider == "claude":
                return _call_claude(key, model, prompt, system, images, max_tokens, timeout)
            if provider == "gemini":
                return _call_gemini(key, model, prompt, system, images, max_tokens, timeout)
            return _call_openai_compat(provider, key, model, prompt, system, images, max_tokens, timeout)
        except _TempError as e:
            raise AIError(f"[{provider}/{model}] {e}")
        except _QuotaError as e:
            key_manager.report_error(provider, key, quota=True, message=str(e))
            last_err = f"Quota: {e}"
        except _AuthError as e:
            key_manager.report_error(provider, key, quota=False, message=str(e))
            last_err = f"Key bị từ chối: {e}"
        except Exception as e:
            last_err = str(e)
            logger.warning(f'{provider}/{entry["label"]}: {e}')
            break
    raise AIError(f"[{provider}/{model}] {last_err}")

class _QuotaError(Exception):
    pass

class _AuthError(Exception):
    pass

class _TempError(Exception):
    """Lỗi TẠM THỜI (rate-limit 'reset after Ns', model bận/overload) — thử lại
        được, KHÔNG phải key hỏng. Không cool key; để lớp trên retry sau khi chờ."""

def _raise_for_status(status: int, body: str):
    if status == 429:
        # A provider's per-key rate/quota limit is exactly why the key store
        # exists: cool this key and let generate() try the next one.
        raise _QuotaError(f"HTTP {status}: {body[:180]}")
    if status in (408, 500, 502, 503, 504, 529):
        raise _TempError(f"HTTP {status}: {body[:180]}")
    if status in (401, 403):
        raise _AuthError(f"HTTP {status}: {body[:150]}")
    if status >= 400:
        raise RuntimeError(f"HTTP {status}: {body[:300]}")

def _call_claude(key, model, prompt, system, images, max_tokens, timeout) -> str:
    import anthropic; client = anthropic.Anthropic(api_key=key, timeout=float(timeout), max_retries=0); content = []
    for img in images or []:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.standard_b64encode(img).decode("utf-8")}})
    content.append({"type": "text", "text": prompt})
    
    try:
        with client.messages.stream(model=model, max_tokens=max_tokens, system=system or anthropic.NOT_GIVEN, thinking={"type": "adaptive"}, messages=[{"role": "user", "content": content}]) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            raise RuntimeError("Claude từ chối yêu cầu (safety refusal).")
        return "".join(b.text for b in msg.content if b.type == "text")
    except anthropic.RateLimitError as e:
        raise _QuotaError(str(e)[:150])
    
    except anthropic.AuthenticationError as e:
        raise _AuthError(str(e)[:150])
    except anthropic.PermissionDeniedError as e:
        raise _AuthError(str(e)[:150])
    
    except anthropic.APIStatusError as e:
        if e.status_code == 429:
            raise _QuotaError(f"HTTP {e.status_code}")
        if e.status_code >= 500:
            raise _TempError(f"server {e.status_code}")
        if e.status_code in (401, 403):
            raise _AuthError(f"HTTP {e.status_code}")
        raise RuntimeError(str(e)[:300])

def _call_gemini(key, model, prompt, system, images, max_tokens, timeout) -> str:
    parts = []
    for img in images or []:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.standard_b64encode(img).decode("utf-8")}})
    parts.append({"text": prompt}); body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = requests.post(
        f"{PROVIDERS["gemini"]["base_url"]}/v1beta/models/{model}:generateContent",
        headers={"X-goog-api-key": key},
        json=body,
        timeout=timeout,
    )
    
    _raise_for_status(r.status_code, r.text); data = r.json()
    
    try:
        return "".join((p.get("text", "") for p in data["candidates"][0]["content"]["parts"]))
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini trả về bất thường: {json.dumps(data)[:200]}")

def _wants_completion_tokens(model: str) -> bool:
    m = (model or "").lower()
    return any((k in m for k in ("gpt-5", "gpt5", "codex", "o1", "o3", "o4", "reasoning")))

def _call_openai_compat(provider, key, model, prompt, system, images, max_tokens, timeout) -> str:
    content = []
    for img in images or []:
        b64 = base64.standard_b64encode(img).decode("utf-8")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    content.append({"type": "text", "text": prompt}); messages = []
    if system:
        messages.append({"role": "system", "content": system})
    
    messages.append({"role": "user", "content": content if images else prompt}); url = f"{PROVIDERS[provider]["base_url"]}/chat/completions"; headers = {"Authorization": f"Bearer {key}"}; tok_key = "max_completion_tokens" if _wants_completion_tokens(model) else "max_tokens"
    def _post(tk):
        payload = {"model": model, "messages": messages, tk: max_tokens}
        return requests.post(url, headers=headers, json=payload, timeout=timeout)
    
    r = _post(tok_key)
    if r.status_code == 400 and ("max_completion_tokens" in r.text or "max_tokens" in r.text):
        other = "max_tokens" if tok_key == "max_completion_tokens" else "max_completion_tokens"
        r = _post(other)
    _raise_for_status(r.status_code, r.text)
    data = r.json()
    try:
        msg = data["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content") or ""
    except (KeyError, IndexError):
        raise RuntimeError(f"{provider} trả về bất thường: {json.dumps(data)[:200]}")
