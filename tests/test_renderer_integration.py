from __future__ import annotations

import json
import os
import subprocess
import asyncio
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from core import preview
from engines import video_encoder
from engines.video_encoder import RendererProcessError, RendererSceneError, render_and_encode


@pytest.mark.asyncio
async def test_node_monitor_stops_renderer_that_never_reports_progress(monkeypatch):
    monkeypatch.setattr(video_encoder, "_RENDERER_IDLE_TIMEOUT_SECONDS", 0.05)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import time; time.sleep(30)",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    with pytest.raises(RendererProcessError, match="không có tiến độ"):
        await video_encoder._monitor_node_process(proc)
    assert proc.returncode is not None


@pytest.mark.asyncio
async def test_terminate_process_ignores_kill_oserror(monkeypatch):
    class UncooperativeProcess:
        pid = None
        returncode = None

        def __init__(self):
            self.wait_calls = 0

        async def wait(self):
            self.wait_calls += 1
            if self.wait_calls == 1:
                await asyncio.sleep(1)
            return 0

        def kill(self):
            raise OSError("process already exited")

    monkeypatch.setattr(video_encoder, "_PROCESS_STOP_GRACE_SECONDS", 0.01)
    proc = UncooperativeProcess()
    await video_encoder._terminate_process_tree(proc)
    assert proc.wait_calls == 2


def test_pipe_recovery_gets_a_fresh_bounded_frames_deadline():
    expired_pipe_deadline = time.monotonic() - 1
    recovered = video_encoder._fallback_deadline(expired_pipe_deadline, 52)
    assert recovered is not None
    assert recovered > time.monotonic() + 100


@pytest.mark.asyncio
async def test_real_node_canvas_ffmpeg_render(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "")
    script = {
        "title": "Renderer",
        "description": "",
        "subject": "general",
        "total_steps": 1,
        "steps": [
            {
                "id": 1,
                "clear": True,
                "voice_text": "Renderer integration",
                "elements": [
                    {
                        "type": "text",
                        "text": "TubeCraft OK",
                        "fontSize": 72,
                        "color": "highlight",
                        "align": "center",
                        "bold": True,
                    }
                ],
            }
        ],
    }
    timing = {
        "steps": [{"id": 1, "start": 0.0, "end": 0.3, "duration": 0.3, "words": []}],
        "total_duration": 0.3,
    }
    script_path = tmp_path / "lesson_script.json"
    timing_path = tmp_path / "timing_map.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")
    timing_path.write_text(json.dumps(timing), encoding="utf-8")

    output = await render_and_encode(
        str(script_path),
        str(timing_path),
        str(tmp_path / "output"),
        "pytest",
        aspect_ratio="1:1",
        gpu_encoder="cpu",
    )
    result = Path(output)
    assert result.is_file()
    assert result.stat().st_size > 1_000


def test_canvas_renderer_renders_vietnamese_diacritics_not_question_marks(tmp_path):
    """The shipped BVP fonts must be found by the same Node path as video render."""
    base_script = {
        "title": "",
        "description": "",
        "subject": "general",
        "total_steps": 1,
        "steps": [{
            "id": 1,
            "clear": True,
            "voice_text": "",
            "elements": [{
                "type": "text",
                "text": "Đủ dấu Ắ ễ ộ ừ",
                "fontSize": 96,
                "color": "white",
                "align": "center",
                "bold": True,
                "x_1_1": 0.5,
                "y_1_1": 0.45,
            }],
        }],
    }
    question_script = json.loads(json.dumps(base_script))
    vietnamese = base_script["steps"][0]["elements"][0]["text"]
    # This exactly mirrors the broken Pango fallback: ASCII remains readable,
    # every non-ASCII glyph is rendered as a question mark.
    question_script["steps"][0]["elements"][0]["text"] = "".join(
        char if ord(char) < 128 else "?" for char in vietnamese
    )
    project = {"theme": "dark", "aspect_ratio": "1:1", "font_family": "Arial", "subtitle_enabled": False}
    rendered = tmp_path / "vietnamese.png"
    questions = tmp_path / "questions.png"
    assert preview.render_step_preview(project, base_script, 0, str(rendered))["ok"]
    assert preview.render_step_preview(project, question_script, 0, str(questions))["ok"]
    with Image.open(rendered).convert("RGB") as actual, Image.open(questions).convert("RGB") as fallback:
        difference = ImageChops.difference(actual, fallback)
        # If the renderer falls back to '?', the two inputs are visually
        # identical.  A real Vietnamese font changes thousands of pixels.
        assert sum((index % 256) * count for index, count in enumerate(difference.histogram())) > 10_000


