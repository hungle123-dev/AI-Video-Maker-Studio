"""Regression checks for portable-release smoke gates."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENE_MODULES = (
    *(f"core.scenes_td_{index}" for index in range(1, 6)),
    *(f"core.scenes_wp_{index}" for index in range(1, 5)),
    *(f"core.scenes_mn_{index}" for index in range(1, 9)),
)


def test_scene_catalog_smoke_loads_every_dynamic_scene_module(tmp_path: Path):
    env = os.environ.copy()
    env["TUBECRAFT_SCENE_CATALOG_SMOKE"] = "1"
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
    assert "[scene-catalog-smoke] OK: 17 modules" in result.stdout


def test_spec_declares_every_dynamic_scene_module():
    spec = (REPO_ROOT / "tubecraft.spec").read_text(encoding="utf-8")
    for module_name in SCENE_MODULES:
        assert f'"{module_name}"' in spec


def test_build_waits_for_the_real_exit_code_of_windowed_smokes():
    build = (REPO_ROOT / "build.ps1").read_text(encoding="utf-8")
    assert "function Invoke-StagedSmoke" in build
    assert "Start-Process -FilePath $Executable" in build
    assert "$process.WaitForExit" in build
    assert "Remove-Item -LiteralPath $StageRoot -Recurse -Force" in build
