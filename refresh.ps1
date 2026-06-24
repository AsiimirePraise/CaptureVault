# Full refresh: clear cached bytecode and optionally reset the local library.
param(
    [switch]$ResetLibrary
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$AppData = Join-Path $env:LOCALAPPDATA "CaptureVault"

Write-Host "CaptureVault refresh" -ForegroundColor Cyan

Get-Process -Name "CaptureVault" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*capturevault*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 1

Get-ChildItem -Path $Root -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cleared __pycache__"

if ($ResetLibrary) {
    $db = Join-Path $AppData "capturevault.db"
    $cfg = Join-Path $AppData "config.json"
    if (Test-Path $db) {
        try {
            Remove-Item $db -Force
            Write-Host "Removed database"
        } catch {
            Write-Host "Could not remove database - close CaptureVault first, then run this script again." -ForegroundColor Red
            exit 1
        }
    }
    if (Test-Path $cfg) {
        Remove-Item $cfg -Force
        Write-Host "Removed config"
    }
    Write-Host "Library reset - folders will be auto-detected on next launch." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Start the app:" -ForegroundColor Green
Write-Host ('  cd "' + $Root + '"')
Write-Host "  .\venv\Scripts\activate"
Write-Host "  python -m capturevault"
Write-Host ""
Write-Host 'Full reset next time:  .\refresh.ps1 -ResetLibrary'
