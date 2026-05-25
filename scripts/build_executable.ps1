# Builds a standalone RFCC Automation executable (Windows).
# Output: dist/RFCC-Automation/RFCC-Automation.exe

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==> RFCC Automation - build executable" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

function Ensure-PythonModule {
    param([string]$ModuleName)
    python -c "import $ModuleName" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing $ModuleName..."
        python -m pip install $ModuleName
    }
}

Write-Host "`n==> Checking Python dependencies..."
Ensure-PythonModule "PyInstaller"
Ensure-PythonModule "playwright"
python -m pip install -r requirements.txt -q

Write-Host "`n==> Running PyInstaller..."
python -m PyInstaller rfcc_automation.spec --noconfirm --clean
if ($LASTEXITCode -ne 0) {
    throw "PyInstaller build failed."
}

$DistDir = Join-Path $ProjectRoot "dist\RFCC-Automation"

Write-Host "`n==> Copying runtime data files..."
$DataSource = Join-Path $ProjectRoot "data"
$DataTarget = Join-Path $DistDir "data"
if (Test-Path $DataTarget) {
    Remove-Item $DataTarget -Recurse -Force
}
Copy-Item $DataSource $DataTarget -Recurse -Force

$ConfigTarget = Join-Path $DistDir "config"
New-Item -ItemType Directory -Force -Path $ConfigTarget | Out-Null
$SecretsSource = Join-Path $ProjectRoot "config\secrets.py"
if (Test-Path $SecretsSource) {
    Copy-Item $SecretsSource (Join-Path $ConfigTarget "secrets.py") -Force
    Write-Host "Copied config/secrets.py"
} else {
    Write-Warning "config/secrets.py not found. Create it before running the executable."
}

Write-Host "`n==> Installing Playwright Chromium browser for the bundle..."
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $DistDir "playwright-browsers"
python -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    throw "Playwright browser install failed."
}

$ExePath = Join-Path $DistDir "RFCC-Automation.exe"
if (-not (Test-Path $ExePath)) {
    throw "Expected executable not found at $ExePath"
}

Write-Host "`n==> Build complete!" -ForegroundColor Green
Write-Host "Executable: $ExePath"
Write-Host "Folder:     $DistDir"
Write-Host "`nLaunch GUI with:"
Write-Host "  `"$ExePath`" --gui"

explorer.exe $DistDir
