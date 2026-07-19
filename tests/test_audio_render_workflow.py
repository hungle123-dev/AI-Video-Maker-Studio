from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from core import jobs, render_service
from core.project_store import ProjectStore
from engines import audio_engine, video_encoder


@pytest.mark.asyncio
async def test_gtts_engine_generates_audio_without_word_boundaries(tmp_path, monkeypatch):
    def synth(text, output_path, lang):
        assert text == "Xin chào"
        assert lang == "vi"
        Path(output_path).write_bytes(b"gtts" * 100)
        return True

    monkeypatch.setattr(audio_engine, "_generate_gtts_sync", synth)
    output = tmp_path / "voice.mp3"
    ok, words = await audio_engine._generate_tts_internal(
        "Xin chào", "vi", str(output), "gtts", "vi"
    )
    assert ok is True
    assert words == []
    assert output.stat().st_size > 100


@pytest.mark.asyncio
async def test_audio_pipeline_builds_timing_and_merged_file(tmp_path, monkeypatch, script_copy):
    async def synth(text, voice, output_path, engine, lang):
        Path(output_path).write_bytes(b"x" * 256)
        return True, [{"word": text.split()[0], "norm": "word", "start": 0.1, "end": 0.3}]

    async def duration(_path):
        return 1.25

    async def merge(files, output, gaps=None):
        Path(output).write_bytes(b"merged" * 40)

    monkeypatch.setattr(audio_engine, "_generate_tts_internal", synth)
    monkeypatch.setattr(audio_engine, "_get_audio_duration", duration)
    monkeypatch.setattr(audio_engine, "_merge_audio_files", merge)
    monkeypatch.setattr(audio_engine.asyncio, "sleep", AsyncMock())

    progress = []
    result = await audio_engine.generate_tts_for_script(
        script_copy,
        str(tmp_path / "audio"),
        progress_callback=lambda pct, msg: progress.append((pct, msg)),
    )
    assert result["total_duration"] == 2.5
    assert len(result["steps"]) == 2
    assert result["steps"][1]["words"][0]["start"] == 1.35
    assert (tmp_path / "audio" / "full_audio.mp3").is_file()
    assert progress[-1][0] == 100


@pytest.mark.asyncio
async def test_vivibe_generates_all_steps_in_one_login(tmp_path, monkeypatch, script_copy):
    from core import tts_vivibe

    calls = []

    def synthesize_batch(
        items, voice, progress_callback=None, master_output_path=None
    ):
        calls.append((list(items), voice))
        for _text, output_path in items:
            Path(output_path).write_bytes(b"vivibe" * 100)
        Path(master_output_path).write_bytes(b"master" * 100)
        return True

    async def merge(files, output, gaps=None):
        Path(output).write_bytes(b"merged" * 40)

    monkeypatch.setattr(tts_vivibe, "synthesize_batch", synthesize_batch)
    monkeypatch.setattr(audio_engine, "_get_audio_duration", AsyncMock(side_effect=[1.0, 1.0, 3.0]))
    monkeypatch.setattr(audio_engine, "_merge_audio_files", merge)

    result = await audio_engine.generate_tts_for_script(
        script_copy,
        str(tmp_path / "audio"),
        voice="Giọng adam",
        tts_engine="vivibe",
    )

    assert len(calls) == 1
    assert len(calls[0][0]) == len(script_copy["steps"])
    assert calls[0][1] == "Giọng adam"
    assert result["tts_engine"] == "vivibe"
    assert result["total_duration"] == 3.0
    assert [step["start"] for step in result["steps"]] == [0.0, 2.0]


