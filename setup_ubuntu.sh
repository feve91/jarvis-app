#!/bin/bash
# ============================================================
#  JARVIS AI — Script de configuración para Ubuntu en WSL2
#  Ejecutar desde Ubuntu: bash setup_ubuntu.sh
# ============================================================

set -e  # Detener en caso de error

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   JARVIS AI — Configuración de compilación   ║"
echo "║            Ubuntu / WSL2 Setup               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Actualizar sistema ─────────────────────────────────────
echo "[1/6] Actualizando Ubuntu..."
sudo apt update -q && sudo apt upgrade -y -q
echo "✓ Sistema actualizado"

# ── 2. Instalar dependencias de sistema ───────────────────────
echo ""
echo "[2/6] Instalando dependencias de compilación..."
sudo apt install -y -q \
    git zip unzip \
    openjdk-17-jdk \
    python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev \
    cmake libstdc++6 \
    libgdbm-dev libsqlite3-dev libreadline-dev liblzma-dev \
    ccache lld
echo "✓ Dependencias instaladas"

# ── 3. Verificar Java ─────────────────────────────────────────
echo ""
echo "[3/6] Verificando Java..."
java -version
echo "✓ Java OK"

# ── 4. Instalar Cython y Buildozer ────────────────────────────
echo ""
echo "[4/6] Instalando Buildozer y Cython..."
pip3 install --user --quiet cython==0.29.33
pip3 install --user --quiet buildozer

# Agregar al PATH si no está
if ! grep -q 'local/bin' ~/.bashrc; then
    echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bashrc
fi
export PATH=$PATH:$HOME/.local/bin
echo "✓ Buildozer $(buildozer --version 2>&1 | head -1) instalado"

# ── 5. Copiar proyecto a home de Ubuntu ───────────────────────
echo ""
echo "[5/6] Copiando proyecto JARVIS al entorno Ubuntu..."
PROJECT_WIN="/mnt/c/Users/Casa/Desktop/aplicaccion jarvis"
PROJECT_LIN="$HOME/jarvis"

if [ -d "$PROJECT_LIN" ]; then
    echo "  Directorio ~/jarvis ya existe, actualizando..."
    rsync -a --exclude='.buildozer' --exclude='bin' \
          --exclude='__pycache__' --exclude='*.pyc' \
          "$PROJECT_WIN/" "$PROJECT_LIN/"
else
    echo "  Copiando por primera vez..."
    cp -r "$PROJECT_WIN" "$PROJECT_LIN"
fi
echo "✓ Proyecto en ~/jarvis"

# ── 6. Resumen final ──────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║               SETUP COMPLETO ✓               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Para compilar el APK, ejecuta:"
echo ""
echo "  cd ~/jarvis"
echo "  buildozer android debug"
echo ""
echo "La primera compilación tarda ~45-90 min."
echo "El APK se generará en: ~/jarvis/bin/"
echo ""
