# JARVIS AI — Compilar APK en Google Colab con Google Drive
# ============================================================
# Versión: 2.5.0 — Carga desde Google Drive e instalación ligera
# ============================================================


# ╔══════════════════════════════════════════════╗
# ║  CELDA 1 — Sistema base (ejecuta primero)   ║
# ╚══════════════════════════════════════════════╝

import subprocess, os, time

print("🔧 Instalando dependencias del sistema...")
cmds = [
    "apt-get update -q",
    """apt-get install -y -q \
        git zip unzip openjdk-17-jdk \
        python3-pip build-essential libssl-dev \
        autoconf libtool pkg-config \
        zlib1g-dev libncurses5-dev cmake \
        libffi-dev libsqlite3-dev""",
]
for cmd in cmds:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"⚠ Advertencia: {r.stderr[-200:]}")

print("✅ Sistema base OK")


# ╔══════════════════════════════════════════════╗
# ║  CELDA 2 — Buildozer y Cython               ║
# ╚══════════════════════════════════════════════╝

import subprocess

print("📦 Instalando Buildozer y paquetes Python...")

paquetes = [
    "pip install -q cython==0.29.33",
    "pip install -q buildozer",
    "pip install -q openpyxl",
    "pip install -q python-telegram-bot",
    "pip install -q edge-tts",
    "pip install -q python-dateutil dateparser",
]

for pkg in paquetes:
    r = subprocess.run(pkg, shell=True, capture_output=True, text=True)
    nombre = pkg.split("install -q ")[1]
    estado = "✅" if r.returncode == 0 else "⚠️"
    print(f"  {estado} {nombre}")

# Verificar buildozer
r = subprocess.run("buildozer --version", shell=True, capture_output=True, text=True)
print(f"\n✅ Buildozer: {r.stdout.strip()}")


# ╔══════════════════════════════════════════════════════════╗
# ║  CELDA 3 — Conectar Google Drive y desempacar ZIP        ║
# ╚══════════════════════════════════════════════════════════╝

from google.colab import drive
import os, zipfile, shutil

# Conectar Google Drive
drive.mount('/content/drive')

if os.path.exists('/content/jarvis'):
    shutil.rmtree('/content/jarvis')

drive_zip = "/content/drive/MyDrive/JARVIS_proyecto.zip"

if os.path.exists(drive_zip):
    print(f"📦 Copiando {drive_zip}...")
    subprocess.run(f'cp "{drive_zip}" /content/', shell=True)
    with zipfile.ZipFile('/content/JARVIS_proyecto.zip', 'r') as z:
        z.extractall('/content/jarvis')
    os.chdir('/content/jarvis')
    print("\n✅ ¡Proyecto desempacado desde Google Drive en 1 segundo!")
else:
    print(f"❌ No se encontró JARVIS_proyecto.zip en 'Mi unidad' de tu Google Drive.")
    print("   Sube el archivo JARVIS_proyecto.zip a drive.google.com y vuelve a correr esta celda.")


# ╔══════════════════════════════════════════════════════════╗
# ║  CELDA 4 — COMPILAR APK (Optimizada sin sobrecargar Colab)║
# ╚══════════════════════════════════════════════════════════╝

import subprocess, sys, os, time

os.chdir('/content/jarvis')
os.environ["PATH"] += ":/root/.local/bin"

print("🔨 Compilando APK...")
print("⏱  Tiempo estimado: 10-20 minutos (Progreso en /content/build.log)")
print("-" * 55)

inicio = time.time()
log_path = "/content/build.log"

with open(log_path, "w", encoding="utf-8") as f_log:
    proc = subprocess.Popen(
        "yes | buildozer android debug 2>&1",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd='/content/jarvis'
    )

    for linea in proc.stdout:
        f_log.write(linea)
        f_log.flush()

        l_str = linea.strip()
        if any(kw in l_str for kw in ["# ", "Downloading", "Compiling", "Building", "Package", "Wrote", "ERROR", "FAILURE", "SUCCESS", "APK"]):
            print(f"  [{int(time.time() - inicio)}s] {l_str[:100]}", flush=True)

    proc.wait()

duracion = int(time.time() - inicio)
print("-" * 55)
print(f"⏱  Tiempo total: {duracion//60}m {duracion%60}s")

if proc.returncode == 0:
    print("✅ ¡COMPILACIÓN EXITOSA!")
else:
    print(f"❌ Error (código {proc.returncode}) — Revisa /content/build.log")


# ╔══════════════════════════════════════════════╗
# ║  CELDA 5 — Descargar APK al computador      ║
# ╚══════════════════════════════════════════════╝

import glob, os
from google.colab import files

apks = glob.glob('/content/jarvis/bin/*.apk')

if apks:
    apk = apks[0]
    size_mb = round(os.path.getsize(apk) / 1024 / 1024, 1)
    print(f"✅ APK encontrado: {os.path.basename(apk)} ({size_mb} MB)")
    print("📥 Descargando...")
    files.download(apk)
else:
    print("❌ No se encontró el APK.")
