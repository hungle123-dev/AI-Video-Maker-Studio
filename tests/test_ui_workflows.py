from __future__ import annotations

import base64
import threading
from pathlib import Path

import flet as ft

from core.project_store import ProjectStore


def test_all_main_views_construct(fake_page, monkeypatch):
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    checks = [
        ("ui.dashboard.view", "DashboardView", (fake_page, lambda *_: None)),
        ("ui.projects.view", "ProjectsView", (fake_page, lambda *_: None)),
        ("ui.render_queue.view", "RenderQueueView", (fake_page,)),
        ("ui.keys.view", "KeysView", (fake_page,)),
        ("ui.settings.view", "SettingsView", (fake_page,)),
        ("ui.templates.view", "TemplatesView", (fake_page,)),
    ]
    for module_name, class_name, args in checks:
        module = __import__(module_name, fromlist=[class_name])
        view = getattr(module, class_name)(*args)
        assert isinstance(view, ft.Control)
        assert view.controls


def test_projects_layout_has_bounded_stretched_content(fake_page):
    from ui.projects.view import ProjectsView

    view = ProjectsView(fake_page, lambda *_: None)
    header, body = view.controls

    assert view.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    assert not header.wrap
    assert body.expand
    assert body.vertical_alignment == ft.CrossAxisAlignment.STRETCH


