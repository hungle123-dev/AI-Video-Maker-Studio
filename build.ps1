param(
    [string]$OutputName = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
Set-Location -LiteralPath $RepoRoot

$ManagedEnvironment = @(
    "PLAYWRIGHT_BROWSERS_PATH",
    "TUBECRAFT_RUNTIME_SMOKE",
    "TUBECRAFT_STARTUP_IMPORT_SMOKE",
    "TUBECRAFT_SCENE_CATALOG_SMOKE",
    "TUBECRAFT_RENDER_SMOKE",
    "TUBECRAFT_RENDER_SMOKE_DIR",
    "TUBECRAFT_DATA_DIR",
    "TUBECRAFT_NODE_MODULES",
    "TUBECRAFT_FFMPEG_DIR"
)
$PreviousEnvironment = @{}
foreach ($Name in $ManagedEnvironment) {
    $PreviousEnvironment[$Name] = [Environment]::GetEnvironmentVariable($Name, "Process")
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Chưa có môi trường build. Chạy .\setup.ps1 trước."
}
if (-not (Test-Path -LiteralPath "node_modules\canvas")) {
    throw "Thiếu node_modules\canvas. Chạy .\setup.ps1 trước."
}
foreach ($Tool in "node.exe", "ffmpeg.exe", "ffprobe.exe") {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "tools\$Tool"))) {
        throw "Thiếu tools\$Tool; bản portable sẽ không độc lập."
    }
}

# Every build is emitted to a fresh staging tree, then moved to a new release
# directory. Existing dist\TubeCraft\data is never copied, replaced, or deleted.
$BuildStamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
if ([string]::IsNullOrWhiteSpace($OutputName)) {
    $OutputName = "TubeCraft-$BuildStamp"
}
if ($OutputName -notmatch '^[A-Za-z0-9._-]+$') {
    throw "OutputName chỉ được chứa chữ, số, dấu chấm, gạch dưới và gạch ngang."
}
$ReleaseRoot = Join-Path $RepoRoot "dist"
$OutputDir = Join-Path $ReleaseRoot $OutputName
$StageRoot = Join-Path $RepoRoot ".build-stage-$BuildStamp"
if (Test-Path -LiteralPath $OutputDir) {
    throw "Từ chối ghi đè release đã có: $OutputDir"
}
if (Test-Path -LiteralPath $StageRoot) {
    throw "Staging directory đã tồn tại: $StageRoot"
}
New-Item -ItemType Directory -Path $StageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

