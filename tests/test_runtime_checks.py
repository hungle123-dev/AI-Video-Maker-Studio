from __future__ import annotations

import os
import sys
import types
from pathlib import Path

from core import runtime_checks


def test_runtime_check_uses_only_bundled_browser_before_driver_starts(tmp_path, monkeypatch):
    browser_root = tmp_path / "playwright-browsers"
    executable = browser_root / "chromium-test" / "chrome-win" / "chrome.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"test")
    events = []

    class FakeBrowser:
        def is_connected(self):
            return True

        def close(self):
            events.append("close")

    class FakeChromium:
        executable_path = str(executable)

        def launch(self, *, headless):
            assert headless is True
            assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_root.resolve())
            events.append("launch")
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        def __enter__(self):
            assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_root.resolve())
            events.append("enter")
            return FakePlaywright()

        def __exit__(self, *_args):
            events.append("exit")

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: FakeManager()
    playwright = types.ModuleType("playwright")
    monkeypatch.setitem(sys.modules, "playwright", playwright)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    assert runtime_checks.check_playwright_browser(browser_root) == executable.resolve()
    assert events == ["enter", "launch", "close", "exit"]


def test_runtime_check_rejects_missing_bundled_browser(tmp_path):
    missing = tmp_path / "missing-browsers"
    try:
        runtime_checks.check_playwright_browser(missing)
    except RuntimeError as exc:
        assert "Thiếu thư mục Chromium bundled" in str(exc)
    else:
        raise AssertionError("Runtime check accepted a missing browser root")
