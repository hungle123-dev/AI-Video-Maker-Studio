"""Small, side-effect-free runtime checks used by setup and release staging."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def check_playwright_browser(browser_root: str | Path) -> Path:
    """Resolve and launch the Chromium bundled with TubeCraft.

    The environment variable is deliberately set before Playwright starts its
    driver.  A successful launch proves both that the installed browser revision
    matches the Python package and that it is not falling back to a system
    browser.
    """
    root = Path(browser_root).resolve()
    if not root.is_dir():
        raise RuntimeError(f"Thiếu thư mục Chromium bundled: {root}")

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(root)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Thiếu Playwright; hãy chạy setup.ps1 lại.") from exc

    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path).resolve()
        try:
            executable.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("Playwright không dùng Chromium bundled của TubeCraft.") from exc
        if not executable.is_file():
            raise RuntimeError(f"Thiếu Chromium Playwright cần dùng: {executable}")
        browser = playwright.chromium.launch(headless=True)
        try:
            if not browser.is_connected():
                raise RuntimeError("Chromium bundled khởi động nhưng không kết nối được.")
        finally:
            browser.close()
    return executable


def check_packaged_runtime() -> Path:
    """Check the minimum portable runtime without creating user data."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Runtime smoke này chỉ dành cho bản EXE đã đóng gói.")
    base_dir = Path(sys.executable).resolve().parent
    missing_tools = [
        name for name in ("node.exe", "ffmpeg.exe", "ffprobe.exe")
        if not (base_dir / "tools" / name).is_file()
    ]
    if missing_tools:
        raise RuntimeError("Thiếu runtime portable: " + ", ".join(missing_tools))
    return check_playwright_browser(base_dir / "playwright-browsers")


def _main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra Chromium Playwright bundled.")
    parser.add_argument("--browser-root", required=True)
    args = parser.parse_args()
    try:
        executable = check_playwright_browser(args.browser_root)
    except Exception as exc:
        print(f"[runtime-check] FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"[runtime-check] OK: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