def test_editor_add_delete_save_and_media_guards(tmp_path, fake_page, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Editor")
    lesson = store.create_lesson(project["id"], "Lesson")
    store.save_script(project["id"], lesson["id"], script_copy)

    import core.project_store as project_store_module

    monkeypatch.setattr(project_store_module, "project_store", store)

    from ui.editor.view import EditorView

    view = EditorView(fake_page, project["id"], lesson["id"], lambda: None)
    original = len(view.script["steps"])
    view._add_step(None)
    assert len(view.script["steps"]) == original + 1
    view._del_step(1)
    assert [step["id"] for step in view.script["steps"]] == list(
        range(1, len(view.script["steps"]) + 1)
    )
    view.title_field.value = "Tiêu đề đã sửa"
    assert view._save()
    assert store.get_lesson(project["id"], lesson["id"])["script"]["title"] == "Tiêu đề đã sửa"


def test_render_dialog_selects_pipeline_or_video(tmp_path, fake_page, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Render")
    lesson = store.create_lesson(project["id"], "Lesson")
    store.save_script(project["id"], lesson["id"], script_copy)

    import core.project_store as project_store_module
    import core.render_service as render_service

    monkeypatch.setattr(project_store_module, "project_store", store)
    calls = []
    monkeypatch.setattr(
        render_service,
        "queue_full_pipeline",
        lambda pid, lid: calls.append(("pipeline", pid, lid)) or {"id": "pipeline-1"},
    )
    monkeypatch.setattr(
        render_service,
        "queue_render",
        lambda pid, lid: calls.append(("render", pid, lid)) or {"id": "render-1"},
    )

    from ui.render_dialog import render_lesson

    render_lesson(fake_page, project["id"], lesson["id"])
    assert calls[-1][0] == "pipeline"

    paths = store.lesson_paths(project["id"], lesson["id"])
    from pathlib import Path
    import json

    timing = {"steps": [{"id": 1, "start": 0, "end": 3}], "total_duration": 3}
    Path(paths["timing"]).write_text(json.dumps(timing), encoding="utf-8")
    render_lesson(fake_page, project["id"], lesson["id"])
    assert calls[-1][0] == "pipeline"

    Path(paths["audio_dir"]).mkdir(parents=True)
    Path(paths["full_audio"]).write_bytes(b"audio")
    assert store.save_timing(project["id"], lesson["id"], timing)
    render_lesson(fake_page, project["id"], lesson["id"])
    assert calls[-1][0] == "render"


def test_preview_and_subtitle_dialogs_open(tmp_path, fake_page, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Preview", aspect_ratio="1:1")
    lesson_meta = store.create_lesson(project["id"], "Lesson")
    store.save_script(project["id"], lesson_meta["id"], script_copy)
    lesson = store.get_lesson(project["id"], lesson_meta["id"])

    import core.project_store as project_store_module

    monkeypatch.setattr(project_store_module, "project_store", store)
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    monkeypatch.setattr(threading.Timer, "start", lambda _self: None)

    from ui.preview_dialog import show_preview
    from ui.subtitle_picker import show_subtitle_dialog

    assert isinstance(show_preview(fake_page, project, lesson), ft.AlertDialog)
    dialog = show_subtitle_dialog(fake_page, project, script=script_copy)
    assert isinstance(dialog, ft.AlertDialog)


def test_main_wires_navigation_layout(fake_page, monkeypatch):
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    import core.sysmon as sysmon

    monkeypatch.setattr(sysmon, "start", lambda: None)
    import main

    main.main(fake_page)
    assert fake_page.app_layout is not None
    assert fake_page.added == [fake_page.app_layout]
    fake_page.app_layout.navigate("settings")
    assert fake_page.app_layout._active == "settings"


def test_main_reuses_long_lived_navigation_views(fake_page, monkeypatch):
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    import core.sysmon as sysmon

    monkeypatch.setattr(sysmon, "start", lambda: None)
    import main

    main.main(fake_page)
    fake_page.app_layout.navigate("projects")
    projects = fake_page.app_layout.content_area.content
    assert projects._active
    fake_page.app_layout.navigate("settings")
    assert not projects._active
    fake_page.app_layout.navigate("projects")
    assert fake_page.app_layout.content_area.content is projects
    assert projects._active


def test_hidden_projects_view_does_not_start_or_show_render_results(fake_page, monkeypatch):
    from ui.projects.view import ProjectsView

    view = ProjectsView(fake_page, lambda *_: None)
    view.selected_project = {"id": "project-hidden"}
    view.deactivate()

    monkeypatch.setattr(
        view,
        "_active_jobs_map",
        lambda: (_ for _ in ()).throw(AssertionError("hidden view polled jobs")),
    )
    view._ensure_poll()
    view._check_finished_renders()
    assert not view._polling


def test_projects_preserves_open_form_when_a_render_finishes(fake_page, monkeypatch):
    from core import jobs
    from ui.projects.view import ProjectsView

    view = ProjectsView(fake_page, lambda *_: None)
    view.selected_project = {"id": "project-open-form"}
    dialog = ft.AlertDialog()
    dialog.open = True
    fake_page.overlay.append(dialog)
    monkeypatch.setattr(
        jobs,
        "list_jobs",
        lambda **_kwargs: [{
            "id": "done-render",
            "status": "done",
            "meta": {"project_id": "project-open-form", "lesson_id": "lesson"},
            "result": {"video": "C:/video.mp4"},
        }],
    )
    monkeypatch.setattr(view, "_active_jobs_map", lambda: {})

    view._check_finished_renders()
    assert fake_page.opened
    assert isinstance(fake_page.opened[-1], ft.SnackBar)


def test_static_preview_ignores_stale_renderer_result(tmp_path, fake_page, monkeypatch):
    import core.preview as preview
    import ui.preview_static as preview_static

    pending = []

    class DeferredThread:
        def __init__(self, *, target, daemon):
            self.target = target

        def start(self):
            pending.append(self.target)

    def render_step(_project, _script, index, output_path, **_kwargs):
        Path(output_path).write_bytes(f"step-{index}".encode())
        return {"ok": True, "path": output_path}

    monkeypatch.setattr(preview_static.threading, "Thread", DeferredThread)
    monkeypatch.setattr(preview_static, "_preview_dir", lambda _project_id, _lesson_id: str(tmp_path))
    monkeypatch.setattr(preview, "render_step_preview", render_step)
    dialog = preview_static.show_static_preview(
        fake_page,
        {"id": "project"},
        {"id": "lesson", "script": {"steps": [
            {"voice_text": "Bước một"}, {"voice_text": "Bước hai"},
        ]}},
    )
    controls = dialog.content.content.controls
    next_button = controls[0].controls[2]
    image = controls[1].controls[0].content

    next_button.on_click(None)
    assert len(pending) == 2
    pending[1]()  # Current Step 2 finishes first.
    expected = base64.b64encode(b"step-1").decode()
    assert image.src_base64 == expected
    pending[0]()  # Stale Step 1 finishes later and must be ignored.
    assert image.src_base64 == expected

    next_button.on_click(None)
    dialog.on_dismiss(None)
    pending[-1]()  # Native dismissal also invalidates a pending worker.
    assert image.src_base64 == expected


def test_local_navigation_has_no_license_route():
    from ui.app_layout import NAV_ITEMS

    routes = [route for route, _icon, _label in NAV_ITEMS]
    assert "license" not in routes
    assert routes == [
        "dashboard",
        "projects",
        "templates",
        "render_queue",
        "keys",
        "settings",
    ]


def test_vivibe_voice_catalog_repaints_overlay_and_replaces_stale_edge_voice(
    fake_page, monkeypatch
):
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    from core import tts_vivibe
    from ui.projects.view import ProjectsView

    monkeypatch.setattr(tts_vivibe, "credentials_ready", lambda: True)
    view = ProjectsView(fake_page, lambda *_: None)
    # Reproduce the real mounted ProjectsView: update() succeeds, but cannot
    # repaint controls hosted by page.overlay.
    monkeypatch.setattr(view, "update", lambda: None)
    monkeypatch.setattr(
        view,
        "_load_prefs",
        lambda: {
            "lang": "vi",
            "tts_engine": "edge",
            "voice": "vi-VN-HoaiMyNeural",
        },
    )

    sections, _values, _validate, _language_bar = view._config_block()

    def descendants(control):
        yield control
        content = getattr(control, "content", None)
        if content is not None:
            yield from descendants(content)
        for child in getattr(control, "controls", None) or []:
            yield from descendants(child)

    controls = [item for section in sections for item in descendants(section)]
    voice = next(
        item
        for item in controls
        if isinstance(item, ft.Dropdown) and item.label == "Giọng đọc"
    )
    engine = next(
        item
        for item in controls
        if isinstance(item, ft.Dropdown) and item.label == "Engine giọng đọc"
    )
    preview_button = next(
        item
        for item in controls
        if isinstance(item, ft.OutlinedButton) and item.text == "Nghe thử"
    )

    updates_before_change = fake_page.update_count
    engine.value = "vivibe"
    engine.on_change(None)

    status_values = [
        item.value for item in controls if isinstance(item, ft.Text)
    ]

    assert voice.value == "Giọng adam"
    assert len(voice.options) == 13
    assert "13 giọng" in status_values
    assert not any("Đang tải danh sách giọng" in str(value) for value in status_values)
    assert fake_page.update_count > updates_before_change

    played = []
    monkeypatch.setattr(view, "_play_file", lambda path: played.append(Path(path).name))
    preview_button.on_click(None)
    assert played == ["001.wav"]