@pytest.mark.asyncio
async def test_render_replaces_only_after_success(tmp_path, monkeypatch):
    script = tmp_path / "script.json"
    timing = tmp_path / "timing.json"
    script.write_text('{"steps":[]}', encoding="utf-8")
    timing.write_text('{"total_duration":1,"steps":[]}', encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    target = output / "edu_atomic_1_1.mp4"
    target.write_bytes(b"old-video" * 200)

    async def canvas():
        return Path(__file__).parents[1] / "node_modules"

    async def success(*args, **_kwargs):
        Path(args[10]).write_bytes(b"new-video" * 200)

    monkeypatch.setattr(video_encoder, "_ensure_canvas", canvas)
    monkeypatch.setattr(video_encoder, "_render_pipe", success)
    result = await video_encoder.render_and_encode(
        str(script), str(timing), str(output), "atomic", aspect_ratio="1:1"
    )
    assert result == str(target)
    assert target.read_bytes().startswith(b"new-video")

    target.write_bytes(b"keep-this" * 200)

    async def failure(*_args, **_kwargs):
        raise RuntimeError("render failed")

    monkeypatch.setattr(video_encoder, "_render_pipe", failure)
    with pytest.raises(RuntimeError, match="render failed"):
        await video_encoder.render_and_encode(
            str(script), str(timing), str(output), "atomic", aspect_ratio="1:1"
        )
    assert target.read_bytes().startswith(b"keep-this")


@pytest.mark.asyncio
async def test_renderer_never_degrades_to_silent_video_when_audio_disappears(tmp_path, monkeypatch):
    script = tmp_path / "script.json"
    timing = tmp_path / "timing.json"
    audio_dir = tmp_path / "audio"
    output = tmp_path / "output"
    audio_dir.mkdir()
    output.mkdir()
    script.write_text('{"steps":[]}', encoding="utf-8")
    timing.write_text('{"total_duration":1,"steps":[]}', encoding="utf-8")
    (audio_dir / "full_audio.mp3").write_bytes(b"audio" * 100)
    target = output / "edu_audio-race_1_1.mp4"
    target.write_bytes(b"previous-video" * 100)

    async def canvas():
        return Path(__file__).parents[1] / "node_modules"

    async def silent_renderer(*args, **_kwargs):
        Path(args[10]).write_bytes(b"silent-video" * 200)
        (audio_dir / "full_audio.mp3").unlink()

    monkeypatch.setattr(video_encoder, "_ensure_canvas", canvas)
    monkeypatch.setattr(video_encoder, "_render_pipe", silent_renderer)
    with pytest.raises(RendererProcessError, match="audio đã biến mất"):
        await render_and_encode(str(script), str(timing), str(output), "audio-race", aspect_ratio="1:1")
    assert target.read_bytes().startswith(b"previous-video")
    assert not (output / "edu_audio-race_1_1.mp4.rendering.mp4").exists()


@pytest.mark.asyncio
async def test_renderer_requires_audio_at_the_final_publish_boundary(tmp_path, monkeypatch):
    script = tmp_path / "lesson_script.json"
    timing = tmp_path / "timing_map.json"
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "full_audio.mp3").write_bytes(b"audio" * 100)
    script.write_text(json.dumps({"steps": []}), encoding="utf-8")
    timing.write_text(json.dumps({"total_duration": 1, "steps": []}), encoding="utf-8")

    async def canvas():
        return Path(__file__).parents[1] / "node_modules"

    async def remove_audio_after_render(*args, **_kwargs):
        Path(args[10]).write_bytes(b"temporary video" * 100)
        Path(args[9]).unlink()

    monkeypatch.setattr(video_encoder, "_ensure_canvas", canvas)
    monkeypatch.setattr(video_encoder, "_render_pipe", remove_audio_after_render)

    with pytest.raises(RendererProcessError, match="Nguồn audio đã biến mất"):
        await render_and_encode(
            str(script), str(timing), str(tmp_path / "output"), "audio-race",
            aspect_ratio="1:1", require_audio=True,
        )
    assert not (tmp_path / "output" / "edu_audio-race_1_1.mp4").exists()


