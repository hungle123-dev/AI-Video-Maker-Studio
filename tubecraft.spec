# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


root = Path(SPECPATH)
SCENE_HIDDENIMPORTS = (
    "core.scenes_td_1",
    "core.scenes_td_2",
    "core.scenes_td_3",
    "core.scenes_td_4",
    "core.scenes_td_5",
    "core.scenes_wp_1",
    "core.scenes_wp_2",
    "core.scenes_wp_3",
    "core.scenes_wp_4",
    "core.scenes_mn_1",
    "core.scenes_mn_2",
    "core.scenes_mn_3",
    "core.scenes_mn_4",
    "core.scenes_mn_5",
    "core.scenes_mn_6",
    "core.scenes_mn_7",
    "core.scenes_mn_8",
)
datas = [
    (str(root / "assets"), "assets"),
    (str(root / "engines"), "engines"),
    (str(root / "samples"), "samples"),
    (str(root / "static"), "static"),
]
for required_dir, destination in (("tools", "tools"), ("node_modules", "node_modules")):
    source_dir = root / required_dir
    if not source_dir.is_dir():
        raise SystemExit(
            f"Thiếu {required_dir} cần cho bản portable. Chạy setup.ps1 trước khi chạy PyInstaller."
        )
    datas.append((str(source_dir), destination))
for required_file in ("node.exe", "ffmpeg.exe", "ffprobe.exe"):
    if not (root / "tools" / required_file).is_file():
        raise SystemExit(f"Thiếu tools/{required_file} cần cho bản portable.")
if not (root / "node_modules" / "canvas").is_dir():
    raise SystemExit("Thiếu node_modules/canvas cần cho renderer portable.")
browser_root = root / "playwright-browsers"
if not browser_root.is_dir() or not any(browser_root.rglob("chrome.exe")):
    raise SystemExit(
        "Thiếu Chromium bundled cho Vivibe. Chạy setup.ps1 trước khi chạy PyInstaller."
    )
datas.append((str(browser_root), "playwright-browsers"))

binaries = []
hiddenimports = []
for package in ("flet", "flet_desktop", "playwright"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

for package in ("anthropic", "edge_tts", "gtts", "fontTools", "openpyxl", "PIL", "pydub"):
    hiddenimports += collect_submodules(package)
hiddenimports += list(SCENE_HIDDENIMPORTS)

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TubeCraft",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(root / "assets" / "icon.ico"),
    contents_directory=".",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="TubeCraft",
)
