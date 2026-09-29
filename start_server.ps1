$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Ambiente nao instalado. Rode primeiro: .\setup_windows.ps1" -ForegroundColor Yellow
    exit 1
}
$env:PYTHONPATH = (Join-Path $PSScriptRoot "src")
& .\.venv\Scripts\python.exe -m uvicorn mineracao_info.server:app --host 127.0.0.1 --port 8791
