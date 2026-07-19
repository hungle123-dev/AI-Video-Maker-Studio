from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.project_store import (
    ProjectStore,
    audio_is_current,
    audio_source_revision,
    render_source_revision,
    script_has_content,
    timing_has_content,
)


def test_project_lesson_media_lifecycle(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project(
        "Series kiểm thử",
        aspect_ratio="16:9",
        lang="vi",
        subtitle_enabled=True,
    )
    assert store.get_project(project["id"])["aspect_ratio"] == "16:9"

    updated = store.update_project(project["id"], title="Series mới", ignored="x")
    assert updated["title"] == "Series mới"
    assert "ignored" not in updated

    lesson = store.create_lesson(project["id"], "Bài một")
    assert lesson and not store.list_lessons(project["id"])[0]["has_script"]

    ok, errors = store.save_script(project["id"], lesson["id"], script_copy)
    assert ok and not errors
    full = store.get_lesson(project["id"], lesson["id"])
    assert full["script"]["total_steps"] == 2
    assert script_has_content(full["script"])

    paths = store.lesson_paths(project["id"], lesson["id"])
    timing = {
        "steps": [{"id": 1, "start": 0, "end": 3, "words": []}],
        "total_duration": 3,
    }
    Path(paths["audio_dir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["full_audio"]).write_bytes(b"audio")
    assert store.save_timing(project["id"], lesson["id"], timing)
    video = store.outputs_root / project["id"] / "video.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    store.update_lesson_meta(
        project["id"], lesson["id"], rendered_video_path=str(video), status="done"
    )

    listed = store.list_lessons(project["id"])[0]
    assert listed["has_script"] and listed["has_audio"] and listed["has_video"]
    assert timing_has_content(timing)
    assert store.delete_lesson(project["id"], lesson["id"])
    assert store.list_lessons(project["id"]) == []
    assert store.delete_project(project["id"])


def test_short_audio_without_word_boundaries_is_still_renderable(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Short narration")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"short narration" * 20)
    timing = {"steps": [{"id": 1, "start": 0, "end": 2, "words": []}], "total_duration": 2}

    assert store.save_timing(project["id"], lesson["id"], timing)
    listed = store.list_lessons(project["id"])[0]
    assert timing_has_content(timing)
    assert listed["has_script"] and listed["has_audio"]


def test_project_aspect_ratio_is_allowlisted_for_create_and_update(tmp_path):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Safe aspect", aspect_ratio="../../victim")
    assert project["aspect_ratio"] == "9:16"
    assert store.update_project(project["id"], aspect_ratio="../../victim") is None
    assert store.get_project(project["id"])["aspect_ratio"] == "9:16"
    assert store.update_project(project["id"], aspect_ratio="1:1")["aspect_ratio"] == "1:1"


def test_duplicate_import_never_modifies_source(tmp_path):
    store = ProjectStore(tmp_path / "store")
    store.create_project("Existing")

    source = tmp_path / "external"
    lesson_dir = source / "lessons" / "lesson_a"
    lesson_dir.mkdir(parents=True)
    source_meta = {"id": "duplicate", "title": "External", "aspect_ratio": "../../victim"}
    (source / "project.json").write_text(json.dumps(source_meta), encoding="utf-8")
    (lesson_dir / "lesson.json").write_text(
        json.dumps({"id": "lesson_a", "project_id": "duplicate"}), encoding="utf-8"
    )
    (store.root / "duplicate").mkdir()
    (store.root / "duplicate" / "project.json").write_text(
        json.dumps({"id": "duplicate", "title": "Local"}), encoding="utf-8"
    )

    imported = store.import_external_project(str(source))
    assert imported and imported["id"] != "duplicate"
    assert imported["aspect_ratio"] == "9:16"
    assert json.loads((source / "project.json").read_text())["id"] == "duplicate"
    imported_lesson = json.loads(
        (store.root / imported["id"] / "lessons" / "lesson_a" / "lesson.json").read_text()
    )
    assert imported_lesson["project_id"] == imported["id"]


def test_import_rejects_invalid_id(tmp_path):
    store = ProjectStore(tmp_path / "store")
    source = tmp_path / "bad"
    source.mkdir()
    (source / "project.json").write_text(
        json.dumps({"id": "../escape", "title": "Bad"}), encoding="utf-8"
    )
    assert store.import_external_project(str(source)) is None

    for invalid_id in ("..", "bad*id", "x" * 65):
        (source / "project.json").write_text(
            json.dumps({"id": invalid_id, "title": "Bad"}), encoding="utf-8"
        )
        assert store.import_external_project(str(source)) is None


def test_unsafe_ids_cannot_escape_project_or_lesson_roots(tmp_path):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Safe")
    lesson = store.create_lesson(project["id"], "Safe lesson")
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("do not touch", encoding="utf-8")

    for unsafe in ("..", "../sentinel", "a/b", "a\\b", "x" * 65, ""):
        assert store.get_project(unsafe) is None
        assert store.update_project(unsafe, title="bad") is None
        assert not store.delete_project(unsafe)
        assert store.get_lesson(project["id"], unsafe) is None
        assert store.update_lesson_meta(project["id"], unsafe, title="bad") is None
        assert not store.delete_lesson(project["id"], unsafe)
        with pytest.raises(ValueError):
            store.lesson_paths(project["id"], unsafe)

    assert store.get_lesson(project["id"], lesson["id"])
    assert sentinel.read_text(encoding="utf-8") == "do not touch"


def test_save_script_and_visual_change_invalidate_stale_artifacts(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Invalidate")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert lesson
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]

    paths = store.lesson_paths(project["id"], lesson["id"])
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"audio" * 100)
    Path(paths["timing"]).write_text(
        json.dumps({"steps": [{"id": 1}], "total_duration": 3}), encoding="utf-8"
    )
    video = store.outputs_root / project["id"] / "old.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    store.update_lesson_meta(
        project["id"], lesson["id"], status="done", rendered_video_path=str(video)
    )

    changed = dict(script_copy)
    changed["title"] = "Script mới"
    changed["steps"] = [dict(script_copy["steps"][0], voice_text="Lời thoại mới")]
    assert store.save_script(project["id"], lesson["id"], changed)[0]
    refreshed = store.get_lesson(project["id"], lesson["id"])
    assert refreshed["status"] == "ready"
    assert not Path(paths["timing"]).exists()
    assert not Path(paths["audio_dir"]).exists()
    assert not refreshed.get("rendered_video_path")


def test_media_revisions_reject_stale_tts_and_render_results(tmp_path, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Revision")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"old-audio" * 100)
    timing = {"steps": [{"id": 1, "start": 0, "end": 3}], "total_duration": 3}
    assert store.save_timing(project["id"], lesson["id"], timing)
    old_video = store.outputs_root / project["id"] / "old.mp4"
    old_video.parent.mkdir(parents=True)
    old_video.write_bytes(b"old-video")
    assert store.update_lesson_meta(
        project["id"], lesson["id"], rendered_video_path=str(old_video), status="done"
    )
    before = store.get_lesson(project["id"], lesson["id"])
    old_audio_revision = audio_source_revision(before)
    old_render_revision = render_source_revision(before)

    reservation = store.begin_tts_generation(project["id"], lesson["id"])
    assert reservation
    reserved = store.get_lesson(project["id"], lesson["id"])
    assert not reserved.get("rendered_video_path")
    assert not audio_is_current(reserved, reserved["timing"], paths["full_audio"])

    stale_bundle = Path(paths["dir"]) / ".audio-job-stale"
    stale_bundle.mkdir()
    (stale_bundle / "full_audio.mp3").write_bytes(b"stale-audio" * 100)
    changed = copy.deepcopy(script_copy)
    changed["title"] = "Nội dung mới"
    assert store.save_script(project["id"], lesson["id"], changed)[0]
    assert not store.commit_audio_bundle(
        project["id"],
        lesson["id"],
        stale_bundle,
        timing,
        expected_audio_revision=reservation["audio_source_revision"],
    )
    assert not stale_bundle.exists()

    stale_video = store.outputs_root / project["id"] / "stale.mp4"
    stale_video.write_bytes(b"stale-video")
    assert not store.publish_rendered_video(
        project["id"],
        lesson["id"],
        str(stale_video),
        "9:16",
        expected_render_revision=old_render_revision,
        expected_audio_revision=old_audio_revision,
    )
    assert not store.get_lesson(project["id"], lesson["id"]).get("rendered_video_path")


def test_script_save_persists_invalidation_before_the_new_script(tmp_path, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Crash safety")
    lesson = store.create_lesson(project["id"], "Lesson")
    assert store.save_script(project["id"], lesson["id"], script_copy)[0]
    paths = store.lesson_paths(project["id"], lesson["id"])
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"audio" * 100)
    timing = {"steps": [{"id": 1, "start": 0, "end": 3}], "total_duration": 3}
    assert store.save_timing(project["id"], lesson["id"], timing)
    video = store.outputs_root / project["id"] / "published.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    assert store.update_lesson_meta(
        project["id"], lesson["id"], rendered_video_path=str(video), status="done"
    )

    import core.project_store as project_store_module

    original_write = project_store_module._write_json

    def fail_new_script(path, data):
        if Path(path).name == "lesson_script.json" and data.get("title") == "Crash mới":
            raise OSError("simulated script write interruption")
        return original_write(path, data)

    monkeypatch.setattr(project_store_module, "_write_json", fail_new_script)
    changed = copy.deepcopy(script_copy)
    changed["title"] = "Crash mới"
    with pytest.raises(OSError, match="simulated"):
        store.save_script(project["id"], lesson["id"], changed)

    recovered = store.get_lesson(project["id"], lesson["id"])
    assert recovered["script"]["title"] != "Crash mới"
    assert not recovered.get("rendered_video_path")
    assert not Path(paths["audio_dir"]).exists()
    assert video.exists()  # Output is not deleted outside the lesson ownership boundary.

    # Recreate valid derived media, then alter a rendering-only project setting.
    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"audio" * 100)
    Path(paths["timing"]).write_text(
        json.dumps({"steps": [{"id": 1}], "total_duration": 3}), encoding="utf-8"
    )
    store.update_lesson_meta(project["id"], lesson["id"], rendered_video_path=str(video))
    store.update_project(project["id"], art_style="cyberpunk")
    refreshed = store.get_lesson(project["id"], lesson["id"])
    assert Path(paths["full_audio"]).exists()
    assert not refreshed.get("rendered_video_path")


