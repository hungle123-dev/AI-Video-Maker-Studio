$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Chưa có môi trường Python. Chạy .\setup.ps1 trước."
}
if (-not (Test-Path -LiteralPath "node_modules\canvas")) {
    throw "Chưa có renderer Canvas. Chạy .\setup.ps1 trước."
}

& $Python main.py

