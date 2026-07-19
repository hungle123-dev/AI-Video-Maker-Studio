from __future__ import annotations

import json
import os
import wave
from pathlib import Path

import pytest

from core import ai_client, tts_deepgram, tts_everai, tts_vivibe, voices


class _Response:
    def __init__(self, status=200, data=None, text="", content=b""):
        self.status_code = status
        self._data = data or {}
        self.text = text
        self.content = content

    def json(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size):
        return [self.content]


class _Keys:
    def __init__(self, values):
        self.values = iter(values)
        self.errors = []

    def acquire_key(self, provider):
        value = next(self.values, None)
        return {"key": value, "label": value, "source": "local"} if value else None

    def report_error(self, provider, key, quota=True, message=""):
        self.errors.append((provider, key, quota))


def test_ai_rotates_rejected_key_and_builds_provider_payloads(monkeypatch):
    keys = _Keys(["bad", "good"])
    monkeypatch.setattr(ai_client, "key_manager", keys)

    def call(key, *_args):
        if key == "bad":
            raise ai_client._AuthError("401")
        return "rotated"

    monkeypatch.setattr(ai_client, "_call_gemini", call)
    assert ai_client.generate("hello", provider="gemini") == "rotated"
    assert keys.errors == [("gemini", "bad", False)]

    posted = []

    def post(_url, **kwargs):
        posted.append(kwargs["json"])
        if len(posted) == 1:
            return _Response(400, text="use max_tokens")
        return _Response(
            200,
            {"choices": [{"message": {"content": "openai-ok"}}]},
        )

    monkeypatch.setattr(ai_client.requests, "post", post)
    result = ai_client._call_openai_compat(
        "openai", "key", "gpt-5-mini", "prompt", "system", [b"png"], 123, 5
    )
    assert result == "openai-ok"
    assert "max_completion_tokens" in posted[0] and "max_tokens" in posted[1]
    assert posted[1]["messages"][1]["content"][0]["type"] == "image_url"


def test_ai_upgrades_saved_retired_gemini_model(monkeypatch):
    monkeypatch.setattr(ai_client, "key_manager", _Keys(["good"]))
    called = {}
    monkeypatch.setattr(
        ai_client,
        "_call_gemini",
        lambda _key, model, *_args: called.setdefault("model", model) and "ok",
    )

    assert ai_client.generate("hello", provider="gemini", model="gemini-2.5-flash") == "ok"
    assert called["model"] == "gemini-3.5-flash"


def test_ai_rotates_rate_limited_key_and_keeps_gemini_key_out_of_url(monkeypatch):
    keys = _Keys(["limited", "good"])
    monkeypatch.setattr(ai_client, "key_manager", keys)
    real_call = ai_client._call_gemini

    def call(key, *_args):
        if key == "limited":
            raise ai_client._QuotaError("429")
        return "rotated"

    monkeypatch.setattr(ai_client, "_call_gemini", call)
    assert ai_client.generate("hello", provider="gemini") == "rotated"
    assert keys.errors == [("gemini", "limited", True)]
    monkeypatch.setattr(ai_client, "_call_gemini", real_call)

    captured = {}
    monkeypatch.setattr(
        ai_client.requests,
        "post",
        lambda url, **kwargs: captured.update(url=url, **kwargs)
        or _Response(200, {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}),
    )
    assert ai_client._call_gemini("secret", "gemini-test", "hello", "", None, 10, 5) == "ok"
    assert "key=" not in captured["url"]
    assert captured["headers"] == {"X-goog-api-key": "secret"}


def test_deepgram_reports_the_key_that_failed(tmp_path, monkeypatch):
    keys = _Keys(["deepgram-key"])
    monkeypatch.setattr(tts_deepgram, "key_manager", keys)
    monkeypatch.setattr(
        tts_deepgram.requests,
        "post",
        lambda *_a, **_k: _Response(429, text="quota"),
    )
    with pytest.raises(tts_deepgram.DeepgramError, match="429"):
        tts_deepgram.synthesize("hello", "aura-2", str(tmp_path / "voice.mp3"))
    assert keys.errors == [("deepgram", "deepgram-key", True)]


