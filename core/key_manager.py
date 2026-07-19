"""core/key_manager.py — PHẦN 1: Quản lý key AI cloud.

Kho key được thiết kế cho luồng desktop độc lập:

  - Key lưu bằng Windows DPAPI (core.crypto, theo Windows user) trong data/keys.enc.json.
  - Mỗi provider giữ NHIỀU key; xoay vòng round-robin thật sự (con trỏ lưu
    theo provider) thay vì "lấy key active đầu tiên".
  - Key lỗi quota bị đánh dấu cooldown có thời hạn (tự sống lại) thay vì
    tắt vĩnh viễn phải bật tay.
  - Nguồn dự phòng cuối: biến môi trường của provider.

Mọi truy cập qua singleton `key_manager`.
"""
import os, json, time, logging, threading
from datetime import datetime
from typing import Optional, List
from config import KEYS_FILE
from core.crypto import encrypt_value, decrypt_value, is_dpapi_value; logger = logging.getLogger("TubeCraft.Keys"); QUOTA_COOLDOWN = 900

PROVIDERS = {"gemini": {"name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com", "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite"], "default_model": "gemini-3.5-flash", "env_var": "GEMINI_API_KEY", "vision": True}, "openai": {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"], "default_model": "gpt-4o-mini", "env_var": "OPENAI_API_KEY", "vision": True}, "claude": {"name": "Anthropic Claude", "base_url": "https://api.anthropic.com/v1", "models": ["claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5"], "default_model": "claude-opus-4-8", "env_var": "ANTHROPIC_API_KEY", "vision": True}, "deepseek": {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-reasoner"], "default_model": "deepseek-chat", "env_var": "DEEPSEEK_API_KEY", "vision": False}, "9router": {"name": "9Router (proxy local)", "base_url": "http://localhost:20128/v1", "models": [], "default_model": "", "env_var": "", "vision": False, "local": True}, "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "models": ["anthropic/claude-sonnet-4.6", "google/gemini-3-flash-preview", "openai/gpt-5-mini", "x-ai/grok-4.1-fast"], "default_model": "google/gemini-3-flash-preview", "env_var": "OPENROUTER_API_KEY", "vision": True}, "everai": {"name": "EverAI TTS", "base_url": "https://everai.vn/api/v1", "models": ["tts"], "default_model": "tts", "env_var": "EVERAI_API_KEY", "vision": False, "kind": "tts"}, "deepgram": {"name": "Deepgram Aura (TTS)", "base_url": "https://api.deepgram.com/v1", "models": ["aura-2"], "default_model": "aura-2", "env_var": "DEEPGRAM_API_KEY", "vision": False, "kind": "tts", "auth_scheme": "Token"}}
for _info in PROVIDERS.values():
    _info.setdefault("kind", "llm")
def _mask(key: str) -> str:
    if len(key) > 10:
        return key[:6] + "..." + key[-4:]
    
    return "***"

class KeyManager:
    """Kho key local đa provider, đa key, xoay vòng và cooldown."""
    def __init__(self, data_file: str=str(KEYS_FILE)):
        self.data_file = data_file; self._lock = threading.RLock(); self._local = {}; self._rr = {}; self._load()
    
    def _load(self):
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                self._local = json.load(f)
        except Exception:
            self._local = {}
    
    def _save(self):
        # Rewrite every readable legacy value (old XOR *and* old plaintext) as
        # DPAPI on the next normal save.  We retain unreadable blobs unchanged
        # rather than accidentally replacing a credential with an empty value.
        for entries in self._local.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                legacy = entry.get("key") if isinstance(entry, dict) else None
                if isinstance(legacy, str) and legacy and not is_dpapi_value(legacy):
                    plaintext = decrypt_value(legacy)
                    if plaintext:
                        entry["key"] = encrypt_value(plaintext)
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True); tmp = (self.data_file) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._local, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.data_file)
    
    def add_key(self, provider: str, api_key: str, label: str="") -> dict:
        if provider not in PROVIDERS:
            return {"ok": False, "message": f"Provider không hỗ trợ: {provider}"}
        api_key = (api_key or "").strip()
        if not api_key:
            return {"ok": False, "message": "Key rỗng."}
        with self._lock:
            entries = self._local.setdefault(provider, [])
            for e in entries:
                if decrypt_value(e.get("key", "")) == api_key:
                    e["active"] = True; e["cooldown_until"] = 0; self._save()
                    return {"ok": True, "message": "Key đã tồn tại — kích hoạt lại."}
            label = (label or f"key-{len(entries) + 1}").strip()
            used_labels = {str(e.get("label", "")).casefold() for e in entries}
            base_label = label
            suffix = 2
            while label.casefold() in used_labels:
                label = f"{base_label}-{suffix}"
                suffix += 1
            entries.append({"label": label, "key": encrypt_value(api_key), "active": True, "cooldown_until": 0,
                            "error_count": 0, "added_at": datetime.now().isoformat(timespec="seconds"), "last_used": ""})
            self._save()
        return {"ok": True, "message": f"Đã thêm key '{label}' cho {provider}."}
    
    def remove_key(self, provider: str, label: str) -> dict:
        with self._lock:
            entries = self._local.get(provider, [])
            kept = [e for e in entries if e.get("label") != label]
            if len(kept) == len(entries):
                return {"ok": False, "message": f"Không thấy key '{label}'."}
            if kept:
                self._local[provider] = kept
            else:
                self._local.pop(provider, None)
            self._save()
        return {"ok": True, "message": f"Đã xoá key '{label}'."}
    
    def set_active(self, provider: str, label: str, active: bool) -> dict:
        with self._lock:
            for e in self._local.get(provider, []):
                if e.get("label") == label:
                    e["active"] = bool(active)
                    if active:
                        e["cooldown_until"] = 0; e["error_count"] = 0
                    self._save()
                    return {"ok": True, "message": "Đã cập nhật."}
        return {"ok": False, "message": f"Không thấy key '{label}'."}
    
    def _usable_local(self, provider: str) -> List[dict]:
        now = time.time()
        return [e for e in self._local.get(provider, []) if e.get("active") and float(e.get("cooldown_until") or 0) <= now]
    
    def acquire_key(self, provider: str) -> Optional[dict]:
        with self._lock:
            pool = [{"key": decrypt_value(e["key"]), "label": e["label"], "source": "local", "_e": e}
                    for e in self._usable_local(provider)]
            if pool:
                idx = self._rr.get(provider, 0) % len(pool); self._rr[provider] = idx + 1
                chosen = pool[idx]; e = chosen.pop("_e", None)
                if e is not None:
                    e["last_used"] = datetime.now().isoformat(timespec="seconds"); self._save()
                return chosen
        env_var = PROVIDERS.get(provider, {}).get("env_var", "")
        env_key = os.environ.get(env_var, "") if env_var else ""
        if env_key:
            return {"key": env_key, "label": env_var, "source": "env"}
        if PROVIDERS.get(provider, {}).get("local"):
            return {"key": provider, "label": "local", "source": "local-dummy"}
        return None
    
    def report_error(self, provider: str, api_key: str, quota: bool=True, message: str="") -> None:
        with self._lock:
            for e in self._local.get(provider, []):
                if decrypt_value(e.get("key", "")) != api_key:
                    continue
                e["error_count"] = int(e.get("error_count") or 0) + 1
                e["status_msg"] = (message or "")[:200]
                if quota:
                    e["cooldown_until"] = time.time() + QUOTA_COOLDOWN
                    logger.warning(f'{provider}/{e["label"]}: quota — nghỉ {QUOTA_COOLDOWN // 60} phút')
                else:
                    e["active"] = False
                    logger.warning(f'{provider}/{e["label"]}: key bị từ chối — đã tắt')
                self._save()
                return
    
    def list_providers(self) -> List[dict]:
        out = []
        
        with self._lock:
            for pid, info in PROVIDERS.items():
                local = self._local.get(pid, [])
                usable = len(self._usable_local(pid))
                has_env = bool(os.environ.get(info.get("env_var") or "", ""))
                is_local = bool(info.get("local"))
                out.append({"id": pid, "kind": info.get("kind", "llm"), "name": info["name"], "models": info["models"], "default_model": info["default_model"], "local_total": len(local), "local_usable": usable, "has_env": has_env, "is_local": is_local, "ready": usable > 0 or has_env or is_local})
        return out
    
    def list_keys(self, provider: str) -> List[dict]:
        out = []; now = time.time()
        
        with self._lock:
            for e in self._local.get(provider, []):
                cd = float(e.get("cooldown_until") or 0)
                out.append({"label": e.get("label", ""), "masked": _mask(decrypt_value(e.get("key", ""))), "active": bool(e.get("active")), "cooling": cd > now, "cooldown_left": max(0, int(cd - now)), "error_count": int(e.get("error_count") or 0), "status_msg": e.get("status_msg", ""), "added_at": e.get("added_at", ""), "last_used": e.get("last_used", ""), "source": "local"})
        return out
    
    def probe_local(self, provider: str, timeout: int=3) -> dict:
        info = PROVIDERS.get(provider) or {}
        if not info.get("local"):
            return {"running": False, "model_count": 0, "models": []}
        headers = {}
        with self._lock:
            usable = self._usable_local(provider)
            if usable:
                headers["Authorization"] = f"Bearer {decrypt_value(usable[0]["key"])}"
        try:
            import requests
            r = requests.get(f"{info["base_url"]}/models", headers=headers, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                models = []
                if isinstance(data, dict) and "data" in data:
                    models = [m.get("id", m.get("name", "")) for m in data["data"] if isinstance(m, dict)]
                return {"running": True, "model_count": len(models), "models": models}
        except Exception:
            pass
        return {"running": False, "model_count": 0, "models": []}
    
    def probe_model(self, provider: str, model: str, timeout: int=20) -> dict:
        import time
        info = PROVIDERS.get(provider) or {}; base = info.get("base_url")
        if not base or not model:
            return {"ok": False, "error": "Thiếu base_url hoặc model."}
        cred = self.acquire_key(provider)
        if not cred and not info.get("local"):
            return {"ok": False, "error": "Chưa có key cho provider này."}
        headers = {"Content-Type": "application/json"}
        if provider == "gemini":
            # Gemini Developer API không có endpoint OpenAI-compatible
            # /chat/completions. Dùng generateContent giống luồng sinh nội dung
            # thật; chỉ cần HTTP 200 để xác nhận model/key dùng được.
            headers["X-goog-api-key"] = cred["key"]
            url = f"{base}/v1beta/models/{model}:generateContent"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": "Reply OK"}]}],
                "generationConfig": {"maxOutputTokens": 64},
            }
        else:
            if cred:
                headers["Authorization"] = f"Bearer {cred["key"]}"
            url = f"{base}/chat/completions"
            payload = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}
        t0 = time.time()
        try:
            import requests
            r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        except Exception as e:
            return {"ok": False, "error": f"Không kết nối được: {e}"}
        ms = int((time.time() - t0) * 1000)
        if r.status_code == 200:
            return {"ok": True, "error": "", "latency_ms": ms}
        try:
            body = r.json()
            if isinstance(body.get("error"), dict):
                msg = (body.get("error") or {}).get("message")
            else:
                msg = body.get("error") or body.get("message") or r.text
        except Exception:
            msg = r.text
        return {"ok": False, "error": f"HTTP {r.status_code}: {str(msg)[:120]}", "latency_ms": ms}
    
    def test_key(self, provider: str, label: str) -> dict:
        with self._lock:
            entry = next((e for e in self._local.get(provider, []) if e.get("label") == label), None)
        if not entry:
            return {"ok": False, "message": "Không thấy key."}
        key = decrypt_value(entry["key"])
        try:
            import requests
            if PROVIDERS.get(provider, {}).get("local"):
                st = self.probe_local(provider)
                if st["running"]:
                    with self._lock:
                        entry["active"] = True
                        entry["cooldown_until"] = 0
                        entry["error_count"] = 0
                        entry["status_msg"] = ""
                        self._save()
                    return {"ok": True, "message": f'✅ {PROVIDERS[provider]["name"]} đang chạy ({st["model_count"]} model).'}
                return {"ok": False, "message": f"{PROVIDERS[provider]["name"]} không phản hồi tại {PROVIDERS[provider]["base_url"]}."}
            elif provider == "gemini":
                r = requests.get(f"{PROVIDERS["gemini"]["base_url"]}/v1beta/models", params={"key": key}, timeout=12)
            elif provider == "claude":
                r = requests.post(
                    f"{PROVIDERS["claude"]["base_url"]}/messages",
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": PROVIDERS["claude"]["default_model"],
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "OK"}],
                    },
                    timeout=12,
                )
            elif provider == "deepgram":
                r = requests.get("https://api.deepgram.com/v1/auth/token", headers={"Authorization": f"Token {key}"}, timeout=15)
            else:
                r = requests.get(f"{PROVIDERS[provider]["base_url"]}/models", headers={"Authorization": f"Bearer {key}"}, timeout=12)
            if r.status_code == 200:
                with self._lock:
                    entry["active"] = True
                    entry["cooldown_until"] = 0
                    entry["error_count"] = 0
                    entry["status_msg"] = ""
                    self._save()
                return {"ok": True, "message": "✅ Key hợp lệ."}
            return {"ok": False, "message": f"HTTP {r.status_code}: {r.text[:120]}"}
        except Exception as e:
            return {"ok": False, "message": f"Lỗi kết nối: {e}"}

key_manager = KeyManager()
