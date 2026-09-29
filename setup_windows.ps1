$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -m venv .venv
    } elseif ($python) {
        & $python.Source -m venv .venv
    } else {
        $localPython = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
        if (-not $localPython) {
            Write-Host "Python 3.11+ nao encontrado. Instale-o e execute novamente." -ForegroundColor Red
            exit 1
        }
        & $localPython.FullName -m venv .venv
    }
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path ".env")) {
    & .\.venv\Scripts\python.exe configure_token.py
}
Write-Host "\nInstalacao concluida." -ForegroundColor Green
Write-Host "Teste a Skill: .\mineracao.ps1 skill-status"
Write-Host "Minere: .\mineracao.ps1 mine 'emagrecimento' --depth quick"
