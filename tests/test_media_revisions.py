from __future__ import annotations

import copy
import json
import threading
from pathlib import Path

import pytest

from core import jobs, render_service
from core.project_store import ProjectStore
from engines import video_encoder


def _ready_lesson(store: ProjectStore, script: dict):
    project = store.create_project("Revision test", subtitle_enabled=False)
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    reservation = store.begin_tts_generation(project["id"], lesson["id"])
    assert reservation
    bundle = Path(paths["dir"]) / ".audio-job-fixture"
    bundle.mkdir()
    (bundle / "full_audio.mp3").write_bytes(b"audio" * 100)
    timing = {"steps": [{"id": 1, "start": 0, "end": 3, "words": []}], "total_duration": 3}
    assert store.commit_audio_bundle(
        project["id"],
        lesson["id"],
        bundle,
        timing,
        expected_audio_revision=reservation["audio_source_revision"],
    )
    return project, lesson, paths


def test_retts_immediately_invalidates_old_video_and_audio_version(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, _paths = _ready_lesson(store, script_copy)
    video = store.outputs_root / project["id"] / "old.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video" * 100)
    store.update_lesson_meta(
        project["id"], lesson["id"], status="done", rendered_video_path=str(video)
    )
    assert store.list_lessons(project["id"])[0]["has_video"]
    assert store.list_lessons(project["id"])[0]["has_audio"]

    reservation = store.begin_tts_generation(project["id"], lesson["id"])
    assert reservation
    refreshed = store.get_lesson(project["id"], lesson["id"])
    listed = store.list_lessons(project["id"])[0]
    assert refreshed["status"] == "ready"
    assert not refreshed.get("rendered_video_path")
    assert not listed["has_video"]
    assert not listed["has_audio"]


def test_stale_tts_bundle_cannot_publish_after_script_edit(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Stale TTS")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    reservation = store.begin_tts_generation(project["id"], lesson["id"])
    bundle = Path(paths["dir"]) / ".audio-job-stale"
    bundle.mkdir()
    (bundle / "full_audio.mp3").write_bytes(b"audio" * 100)
    timing = {"steps": [{"id": 1, "start": 0, "end": 3, "words": []}], "total_duration": 3}

    changed = copy.deepcopy(script_copy)
    changed["title"] = "Nội dung mới hơn TTS"
    assert store.save_script(project["id"], lesson["id"], changed)[0]
    assert not store.commit_audio_bundle(
        project["id"], lesson["id"], bundle, timing,
        expected_audio_revision=reservation["audio_source_revision"],
    )
    assert not bundle.exists()
    refreshed = store.get_lesson(project["id"], lesson["id"])
    assert refreshed["script"]["title"] == "Nội dung mới hơn TTS"
    assert not store.list_lessons(project["id"])[0]["has_audio"]


def test_script_save_crash_never_persists_new_script_with_old_video(
    tmp_path, monkeypatch, script_copy
):
    import core.project_store as project_store_module

    store = ProjectStore(tmp_path / "projects")
    project, lesson, paths = _ready_lesson(store, script_copy)
    video = store.outputs_root / project["id"] / "old.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video" * 100)
    store.update_lesson_meta(
        project["id"], lesson["id"], status="done", rendered_video_path=str(video)
    )
    changed = copy.deepcopy(script_copy)
    changed["title"] = "Script chưa được commit"
    original_write = project_store_module._write_json

    def fail_script_write(path, data):
        if Path(path) == Path(paths["script"]):
            raise OSError("simulated script write failure")
        return original_write(path, data)

    monkeypatch.setattr(project_store_module, "_write_json", fail_script_write)
    with pytest.raises(OSError, match="simulated script"):
        store.save_script(project["id"], lesson["id"], changed)

    refreshed = store.get_lesson(project["id"], lesson["id"])
    assert refreshed["script"]["title"] == script_copy["title"]
    assert not refreshed.get("rendered_video_path")
    assert refreshed["status"] == "ready"