def test_import_normalizes_script_and_keeps_audit_record(tmp_path):
    store = ProjectStore(tmp_path / "projects")
    source = tmp_path / "external"
    lesson_dir = source / "lessons" / "lesson_safe"
    lesson_dir.mkdir(parents=True)
    (source / "project.json").write_text(
        json.dumps({"id": "source_safe", "title": "External"}), encoding="utf-8"
    )
    (lesson_dir / "lesson.json").write_text(
        json.dumps({"id": "lesson_safe", "project_id": "source_safe"}), encoding="utf-8"
    )
    (lesson_dir / "lesson_script.json").write_text(
        json.dumps(
            {
                "title": "Unsafe",
                "steps": [{
                    "id": 1,
                    "voice_text": "Nội dung vẫn còn.",
                    "elements": [
                        {"type": "text", "text": "An toàn"},
                        {"type": "custom_js", "code": "process.exit(99)"},
                    ],
                }],
            }
        ),
        encoding="utf-8",
    )

    imported = store.import_external_project(str(source))
    assert imported
    saved_script = json.loads(
        (store.root / imported["id"] / "lessons" / "lesson_safe" / "lesson_script.json").read_text(
            encoding="utf-8"
        )
    )
    assert "process.exit" not in json.dumps(saved_script)
    assert all(
        element.get("type") != "custom_js"
        for element in saved_script["steps"][0]["elements"]
    )
    audit = json.loads((store.root / imported["id"] / "import_audit.json").read_text(encoding="utf-8"))
    assert audit["warnings"]


