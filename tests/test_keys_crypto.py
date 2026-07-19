from __future__ import annotations

import json

from core.crypto import decrypt_value, encrypt_value
from core.key_manager import KeyManager


def test_crypto_roundtrip_and_plaintext_compatibility():
    encrypted = encrypt_value("secret-value")
    assert encrypted.startswith("dpapi:") and "secret-value" not in encrypted
    assert decrypt_value(encrypted) == "secret-value"
    assert decrypt_value("legacy-plain") == "legacy-plain"


def test_key_rotation_cooldown_and_unique_labels(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path = tmp_path / "keys.json"
    manager = KeyManager(str(path))
    assert manager.add_key("gemini", "key-one", "work")["ok"]
    assert manager.add_key("gemini", "key-two", "work")["ok"]
    labels = [entry["label"] for entry in manager.list_keys("gemini")]
    assert labels == ["work", "work-2"]
    assert "key-one" not in path.read_text(encoding="utf-8")

    first = manager.acquire_key("gemini")
    second = manager.acquire_key("gemini")
    assert {first["key"], second["key"]} == {"key-one", "key-two"}

    manager.report_error("gemini", first["key"], quota=True, message="quota")
    usable = manager.acquire_key("gemini")
    assert usable["key"] == second["key"]
    manager.report_error("gemini", second["key"], quota=False, message="invalid")
    assert manager.acquire_key("gemini") is None

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert all(item["key"].startswith("dpapi:") for item in stored["gemini"])


def test_key_manager_migrates_plaintext_legacy_key_on_normal_use(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path = tmp_path / "keys.json"
    plaintext = "legacy-demo-key"
    path.write_text(
        json.dumps({"gemini": [{
            "label": "old", "key": plaintext, "active": True, "cooldown_until": 0,
        }]}),
        encoding="utf-8",
    )

    acquired = KeyManager(str(path)).acquire_key("gemini")
    assert acquired["key"] == plaintext
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["gemini"][0]["key"].startswith("dpapi:")
    assert plaintext not in path.read_text(encoding="utf-8")


def test_local_provider_test_reports_offline(tmp_path, monkeypatch):
    manager = KeyManager(str(tmp_path / "keys.json"))
    manager.add_key("9router", "optional", "local")
    monkeypatch.setattr(
        manager,
        "probe_local",
        lambda *_args, **_kwargs: {"running": False, "model_count": 0, "models": []},
    )
    result = manager.test_key("9router", "local")
    assert result["ok"] is False
    assert "không phản hồi" in result["message"]


def test_gemini_model_probe_uses_generate_content(tmp_path, monkeypatch):
    manager = KeyManager(str(tmp_path / "keys.json"))
    manager.add_key("gemini", "secret-gemini-key", "primary")
    captured = {}

    class Response:
        status_code = 200
        text = "{}"

        @staticmethod
        def json():
            return {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("requests.post", fake_post)
    result = manager.probe_model("gemini", "gemini-2.5-flash")

    assert result["ok"] is True
    assert captured["url"].endswith(
        "/v1beta/models/gemini-2.5-flash:generateContent"
    )
    assert captured["headers"]["X-goog-api-key"] == "secret-gemini-key"
    assert "Authorization" not in captured["headers"]
    assert captured["json"]["contents"][0]["parts"][0]["text"] == "Reply OK"


def test_claude_model_probe_uses_messages_protocol(tmp_path, monkeypatch):
    manager = KeyManager(str(tmp_path / "keys.json"))
    manager.add_key("claude", "secret-claude-key", "primary")
    captured = {}

    class Response:
        status_code = 200
        text = "{}"

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("requests.post", fake_post)
    result = manager.test_key("claude", "primary")

    assert result["ok"] is True
    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"]["x-api-key"] == "secret-claude-key"
    assert captured["json"]["max_tokens"] == 1
