"""One-command local launcher for TubeCraft.

Run ``python run.py`` after cloning.  The first run creates ``.venv`` and
installs the locked Python/Node dependencies; later runs start the app.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
PYTHON = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQUIREMENTS = ROOT / "requirements.txt"
DEPS_STAMP = VENV_DIR / ".tubecraft-requirements.sha256"
TOOLS_DIR = ROOT / "tools"
NODE_VERSION = "22.17.1"
NODE_DIR = TOOLS_DIR / "node"
NODE_EXE = TOOLS_DIR / "node.exe"
NPM_CLI = NODE_DIR / "node_modules" / "npm" / "bin" / "npm-cli.js"
FFMPEG_EXE = TOOLS_DIR / "ffmpeg.exe"
FFPROBE_EXE = TOOLS_DIR / "ffprobe.exe"
BROWSER_DIR = ROOT / "playwright-browsers"


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_python_dependencies() -> None:
    if not PYTHON.is_file():
        print("[TubeCraft] Đang tạo môi trường Python...")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    required = _digest(REQUIREMENTS)
    if DEPS_STAMP.is_file() and DEPS_STAMP.read_text(encoding="utf-8").strip() == required:
        return
    print("[TubeCraft] Đang cài Python dependencies (chỉ lần đầu)...")
    _run([str(PYTHON), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    _run([str(PYTHON), "-m", "pip", "check"])
    DEPS_STAMP.write_text(required + "\n", encoding="utf-8")


def _ensure_canvas() -> None:
    if (ROOT / "node_modules" / "canvas").is_dir():
        return
    print("[TubeCraft] Đang cài Canvas renderer (chỉ lần đầu)...")
    _run([str(NODE_EXE), str(NPM_CLI), "ci", "--no-audit", "--no-fund"])


def _download(url: str, label: str) -> Path:
    print(f"[TubeCraft] Đang tải {label} (chỉ lần đầu)...")
    fd, name = tempfile.mkstemp(prefix="tubecraft-", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as target, urlopen(url, timeout=60) as source:
            shutil.copyfileobj(source, target)
        return Path(name)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def _extract_node(archive_path: Path) -> None:
    staging = TOOLS_DIR / ".node-staging"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = [item.filename for item in archive.infolist() if not item.is_dir()]
            prefix = names[0].split("/", 1)[0] + "/" if names else ""
            if not prefix or not any(name == prefix + "node.exe" for name in names):
                raise RuntimeError("Gói Node tải về không hợp lệ.")
            for item in archive.infolist():
                if item.is_dir() or not item.filename.startswith(prefix):
                    continue
                relative = Path(item.filename[len(prefix):])
                if not relative.parts or ".." in relative.parts:
                    raise RuntimeError("Gói Node chứa đường dẫn không an toàn.")
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, open(target, "wb") as destination:
                    shutil.copyfileobj(source, destination)
        if not (staging / "node.exe").is_file() or not (staging / "node_modules" / "npm" / "bin" / "npm-cli.js").is_file():
            raise RuntimeError("Gói Node thiếu node hoặc npm.")
        shutil.rmtree(NODE_DIR, ignore_errors=True)
        os.replace(staging, NODE_DIR)
        shutil.copy2(NODE_DIR / "node.exe", NODE_EXE)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _extract_ffmpeg(archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        members = {Path(item.filename).name.lower(): item for item in archive.infolist() if not item.is_dir()}
        for name, target in (("ffmpeg.exe", FFMPEG_EXE), ("ffprobe.exe", FFPROBE_EXE)):
            item = members.get(name)
            if item is None:
                raise RuntimeError(f"Gói FFmpeg thiếu {name}.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, open(target, "wb") as destination:
                shutil.copyfileobj(source, destination)


def _ensure_runtime() -> None:
    if os.name != "nt":
        raise RuntimeError("Launcher này hiện hỗ trợ Windows 10/11.")
    if not NODE_EXE.is_file() or not NPM_CLI.is_file():
        archive = _download(
            f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-win-x64.zip",
            f"Node.js {NODE_VERSION}",
        )
        try:
            _extract_node(archive)
        finally:
            archive.unlink(missing_ok=True)
    if not FFMPEG_EXE.is_file() or not FFPROBE_EXE.is_file():
        archive = _download("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "FFmpeg")
        try:
            _extract_ffmpeg(archive)
        finally:
            archive.unlink(missing_ok=True)


def _ensure_browser() -> None:
    if any(BROWSER_DIR.rglob("chrome.exe")):
        return
    print("[TubeCraft] Đang cài Chromium cho Vivibe (chỉ lần đầu)...")
    env = os.environ | {"PLAYWRIGHT_BROWSERS_PATH": str(BROWSER_DIR)}
    subprocess.run([str(PYTHON), "-m", "playwright", "install", "chromium"], cwd=ROOT, check=True, env=env)


def main() -> None:
    try:
        _ensure_python_dependencies()
        _ensure_runtime()
        _ensure_canvas()
        _ensure_browser()
        os.execv(str(PYTHON), [str(PYTHON), str(ROOT / "main.py")])
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"[TubeCraft] Không thể khởi động: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
