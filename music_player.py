"""
music_player.py — Reproductor de música de fondo (estilo Iron Man).

Busca archivos MP3 en la carpeta assets/music/ y los reproduce en bucle.
Si no hay archivos, imprime instrucciones de cómo agregarlos.

Canciones sugeridas de las películas de Iron Man:
  - Iron Man (2008): "Iron Man" de Black Sabbath, "Shoot to Thrill" de AC/DC
  - Iron Man 2 (2010): "Highway to Hell", "War Machine"
  - Iron Man 3 (2013): "Can You Dig It" de Brian Tyler
  - Avengers: "The Avengers Theme" de Alan Silvestri
"""

import os
import glob
import random
import threading
import time

try:
    import pygame
    _PYGAME_OK = True
except ImportError:
    _PYGAME_OK = False
    print("[MUSIC] pygame no disponible, sin música de fondo.")

# Canal 0 (pygame.mixer.music) = música de fondo  ← exclusivo para canciones
# Canal 1                       = voz de JARVIS    ← manejado por chat_screen.py

CARPETA_MUSICA = os.path.join(os.path.dirname(__file__), "assets", "music")

VOLUMEN = 0.18  # Volumen normal de la música (0.0 - 1.0)

_lock       = threading.Lock()
_activo     = False
_hilo       = None
_playlist   = []
_indice     = 0
_pausado    = False


def _inicializar_pygame():
    if not _PYGAME_OK:
        return False
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        # Asegurar al menos 8 canales: Canal 0 = música, Canal 1 = voz JARVIS
        pygame.mixer.set_num_channels(8)
        pygame.mixer.music.set_volume(VOLUMEN)
        return True
    except Exception as e:
        print(f"[MUSIC] Error init pygame: {e}")
        return False



def _cargar_playlist():
    global _playlist, _indice
    os.makedirs(CARPETA_MUSICA, exist_ok=True)
    archivos = (
        glob.glob(os.path.join(CARPETA_MUSICA, "*.mp3")) +
        glob.glob(os.path.join(CARPETA_MUSICA, "*.ogg")) +
        glob.glob(os.path.join(CARPETA_MUSICA, "*.wav"))
    )
    if not archivos:
        _mostrar_instrucciones()
        return False
    random.shuffle(archivos)
    _playlist = archivos
    _indice   = 0
    print(f"[MUSIC] {len(_playlist)} canciones encontradas.")
    return True


def _mostrar_instrucciones():
    print("""
[MUSIC] No se encontraron canciones en assets/music/

Para agregar música de fondo de Iron Man:
  1. Crea la carpeta:  aplicaccion jarvis\\assets\\music\\
  2. Copia tus archivos MP3/OGG ahí. Sugerencias:
       - Shoot to Thrill - AC/DC
       - Highway to Hell - AC/DC
       - Iron Man Theme - Brian Tyler
       - The Avengers Theme - Alan Silvestri
       - Can You Dig It - Brian Tyler
  3. Reinicia JARVIS

La app funciona sin música, solo no habrá audio de fondo.
""")


def _bucle_musica():
    global _activo, _indice, _pausado
    if not _inicializar_pygame():
        return
    if not _cargar_playlist():
        return

    _activo = True
    while _activo:
        if _pausado:
            import time
            time.sleep(0.5)
            continue
        try:
            cancion = _playlist[_indice % len(_playlist)]
            print(f"[MUSIC] Reproduciendo: {os.path.basename(cancion)}")
            pygame.mixer.music.load(cancion)
            pygame.mixer.music.set_volume(VOLUMEN)
            pygame.mixer.music.play()

            # Esperar a que termine
            import time
            while pygame.mixer.music.get_busy() and _activo and not _pausado:
                time.sleep(0.5)

            _indice = (_indice + 1) % len(_playlist)
        except Exception as e:
            print(f"[MUSIC] Error reproduciendo: {e}")
            _indice = (_indice + 1) % max(len(_playlist), 1)
            import time
            time.sleep(1)

    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def iniciar():
    """Inicia la música de fondo en un hilo daemon."""
    global _hilo, _activo
    with _lock:
        if _hilo and _hilo.is_alive():
            return
        _activo = True
        _hilo   = threading.Thread(target=_bucle_musica, daemon=True, name="JarvisMusic")
        _hilo.start()


def detener():
    global _activo
    _activo = False
    try:
        if _PYGAME_OK:
            pygame.mixer.music.stop()
    except Exception:
        pass


def pausar():
    global _pausado
    _pausado = True
    try:
        if _PYGAME_OK:
            pygame.mixer.music.pause()
    except Exception:
        pass


def reanudar():
    global _pausado
    _pausado = False
    try:
        if _PYGAME_OK:
            pygame.mixer.music.unpause()
    except Exception:
        pass


def siguiente():
    global _indice
    _indice += 1
    try:
        if _PYGAME_OK:
            pygame.mixer.music.stop()
    except Exception:
        pass


def set_volumen(v: float):
    """v entre 0.0 y 1.0"""
    global VOLUMEN
    VOLUMEN = max(0.0, min(1.0, v))
    try:
        if _PYGAME_OK:
            pygame.mixer.music.set_volume(VOLUMEN)
    except Exception:
        pass