@pytest.mark.asyncio
async def test_renderer_rejects_malicious_aspect_before_constructing_output_path(tmp_path, monkeypatch):
    script = tmp_path / "lesson_script.json"
    timing = tmp_path / "timing_map.json"
    script.write_text(json.dumps({"steps": []}), encoding="utf-8")
    timing.write_text(json.dumps({"total_duration": 1, "steps": []}), encoding="utf-8")
    victim = tmp_path / "victim.mp4"
    victim.write_bytes(b"do-not-replace")

    monkeypatch.setattr(video_encoder, "_ensure_canvas", lambda: pytest.fail("renderer must not start"))
    with pytest.raises(ValueError, match="Tỉ lệ khung hình không hợp lệ"):
        await render_and_encode(
            str(script), str(timing), str(tmp_path / "out" / "project"), "aspect-race",
            aspect_ratio="../../../../victim",
        )
    assert victim.read_bytes() == b"do-not-replace"


@pytest.mark.asyncio
async def test_renderer_rejects_raw_custom_js_before_node_runs(tmp_path, monkeypatch):
    script = tmp_path / "unsafe.json"
    timing = tmp_path / "timing.json"
    script.write_text(
        json.dumps({
            "title": "Unsafe",
            "steps": [{
                "id": 1,
                "voice_text": "Không chạy mã tùy ý.",
                "elements": [{"type": "custom_js", "code": "process.exit(99)"}],
            }],
        }),
        encoding="utf-8",
    )
    timing.write_text(json.dumps({"total_duration": 1, "steps": []}), encoding="utf-8")
    monkeypatch.setattr(video_encoder, "_ensure_canvas", lambda: pytest.fail("Node không được chạy"))

    with pytest.raises(RendererSceneError, match="custom_js raw"):
        await render_and_encode(str(script), str(timing), str(tmp_path / "output"), "unsafe")


@pytest.mark.asyncio
async def test_renderer_rejects_external_image_before_node_runs(tmp_path, monkeypatch):
    script = tmp_path / "unsafe-image.json"
    timing = tmp_path / "timing.json"
    script.write_text(
        json.dumps({"steps": [{"id": 1, "elements": [{
            "type": "image", "src": "https://example.invalid/probe.png",
        }]}]}),
        encoding="utf-8",
    )
    timing.write_text(json.dumps({"total_duration": 1, "steps": []}), encoding="utf-8")
    monkeypatch.setattr(video_encoder, "_ensure_canvas", lambda: pytest.fail("Node không được chạy"))

    with pytest.raises(RendererSceneError, match="image src"):
        await render_and_encode(str(script), str(timing), str(tmp_path / "output"), "unsafe-image")


@pytest.mark.asyncio
async def test_frames_renderer_fails_instead_of_publishing_silent_video(tmp_path):
    script = tmp_path / "script.json"
    timing = tmp_path / "timing.json"
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "full_audio.mp3").write_bytes(b"not a real mp3" * 20)
    script.write_text(
        json.dumps({"steps": [{"id": 1, "voice_text": "Audio bắt buộc", "elements": [{
            "type": "text", "text": "Không xuất video câm", "fontSize": 48,
        }]}]}),
        encoding="utf-8",
    )
    timing.write_text(
        json.dumps({"total_duration": 0.2, "steps": [{"id": 1, "start": 0, "end": 0.2}]}),
        encoding="utf-8",
    )

    with pytest.raises(video_encoder.RendererProcessError, match="mux audio"):
        await render_and_encode(
            str(script), str(timing), str(tmp_path / "output"), "bad-audio",
            aspect_ratio="1:1", gpu_encoder="cpu", render_mode="frames",
        )
    assert not (tmp_path / "output" / "edu_bad-audio_1_1.mp4").exists()