def test_everai_poll_download_and_voice_routing(tmp_path, monkeypatch):
    keys = _Keys(["ever-key"])
    monkeypatch.setattr(tts_everai, "key_manager", keys)
    monkeypatch.setattr(tts_everai.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        tts_everai.requests,
        "post",
        lambda *_a, **_k: _Response(
            200, {"status": "1", "result": {"request_id": "request-1"}}
        ),
    )

    def get(url, **_kwargs):
        if url.endswith("request-1"):
            return _Response(
                200,
                {"result": {"status": "done", "audio_link": "https://audio"}},
            )
        return _Response(200, content=b"audio" * 30)

    monkeypatch.setattr(tts_everai.requests, "get", get)
    output = tmp_path / "ever.mp3"
    result = tts_everai.synthesize("Xin chào", "vi_female_thuytrang_mb", str(output))
    assert result["status"] == "success" and output.stat().st_size > 100

    monkeypatch.setattr(voices, "_edge_all", lambda: [{"id": "vi-test", "lang": "vi"}])
    assert voices.list_voices("edge", "vi-VN")[0]["id"] == "vi-test"
    assert voices.list_voices("gtts", "vi-VN")[0]["id"] == "vi"
    assert voices.list_voices("everai", "en") == []
    assert len(voices.list_voices("vivibe", "vi")) == 13
    assert voices.list_voices("vivibe", "en") == []
    assert "không có giọng" in voices.unsupported_msg("deepgram", "vi")


def test_vivibe_credentials_are_encrypted_at_rest(tmp_path, monkeypatch):
    credentials_file = tmp_path / "vivibe.enc.json"
    monkeypatch.setattr(tts_vivibe, "_CREDENTIALS_FILE", credentials_file)
    monkeypatch.delenv("VIVIBE_USERNAME", raising=False)
    monkeypatch.delenv("VIVIBE_PASSWORD", raising=False)

    tts_vivibe.save_credentials("voice@example.test", "not-plain-password")

    raw = credentials_file.read_text(encoding="utf-8")
    assert "voice@example.test" not in raw
    assert "not-plain-password" not in raw
    assert tts_vivibe.load_credentials() == (
        "voice@example.test",
        "not-plain-password",
    )


def test_vivibe_migrates_plaintext_legacy_credentials_when_loaded(tmp_path, monkeypatch):
    credentials_file = tmp_path / "vivibe.enc.json"
    username = "legacy@example.test"
    password = "legacy-password"
    credentials_file.write_text(
        json.dumps({"username": username, "password": password}), encoding="utf-8"
    )
    monkeypatch.setattr(tts_vivibe, "_CREDENTIALS_FILE", credentials_file)
    monkeypatch.delenv("VIVIBE_USERNAME", raising=False)
    monkeypatch.delenv("VIVIBE_PASSWORD", raising=False)

    assert tts_vivibe.load_credentials() == (username, password)
    raw = credentials_file.read_text(encoding="utf-8")
    assert username not in raw and password not in raw
    stored = json.loads(raw)
    assert stored["username"].startswith("dpapi:")
    assert stored["password"].startswith("dpapi:")


def test_vivibe_keeps_capassistant_browser_launch_behavior():
    source = Path(tts_vivibe.__file__).read_text(encoding="utf-8")
    assert "--no-sandbox" in source
    assert "AutomationControlled" in source
    assert "navigator, 'webdriver'" in source


def test_vivibe_configures_bundled_browser_before_driver_start(tmp_path, monkeypatch):
    browser_root = tmp_path / "playwright-browsers"
    browser_root.mkdir()
    monkeypatch.setattr(tts_vivibe, "BASE_DIR", tmp_path)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    assert tts_vivibe._configure_playwright_browser_path() == browser_root
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_root)
    source = Path(tts_vivibe.__file__).read_text(encoding="utf-8")
    assert source.index("bundled_browsers = _configure_playwright_browser_path()") < source.index(
        "with sync_playwright() as playwright:"
    )


def test_vivibe_parses_original_text_and_srt_rules():
    previews = [tts_vivibe.preview_path(voice["id"]) for voice in tts_vivibe.VIVIBE_VOICES]
    assert [path.name for path in previews] == [f"{index:03d}.wav" for index in range(1, 14)]
    assert all(path.read_bytes()[:4] == b"RIFF" for path in previews)
    assert tts_vivibe._voice_search_terms("Trường An (Phật Pháp)") == [
        "Trường An Phật Pháp",
        "Trường An",
    ]
    text_blocks, error = tts_vivibe._parse_blocks(
        "Câu một.\n\nCâu hai.", "text", False
    )
    assert error == ""
    assert [block["text"] for block in text_blocks] == ["Câu một.", "Câu hai."]

    srt = (
        "1\n00:00:01,250 --> 00:00:02,000\n<b>Xin chào</b>\n\n"
        "2\n00:00:03,500 --> 00:00:04,000\nViệt Nam"
    )
    srt_blocks, error = tts_vivibe._parse_blocks(srt, "srt", False)
    assert error == ""
    assert [block["start"] for block in srt_blocks] == [1250, 3500]
    assert [block["text"] for block in srt_blocks] == ["Xin chào", "Việt Nam"]


