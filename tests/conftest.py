from __future__ import annotations

import copy

import pytest


class FakeWindow:
    def __init__(self):
        self.maximized = True
        self.minimized = False
        self.min_width = 0
        self.min_height = 0
        self.title_bar_hidden = False
        self.title_bar_buttons_hidden = False
        self.icon = None
        self.closed = False

    def close(self):
        self.closed = True


class FakePage:
    width = 1280
    height = 800

    def __init__(self):
        self.window = FakeWindow()
        self.overlay = []
        self.opened = []
        self.closed = []
        self.added = []
        self.app_layout = None
        self.update_count = 0

    def update(self, *_controls):
        self.update_count += 1

    def open(self, control):
        self.opened.append(control)
        return control

    def close(self, control):
        self.closed.append(control)

    def add(self, *controls):
        self.added.extend(controls)


@pytest.fixture
def fake_page():
    return FakePage()


@pytest.fixture
def sample_script():
    return {
        "title": "Bài kiểm thử",
        "description": "Luồng hoàn chỉnh",
        "subject": "tech",
        "total_steps": 2,
        "steps": [
            {
                "id": 1,
                "clear": True,
                "voice_text": "Bước đầu tiên giải thích vấn đề.",
                "elements": [
                    {"type": "text", "text": "Bước một", "fontSize": 54},
                    {
                        "type": "custom_js",
                        "template": "big_word",
                        "params": {"word": "Bước một", "sub": ""},
                    },
                ],
            },
            {
                "id": 2,
                "clear": True,
                "voice_text": "Bước thứ hai hoàn tất quy trình.",
                "elements": [
                    {"type": "text", "text": "Bước hai", "fontSize": 54},
                    {
                        "type": "custom_js",
                        "template": "orbit_cycle",
                        "params": {
                            "items": [
                                {"icon": "1", "label": "Chuẩn bị"},
                                {"icon": "2", "label": "Thực hiện"},
                            ],
                            "center_label": "Quy trình",
                        },
                    },
                ],
            },
        ],
    }


@pytest.fixture
def script_copy(sample_script):
    return copy.deepcopy(sample_script)