try {
    $BrowserDir = Join-Path $RepoRoot "playwright-browsers"
    $env:PLAYWRIGHT_BROWSERS_PATH = $BrowserDir
    & $Python -m core.runtime_checks --browser-root $BrowserDir
    if ($LASTEXITCODE -ne 0) {
        throw "Chromium bundled cho Vivibe chưa sẵn sàng. Chạy .\setup.ps1 trước khi build release."
    }

    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency Python không nhất quán; chạy .\setup.ps1 lại."
    }
    npm run check
    if ($LASTEXITCODE -ne 0) {
        throw "Node renderer không qua syntax check."
    }

    $SourceNode = Join-Path $RepoRoot "tools\node.exe"
    $SourceFfmpeg = Join-Path $RepoRoot "tools\ffmpeg.exe"
    $SourceFfprobe = Join-Path $RepoRoot "tools\ffprobe.exe"
    & $SourceNode -e "require('canvas');"
    if ($LASTEXITCODE -ne 0) {
        throw "tools\node.exe không tải được node_modules\canvas."
    }
    & $SourceFfmpeg -version
    if ($LASTEXITCODE -ne 0) {
        throw "tools\ffmpeg.exe không chạy được."
    }
    & $SourceFfprobe -version
    if ($LASTEXITCODE -ne 0) {
        throw "tools\ffprobe.exe không chạy được."
    }

    # Test imports must not create or read the source/user runtime directory.
    $env:TUBECRAFT_DATA_DIR = Join-Path $StageRoot "pytest-data"
    $env:TUBECRAFT_NODE_MODULES = Join-Path $RepoRoot "node_modules"
    $env:TUBECRAFT_FFMPEG_DIR = Join-Path $RepoRoot "tools"
    foreach ($Name in "TUBECRAFT_RUNTIME_SMOKE", "TUBECRAFT_STARTUP_IMPORT_SMOKE", "TUBECRAFT_SCENE_CATALOG_SMOKE", "TUBECRAFT_RENDER_SMOKE", "TUBECRAFT_RENDER_SMOKE_DIR") {
        [Environment]::SetEnvironmentVariable($Name, $null, "Process")
    }
    $TestTemp = Join-Path $StageRoot "pytest"
    & $Python -m pytest -q -p no:cacheprovider --basetemp $TestTemp
    if ($LASTEXITCODE -ne 0) {
        throw "Tests thất bại; không build release."
    }

    $StageDist = Join-Path $StageRoot "dist"
    $StageWork = Join-Path $StageRoot "work"
    & $Python -m PyInstaller --noconfirm --clean --distpath $StageDist --workpath $StageWork tubecraft.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build thất bại; staging giữ nguyên để kiểm tra."
    }

    $StagedApp = Join-Path $StageDist "TubeCraft"
    if (-not (Test-Path -LiteralPath (Join-Path $StagedApp "TubeCraft.exe"))) {
        throw "Build không tạo TubeCraft.exe."
    }
    if (Test-Path -LiteralPath (Join-Path $StagedApp "data")) {
        throw "Build staging chứa data người dùng; từ chối publish để tránh ghi đè dữ liệu."
    }
    foreach ($Tool in "node.exe", "ffmpeg.exe", "ffprobe.exe") {
        if (-not (Test-Path -LiteralPath (Join-Path $StagedApp "tools\$Tool"))) {
            throw "Build thiếu tools\$Tool."
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $StagedApp "node_modules\canvas"))) {
        throw "Build thiếu node_modules\canvas."
    }

    function Invoke-StagedSmoke {
        param(
            [string]$Label,
            [string]$Executable,
            [int]$TimeoutSeconds = 90
        )

        # A windowed EXE invoked with ``&`` returns control to PowerShell
        # before it exits, leaving $LASTEXITCODE unset. Wait for the actual
        # process and reject a timeout/non-zero exit before publishing.
        $process = Start-Process -FilePath $Executable -WorkingDirectory $StagedApp `
            -WindowStyle Hidden -PassThru
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            } catch {
            }
            throw "$Label vượt quá $TimeoutSeconds giây."
        }
        if ($process.ExitCode -ne 0) {
            throw "$Label thất bại với exit code $($process.ExitCode)."
        }
    }

    # Every packaged smoke uses only staging paths. No smoke may initialize
    # data/ beside TubeCraft.exe or fall back to a development runtime.
    $env:TUBECRAFT_NODE_MODULES = Join-Path $StagedApp "node_modules"
    $env:TUBECRAFT_FFMPEG_DIR = Join-Path $StagedApp "tools"
    $env:TUBECRAFT_DATA_DIR = Join-Path $StageRoot "runtime-smoke-data"
    $env:TUBECRAFT_RUNTIME_SMOKE = "1"
    Invoke-StagedSmoke -Label "Bản EXE staging không qua được runtime smoke (tools/Chromium)" -Executable (Join-Path $StagedApp "TubeCraft.exe")

    [Environment]::SetEnvironmentVariable("TUBECRAFT_RUNTIME_SMOKE", $null, "Process")
    $env:TUBECRAFT_SCENE_CATALOG_SMOKE = "1"
    Invoke-StagedSmoke -Label "Bản EXE staging thiếu catalog scene động" -Executable (Join-Path $StagedApp "TubeCraft.exe")

    [Environment]::SetEnvironmentVariable("TUBECRAFT_SCENE_CATALOG_SMOKE", $null, "Process")
    $env:TUBECRAFT_STARTUP_IMPORT_SMOKE = "1"
    $env:TUBECRAFT_DATA_DIR = Join-Path $StageRoot "startup-smoke-data"
    Invoke-StagedSmoke -Label "Bản EXE staging không qua được startup-import smoke (Flet/UI)" -Executable (Join-Path $StagedApp "TubeCraft.exe")

    [Environment]::SetEnvironmentVariable("TUBECRAFT_STARTUP_IMPORT_SMOKE", $null, "Process")
    $env:TUBECRAFT_RENDER_SMOKE = "1"
    $env:TUBECRAFT_RENDER_SMOKE_DIR = Join-Path $StageRoot "renderer-smoke"
    $env:TUBECRAFT_DATA_DIR = Join-Path $StageRoot "renderer-smoke-data"
    Invoke-StagedSmoke -Label "Bản EXE staging không qua được renderer smoke (Node/Canvas/FFmpeg/FFprobe)" -Executable (Join-Path $StagedApp "TubeCraft.exe")

    if (Test-Path -LiteralPath (Join-Path $StagedApp "data")) {
        throw "Runtime smoke đã tạo data trong release staging; từ chối publish."
    }
}
finally {
    foreach ($Name in $ManagedEnvironment) {
        [Environment]::SetEnvironmentVariable($Name, $PreviousEnvironment[$Name], "Process")
    }
}

Move-Item -LiteralPath $StagedApp -Destination $OutputDir -ErrorAction Stop
# Keep failed staging for diagnosis, but a published release has no reason to
# retain its duplicate PyInstaller work tree.
Remove-Item -LiteralPath $StageRoot -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Release portable mới: $OutputDir\TubeCraft.exe"
Write-Host "dist\TubeCraft hiện tại và toàn bộ data của nó không bị đụng tới."