def test_vivibe_batch_uses_capassistant_srt_contract(tmp_path, monkeypatch):
    captured = {}

    monkeypatch.setattr(tts_vivibe, "load_credentials", lambda: ("user", "pass"))
    monkeypatch.setattr(tts_vivibe, "_merge_caption_parts", lambda _parts, _destination: None)

    def run(**kwargs):
        captured.update(kwargs)
        return True, "ok"

    monkeypatch.setattr(tts_vivibe, "_run_premium_engine", run)
    assert tts_vivibe.synthesize_batch(
        [("Câu một", str(tmp_path / "one.mp3")), ("Câu hai", str(tmp_path / "two.mp3"))],
        "Quang Anh",
        master_output_path=str(tmp_path / "master.mp3"),
    )
    assert captured["req_type"] == "srt"
    assert captured["sync_timeline"] is True
    blocks, error = tts_vivibe._parse_blocks(captured["text"], "srt", False)
    assert error == ""
    assert [block["text"] for block in blocks] == ["Câu một", "Câu hai"]


def test_vivibe_uses_capassistant_two_second_text_rows():
    source = "Câu một. Câu hai!\nCâu ba"
    srt, slots, groups = tts_vivibe.build_capassistant_srt([source])

    blocks, error = tts_vivibe._parse_blocks(srt, "srt", False)
    assert error == ""
    assert [block["text"] for block in blocks] == ["Câu một. Câu hai!", "Câu ba"]
    assert [(block["start"], block["end"]) for block in blocks] == [
        (0, 2_000), (2_000, 4_000)
    ]
    assert len(groups[0]) == len(blocks)
    assert slots == [(blocks[0]["start"], blocks[-1]["end"])]


def test_vivibe_card_prefixes_distinguish_shared_openings():
    texts = [
        "Khi đã chọn đúng ngách, việc sản xuất video trở nên nhẹ nhàng hơn.",
        "Khi đã chọn đúng ngách, việc sản xuất video trở nên dễ dàng hơn.",
    ]
    prefixes = tts_vivibe._unique_card_prefixes(texts)

    assert prefixes[0] != prefixes[1]
    assert all(len(prefix) > 15 for prefix in prefixes)
    assert all(text.startswith(prefix) for text, prefix in zip(texts, prefixes))


def test_vivibe_original_merge_inserts_200ms_and_exports_mp3(tmp_path):
    def write_silence(path: Path, duration_ms: int) -> None:
        frame_rate = 16_000
        frames = int(frame_rate * duration_ms / 1000)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(frame_rate)
            output.writeframes(b"\0\0" * frames)

    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    output = tmp_path / "merged.mp3"
    write_silence(first, 400)
    write_silence(second, 400)

    tts_vivibe.merge_step_audio_files([str(first), str(second)], str(output))

    AudioSegment = tts_vivibe._audio_segment()
    duration_ms = len(AudioSegment.from_file(output))
    assert 950 <= duration_ms <= 1050
    assert output.stat().st_size > 100


def test_vivibe_srt_merge_keeps_original_audio_without_time_stretching(tmp_path):
    def write_silence(path: Path, duration_ms: int) -> None:
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\0\0" * int(16_000 * duration_ms / 1000))

    first, second = tmp_path / "first.wav", tmp_path / "second.wav"
    output = tmp_path / "source-srt.mp3"
    write_silence(first, 3_000)
    write_silence(second, 1_000)

    timeline = tts_vivibe._merge_original_audio(
        [
            {"start": 0, "path": str(first)},
            {"start": 2_000, "path": str(second)},
        ],
        str(output),
        "srt",
        False,
    )

    duration_ms = len(tts_vivibe._audio_segment().from_file(output))
    assert 3_950 <= duration_ms <= 4_050
    assert timeline == [{"start": 0, "end": 3_000}, {"start": 3_000, "end": 4_000}]


def test_vivibe_hides_pydub_console_on_windows(monkeypatch):
    if os.name != "nt":
        pytest.skip("Windows-only console behavior")
    called = {}

    def fake_popen(*args, **kwargs):
        called.update(kwargs)
        return object()

    monkeypatch.setattr(tts_vivibe.subprocess, "Popen", fake_popen)
    tts_vivibe._hidden_popen(["ffmpeg"])
    assert called["creationflags"] == 0x08000000
