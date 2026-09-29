$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python Launcher (py) nao encontrado. Instale Python 3.11+ e marque Add Python to PATH." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path ".venv")) { py -3 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt
if (-not (Test-Path ".env")) {
    & .\.venv\Scripts\python.exe configure_token.py
}
Write-Host "\nInstalacao concluida." -ForegroundColor Green
Write-Host "Teste a Skill: .\mineracao.ps1 skill-status"
Write-Host "Minere: .\mineracao.ps1 mine 'emagrecimento' --depth quick"