@pytest.mark.asyncio
async def test_stale_render_job_cannot_republish_video_after_edit(tmp_path, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, _paths = _ready_lesson(store, script_copy)
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(render_service, "project_store", store)
    monkeypatch.setattr(render_service, "OUTPUTS_DIR", tmp_path / "outputs")

    async def stale_render(**kwargs):
        output = Path(kwargs["output_dir"]) / "stale.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video" * 300)
        changed = copy.deepcopy(script_copy)
        changed["title"] = "Đã sửa khi render đang chạy"
        assert store.save_script(project["id"], lesson["id"], changed)[0]
        return str(output)

    monkeypatch.setattr(video_encoder, "render_and_encode", stale_render)
    job = jobs.create_job("render", {"project_id": project["id"], "lesson_id": lesson["id"]})
    await render_service._run_render(job["id"], project["id"], lesson["id"])

    completed = jobs.get_job(job["id"])
    assert completed["status"] == "cancelled"
    assert completed["result"] == {"stale": True}
    assert not list((tmp_path / "outputs").rglob("stale.mp4"))
    refreshed = store.get_lesson(project["id"], lesson["id"])
    assert refreshed["script"]["title"] == "Đã sửa khi render đang chạy"
    assert not refreshed.get("rendered_video_path")


def test_read_only_normalization_never_rewrites_script_or_advertises_old_media(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, paths = _ready_lesson(store, script_copy)
    video = store.outputs_root / project["id"] / "old.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video" * 100)
    assert store.update_lesson_meta(
        project["id"], lesson["id"], status="done", rendered_video_path=str(video)
    )
    assert store.list_lessons(project["id"])[0]["has_video"]

    raw_legacy = {
        "title": "Legacy raw scene",
        "steps": [{
            "id": 1,
            "voice_text": "Không được chạy code thô.",
            "elements": [{"type": "custom_js", "code": "process.exit(99)"}],
        }],
    }
    Path(paths["script"]).write_text(json.dumps(raw_legacy), encoding="utf-8")
    before_read = Path(paths["script"]).read_bytes()

    listed = store.list_lessons(project["id"])[0]
    loaded = store.get_lesson(project["id"], lesson["id"])
    assert Path(paths["script"]).read_bytes() == before_read
    assert loaded["script_validation_errors"]
    assert not listed["has_audio"]
    assert not listed["has_video"]


def test_visual_change_without_existing_video_persists_revision_and_rejects_old_render(
    tmp_path, script_copy
):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, _paths = _ready_lesson(store, script_copy)
    before = store.get_render_snapshot(project["id"], lesson["id"])
    assert before

    assert store.update_project(project["id"], art_style="cyberpunk")
    after = store.get_render_snapshot(project["id"], lesson["id"])
    assert after
    assert after["render_source_revision"] > before["render_source_revision"]

    stale = store.outputs_root / project["id"] / "stale-visual.mp4"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"video" * 100)
    assert not store.publish_rendered_video(
        project["id"], lesson["id"], str(stale), "9:16",
        expected_render_revision=before["render_source_revision"],
        expected_audio_revision=before["audio_source_revision"],
    )


def test_save_timing_advances_revisions_before_it_can_replace_render_contract(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, _paths = _ready_lesson(store, script_copy)
    before = store.get_render_snapshot(project["id"], lesson["id"])
    assert before
    assert store.save_timing(
        project["id"], lesson["id"],
        {"steps": [{"id": 1, "start": 0, "end": 9, "words": []}], "total_duration": 9},
    )
    after = store.get_render_snapshot(project["id"], lesson["id"])
    assert after
    assert after["audio_source_revision"] > before["audio_source_revision"]
    assert after["render_source_revision"] > before["render_source_revision"]

    stale = store.outputs_root / project["id"] / "stale-timing.mp4"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"video" * 100)
    assert not store.publish_rendered_video(
        project["id"], lesson["id"], str(stale), "9:16",
        expected_render_revision=before["render_source_revision"],
        expected_audio_revision=before["audio_source_revision"],
    )


