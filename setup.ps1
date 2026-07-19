$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Không tạo được môi trường Python (.venv)."
    }
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Không nâng cấp được pip."
}
& ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) {
    throw "Không cài được dependency Python."
}
& ".venv\Scripts\python.exe" -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "Dependency Python không nhất quán sau khi cài."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Không tìm thấy npm để kiểm tra/cài Canvas renderer."
}
if (-not (Test-Path -LiteralPath "node_modules\canvas")) {
    if (Test-Path -LiteralPath "package-lock.json") {
        npm ci
    } else {
        npm install
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Không cài được node_modules/canvas."
    }
}
npm run check
if ($LASTEXITCODE -ne 0) {
    throw "Node renderer không qua syntax check."
}

foreach ($Tool in "node.exe", "ffmpeg.exe", "ffprobe.exe") {
    if (-not (Test-Path -LiteralPath (Join-Path "tools" $Tool))) {
        throw "Repo thiếu tools\$Tool; hãy khôi phục bundle TubeCraft đầy đủ."
    }
}
& ".\tools\node.exe" -e "require('canvas');"
if ($LASTEXITCODE -ne 0) {
    throw "tools\node.exe không tải được node_modules\canvas."
}
& ".\tools\ffmpeg.exe" -version
if ($LASTEXITCODE -ne 0) {
    throw "tools\ffmpeg.exe không chạy được."
}
& ".\tools\ffprobe.exe" -version
if ($LASTEXITCODE -ne 0) {
    throw "tools\ffprobe.exe không chạy được."
}

$BrowserDir = Join-Path $RepoRoot "playwright-browsers"
$BrowserReady = $false
if (Test-Path -LiteralPath $BrowserDir) {
    $env:PLAYWRIGHT_BROWSERS_PATH = $BrowserDir
    & ".venv\Scripts\python.exe" -m core.runtime_checks --browser-root $BrowserDir
    $BrowserReady = $LASTEXITCODE -eq 0
}
if (-not $BrowserReady) {
    $env:PLAYWRIGHT_BROWSERS_PATH = $BrowserDir
    & ".venv\Scripts\python.exe" -m playwright install chromium
    if ($LASTEXITCODE -ne 0) {
        throw "Không tải được Chromium cho Vivibe. Kiểm tra mạng rồi chạy setup.ps1 lại."
    }
    & ".venv\Scripts\python.exe" -m core.runtime_checks --browser-root $BrowserDir
    if ($LASTEXITCODE -ne 0) {
        throw "Chromium cho Vivibe không khởi động được sau khi cài."
    }
}

Write-Host "TubeCraft đã sẵn sàng (Canvas/FFmpeg/FFprobe/Chromium đã qua kiểm tra). Chạy .\run.ps1"