@pytest.mark.asyncio
async def test_vivibe_uses_the_source_merge_timeline_when_available(tmp_path, monkeypatch, script_copy):
    from core import tts_vivibe

    def synthesize_batch(items, _voice, progress_callback=None, master_output_path=None):
        for _text, output_path in items:
            Path(output_path).write_bytes(b"vivibe" * 100)
        Path(master_output_path).write_bytes(b"master" * 100)
        return {"ranges": [{"start": 0.0, "end": 1.25}, {"start": 1.25, "end": 3.0}]}

    monkeypatch.setattr(tts_vivibe, "synthesize_batch", synthesize_batch)
    monkeypatch.setattr(audio_engine, "_get_audio_duration", AsyncMock(side_effect=[1.25, 1.75, 3.0]))

    result = await audio_engine.generate_tts_for_script(
        script_copy, str(tmp_path / "audio"), voice="Giọng adam", tts_engine="vivibe"
    )

    assert [(step["start"], step["end"]) for step in result["steps"]] == [(0.0, 1.25), (1.25, 3.0)]
    assert result["total_duration"] == 3.0


@pytest.mark.asyncio
async def test_failed_merge_keeps_previous_complete_bundle_and_no_partial_files(tmp_path, monkeypatch, script_copy):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    stale = audio_dir / "full_audio.mp3"
    stale_bytes = b"stale" * 100
    stale.write_bytes(stale_bytes)

    async def synth(_text, _voice, output_path, _engine, _lang):
        Path(output_path).write_bytes(b"fresh" * 100)
        return True, []

    async def fail_merge(*_args, **_kwargs):
        raise RuntimeError("merge failed")

    monkeypatch.setattr(audio_engine, "_generate_tts_internal", synth)
    monkeypatch.setattr(audio_engine, "_get_audio_duration", AsyncMock(return_value=1.0))
    monkeypatch.setattr(audio_engine, "_merge_audio_files", fail_merge)
    monkeypatch.setattr(audio_engine.asyncio, "sleep", AsyncMock())
    with pytest.raises(RuntimeError, match="merge failed"):
        await audio_engine.generate_tts_for_script(script_copy, str(audio_dir))
    assert stale.read_bytes() == stale_bytes
    assert not list(tmp_path.glob(".tts-*"))


@pytest.mark.asyncio
async def test_tts_staging_name_stays_short_for_deep_job_paths(tmp_path, monkeypatch):
    captured = {}

    async def synth(_script, output_dir, **_kwargs):
        stage = Path(output_dir)
        captured["stage"] = stage
        stage.mkdir(parents=True, exist_ok=True)
        (stage / "full_audio.mp3").write_bytes(b"audio" * 100)
        return {"steps": [], "total_duration": 0}

    monkeypatch.setattr(audio_engine, "_generate_tts_for_script_into", synth)
    final_dir = tmp_path / ("lesson_" + "x" * 40) / ".audio-job-pipeline_12345678"
    await audio_engine.generate_tts_for_script({"steps": []}, str(final_dir))

    assert captured["stage"].parent == final_dir.parent
    assert captured["stage"].name.startswith(".tts-")
    assert len(captured["stage"].name) <= 40


@pytest.mark.asyncio
async def test_render_service_tts_then_render(tmp_path, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Pipeline", aspect_ratio="1:1", subtitle_enabled=True)
    lesson = store.create_lesson(project["id"], "Lesson")
    store.save_script(project["id"], lesson["id"], script_copy)

    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(render_service, "project_store", store)
    monkeypatch.setattr(render_service, "OUTPUTS_DIR", tmp_path / "outputs")

    async def fake_tts(script, output_dir, **kwargs):
        audio_dir = Path(output_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)
        (audio_dir / "full_audio.mp3").write_bytes(b"audio" * 100)
        callback = kwargs.get("progress_callback")
        if callback:
            callback(50, "TTS")
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("👉 Đang thu hoạch câu 1/1...")
        return {
            "steps": [{"id": 1, "start": 0, "end": 3, "words": []}],
            "total_duration": 3,
        }

    async def fake_render(**kwargs):
        output = Path(kwargs["output_dir"]) / "result.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video" * 300)
        kwargs["progress_callback"](80, "Render")
        return str(output)

    monkeypatch.setattr(audio_engine, "generate_tts_for_script", fake_tts)
    monkeypatch.setattr(video_encoder, "render_and_encode", fake_render)

    job = jobs.create_job("pipeline", {"project_id": project["id"], "lesson_id": lesson["id"]})
    await render_service._run_pipeline(job["id"], project["id"], lesson["id"])
    completed = jobs.get_job(job["id"])
    assert completed["status"] == "done"
    assert "👉 Đang thu hoạch câu 1/1..." in completed["logs"]
    assert Path(completed["result"]["video"]).is_file()
    saved_lesson = store.get_lesson(project["id"], lesson["id"])
    assert saved_lesson["status"] == "done"
    assert Path(saved_lesson["rendered_video_path"]).is_file()