def test_symlinked_lesson_root_is_not_followed(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("Platform không hỗ trợ symlink")
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Safe")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "lesson_outside").mkdir()
    (outside / "lesson_outside" / "lesson.json").write_text(
        json.dumps({"id": "lesson_outside", "project_id": project["id"]}), encoding="utf-8"
    )
    link = store.root / project["id"] / "lessons"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Tạo symlink cần quyền đặc biệt trên Windows")

    assert store.list_lessons(project["id"]) == []
    assert store.get_lesson(project["id"], "lesson_outside") is None
    assert not store.delete_lesson(project["id"], "lesson_outside")
    assert (outside / "lesson_outside").is_dir()


def test_create_lesson_retries_collision_without_overwriting_existing(tmp_path, monkeypatch):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Collision")
    existing_id = "lesson_" + "a" * 32
    existing_dir = store._lesson_dir(project["id"], existing_id)
    assert existing_dir is not None
    existing_dir.mkdir(parents=True)
    (existing_dir / "lesson.json").write_text(
        json.dumps({"id": existing_id, "project_id": project["id"], "title": "Giữ nguyên"}),
        encoding="utf-8",
    )
    (existing_dir / "lesson_script.json").write_text(
        json.dumps({"title": "Giữ nguyên", "steps": []}), encoding="utf-8"
    )

    import core.project_store as project_store_module

    uuids = iter(["a" * 32, "b" * 32])
    monkeypatch.setattr(
        project_store_module.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=next(uuids)),
    )
    created = store.create_lesson(project["id"], "Bài mới")

    assert created and created["id"] == "lesson_" + "b" * 32
    original = json.loads((existing_dir / "lesson.json").read_text(encoding="utf-8"))
    assert original["title"] == "Giữ nguyên"
    assert {lesson["id"] for lesson in store.list_lessons(project["id"])} == {
        existing_id,
        created["id"],
    }


