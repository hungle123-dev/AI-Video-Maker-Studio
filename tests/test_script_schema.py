from __future__ import annotations

import copy
import json

import pytest

from core import script_generator
from core.schema import check_custom_js, normalize_gallery_src, validate_script


def test_script_helpers_cover_json_comments_and_quota():
    assert script_generator._extract_json('prefix ```json\n{"a": 1}\n``` suffix') == {"a": 1}
    assert script_generator._parse_reset_seconds("reset after 1h 2m 3s") == 3723
    code = "ctx.save();// broken inline comment ctx.fillRect(1,2,3,4);ctx.restore();return 900;"
    fixed = script_generator._fix_inline_comments(code)
    assert "ctx.fillRect" in fixed
    duplicate = (
        "ui.title(W/2,100,'Bước một',{size:54,color:rc('cyan')});"
        "ui.chip(W/2,60,'TÍNH NĂNG 1');"
    )
    cleaned = script_generator._without_repeated_custom_heading(duplicate, "Bước một")
    assert "ui.title" not in cleaned
    assert "TÍNH NĂNG 1" in cleaned
    assert script_generator._ui_called_inside_transform(
        "ctx.save();ctx.translate(10,20);ui.chip(10,20,'Sai');ctx.restore();"
    )
    assert not script_generator._ui_called_inside_transform(
        "ctx.save();ctx.translate(10,20);ctx.restore();ui.chip(10,20,'Đúng');"
    )
    issues = script_generator._custom_layout_issues(
        "ui.chip(540,100,'NHÃN QUÁ DÀI BỊ CHỒNG');"
        "ctx.roundRect(10,20,30,40,8);ctx.fill();"
        "ctx.fillText('A sentence that cannot fit inside its card',10,20);"
    )
    assert any("chip quá dài" in issue for issue in issues)
    assert any("roundRect" in issue for issue in issues)
    assert any("fillText không wrap" in issue for issue in issues)
    assert script_generator._height_at_least({"height": "900"}, 800)
    assert not script_generator._height_at_least({"height": "auto"}, 800)
    hint = script_generator._template_hint({"name": "Mẫu", "vibe": "Tông rõ", "effect": "flow_pipeline"})
    assert "Tông rõ" in hint and "flow_pipeline" in hint


def test_generate_outline_enforces_requested_count(monkeypatch):
    payload = {
        "project_title": "Series",
        "description": "Desc",
        "subject": "tech",
        "lessons": [
            {"title": "Một", "brief": "A"},
            {"title": "Hai", "brief": "B"},
            {"title": "Ba", "brief": "C"},
        ],
    }
    monkeypatch.setattr(script_generator.ai_client, "generate", lambda *_a, **_k: json.dumps(payload))
    result = script_generator.generate_outline("AI", 2, provider="gemini")
    assert [item["title"] for item in result["lessons"]] == ["Một", "Hai"]


def test_generate_lesson_script_normalizes_and_validates(monkeypatch, sample_script):
    payload = copy.deepcopy(sample_script)
    payload["steps"][0]["id"] = 99
    payload["steps"][0]["elements"][1].update({"x_9_16": 0.5, "y_9_16": 0.5})
    payload["steps"][0]["elements"][1]["code"] = (
        "process.getBuiltinModule('fs').writeFileSync('owned.txt','no');"
    )
    monkeypatch.setattr(
        script_generator.ai_client,
        "generate",
        lambda *_args, **_kwargs: "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```",
    )
    output, errors = script_generator.generate_lesson_script(
        "Nội dung", step_count=2, provider="gemini"
    )
    assert not errors
    assert output["total_steps"] == 2
    assert [step["id"] for step in output["steps"]] == [1, 2]
    visual = output["steps"][0]["elements"][1]
    assert visual["template"] == "big_word"
    assert visual["trusted_template"] == "big_word"
    assert "getBuiltinModule" not in visual["code"]
    assert check_custom_js(output) == []


