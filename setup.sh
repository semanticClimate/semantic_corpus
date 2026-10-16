#!/usr/bin/env bash
# setup.sh - Configuración automática del entorno de desarrollo para semantic_corpus (Linux / macOS)
set -e

echo "============================================================"
echo "   Configurando entorno virtual y herramientas de calidad   "
echo "============================================================"

# 1. Determinar ejecutable de Python
PYTHON_BIN=""
if command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
else
    echo "ERROR: No se encontró Python en el sistema. Por favor instálalo."
    exit 1
fi

# 2. Crear entorno virtual (.venv) si no existe
if [ ! -d ".venv" ]; then
    echo -e "\n[1/4] Creando entorno virtual en .venv..."
    $PYTHON_BIN -m venv .venv
else
    echo -e "\n[1/4] Entorno virtual .venv existente encontrado."
fi

VENV_PYTHON=".venv/bin/python"
VENV_PRECOMMIT=".venv/bin/pre-commit"

# 3. Actualizar pip e instalar dependencias dev
echo -e "\n[2/4] Actualizando pip..."
$VENV_PYTHON -m pip install --upgrade pip

echo -e "\n[3/4] Instalando el paquete y dependencias dev (Ruff, pytest, etc.)..."
$VENV_PYTHON -m pip install -e ".[dev]"

# 4. Configurar Git Hooks con pre-commit
echo -e "\n[4/4] Configurando Git Hooks automáticos (pre-commit con Ruff)..."
if [ -f "$VENV_PRECOMMIT" ]; then
    $VENV_PRECOMMIT install
    echo "Hooks de pre-commit instalados correctamente."
else
    $VENV_PYTHON -m pre_commit install
fi

echo -e "\n============================================================"
echo "  ¡Instalación completada exitosamente!"
echo "============================================================"
echo "Para activar tu entorno virtual:"
echo "   source .venv/bin/activate"
echo -e "\nComandos útiles:"
echo "   ruff check .         (revisar errores de código)"
echo "   ruff check --fix .   (corregir errores automáticamente)"
echo "   ruff format .        (formatear código)"
