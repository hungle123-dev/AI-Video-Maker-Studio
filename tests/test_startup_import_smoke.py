"""Regression check for the non-GUI desktop startup import gate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_startup_import_smoke_loads_every_desktop_view_without_a_window(tmp_path: Path):
    env = os.environ.copy()
    env["TUBECRAFT_STARTUP_IMPORT_SMOKE"] = "1"
    env.pop("TUBECRAFT_RUNTIME_SMOKE", None)
    env["TUBECRAFT_DATA_DIR"] = str(tmp_path / "isolated-data")

    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[startup-import-smoke] OK" in result.stdout
    assert (tmp_path / "isolated-data").is_dir()
