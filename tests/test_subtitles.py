import json

from core.project_store import ProjectStore
from core.subtitles import subtitle_config


def test_legacy_auto_subtitle_label_uses_style_default():
    config = subtitle_config({
        "subtitle_enabled": True,
        "subtitle_preset": "🤖 Tự động theo phong cách",
        "art_style": "techdark",
    }, {})

    assert config["preset"] == "tech_chip"


def test_legacy_project_preferences_migrate_without_template_drift(tmp_path):
    store = ProjectStore(tmp_path / "projects")
    project = store.create_project("Legacy", template="tech_explainer")
    path = store._project_json(project["id"])
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.update({
        "art_style": "default",
        "bg": "Theo phong cách (mặc định)",
        "subtitle_preset": "🤖 Tự động theo phong cách",
    })
    path.write_text(json.dumps(raw), encoding="utf-8")

    assert store.migrate_legacy_preferences() == 1
    migrated = store.get_project(project["id"])
    assert migrated["art_style"] == "techdark"
    assert migrated["bg"] == ""
    assert migrated["subtitle_preset"] == ""