def test_delete_lesson_cleans_only_owned_output_preview_and_jobs(tmp_path, monkeypatch):
    from core import jobs

    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Project A")
    other_project = store.create_project("Project B")
    lesson = store.create_lesson(project["id"], "Bài A")
    other_lesson = store.create_lesson(project["id"], "Bài B")
    foreign_lesson = store.create_lesson(other_project["id"], "Bài ngoài")
    assert lesson and other_lesson and foreign_lesson
    # Subtitle cards intentionally use a generic sample instead of lesson
    # content. Give the surviving project a different visual context so this
    # test exercises cleanup of a genuinely unshared cache entry.
    assert store.update_project(other_project["id"], theme="light")

    output_dir = store.outputs_root / project["id"]
    output_dir.mkdir(parents=True)
    generated = output_dir / f"edu_{project['id']}_{lesson['id']}_r1_9_16.mp4"
    generated.write_bytes(b"owned render")
    temp_dir = output_dir / f"temp_chunks_{generated.name}.rendering.mp4"
    temp_dir.mkdir()
    owned_legacy = output_dir / "owned-legacy.mp4"
    owned_legacy.write_bytes(b"owned legacy")
    other_legacy = output_dir / "other-lesson.mp4"
    other_legacy.write_bytes(b"other lesson")
    foreign_output = store.outputs_root / other_project["id"] / "foreign.mp4"
    foreign_output.parent.mkdir(parents=True)
    foreign_output.write_bytes(b"foreign project")
    assert store.update_lesson_meta(
        project["id"], lesson["id"], rendered_video_path=str(owned_legacy)
    )
    assert store.update_lesson_meta(
        project["id"], other_lesson["id"], rendered_video_path=str(other_legacy)
    )

    previews = store.root.parent / "previews"
    legacy_preview = previews / lesson["id"] / "s_0.png"
    scoped_preview = previews / project["id"] / lesson["id"] / "s_0.png"
    other_preview = previews / project["id"] / other_lesson["id"] / "s_0.png"
    for preview in (legacy_preview, scoped_preview, other_preview):
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"preview")

    owned_thumb = next(
        iter(
            store._subtitle_thumb_paths_for(
                store.get_project(project["id"]),
                store.get_lesson(project["id"], lesson["id"])["script"],
            )
        )
    )
    foreign_thumb = next(
        iter(
            store._subtitle_thumb_paths_for(
                store.get_project(other_project["id"]),
                store.get_lesson(other_project["id"], foreign_lesson["id"])["script"],
            )
        )
    )
    assert owned_thumb != foreign_thumb
    owned_thumb.parent.mkdir(parents=True, exist_ok=True)
    owned_thumb.write_bytes(b"owned subtitle thumbnail")
    foreign_thumb.parent.mkdir(parents=True, exist_ok=True)
    foreign_thumb.write_bytes(b"foreign subtitle thumbnail")

    matching_job = jobs.create_job("render", {"project_id": project["id"], "lesson_id": lesson["id"]})
    other_lesson_job = jobs.create_job(
        "render", {"project_id": project["id"], "lesson_id": other_lesson["id"]}
    )
    foreign_job = jobs.create_job(
        "render", {"project_id": other_project["id"], "lesson_id": foreign_lesson["id"]}
    )

    assert store.delete_lesson(project["id"], lesson["id"])
    assert not generated.exists()
    assert not temp_dir.exists()
    assert not owned_legacy.exists()
    assert other_legacy.exists()
    assert foreign_output.exists()
    assert not legacy_preview.exists()
    assert not scoped_preview.exists()
    assert other_preview.exists()
    # The remaining lesson in this project uses the same generic style card,
    # so the shared cache must survive deletion of just one lesson.
    assert owned_thumb.exists()
    assert foreign_thumb.exists()
    assert jobs.get_job(matching_job["id"]) is None
    assert jobs.get_job(other_lesson_job["id"]) is not None
    assert jobs.get_job(foreign_job["id"]) is not None