@pytest.mark.asyncio
async def test_render_service_discards_media_when_inputs_change_mid_job(tmp_path, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Stale job")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"audio" * 100)
    assert store.save_timing(
        project["id"], lesson["id"],
        {"steps": [{"id": 1, "start": 0, "end": 3}], "total_duration": 3},
    )

    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(render_service, "project_store", store)
    monkeypatch.setattr(render_service, "OUTPUTS_DIR", tmp_path / "outputs")
    started = asyncio.Event()
    release = asyncio.Event()

    async def delayed_render(**kwargs):
        started.set()
        await release.wait()
        output = Path(kwargs["output_dir"]) / "stale-result.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"stale video" * 100)
        return str(output)

    monkeypatch.setattr(video_encoder, "render_and_encode", delayed_render)
    job = jobs.create_job("render", {"project_id": project["id"], "lesson_id": lesson["id"]})
    task = asyncio.create_task(render_service._run_render(job["id"], project["id"], lesson["id"]))
    await started.wait()
    changed = dict(script_copy)
    changed["title"] = "Script mới trong lúc render"
    assert store.save_script(project["id"], lesson["id"], changed)[0]
    release.set()
    await task

    completed = jobs.get_job(job["id"])
    assert completed["status"] == "cancelled"
    assert completed["result"] == {"stale": True}
    assert not store.get_lesson(project["id"], lesson["id"]).get("rendered_video_path")
    assert not (tmp_path / "outputs" / project["id"] / "stale-result.mp4").exists()


@pytest.mark.asyncio
async def test_render_service_rejects_video_when_audio_disappears_mid_job(tmp_path, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Missing audio")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"audio" * 100)
    assert store.save_timing(
        project["id"], lesson["id"],
        {"steps": [{"id": 1, "start": 0, "end": 3}], "total_duration": 3},
    )

    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(render_service, "project_store", store)
    monkeypatch.setattr(render_service, "OUTPUTS_DIR", tmp_path / "outputs")

    async def render_after_audio_removed(**kwargs):
        assert kwargs["require_audio"] is True
        Path(paths["full_audio"]).unlink()
        output = Path(kwargs["output_dir"]) / "audio-missing.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video" * 300)
        return str(output)

    monkeypatch.setattr(video_encoder, "render_and_encode", render_after_audio_removed)
    job = jobs.create_job("render", {"project_id": project["id"], "lesson_id": lesson["id"]})
    await render_service._run_render(job["id"], project["id"], lesson["id"])

    completed = jobs.get_job(job["id"])
    assert completed["status"] == "cancelled"
    assert completed["result"] == {"stale": True}
    assert not store.get_lesson(project["id"], lesson["id"]).get("rendered_video_path")
    assert not (tmp_path / "outputs" / project["id"] / "audio-missing.mp4").exists()


def test_encoder_dependency_resolution_is_repository_local():
    node_modules = video_encoder._find_node_modules()
    assert node_modules is not None
    assert (Path(node_modules) / "canvas").is_dir()
    assert "tubecli" not in str(node_modules).lower()
    for executable in ("node", "ffmpeg", "ffprobe"):
        resolved = Path(video_encoder._find_executable(executable))
        assert resolved.parent.name == "tools"
        assert resolved.is_file()


@pytest.mark.asyncio
async def test_missing_canvas_never_installs_system_dependencies(monkeypatch):
    monkeypatch.setattr(video_encoder, "_find_node_modules", lambda: None)
    with pytest.raises(RuntimeError, match="khôi phục bundle"):
        await video_encoder._ensure_canvas()
