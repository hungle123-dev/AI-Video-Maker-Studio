from __future__ import annotations

from core.templates import list_templates


def test_all_bundled_templates_are_available_locally_without_locks():
    expected_pack_templates = {
        "tech_news",
        "ai_hotlist",
        "light_news",
        "tech_light",
        "neon_sketch",
        "tech_explainer",
        "paper_explainer",
        "math_noir",
    }

    templates = list_templates()
    template_ids = {template["id"] for template in templates}

    assert expected_pack_templates <= template_ids
    assert len(template_ids) == len(templates)
    assert not any(template.get("locked") for template in templates)
    assert not any("min_plan" in template for template in templates)
