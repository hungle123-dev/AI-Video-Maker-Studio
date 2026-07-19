from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from core import font_store, fonts


def test_local_and_online_font_install_preview_remove(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "engines" / "web" / "Pangolin-Regular.ttf"
    font_dir = tmp_path / "data" / "fonts"
    manifest = tmp_path / "data" / "fonts.json"
    monkeypatch.setattr(fonts, "FONTS_DIR", font_dir)
    monkeypatch.setattr(fonts, "_manifest_path", lambda: manifest)

    record = fonts.add_font(str(source))
    assert record["family"] == "Pangolin"
    assert record["file"].startswith("fonts/")
    installed = fonts.resolve_user_font_path(record)
    assert installed is not None and installed.is_file()
    assert any(item["family"] == "Pangolin" for item in fonts.list_fonts())

    cache_dir = tmp_path / "font_cache"
    preview_dir = tmp_path / "font_preview"
    cache_dir.mkdir()
    preview_dir.mkdir()
    monkeypatch.setattr(font_store, "_cache_dir", lambda: cache_dir)
    monkeypatch.setattr(font_store, "_preview_dir", lambda: preview_dir)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("pangolin-regular.ttf", source.read_bytes())
    monkeypatch.setattr(font_store, "_download", lambda *_a, **_k: archive.getvalue())

    fetched = Path(font_store.fetch_font("Pangolin", "vietnamese"))
    sample = Path(font_store.render_sample("Pangolin", "vietnamese", "Việt Nam 0123"))
    assert fetched.is_file() and sample.is_file() and sample.stat().st_size > 100

    monkeypatch.setitem(
        font_store._cache,
        "fams",
        [
            {
                "family": "Pangolin",
                "category": "Handwriting",
                "subsets": ["latin", "vietnamese"],
                "popularity": 1,
            }
        ],
    )
    assert font_store.list_online("vietnamese")[0]["family"] == "Pangolin"
    assert font_store.region_count("vietnamese") == 1

    fonts.remove_font("Pangolin")
    assert not installed.exists()
    assert all(item["family"] != "Pangolin" for item in fonts._load_user())


def test_legacy_absolute_font_manifest_migrates_to_portable_data_dir(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "engines" / "web" / "Pangolin-Regular.ttf"
    legacy = tmp_path / "legacy-static" / "Pangolin-Regular.ttf"
    legacy.parent.mkdir()
    legacy.write_bytes(source.read_bytes())
    manifest = tmp_path / "data" / "fonts.json"
    manifest.parent.mkdir()
    manifest.write_text(
        '[{"family":"Pangolin","display":"Pangolin","file":' + json.dumps(str(legacy)) + ',"vietnamese":true,"user":true}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(fonts, "FONTS_DIR", tmp_path / "data" / "fonts")
    monkeypatch.setattr(fonts, "_manifest_path", lambda: manifest)

    records = fonts._load_user()
    assert len(records) == 1
    assert records[0]["file"].startswith("fonts/")
    resolved = fonts.resolve_user_font_path(records[0])
    assert resolved is not None and resolved.is_file()
    persisted = json.loads(manifest.read_text(encoding="utf-8"))
    assert not Path(persisted[0]["file"]).is_absolute()
