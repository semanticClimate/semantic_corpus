# setup.ps1 - Configuración automática del entorno de desarrollo para semantic_corpus (Windows)
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Configurando entorno virtual y herramientas de calidad   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Verificar si existe Python en el sistema
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
    $pythonCmd = (Get-Command py -ErrorAction SilentlyContinue)
}

if (-not $pythonCmd) {
    Write-Host "ERROR: No se encontró Python en el sistema. Por favor instálalo primero." -ForegroundColor Red
    exit 1
}

# 2. Crear entorno virtual (.venv) si no existe
if (-not (Test-Path ".venv")) {
    Write-Host "`n[1/4] Creando entorno virtual en .venv..." -ForegroundColor Yellow
    & $pythonCmd.Source -m venv .venv
} else {
    Write-Host "`n[1/4] Entorno virtual .venv existente encontrado." -ForegroundColor Green
}

$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$venvPreCommit = Join-Path (Get-Location) ".venv\Scripts\pre-commit.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: No se encontró el ejecutable de Python en '$venvPython'." -ForegroundColor Red
    exit 1
}

# 3. Actualizar pip e instalar dependencias dev (incluyendo Ruff y pre-commit)
Write-Host "`n[2/4] Actualizando pip..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip

Write-Host "`n[3/4] Instalando el paquete y dependencias dev (Ruff, pytest, etc.)..." -ForegroundColor Yellow
& $venvPython -m pip install -e ".[dev]"

# 4. Configurar Git Hooks con pre-commit
Write-Host "`n[4/4] Configurando Git Hooks automáticos (pre-commit con Ruff)..." -ForegroundColor Yellow
if (Test-Path $venvPreCommit) {
    & $venvPreCommit install
    Write-Host "Hooks de pre-commit instalados correctamente." -ForegroundColor Green
} else {
    & $venvPython -m pre_commit install
}

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  ¡Instalación completada exitosamente!                     " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Para activar tu entorno virtual:" -ForegroundColor Cyan
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "`nComandos útiles:" -ForegroundColor Cyan
Write-Host "   python -m ruff check .       (revisar errores de código)" -ForegroundColor White
Write-Host "   python -m ruff check --fix . (corregir errores automáticamente)" -ForegroundColor White
Write-Host "   python -m ruff format .      (formatear código)" -ForegroundColor White