def test_delete_project_cleans_its_artifacts_without_touching_other_project(tmp_path, monkeypatch):
    from core import jobs

    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Project A")
    other_project = store.create_project("Project A")
    lesson = store.create_lesson(project["id"], "Bài A")
    other_lesson = store.create_lesson(other_project["id"], "Bài B")
    assert lesson and other_lesson

    # Simulate a legacy cross-project collision: the old preview layout has
    # no project ID, so it must be retained for the surviving project.
    shared_dir = store._lesson_dir(other_project["id"], lesson["id"])
    assert shared_dir is not None
    shared_dir.mkdir(parents=True)
    (shared_dir / "lesson.json").write_text(
        json.dumps({"id": lesson["id"], "project_id": other_project["id"]}),
        encoding="utf-8",
    )
    (shared_dir / "lesson_script.json").write_text(
        json.dumps({"title": "Shared", "steps": []}), encoding="utf-8"
    )

    own_output = store.outputs_root / project["id"] / "render.mp4"
    foreign_output = store.outputs_root / other_project["id"] / "render.mp4"
    own_output.parent.mkdir(parents=True)
    foreign_output.parent.mkdir(parents=True)
    own_output.write_bytes(b"delete me")
    foreign_output.write_bytes(b"keep me")

    previews = store.root.parent / "previews"
    own_scoped_preview = previews / project["id"] / lesson["id"] / "s_0.png"
    foreign_scoped_preview = previews / other_project["id"] / other_lesson["id"] / "s_0.png"
    shared_legacy_preview = previews / lesson["id"] / "s_0.png"
    own_subtitle_preview = previews / "subtitle_dialog" / f"{project['id']}_0_token.png"
    foreign_subtitle_preview = previews / "subtitle_dialog" / f"{other_project['id']}_0_token.png"
    for preview in (
        own_scoped_preview,
        foreign_scoped_preview,
        shared_legacy_preview,
        own_subtitle_preview,
        foreign_subtitle_preview,
    ):
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"preview")

    own_thumb_paths = store._subtitle_thumb_paths_for(
        store.get_project(project["id"]),
        store.get_lesson(project["id"], lesson["id"])["script"],
    )
    foreign_thumb_paths = store._subtitle_thumb_paths_for(
        store.get_project(other_project["id"]),
        store.get_lesson(other_project["id"], other_lesson["id"])["script"],
    )
    shared_thumbs = own_thumb_paths & foreign_thumb_paths
    assert shared_thumbs
    shared_thumb = next(iter(shared_thumbs))
    shared_thumb.parent.mkdir(parents=True, exist_ok=True)
    shared_thumb.write_bytes(b"shared subtitle thumbnail")

    owned_job = jobs.create_job("render", {"project_id": project["id"], "lesson_id": lesson["id"]})
    autopilot_job = jobs.create_job("autopilot", {"idea": "private"})
    jobs.update_job(autopilot_job["id"], result={"project_id": project["id"], "lessons": [lesson["id"]]})
    foreign_job = jobs.create_job(
        "render", {"project_id": other_project["id"], "lesson_id": other_lesson["id"]}
    )

    assert store.delete_project(project["id"])
    assert not (store.root / project["id"]).exists()
    assert not (store.outputs_root / project["id"]).exists()
    assert foreign_output.exists()
    assert not own_scoped_preview.exists()
    assert foreign_scoped_preview.exists()
    assert shared_legacy_preview.exists()
    assert not own_subtitle_preview.exists()
    assert foreign_subtitle_preview.exists()
    assert shared_thumb.exists()
    assert jobs.get_job(owned_job["id"]) is None
    assert jobs.get_job(autopilot_job["id"]) is None
    assert jobs.get_job(foreign_job["id"]) is not None
