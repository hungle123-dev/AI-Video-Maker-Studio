from __future__ import annotations

import pytest

from core.scenes_mn_3 import mn_shape_grid, mn_steps_math
from core.scenes_td_2 import td_hex_chain, td_pipeline, td_turn_ring
from core.scenes_td_4 import td_state_board, td_step_chain, td_versus_cross
from core.scenes_wp_2 import wp_rules, wp_timeline


@pytest.mark.parametrize(
    ("factory", "kwargs", "tokens", "height"),
    [
        (
            mn_shape_grid,
            {
                "items": [
                    {"kind": "circle_plus", "label": "CUSTOM_SHAPE_A"},
                    {"kind": "wave", "label": "CUSTOM_SHAPE_B"},
                    {"kind": "triangle", "label": "CUSTOM_SHAPE_C"},
                    {"kind": "radius", "label": "CUSTOM_SHAPE_D"},
                ],
                "cols": 3,
            },
            ("CUSTOM_SHAPE_A", "CUSTOM_SHAPE_D"),
            820,
        ),
        (
            td_pipeline,
            {"steps": [{"icon": "A", "label": "CUSTOM_PIPE_A"}, {"icon": "B", "label": "CUSTOM_PIPE_B"}]},
            ("CUSTOM_PIPE_A", "CUSTOM_PIPE_B"),
            330,
        ),
        (
            td_turn_ring,
            {"orbits": ["CUSTOM_ORBIT_A", "CUSTOM_ORBIT_B"], "items": ["CUSTOM_ITEM_A", "CUSTOM_ITEM_B"]},
            ("CUSTOM_ORBIT_A", "CUSTOM_ITEM_B"),
            460,
        ),
        (
            td_hex_chain,
            {"turns": ["CUSTOM_TURN_A", "CUSTOM_TURN_B"], "inputs": ["CUSTOM_INPUT_A", "CUSTOM_INPUT_B"]},
            ("CUSTOM_TURN_A", "CUSTOM_INPUT_B"),
            560,
        ),
        (
            td_state_board,
            {
                "steps": [{"icon": "A", "label": "CUSTOM_STATE_A"}],
                "limits": [{"label": "CUSTOM_LIMIT_A", "color": "red"}],
            },
            ("CUSTOM_STATE_A", "CUSTOM_LIMIT_A"),
            520,
        ),
        (
            td_versus_cross,
            {"wrongs": ["CUSTOM_WRONG_A"], "rights": ["CUSTOM_RIGHT_A"]},
            ("CUSTOM_WRONG_A", "CUSTOM_RIGHT_A"),
            460,
        ),
        (
            td_step_chain,
            {"steps": [{"tag": "CUSTOM_TAG_A", "label": "CUSTOM_CHAIN_A", "color": "cyan"}]},
            ("CUSTOM_TAG_A", "CUSTOM_CHAIN_A"),
            330,
        ),
        (
            wp_timeline,
            {"items": [{"date": "CUSTOM_DATE_A", "brand": "CUSTOM_BRAND_A", "head": "CUSTOM_HEAD_A", "sub": "CUSTOM_SUB_A"}]},
            ("CUSTOM_DATE_A", "CUSTOM_SUB_A"),
            456,
        ),
        (
            wp_rules,
            {"items": [{"lead": "CUSTOM_RULE_A", "desc": "CUSTOM_RULE_DESC_A"}]},
            ("CUSTOM_RULE_A", "CUSTOM_RULE_DESC_A"),
            362,
        ),
    ],
)
def test_scene_respects_custom_collections(factory, kwargs, tokens, height):
    result = factory(**kwargs)

    assert result["type"] == "custom_js"
    assert result["height"] == height
    assert all(token in result["code"] for token in tokens)


def test_optional_scene_sections_expand_the_height():
    assert mn_steps_math(title="", lines=["one"])["height"] == 260
    assert mn_steps_math(title="heading", lines=["one"])["height"] == 340
    assert td_pipeline(steps=[{"en": "one"}], note="")["height"] == 330
    assert td_pipeline(steps=[{"en": "one"}], note="note")["height"] == 374
