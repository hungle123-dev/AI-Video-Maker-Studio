from __future__ import annotations

import threading

import flet as ft

from core import jobs
from core.key_manager import KeyManager
from core.project_store import ProjectStore


def _find_control(root, kind, label):
    pending, seen = [root], set()
    while pending:
        control = pending.pop()
        if control is None or id(control) in seen:
            continue
        seen.add(id(control))
        if isinstance(control, kind) and getattr(control, "label", None) == label:
            return control
        for attr in ("controls", "actions"):
            pending.extend(getattr(control, attr, None) or [])
        content = getattr(control, "content", None)
        if content is not None:
            pending.append(content)
    raise AssertionError(f"Không tìm thấy control {label}")


def test_settings_actions(fake_page, monkeypatch):
    import config
    import core.tts_vivibe as tts_vivibe

    settings = {"ai_provider": "gemini", "render_fps": 30, "gpu_encoder": "auto"}
    saved = []
    monkeypatch.setattr(config, "load_settings", lambda: dict(settings))
    monkeypatch.setattr(config, "save_settings", lambda value: saved.append(dict(value)))
    saved_credentials = []
    monkeypatch.setattr(tts_vivibe, "load_credentials", lambda: ("", ""))
    monkeypatch.setattr(
        tts_vivibe,
        "save_credentials",
        lambda username, password: saved_credentials.append((username, password)),
    )

    from ui.settings.view import SettingsView

    view = SettingsView(fake_page)
    view.ai_provider.value = "openai"
    view.ai_model.value = "gpt-4o-mini"
    view.fps.value = "99"
    view.gpu.value = "cpu"
    view.vivibe_user.value = "voice@example.test"
    view.vivibe_password.value = "secret"
    view._save(None)
    assert saved[-1]["render_fps"] == 60
    assert saved[-1]["ai_provider"] == "openai"
    assert saved_credentials == [("voice@example.test", "secret")]


def test_keys_and_local_template_actions(tmp_path, fake_page, monkeypatch):
    import core.key_manager as key_manager_module

    manager = KeyManager(str(tmp_path / "keys.json"))
    manager.add_key("gemini", "key-one", "primary")
    monkeypatch.setattr(key_manager_module, "key_manager", manager)
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)

    from ui.keys.view import KeysView
    from ui.templates.view import TemplatesView

    keys_view = KeysView(fake_page)
    keys_view._toggle("gemini", "primary", False)
    assert manager.list_keys("gemini")[0]["active"] is False
    keys_view._remove("gemini", "primary")
    assert manager.list_keys("gemini") == []

    templates_view = TemplatesView(fake_page)
    templates_view._set_aspect("1:1")
    assert templates_view._aspect == "1:1"


def test_projects_actions_ai_batch_and_finished_result(
    tmp_path, fake_page, monkeypatch, script_copy
):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Workflow", min_steps=2)
    first = store.create_lesson(project["id"], "Một")
    second = store.create_lesson(project["id"], "Hai")
    store.save_script(project["id"], first["id"], script_copy)
    store.save_script(project["id"], second["id"], script_copy)

    import core.project_store as project_store_module
    import core.render_service as render_service
    import core.script_generator as script_generator

    monkeypatch.setattr(project_store_module, "project_store", store)
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    from ui.projects.view import ProjectsView

    view = ProjectsView(fake_page, lambda *_a: None)
    view._select_project(project)
    view._change_style(project["id"], "cyberpunk")
    view._change_bg(project["id"], "paper")
    view._change_template(project["id"], "lux_finance")
    current = store.get_project(project["id"])
    assert current["template"] == "lux_finance"

    queued = []
    monkeypatch.setattr(render_service, "queue_tts", lambda pid, lid: queued.append(("tts", lid)) or {"id": "t"})
    monkeypatch.setattr(render_service, "queue_render", lambda pid, lid: queued.append(("render", lid)) or {"id": "r"})
    monkeypatch.setattr(render_service, "queue_full_pipeline", lambda pid, lid: queued.append(("pipeline", lid)) or {"id": "p"})
    monkeypatch.setattr(view, "_ensure_poll", lambda: None)
    view._do_batch(
        [
            {"id": first["id"], "has_audio": True},
            {"id": second["id"], "has_audio": False},
        ],
        "pipeline",
    )
    assert queued[-2:] == [("render", first["id"]), ("pipeline", second["id"])]

    generated = dict(script_copy)
    generated["title"] = "Kịch bản AI"
    monkeypatch.setattr(script_generator, "generate_lesson_script", lambda *_a, **_k: (generated, []))
    monkeypatch.setattr(threading.Thread, "start", lambda self: self.run())
    view._ai_gen_lesson(second["id"])
    assert store.get_lesson(project["id"], second["id"])["script"]["title"] == "Kịch bản AI"

    job = jobs.create_job("autopilot")
    jobs.update_job(job["id"], status="done", progress=100, message="Xong")
    progress, status, log = ft.ProgressBar(value=0), ft.Text(), ft.Column([])
    done = []
    view._watch_autopilot(job["id"], progress, status, log, done.append)
    assert progress.value == 1 and status.value == "Xong" and done

    video = tmp_path / "done.mp4"
    video.write_bytes(b"video")
    completed = {
        "id": "render-done",
        "status": "done",
        "meta": {"project_id": project["id"], "lesson_id": first["id"]},
        "result": {"video": str(video)},
    }
    monkeypatch.setattr(jobs, "list_jobs", lambda **_k: [completed])
    monkeypatch.setattr(view, "_active_jobs_map", lambda: {})
    shown = []
    import ui.components as components

    monkeypatch.setattr(components, "show_result", lambda *args: shown.append(args))
    view._check_finished_renders()
    assert shown and shown[0][-1] == str(video)