def test_generate_lesson_script_rejects_wrong_count(monkeypatch, sample_script):
    payload = copy.deepcopy(sample_script)
    payload["steps"] = payload["steps"][:1]
    monkeypatch.setattr(
        script_generator.ai_client, "generate", lambda *_a, **_k: json.dumps(payload)
    )
    monkeypatch.setattr(script_generator.time, "sleep", lambda *_a: None)
    with pytest.raises(ValueError, match="yêu cầu chính xác 2 step"):
        script_generator.generate_lesson_script("Nội dung", step_count=2, provider="gemini")


def test_schema_expands_known_scene_and_reports_unknown():
    known = {
        "title": "Scene",
        "steps": [
            {
                "voice_text": "Công thức x bằng hai",
                "elements": [
                    {
                        "type": "custom_js",
                        "template": "mn_formula",
                        "params": {"formula": "x = 2"},
                    }
                ],
            }
        ],
    }
    output, errors = validate_script(known)
    assert not errors
    assert output["steps"][0]["elements"][0]["code"]
    assert output["steps"][0]["elements"][0]["trusted_template"] == "mn_formula"

    unknown = {
        "title": "Bad",
        "steps": [
            {
                "voice_text": "x",
                "elements": [{"type": "custom_js", "template": "does_not_exist"}],
            }
        ],
    }
    _, errors = validate_script(unknown)
    assert any("does_not_exist" in error for error in errors)


def test_scene_first_catalog_and_ai_component_aliases_are_normalized():
    """Regression: Gemini used React-shaped props in a real Paper Brief run."""
    from core.templates import get_template

    paper = get_template("paper_explainer")
    tech = get_template("tech_explainer")
    assert 'wp_grid {"tag"' in paper["ai_hint"]
    assert tech["scene_prefix"] == "td_"
    assert tech["chrome_scene"] == "td_chrome"
    assert 'td_pipeline {"steps"' in tech["ai_hint"]

    script, errors = validate_script({
        "title": "AI học đúng", "steps": [{"voice_text": "Nội dung", "elements": [
            {"type": "custom_js", "template": "wp_title_stack", "params": {
                "kicker": "HỌC THÔNG MINH",
                "title_lines": [{"text": "AI & Kiến Thức", "color": "blue"}],
            }},
            {"type": "custom_js", "template": "wp_rules", "params": {
                "tag": {"text": "MỤC TIÊU", "color": "blue"},
                "rules": [{"rule": "Xác định mục tiêu", "description": "Biết mình cần gì"}],
            }},
            {"type": "custom_js", "template": "wp_grid", "params": {
                "tag": {"text": "NGUỒN TIN", "color": "orange"},
                "items": [{"label": "Tài liệu gốc", "icon": "AIIcon"}],
            }},
            {"type": "custom_js", "template": "wp_before_after", "params": {
                "before_label": "HỌC THỤ ĐỘNG", "before_items": ["Đọc lướt"],
                "after_label": "HỌC CHỦ ĐỘNG", "after_items": ["Tự kiểm tra"],
            }},
            {"type": "custom_js", "template": "wp_outro", "params": {
                "cta_buttons": [{"text": "Theo dõi", "icon": "AIIcon", "color": "green"}],
            }},
        ]}]},
    )
    assert not errors
    visuals = script["steps"][0]["elements"]
    assert visuals[0]["params"]["tag"] == "HỌC THÔNG MINH"
    assert visuals[0]["params"]["lines"][0]["text"] == "AI & Kiến Thức"
    assert visuals[1]["params"]["tag"] == "MỤC TIÊU"
    assert visuals[1]["params"]["items"][0] == {"lead": "Xác định mục tiêu", "desc": "Biết mình cần gì"}
    assert visuals[2]["params"]["items"][0]["name"] == "Tài liệu gốc"
    assert visuals[3]["params"]["old"]["boxes"] == ["Đọc lướt"]
    assert visuals[3]["params"]["new"]["left"] == ["Tự kiểm tra"]
    assert visuals[4]["params"]["actions"][0]["icon"] == ""
    code = "\n".join(visual["code"] for visual in visuals)
    assert "[object Object]" not in code
    assert "{’text’" not in code