def test_node_stops_on_a_trusted_scene_runtime_error(tmp_path):
    script = tmp_path / "scene-error.json"
    timing = tmp_path / "timing.json"
    script.write_text(
        json.dumps({
            "title": "Scene error",
            "steps": [{
                "id": 1,
                "voice_text": "Test.",
                "elements": [{
                    "type": "custom_js",
                    "template": "test_scene",
                    "trusted_template": "test_scene",
                    "code": "throw new Error('scene broke')",
                }],
            }],
        }),
        encoding="utf-8",
    )
    timing.write_text(
        json.dumps({"total_duration": 0.3, "steps": [{"id": 1, "start": 0, "end": 0.3}]}),
        encoding="utf-8",
    )
    env = dict(os.environ, NODE_PATH=str(video_encoder._find_node_modules()))
    result = subprocess.run(
        [
            str(video_encoder._find_executable("node")),
            str(video_encoder.CANVAS_RENDERER_JS),
            "--script", str(script), "--timing", str(timing), "--output", str(tmp_path),
            "--mode", "preview", "--previewTime", "0.1",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(video_encoder._APP_DIR),
        timeout=30,
    )
    assert result.returncode != 0
    assert "custom_scene_error" in result.stderr


def test_node_rejects_direct_image_path_bypass_before_loading(tmp_path):
    script = tmp_path / "unsafe-image.json"
    timing = tmp_path / "timing.json"
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    script.write_text(
        json.dumps({
            "title": "Unsafe image",
            "steps": [{
                "id": 1,
                "voice_text": "Không đọc file ngoài gallery.",
                "elements": [{"type": "image", "src": "gallery:../outside.png"}],
            }],
        }),
        encoding="utf-8",
    )
    timing.write_text(
        json.dumps({"total_duration": 0.2, "steps": [{"id": 1, "start": 0, "end": 0.2}]}),
        encoding="utf-8",
    )
    env = dict(
        os.environ,
        NODE_PATH=str(video_encoder._find_node_modules()),
        TUBECRAFT_GALLERY_DIR=str(gallery),
    )
    result = subprocess.run(
        [
            str(video_encoder._find_executable("node")),
            str(video_encoder.CANVAS_RENDERER_JS),
            "--script", str(script), "--timing", str(timing), "--output", str(tmp_path),
            "--mode", "preview", "--previewTime", "0.1",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(video_encoder._APP_DIR),
        timeout=30,
    )
    assert result.returncode != 0
    assert "image_asset_error" in result.stderr


def test_node_rejects_http_image_without_making_a_request(tmp_path):
    hits = []

    class ProbeHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib handler API
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(b"not-a-real-png")

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ProbeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        script = tmp_path / "external-image.json"
        timing = tmp_path / "timing.json"
        script.write_text(
            json.dumps({
                "title": "External image must not fetch",
                "steps": [{
                    "id": 1,
                    "voice_text": "Không gọi HTTP.",
                    "elements": [{"type": "image", "src": f"http://127.0.0.1:{port}/probe.png"}],
                }],
            }),
            encoding="utf-8",
        )
        timing.write_text(
            json.dumps({"total_duration": 0.2, "steps": [{"id": 1, "start": 0, "end": 0.2}]}),
            encoding="utf-8",
        )
        env = dict(
            os.environ,
            NODE_PATH=str(video_encoder._find_node_modules()),
            TUBECRAFT_GALLERY_DIR=str(tmp_path / "gallery"),
        )
        (tmp_path / "gallery").mkdir()
        result = subprocess.run(
            [
                str(video_encoder._find_executable("node")),
                str(video_encoder.CANVAS_RENDERER_JS),
                "--script", str(script), "--timing", str(timing), "--output", str(tmp_path),
                "--mode", "preview", "--previewTime", "0.1",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(video_encoder._APP_DIR),
            timeout=30,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    assert result.returncode != 0
    assert "image_asset_error" in result.stderr
    assert hits == []


def test_renderer_contains_no_runtime_network_fetches():
    source = video_encoder.CANVAS_RENDERER_JS.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in source
    assert "https.get(" not in source


@pytest.mark.asyncio
async def test_frames_render_rejects_broken_audio_instead_of_publishing_silent_video(tmp_path):
    script = tmp_path / "lesson_script.json"
    timing = tmp_path / "timing_map.json"
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    script.write_text(
        json.dumps({
            "title": "Broken audio",
            "steps": [{
                "id": 1,
                "voice_text": "Âm thanh này cố ý không hợp lệ.",
                "elements": [{"type": "text", "text": "Không xuất video câm"}],
            }],
        }),
        encoding="utf-8",
    )
    timing.write_text(
        json.dumps({"total_duration": 0.2, "steps": [{"id": 1, "start": 0, "end": 0.2}]}),
        encoding="utf-8",
    )
    (audio_dir / "full_audio.mp3").write_bytes(b"not-an-mp3" * 100)
    output_dir = tmp_path / "output"

    with pytest.raises(RendererProcessError, match="mux audio"):
        await render_and_encode(
            str(script), str(timing), str(output_dir), "broken_audio",
            aspect_ratio="1:1", gpu_encoder="cpu", render_mode="frames",
        )
    assert not (output_dir / "edu_broken_audio_1_1.mp4").exists()
