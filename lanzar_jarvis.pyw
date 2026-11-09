import os
import sys
import shutil
import subprocess
import time
import psutil

_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_dir)

# 1. Matar unicamente instancias previas de main.py en memoria (sin matar otros procesos de python)
my_pid = os.getpid()
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['pid'] == my_pid:
            continue
        pname = (proc.info['name'] or '').lower()
        if pname in ('python.exe', 'pythonw.exe'):
            cmdline = [str(x).lower() for x in (proc.info['cmdline'] or [])]
            if any('main.py' in arg for arg in cmdline):
                proc.kill()
    except Exception:
        pass

time.sleep(0.3)

# 2. Limpiar cache __pycache__ y *.pyc silenciosamente en Python puro
for root, dirs, files in os.walk(_dir):
    for d in dirs:
        if d == '__pycache__':
            try:
                shutil.rmtree(os.path.join(root, d))
            except Exception:
                pass
    for f in files:
        if f.endswith('.pyc'):
            try:
                os.remove(os.path.join(root, f))
            except Exception:
                pass

# 3. Lanzar main.py con pythonw.exe de forma 100% silenciosa (CREATE_NO_WINDOW)
pythonw_exe = os.path.join(sys.prefix, "pythonw.exe")
if not os.path.exists(pythonw_exe):
    pythonw_exe = r"C:\Users\Casa\AppData\Local\Programs\Python\Python312\pythonw.exe"

main_py = os.path.join(_dir, "main.py")

DETACHED_PROCESS = 0x00000008

subprocess.Popen(
    [pythonw_exe, main_py],
    cwd=_dir,
    creationflags=DETACHED_PROCESS if os.name == 'nt' else 0
)