def test_neon_doodle_uses_the_local_sprite_scene():
    from core.templates import get_template
    from core import custom_scenes

    template = get_template("neon_sketch")
    assert template["effect"] == "neon_sprite_panel"
    assert "neon_sprite_panel" in template["effects"]
    script, errors = validate_script(
        {
            "title": "Neon",
            "steps": [{"elements": [{
                "type": "custom_js",
                "template": "neon_sprite_panel",
                "params": {"sprite": "climb", "title": "TIẾN LÊN", "rows": ["BƯỚC 1"]},
            }]}],
        }
    )
    visual = script["steps"][0]["elements"][0]
    assert not errors
    assert visual["trusted_template"] == "neon_sprite_panel"
    assert "ui.sprite" in visual["code"]
    assert check_custom_js(script) == []
    rows = custom_scenes.expand("neon_sprite_panel", {"rows": [{"text": "Hàng đúng"}]})
    assert "Hàng đúng" in rows["code"] and "{’text’" not in rows["code"]
    assert "py=y+560" in rows["code"]
    assert "var NT=" not in rows["code"]


def test_neon_doodle_keeps_its_hero_scene_when_ai_returns_two_visuals(monkeypatch, sample_script):
    payload = copy.deepcopy(sample_script)
    for step in payload["steps"]:
        visual = next(element for element in step["elements"] if element["type"] == "custom_js")
        visual.update({
            "template": "neon_sprite_panel",
            "params": {"sprite": "idea", "title": "MỘT CẢNH", "rows": ["Hàng 1"]},
        })
        step["elements"].append({
            "type": "custom_js",
            "template": "flow_pipeline",
            "params": {"title": "CẢNH THỪA", "steps": ["A", "B"]},
        })
    monkeypatch.setattr(script_generator.ai_client, "generate", lambda *_a, **_k: json.dumps(payload))

    output, errors = script_generator.generate_lesson_script(
        "Nội dung", step_count=2, provider="gemini", template="neon_sketch"
    )

    assert not errors
    for step in output["steps"]:
        visuals = [element for element in step["elements"] if element["type"] == "custom_js"]
        assert [visual["template"] for visual in visuals] == ["neon_sprite_panel"]
        assert "subtitle_y_pct_9_16" not in step


def test_schema_blocks_raw_code_and_migrates_shipped_effects():
    unsafe = {
        "title": "Unsafe",
        "steps": [{"elements": [{"type": "custom_js", "code": "process.exit(1);"}]}],
    }
    output, errors = validate_script(unsafe)
    assert any("raw" in error for error in errors)
    assert output["steps"][0]["elements"] == []
    assert "process.exit" not in json.dumps(output)

    from core.effects_catalog import EFFECTS

    legacy = {
        "title": "Legacy",
        "steps": [{"elements": [{"type": "custom_js", "code": EFFECTS[0]["code"]}]}],
    }
    output, errors = validate_script(legacy)
    visual = output["steps"][0]["elements"][0]
    assert not errors
    assert visual["template"] == EFFECTS[0]["name"]
    assert visual["trusted_template"] == EFFECTS[0]["name"]
    assert check_custom_js(output) == []


def test_schema_allows_only_owned_gallery_image_references():
    assert normalize_gallery_src("gallery:items/logo.PNG") == "gallery:items/logo.PNG"
    assert normalize_gallery_src("/api/v1/edu_video/gallery/file/items/logo.png") == "gallery:items/logo.png"
    assert normalize_gallery_src("/api/v1/edu_video_studio/gallery/file/logo.jpg") == "gallery:logo.jpg"
    for unsafe in (
        "https://example.invalid/p.png",
        "http://127.0.0.1/p.png",
        "file:///C:/secret.png",
        r"\\attacker\share\probe.png",
        r"C:\secret.png",
        "data:image/png;base64,AAAA",
        "gallery:../secret.png",
        "gallery:items/%2e%2e/secret.png",
        "/api/v1/edu_video/gallery/file/items/../../secret.png",
        "gallery:items/logo.svg",
    ):
        assert normalize_gallery_src(unsafe) is None

    script = {
        "steps": [{"elements": [
            {"type": "image", "src": "https://example.invalid/p.png"},
            {"type": "image", "src": "gallery:items/logo.png"},
        ]}],
    }
    normalized, errors = validate_script(script)
    assert any("image src" in error for error in errors)
    assert normalized["steps"][0]["elements"] == [
        {"type": "image", "src": "gallery:items/logo.png"}
    ]