def test_render_snapshot_cannot_mix_old_project_with_new_lesson_revision(tmp_path, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, _paths = _ready_lesson(store, script_copy)
    initial = store.get_render_snapshot(project["id"], lesson["id"])
    assert initial

    project_read = threading.Event()
    allow_snapshot = threading.Event()
    original_project_meta = store._valid_project_meta

    def pause_after_project_read(project_id):
        meta = original_project_meta(project_id)
        if threading.current_thread().name == "snapshot-reader" and not project_read.is_set():
            project_read.set()
            assert allow_snapshot.wait(5)
        return meta

    monkeypatch.setattr(store, "_valid_project_meta", pause_after_project_read)
    result = {}
    reader = threading.Thread(
        name="snapshot-reader",
        target=lambda: result.setdefault("snapshot", store.get_render_snapshot(project["id"], lesson["id"])),
    )
    update_done = threading.Event()

    def update_style():
        store.update_project(project["id"], art_style="cyberpunk")
        update_done.set()

    reader.start()
    assert project_read.wait(5)
    updater = threading.Thread(target=update_style)
    updater.start()
    # update_project uses the same lock, so it cannot splice a new lesson
    # revision into the half-read snapshot.
    assert not update_done.wait(0.15)
    allow_snapshot.set()
    reader.join(timeout=5)
    updater.join(timeout=5)
    assert not reader.is_alive() and not updater.is_alive()
    assert update_done.is_set()

    snapshot = result["snapshot"]
    assert snapshot["project"]["art_style"] == "default"
    assert snapshot["render_source_revision"] == initial["render_source_revision"]
    current = store.get_render_snapshot(project["id"], lesson["id"])
    assert current and current["project"]["art_style"] == "cyberpunk"
    assert current["render_source_revision"] > snapshot["render_source_revision"]


def test_delete_waits_for_publish_then_removes_lesson_without_resurrection(
    tmp_path, monkeypatch, script_copy
):
    store = ProjectStore(tmp_path / "projects")
    project, lesson, _paths = _ready_lesson(store, script_copy)
    snapshot = store.get_render_snapshot(project["id"], lesson["id"])
    assert snapshot
    video = store.outputs_root / project["id"] / "pending.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video" * 100)

    import core.project_store as project_store_module

    lesson_meta_path = Path(snapshot["paths"]["dir"]) / "lesson.json"
    entered_publish = threading.Event()
    release_publish = threading.Event()
    original_write = project_store_module._write_json

    def pause_publish(path, data):
        if (
            Path(path) == lesson_meta_path
            and threading.current_thread().name == "publisher"
            and not entered_publish.is_set()
        ):
            entered_publish.set()
            assert release_publish.wait(5)
        return original_write(path, data)

    monkeypatch.setattr(project_store_module, "_write_json", pause_publish)
    published = {}
    publisher = threading.Thread(
        name="publisher",
        target=lambda: published.setdefault(
            "ok",
            store.publish_rendered_video(
                project["id"], lesson["id"], str(video), "9:16",
                expected_render_revision=snapshot["render_source_revision"],
                expected_audio_revision=snapshot["audio_source_revision"],
            ),
        ),
    )
    deleted = {}
    deleted_done = threading.Event()

    def remove_lesson():
        deleted["ok"] = store.delete_lesson(project["id"], lesson["id"])
        deleted_done.set()

    publisher.start()
    assert entered_publish.wait(5)
    deleter = threading.Thread(target=remove_lesson)
    deleter.start()
    assert not deleted_done.wait(0.15)
    release_publish.set()
    publisher.join(timeout=5)
    deleter.join(timeout=5)
    assert published == {"ok": True}
    assert deleted == {"ok": True}
    assert not Path(snapshot["paths"]["dir"]).exists()
