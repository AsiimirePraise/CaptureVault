# Build CaptureVault for Windows distribution
param(
    [switch]$InstallerOnly
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

if (-not $InstallerOnly) {
    Write-Host "Building CaptureVault.exe with PyInstaller..."
    & "$Root\venv\Scripts\pyinstaller.exe" "$Root\build\capturevault.spec" --noconfirm
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done: dist\CaptureVault.exe"
}

$Iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    Write-Warning "Inno Setup not found. Install from https://jrsoftware.org/isinfo.php"
    exit 1
}

$version = (Get-Content "$Root\version.txt").Trim()
$iss = Get-Content "$Root\installer\CaptureVault.iss" -Raw
$iss = $iss -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$version`""
Set-Content "$Root\installer\CaptureVault.iss" $iss -NoNewline

Write-Host "Building CaptureVaultSetup.exe..."
& $Iscc "$Root\installer\CaptureVault.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done: dist\installer\CaptureVaultSetup.exe"