def test_create_project_and_start_autopilot_dialogs(tmp_path, fake_page, monkeypatch):
    store = ProjectStore(tmp_path / "projects")
    import core.autopilot as autopilot
    import core.project_store as project_store_module
    import core.voices as voices

    monkeypatch.setattr(project_store_module, "project_store", store)
    monkeypatch.setattr(
        voices,
        "list_voices",
        lambda _engine, _lang: [
            {"id": "vi-VN-HoaiMyNeural", "display": "Hoài My"}
        ],
    )
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    from ui.projects.view import ProjectsView

    view = ProjectsView(fake_page, lambda *_a: None)
    monkeypatch.setattr(view, "_save_prefs", lambda _values: None)
    monkeypatch.setattr(threading.Thread, "start", lambda self: self.run())

    create_dialog = view._create_dialog()
    _find_control(create_dialog, ft.TextField, "Tên project *").value = "Project UI"
    create_dialog.actions[-1].on_click(None)
    assert store.list_projects()[0]["title"] == "Project UI"

    started = []
    monkeypatch.setattr(
        autopilot,
        "run_autopilot",
        lambda idea, count, **options: started.append((idea, count, options))
        or {"id": "autopilot-fake"},
    )
    auto_dialog = view._autopilot_dialog()
    _find_control(auto_dialog, ft.TextField, "Ý tưởng của bạn *").value = "Dạy AI"
    auto_dialog.actions[-1].on_click(None)
    assert started and started[0][0:2] == ("Dạy AI", 5)
    assert started[0][2]["voice"] == "vi-VN-HoaiMyNeural"


def test_project_form_reapplies_saved_template_and_uses_stable_auto_ids(fake_page, monkeypatch):
    import core.voices as voices

    monkeypatch.setattr(
        voices,
        "list_voices",
        lambda _engine, _lang: [{"id": "vi-VN-HoaiMyNeural", "display": "Hoài My"}],
    )
    monkeypatch.setattr(threading.Thread, "start", lambda self: self.run())
    from ui.projects.view import ProjectsView

    view = ProjectsView(fake_page, lambda *_a: None)
    monkeypatch.setattr(view, "_load_prefs", lambda: {
        "template": "tech_explainer",
        "art_style": "default",
        "bg": "Theo phong cách (mặc định)",
        "subtitle_preset": "🤖 Tự động theo phong cách",
        "tts_engine": "edge",
        "lang": "vi",
    })
    _sections, values, _validate, _language = view._config_block()

    options = values()
    assert options["template"] == "tech_explainer"
    assert options["art_style"] == "techdark"
    assert options["bg"] == ""
    assert options["subtitle_preset"] == ""


def test_editor_ai_and_subtitle_save(tmp_path, fake_page, monkeypatch, script_copy):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Editor", min_steps=2)
    lesson = store.create_lesson(project["id"], "Bài")
    store.save_script(project["id"], lesson["id"], script_copy)

    import core.project_store as project_store_module
    import core.script_generator as script_generator

    monkeypatch.setattr(project_store_module, "project_store", store)
    from ui.editor.view import EditorView

    view = EditorView(fake_page, project["id"], lesson["id"], lambda: None)
    generated = dict(script_copy)
    generated["title"] = "AI hoàn tất"
    monkeypatch.setattr(script_generator, "generate_lesson_script", lambda *_a, **_k: (generated, []))
    monkeypatch.setattr(threading.Thread, "start", lambda self: self.run())
    view._ai_dialog(None)
    dialog = fake_page.opened[-1]
    dialog.content.controls[0].value = "Chủ đề AI"
    dialog.actions[-1].on_click(None)
    assert store.get_lesson(project["id"], lesson["id"])["script"]["title"] == "AI hoàn tất"

    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    monkeypatch.setattr(threading.Timer, "start", lambda _self: None)
    from ui.subtitle_picker import show_subtitle_dialog

    saved = []
    subtitle = show_subtitle_dialog(fake_page, store.get_project(project["id"]), on_saved=saved.append)
    subtitle.actions[-1].on_click(None)
    assert saved and "subtitle_preset" in store.get_project(project["id"])
