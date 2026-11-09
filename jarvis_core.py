"""
JARVIS Core — Motor de procesamiento de comandos
Versión completa: crypto, acciones, noticias, WhatsApp (CallMeBot/pywhatkit/twilio),
alarmas inteligentes, apps de Windows, pendientes, Telegram.
"""

import re
import os
import uuid
import json
import threading
import webbrowser

def abrir_url_silenciosa(url):
    if not url:
        return
    try:
        if os.name == 'nt' and hasattr(os, 'startfile'):
            os.startfile(url)
        else:
            abrir_url_silenciosa(url)
    except Exception:
        try:
            abrir_url_silenciosa(url)
        except Exception:
            pass

import subprocess
from datetime import datetime, timedelta

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False
import requests
from dateparser.search import search_dates

# ─── Detección de plataforma ───────────────────────────────────────────────────
try:
    from kivy.utils import platform as _kv_platform
    PLATFORM = _kv_platform   # 'android', 'win', 'linux', 'macosx'
except Exception:
    PLATFORM = "win"

# ─── Ruta de datos ─────────────────────────────────────────────────────────────
def _get_data_dir():
    if PLATFORM == "android":
        try:
            from android.storage import app_storage_path
            return app_storage_path()
        except Exception:
            return os.getcwd()
    return os.path.dirname(os.path.abspath(__file__))

_DATA_DIR        = _get_data_dir()
ARCHIVO_MEMORIA  = os.path.join(_DATA_DIR, "memoria.json")
ARCHIVO_SETTINGS = os.path.join(_DATA_DIR, "jarvis_settings.json")

# =========================================================================
# CONFIGURACIÓN — edita esta sección para personalizar JARVIS
# =========================================================================

# ─── WhatsApp ─────────────────────────────────────────────────────────────────
# Método: "callmebot" (gratis, instantáneo) | "pywhatkit" (abre navegador) | "twilio" (pago)
METODO_WHATSAPP = os.getenv("METODO_WHATSAPP", "callmebot").lower()

TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# Tus contactos — número: código de país + número sin espacios ni '+'
# apikey: solo necesaria para CallMeBot (cada contacto obtiene la suya)
CONTACTOS_WHATSAPP = {
    "yo":       {"numero": "573104216955", "apikey": "7511054"},
    "mi diosa": {"numero": "573117537900", "apikey": None},
    "madre":    {"numero": "573206135170", "apikey": None},
    "padre":    {"numero": "573041011424", "apikey": None},
}

# ─── Aplicaciones de Windows ───────────────────────────────────────────────────
RUTA_SPOTIFY         = os.path.join(os.getenv("APPDATA", ""), "Spotify", "Spotify.exe")
RUTA_BRAVE           = os.path.join(os.getenv("LOCALAPPDATA", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
RUTA_DISCORD_UPDATE  = os.path.join(os.getenv("LOCALAPPDATA", ""), "Discord", "Update.exe")

def _matar_proceso_silencioso(nombre_proceso):
    """Mata un proceso por nombre usando psutil puro en memoria (0 consolas)."""
    if not nombre_proceso:
        return
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == nombre_proceso.lower():
                proc.kill()
        except Exception:
            pass

def _tiene_ventana_visible(nombre_proceso):
    """Verifica si el proceso tiene una ventana visible usando Win32 API pura en memoria (0 consolas)."""
    if os.name != 'nt':
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        pids = [p.pid for p in psutil.process_iter(['name', 'pid']) if p.info['name'] and p.info['name'].lower() == nombre_proceso.lower()]
        if not pids:
            return False
        found = [False]
        def _enum_cb(h, _):
            if not user32.IsWindowVisible(h):
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if pid.value in pids:
                if user32.GetWindowTextLengthW(h) > 0:
                    found[0] = True
                    return False
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        return found[0]
    except Exception:
        return False

def _abrir_cmd(cmd, nombre):
    if PLATFORM in ("android", "ios"):
        return f"Apertura de {nombre} no disponible en móvil."
    try:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(cmd, shell=True, creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except Exception:
        pass
    return f"Abriendo {nombre}"

def _abrir_ruta(ruta, nombre):
    if PLATFORM in ("android", "ios"):
        return f"Apertura de {nombre} no disponible en móvil."
    if ruta and os.path.exists(ruta):
        os.startfile(ruta)
        return f"Abriendo {nombre}"
    return f"No encontré {nombre} instalado en este equipo."

def _abrir_discord():
    if os.path.exists(RUTA_DISCORD_UPDATE):
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen([RUTA_DISCORD_UPDATE, "--processStart", "Discord.exe"], creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return "Abriendo Discord"
    return "No encontré Discord instalado."

def _abrir_spotify():
    if PLATFORM in ("android", "ios"):
        return "Apertura de Spotify no disponible en móvil."

    if _tiene_ventana_visible("Spotify.exe"):
        try:
            abrir_url_silenciosa("spotify:")
            return "Abriendo Spotify"
        except Exception:
            return "Spotify ya está en ejecución."

    _matar_proceso_silencioso("Spotify.exe")
    import time; time.sleep(0.3)

    if RUTA_SPOTIFY and os.path.exists(RUTA_SPOTIFY):
        try:
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen([RUTA_SPOTIFY], creationflags=(CREATE_NO_WINDOW | DETACHED_PROCESS) if os.name == 'nt' else 0)
            return "Abriendo Spotify"
        except Exception:
            pass

    try:
        abrir_url_silenciosa("spotify:")
        return "Abriendo Spotify"
    except Exception:
        return "No encontré Spotify instalado."

def _abrir_chrome():
    if PLATFORM in ("android", "ios"):
        return "Apertura de Chrome no disponible en móvil."

    if _tiene_ventana_visible("chrome.exe"):
        abrir_url_silenciosa("https://www.google.com")
        return "Abriendo Google Chrome"

    _matar_proceso_silencioso("chrome.exe")
    import time; time.sleep(0.3)

    rutas_chrome = [
        os.path.join(os.getenv("PROGRAMFILES", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.getenv("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for r in rutas_chrome:
        if os.path.exists(r):
            try:
                CREATE_NO_WINDOW = 0x08000000
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen([r, "https://www.google.com"], creationflags=(CREATE_NO_WINDOW | DETACHED_PROCESS) if os.name == 'nt' else 0)
                return "Abriendo Google Chrome"
            except Exception:
                pass
    abrir_url_silenciosa("https://www.google.com")
    return "Abriendo Google Chrome"

def _abrir_web_o_app(uri, url, nombre):
    if PLATFORM in ("android", "ios"):
        abrir_url_silenciosa(url)
        return f"Abriendo {nombre}"
    try:
        abrir_url_silenciosa(uri)
        return f"Abriendo {nombre}"
    except Exception:
        abrir_url_silenciosa(url)
        return f"Abriendo {nombre}"

APPS_WINDOWS = {
    "chrome":        {"nombre": "Google Chrome",    "proceso": "chrome.exe",       "alias": ["chrome", "google chrome", "navegador chrome"], "abrir": _abrir_chrome},
    "edge":          {"nombre": "Microsoft Edge",   "proceso": "msedge.exe",        "alias": ["edge", "microsoft edge"],"abrir": lambda: _abrir_cmd("start msedge", "Microsoft Edge")},
    "brave":         {"nombre": "Brave",            "proceso": "brave.exe",         "alias": ["brave"],                "abrir": lambda: _abrir_ruta(RUTA_BRAVE, "Brave")},
    "firefox":       {"nombre": "Firefox",          "proceso": "firefox.exe",       "alias": ["firefox"],              "abrir": lambda: _abrir_cmd("start firefox", "Firefox")},
    "word":          {"nombre": "Microsoft Word",   "proceso": "WINWORD.EXE",       "alias": ["word"],                 "abrir": lambda: _abrir_cmd("start winword", "Microsoft Word")},
    "excel":         {"nombre": "Microsoft Excel",  "proceso": "EXCEL.EXE",         "alias": ["excel"],                "abrir": lambda: _abrir_cmd("start excel", "Microsoft Excel")},
    "powerpoint":    {"nombre": "PowerPoint",       "proceso": "POWERPNT.EXE",      "alias": ["powerpoint", "power point"], "abrir": lambda: _abrir_cmd("start powerpnt", "PowerPoint")},
    "spotify":       {"nombre": "Spotify",          "proceso": "Spotify.exe",       "alias": ["spotify"],              "abrir": _abrir_spotify},
    "discord":       {"nombre": "Discord",          "proceso": "Discord.exe",       "alias": ["discord"],              "abrir": _abrir_discord},
    "netflix":       {"nombre": "Netflix",          "proceso": "Netflix.exe",       "alias": ["netflix"],              "abrir": lambda: _abrir_web_o_app("netflix:", "https://www.netflix.com", "Netflix")},
    "prime":         {"nombre": "Prime Video",      "proceso": "PrimeVideo.exe",    "alias": ["prime", "prime video", "amazon prime"], "abrir": lambda: _abrir_web_o_app("primevideo:", "https://www.primevideo.com", "Prime Video")},
    "disney":        {"nombre": "Disney+",          "proceso": "DisneyPlus.exe",     "alias": ["disney", "disney+", "disney plus"], "abrir": lambda: _abrir_web_o_app("disneyplus:", "https://www.disneyplus.com", "Disney+")},
    "max":           {"nombre": "Max",              "proceso": "Max.exe",            "alias": ["max", "hbo", "hbo max"], "abrir": lambda: _abrir_web_o_app("max:", "https://www.max.com", "Max")},
    "twitch":        {"nombre": "Twitch",           "proceso": "Twitch.exe",         "alias": ["twitch"],              "abrir": lambda: _abrir_web_o_app("twitch:", "https://www.twitch.tv", "Twitch")},
    "calculadora":   {"nombre": "la calculadora",   "proceso": ["CalculatorApp.exe", "calc.exe"], "alias": ["calculadora"], "abrir": lambda: _abrir_cmd("calc", "la calculadora")},
    "bloc_de_notas": {"nombre": "el bloc de notas", "proceso": "notepad.exe",      "alias": ["bloc de notas"],        "abrir": lambda: _abrir_cmd("notepad", "el bloc de notas")},
}

# Apps de Android (package name para Intent)
APPS_ANDROID = {
    "spotify":   {"nombre": "Spotify",   "alias": ["spotify"],            "package": "com.spotify.music"},
    "whatsapp":  {"nombre": "WhatsApp",  "alias": ["whatsapp", "wasap"],  "package": "com.whatsapp"},
    "youtube":   {"nombre": "YouTube",   "alias": ["youtube"],            "package": "com.google.android.youtube"},
    "chrome":    {"nombre": "Chrome",    "alias": ["chrome"],             "package": "com.android.chrome"},
    "maps":      {"nombre": "Maps",      "alias": ["maps", "mapa", "google maps"], "package": "com.google.android.apps.maps"},
    "instagram": {"nombre": "Instagram", "alias": ["instagram"],          "package": "com.instagram.android"},
    "telegram":  {"nombre": "Telegram",  "alias": ["telegram"],           "package": "org.telegram.messenger"},
    "netflix":   {"nombre": "Netflix",   "alias": ["netflix"],            "package": "com.netflix.mediaclient", "url_fallback": "https://www.netflix.com"},
    "prime":     {"nombre": "Prime Video", "alias": ["prime", "prime video"], "package": "com.amazon.avod.thirdpartyclient", "url_fallback": "https://www.primevideo.com"},
    "disney":    {"nombre": "Disney+",   "alias": ["disney", "disney+"],  "package": "com.disney.disneyplus", "url_fallback": "https://www.disneyplus.com"},
    "max":       {"nombre": "Max",       "alias": ["max", "hbo"],         "package": "com.wbd.stream", "url_fallback": "https://www.max.com"},
    "twitch":    {"nombre": "Twitch",    "alias": ["twitch"],             "package": "tv.twitch.android.app", "url_fallback": "https://www.twitch.tv"},
}

# Acciones que piden confirmación
ACCIONES_CONFIRMACION = {
    "apagar":       {"pregunta": "¿Apagar el equipo?",       "comando_sistema": "shutdown /s /t 5", "respuesta_ok": "Apagando.", "respuesta_cancelado": "Apagado cancelado.", "termina_programa": True},
    "reiniciar":    {"pregunta": "¿Reiniciar el equipo?",    "comando_sistema": "shutdown /r /t 5", "respuesta_ok": "Reiniciando.", "respuesta_cancelado": "Reinicio cancelado.", "termina_programa": True},
    "cerrar_sesion":{"pregunta": "¿Cerrar sesión?",          "comando_sistema": "shutdown /l",      "respuesta_ok": "Cerrando sesión.", "respuesta_cancelado": "Cancelado.", "termina_programa": True},
    "bloquear":     {"pregunta": "¿Bloquear el equipo?",     "comando_sistema": "rundll32.exe user32.dll,LockWorkStation", "respuesta_ok": "Bloqueando.", "respuesta_cancelado": "Cancelado.", "termina_programa": False},
}

# ─── Criptomonedas ─────────────────────────────────────────────────────────────
CRYPTO_IDS = {
    "bitcoin": "bitcoin",       "btc": "bitcoin",
    "ethereum": "ethereum",     "eth": "ethereum",
    "dogecoin": "dogecoin",     "doge": "dogecoin",
    "solana": "solana",         "sol": "solana",
    "cardano": "cardano",       "ada": "cardano",
    "ripple": "ripple",         "xrp": "ripple",
    "litecoin": "litecoin",     "ltc": "litecoin",
    "binance coin": "binancecoin", "bnb": "binancecoin",
    "polkadot": "polkadot",     "dot": "polkadot",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "chainlink": "chainlink",   "link": "chainlink",
    "polygon": "matic-network", "matic": "matic-network",
    "shiba inu": "shiba-inu",   "shiba": "shiba-inu",
    "tron": "tron",             "trx": "tron",
}

EMPRESAS_CRIPTO = {
    "coinbase": "COIN",   "microstrategy": "MSTR",
    "tesla": "TSLA",      "nvidia": "NVDA",
    "riot": "RIOT",       "marathon": "MARA",
    "block": "SQ",        "square": "SQ",
    "paypal": "PYPL",     "robinhood": "HOOD",
}

FUENTE_RSS_CRIPTO = "https://cointelegraph.com/rss"

# ─── Telegram ─────────────────────────────────────────────────────────────────
NUMEROS_TEXTO = {
    "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}
NOMBRES_DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# =========================================================================
# SETTINGS (token Telegram, chats autorizados)
# =========================================================================

def cargar_settings():
    if os.path.exists(ARCHIVO_SETTINGS):
        try:
            with open(ARCHIVO_SETTINGS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def guardar_settings(datos):
    with open(ARCHIVO_SETTINGS, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

def get_nombre_asistente(default="JARVIS"):
    """Devuelve el nombre del asistente configurado en settings (o 'JARVIS' por defecto)."""
    try:
        return cargar_settings().get("nombre_asistente", default) or default
    except Exception:
        return default

def get_nombre_asistente_hud(default="JARVIS"):
    """Devuelve el nombre con puntos estilo HUD: 'JARVIS' → 'J·A·R·V·I·S'."""
    nombre = get_nombre_asistente(default)
    return "·".join(list(nombre.upper()))

def get_nombre_usuario(default="señor"):
    """Devuelve el nombre del usuario configurado en settings."""
    try:
        return cargar_settings().get("nombre_usuario", default) or default
    except Exception:
        return default


def get_telegram_token():
    s = cargar_settings()
    return s.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")

def get_chats_autorizados():
    s = cargar_settings()
    ids = s.get("chats_autorizados", [])
    if not ids:
        env = os.getenv("TELEGRAM_CHAT_ID", "")
        ids = [int(x) for x in env.split(",") if x.strip().isdigit()]
    return ids

# =========================================================================
# CONVERSIÓN NÚMEROS EN TEXTO → DÍGITOS
# =========================================================================

_UNIDADES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
}
_DIEZ_A_DIECINUEVE = {
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
}
_VEINTES = {
    "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}
_DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60}
_NUMEROS_PALABRA = {**_UNIDADES, **_DIEZ_A_DIECINUEVE, **_VEINTES, **_DECENAS}


def _convertir_numeros_en_texto(texto):
    palabras = texto.split()
    resultado = []
    i = 0
    while i < len(palabras):
        p = palabras[i].strip(",.")
        if (p in _DECENAS and i + 2 < len(palabras)
                and palabras[i + 1] == "y"
                and palabras[i + 2].strip(",.") in _UNIDADES):
            resultado.append(str(_DECENAS[p] + _UNIDADES[palabras[i + 2].strip(",.")]))
            i += 3
            continue
        if p in _NUMEROS_PALABRA:
            resultado.append(str(_NUMEROS_PALABRA[p]))
        else:
            resultado.append(palabras[i])
        i += 1
    return " ".join(resultado)


_CORRECCIONES_ACENTOS = {
    "manana": "mañana", "sabado": "sábado", "miercoles": "miércoles",
    "dia": "día", "proximo": "próximo", "despues": "después",
}


def _corregir_acentos(texto):
    for sin, con in _CORRECCIONES_ACENTOS.items():
        texto = re.sub(rf"\b{sin}\b", con, texto)
    return texto


def _extraer_hora_explicita(texto):
    texto = texto.lower()
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|a\.m\.|de la mañana)\b", texto)
    if m:
        return int(m.group(1)) % 12, int(m.group(2) or 0)
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(pm|p\.m\.|de la tarde|de la noche)\b", texto)
    if m:
        return (int(m.group(1)) % 12) + 12, int(m.group(2) or 0)
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", texto)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _detectar_por_palabra(comando, diccionario):
    palabras = set(comando.split())
    for clave in diccionario:
        if " " in clave:
            if clave in comando:
                return clave
        elif clave in palabras:
            return clave
    return None

# =========================================================================
# MEMORIA / PENDIENTES / ALARMAS
# =========================================================================

def cargar_memoria():
    if not os.path.exists(ARCHIVO_MEMORIA):
        return {"pendientes": [], "alarmas": []}
    with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
        m = json.load(f)
    m.setdefault("pendientes", [])
    m.setdefault("alarmas", [])
    return m


def guardar_memoria(memoria):
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)


def guardar_pendiente(texto, prioridad="normal"):
    m = cargar_memoria()
    nuevo = {"texto": texto, "prioridad": prioridad}
    if prioridad == "urgente":
        m["pendientes"].insert(0, nuevo)
    else:
        m["pendientes"].append(nuevo)
    guardar_memoria(m)


def obtener_pendientes():
    return cargar_memoria()["pendientes"]


def eliminar_varios_pendientes(numeros):
    m = cargar_memoria()
    pendientes = m["pendientes"]
    eliminados = []
    for n in sorted(set(numeros), reverse=True):
        idx = n - 1
        if 0 <= idx < len(pendientes):
            eliminados.append(pendientes.pop(idx))
    guardar_memoria(m)
    return eliminados


def eliminar_pendiente_por_texto(texto):
    m = cargar_memoria()
    for p in m["pendientes"]:
        t = p["texto"] if isinstance(p, dict) else p
        if texto in t:
            m["pendientes"].remove(p)
            guardar_memoria(m)
            return t
    return None


def buscar_pendientes_por_texto(texto_busqueda):
    if not texto_busqueda:
        return []
    tb = texto_busqueda.lower().strip()
    return [p for p in obtener_pendientes()
            if tb in (p["texto"] if isinstance(p, dict) else str(p)).lower()]


def calcular_proxima_ejecucion(tipo, dias_semana, hora, minuto, ahora=None):
    ahora = ahora or datetime.now()
    if tipo == "diaria":
        c = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if c <= ahora:
            c += timedelta(days=1)
        return c
    for delta in range(8):
        c = (ahora + timedelta(days=delta)).replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if c.weekday() in dias_semana and c > ahora:
            return c
    return ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0) + timedelta(days=7)


def guardar_alarma(texto, fecha_hora, recurrente=False, tipo=None, dias_semana=None):
    m = cargar_memoria()
    m["alarmas"].append({
        "texto": texto,
        "fecha_hora": fecha_hora.isoformat(),
        "recurrente": recurrente,
        "tipo": tipo,
        "dias_semana": dias_semana or [],
    })
    guardar_memoria(m)


def obtener_alarmas():
    return sorted(cargar_memoria()["alarmas"], key=lambda a: a["fecha_hora"])


def eliminar_alarma_por_numero(numero):
    alarmas = obtener_alarmas()
    idx = numero - 1
    if idx < 0 or idx >= len(alarmas):
        return None
    alarma = alarmas[idx]
    m = cargar_memoria()
    m["alarmas"] = [a for a in m["alarmas"] if a != alarma]
    guardar_memoria(m)
    return alarma


# =========================================================================
# AGENDA (citas, eventos del calendario)
# =========================================================================

import uuid as _uuid


def guardar_agenda(titulo, fecha_str, hora_str, descripcion=""):
    """Guarda un evento en la agenda. fecha_str: 'DD/MM/AAAA', hora_str: 'HH:MM'."""
    m = cargar_memoria()
    m.setdefault("agenda", [])
    m["agenda"].append({
        "id":          _uuid.uuid4().hex[:8],
        "titulo":      titulo,
        "fecha":       fecha_str,      # DD/MM/AAAA
        "hora":        hora_str,       # HH:MM
        "descripcion": descripcion,
        "completado":  False,
    })
    guardar_memoria(m)


def obtener_agenda(fecha=None):
    """Devuelve eventos. Si fecha='DD/MM/AAAA' filtra por ese día, si no todos."""
    m = cargar_memoria()
    eventos = m.get("agenda", [])
    if fecha:
        eventos = [e for e in eventos if e.get("fecha") == fecha]
    return eventos


def eliminar_evento_agenda(eid):
    """Elimina un evento por su id."""
    m = cargar_memoria()
    m["agenda"] = [e for e in m.get("agenda", []) if e.get("id") != eid]
    guardar_memoria(m)


def obtener_eventos_hoy():
    """Devuelve los eventos de hoy."""
    hoy = datetime.now().strftime("%d/%m/%Y")
    return obtener_agenda(fecha=hoy)


# =========================================================================
# CRIPTOMONEDAS, ACCIONES Y NOTICIAS
# =========================================================================


def _precio_cripto(id_cripto):
    try:
        url = (f"https://api.coingecko.com/api/v3/simple/price?ids={id_cripto}"
               "&vs_currencies=usd,cop&include_24hr_change=true")
        r = requests.get(url, timeout=10)
        d = r.json()
        return (d[id_cripto], None) if id_cripto in d else (None, "No encontré esa criptomoneda.")
    except Exception as e:
        return None, str(e)


def _precio_accion(ticker):
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        precio = getattr(info, "last_price", None) or (info.get("lastPrice") if hasattr(info, "get") else None)
        moneda = getattr(info, "currency", "USD")
        return ({"precio": precio, "moneda": moneda}, None) if precio else (None, "No pude obtener el precio.")
    except ImportError:
        return None, "yfinance no instalado. Ejecuta: pip install yfinance"
    except Exception as e:
        return None, str(e)


def _noticias(tema, cantidad=3):
    try:
        import feedparser
        from urllib.parse import quote
        url = f"https://news.google.com/rss/search?q={quote(tema)}&hl=es-419&gl=CO&ceid=CO:es-419"
        feed = feedparser.parse(url)
        return [e.title for e in feed.entries[:cantidad]], None
    except ImportError:
        return None, "feedparser no instalado. Ejecuta: pip install feedparser"
    except Exception as e:
        return None, str(e)


def _noticias_cripto(cantidad=5):
    try:
        import feedparser
        feed = feedparser.parse(FUENTE_RSS_CRIPTO)
        return [e.title for e in feed.entries[:cantidad]], None
    except ImportError:
        return None, "feedparser no instalado."
    except Exception as e:
        return None, str(e)


# =========================================================================
# WHATSAPP
# =========================================================================

def _callmebot(numero, mensaje, apikey):
    if not apikey:
        return False, ("Sin apikey de CallMeBot. Ese contacto debe enviar "
                       "'I allow callmebot to send me messages' al número de CallMeBot.")
    from urllib.parse import quote
    numero = numero.lstrip("+")
    url = f"https://api.callmebot.com/whatsapp.php?phone={numero}&text={quote(mensaje)}&apikey={apikey}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and "queued" in r.text.lower():
            return True, None
        return False, f"CallMeBot: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def _pywhatkit(numero, mensaje):
    try:
        import pywhatkit
        numero_fmt = numero if numero.startswith("+") else f"+{numero}"
        pywhatkit.sendwhatmsg_instantly(numero_fmt, mensaje, wait_time=20, tab_close=True)
        return True, None
    except ImportError:
        return False, "pywhatkit no instalado."
    except Exception as e:
        return False, str(e)


def _twilio_wa(numero, mensaje):
    try:
        from twilio.rest import Client
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            return False, "Twilio no configurado (faltan SID/Token)."
        numero_fmt = numero if numero.startswith("+") else f"+{numero}"
        Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(
            from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{numero_fmt}", body=mensaje)
        return True, None
    except ImportError:
        return False, "twilio no instalado. Ejecuta: pip install twilio"
    except Exception as e:
        return False, str(e)


def enviar_whatsapp(numero, mensaje, apikey=None):
    if METODO_WHATSAPP == "twilio":
        return _twilio_wa(numero, mensaje)
    if METODO_WHATSAPP == "callmebot":
        return _callmebot(numero, mensaje, apikey)
    return _pywhatkit(numero, mensaje)


def _hilo_enviar_whatsapp(numero, mensaje, nombre, apikey=None):
    exito, error = enviar_whatsapp(numero, mensaje, apikey=apikey)
    if exito:
        print(f"[WHATSAPP] Enviado a {nombre}.")
    else:
        print(f"[WHATSAPP] Error a {nombre}: {error}")


# =========================================================================
# APPS EN ANDROID
# =========================================================================

def _abrir_app_android(package, nombre, url_fallback=None):
    if PLATFORM == "android":
        try:
            from jnius import autoclass
            ctx = autoclass("org.kivy.android.PythonActivity").mActivity
            intent = ctx.getPackageManager().getLaunchIntentForPackage(package)
            if intent:
                ctx.startActivity(intent)
                return f"Abriendo {nombre}"
        except Exception as e:
            print(f"[APPS] {e}")
    if url_fallback:
        abrir_url_silenciosa(url_fallback)
        return f"Abriendo {nombre} en el navegador"
    return f"No pude abrir {nombre}"


def ejecutar_accion_sistema(accion):
    info = ACCIONES_CONFIRMACION[accion]
    if PLATFORM not in ("android", "ios"):
        os.system(info["comando_sistema"])
    return info["respuesta_ok"]


def aplicacion_abierta(proceso):
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == proceso.lower():
                return True
        except Exception:
            pass
    return False


# =========================================================================
# NÚCLEO: procesar_comando
# =========================================================================

def procesar_comando(comando):
    comando = comando.lower().strip()
    resultado = {"respuesta": "", "confirmar": None, "salir": False}

    if not comando:
        resultado["respuesta"] = "No escuche ningun comando."
        return resultado

    # ── Salida ──────────────────────────────────────────────────────────────────
    palabras_salida = {"salir", "sal", "adios", "chao", "chau", "apagate"}
    if set(comando.split()) & palabras_salida or "hasta luego" in comando:
        resultado["respuesta"] = "Hasta luego."
        resultado["salir"] = True
        return resultado

    # ── Hora / Fecha ─────────────────────────────────────────────────────────────
    if "hora" in comando:
        resultado["respuesta"] = f"Son las {datetime.now().strftime('%H:%M')}"

    elif "fecha" in comando:
        resultado["respuesta"] = f"Hoy es {datetime.now().strftime('%d/%m/%Y')}"

    # ── Web ──────────────────────────────────────────────────────────────────────
    elif "google" in comando and "chrome" not in comando and "noticias" not in comando:
        abrir_url_silenciosa("https://www.google.com")
        resultado["respuesta"] = "Abriendo Google"

    elif "youtube" in comando:
        if any(p in comando for p in ["buscar", "busca"]):
            video = re.sub(r"\b(buscar en youtube|busca en youtube|buscar youtube|busca youtube|en youtube|youtube|buscar|busca)\b", "", comando).strip()
            if video:
                abrir_url_silenciosa(f"https://www.youtube.com/results?search_query={video}")
                resultado["respuesta"] = f"Buscando {video} en YouTube"
            else:
                resultado["respuesta"] = "¿Que desea buscar en YouTube?"
        else:
            abrir_url_silenciosa("https://www.youtube.com")
            resultado["respuesta"] = "Abriendo YouTube"

    # ── Sistema ──────────────────────────────────────────────────────────────────
    elif "estado del sistema" in comando:
        cpu   = psutil.cpu_percent(interval=1)
        ram   = psutil.virtual_memory().percent
        disco = psutil.disk_usage("/" if PLATFORM != "win" else "C:")
        libre = round(disco.free / (1024 ** 3), 1)
        bat   = psutil.sensors_battery()
        bat_txt = f"Bateria al {int(bat.percent)}%." if bat else ""
        resultado["respuesta"] = f"CPU al {cpu}%. RAM al {ram}%. Disco libre {libre} GB. {bat_txt}"

    elif "explorador" in comando:
        resultado["respuesta"] = _abrir_cmd("explorer", "explorador de archivos")

    elif "descargas" in comando:
        resultado["respuesta"] = _abrir_ruta(os.path.join(os.path.expanduser("~"), "Downloads"), "descargas")

    elif "documentos" in comando:
        resultado["respuesta"] = _abrir_ruta(os.path.join(os.path.expanduser("~"), "Documents"), "documentos")

    elif "escritorio" in comando:
        resultado["respuesta"] = _abrir_ruta(os.path.join(os.path.expanduser("~"), "Desktop"), "escritorio")

    # ── Acciones con confirmación ─────────────────────────────────────────────────
    elif "apagar" in comando and "no" not in comando:
        resultado["confirmar"] = "apagar"
    elif "reiniciar" in comando and "no" not in comando:
        resultado["confirmar"] = "reiniciar"
    elif any(x in comando for x in ["cerrar sesion", "cerrar sesión"]):
        resultado["confirmar"] = "cerrar_sesion"
    elif "bloquear equipo" in comando:
        resultado["confirmar"] = "bloquear"

    # ── Modos ────────────────────────────────────────────────────────────────────
    elif any(x in comando for x in ["modo trabajo", "modo de trabajo", "modo laboral"]):
        if PLATFORM not in ("android", "ios"):
            abrir_url_silenciosa("https://mail.google.com")
            abrir_url_silenciosa("https://web.whatsapp.com")
        resultado["respuesta"] = "Modo trabajo activado. Abriendo correo y WhatsApp Web."

    elif any(x in comando for x in ["modo entretenimiento", "modo de entretenimiento", "modo juego", "modo relax"]):
        if PLATFORM not in ("android", "ios"):
            abrir_url_silenciosa("https://www.youtube.com")
        resultado["respuesta"] = "Modo entretenimiento activado. Abriendo YouTube."

    # ── AGENDA: listar ────────────────────────────────────────────────────────────
    elif any(x in comando for x in ["mi agenda", "mis citas", "agenda del dia", "agenda de hoy"]):
        eventos = obtener_eventos_hoy()
        if not eventos:
            resultado["respuesta"] = "No tienes eventos en la agenda de hoy."
        else:
            ev_sorted = sorted(eventos, key=lambda e: e.get("hora", "00:00"))
            lista = [f"{e['hora']} — {e['titulo']}" for e in ev_sorted]
            resultado["respuesta"] = "Agenda de hoy: " + ". ".join(lista)

    elif "agenda de manana" in comando or "agenda de mañana" in comando:
        manana = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
        eventos = obtener_agenda(fecha=manana)
        if not eventos:
            resultado["respuesta"] = "No tienes eventos para mañana."
        else:
            ev_sorted = sorted(eventos, key=lambda e: e.get("hora", "00:00"))
            lista = [f"{e['hora']} — {e['titulo']}" for e in ev_sorted]
            resultado["respuesta"] = "Agenda de mañana: " + ". ".join(lista)

    # ── AGENDA: crear ─────────────────────────────────────────────────────────────
    elif any(x in comando for x in ["agendar", "agenda para", "programa una cita", "programa un evento"]):
        cn = _convertir_numeros_en_texto(comando)
        cn = _corregir_acentos(cn)

        coincidencias = search_dates(cn, languages=["es"], settings={"PREFER_DATES_FROM": "future"})
        texto_fecha, fh_det = coincidencias[0] if coincidencias else ("", None)

        if fh_det is not None:
            hora_exp = _extraer_hora_explicita(cn)
            if hora_exp:
                fh_det = fh_det.replace(hour=hora_exp[0], minute=hora_exp[1], second=0, microsecond=0)

        if fh_det is None:
            resultado["respuesta"] = (
                "No entendi la fecha u hora. Ejemplo: "
                "'agendar reunion para el martes a las 3 de la tarde'"
            )
        else:
            # ── Extraer título limpiando SOLO el trigger y los marcadores de fecha/hora ──
            titulo_ev = cn

            # 1. Quitar el trigger del comando
            titulo_ev = re.sub(
                r"^(jarvis[,\s]+)?(agendar|agenda para|programa una cita|programa un evento)\s*",
                "", titulo_ev, flags=re.IGNORECASE
            ).strip()

            # 2. Quitar marcadores de fecha/hora específicos (sin tocar el contenido)
            _FECHA_HORA_PATTERNS = [
                r"\bpara (el |la )?(próximo |proximo )?(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b",
                r"\bpara (mañana|manana|hoy|pasado mañana|pasado manana)\b",
                r"\b(el |al )?\d{1,2} de [a-záéíóúñ]+ (de \d{4})?\b",
                r"\bel (próximo|proximo|siguiente) \w+\b",
                r"\ba las \d{1,2}(:\d{2})?\s*(am|pm|de la mañana|de la tarde|de la noche)?\b",
                r"\b\d{1,2}:\d{2}\s*(am|pm)?\b",
                r"\b\d{1,2}\s*(am|pm)\b",
                r"\b(de la mañana|de la tarde|de la noche|en punto)\b",
                r"\bpara el día \d{1,2}\b",
            ]
            for pat in _FECHA_HORA_PATTERNS:
                titulo_ev = re.sub(pat, "", titulo_ev, flags=re.IGNORECASE)

            titulo_ev = re.sub(r"\s+", " ", titulo_ev).strip()

            # Si queda vacío, pedir que repita con más detalle
            if not titulo_ev or len(titulo_ev) < 2:
                resultado["respuesta"] = (
                    "No entendí el evento. Ejemplo: "
                    "'agendar reunion medica para el viernes a las 3 pm'"
                )
            else:
                fecha_str = fh_det.strftime("%d/%m/%Y")
                hora_str  = fh_det.strftime("%H:%M")
                guardar_agenda(titulo_ev, fecha_str, hora_str)
                resultado["respuesta"] = (
                    f"Agendado: '{titulo_ev}' para el {fecha_str} a las {hora_str}."
                )


    # ── ALARMAS: listar ──────────────────────────────────────────────────────────

    elif any(x in comando for x in ["mis alarmas", "lista de alarmas", "que alarmas tengo"]):
        alarmas = obtener_alarmas()
        if not alarmas:
            resultado["respuesta"] = "No tienes alarmas programadas."
        else:
            lista = []
            for i, a in enumerate(alarmas, 1):
                fh = datetime.fromisoformat(a["fecha_hora"])
                hora_str = fh.strftime("%H:%M")
                if a.get("recurrente") and a.get("tipo") == "diaria":
                    cuando = f"todos los dias a las {hora_str}"
                elif a.get("recurrente") and a.get("tipo") == "semanal":
                    nombres = [NOMBRES_DIAS_SEMANA[d].capitalize() for d in a.get("dias_semana", [])]
                    cuando = f"cada {', '.join(nombres)} a las {hora_str}"
                else:
                    cuando = f"el {fh.strftime('%d/%m')} a las {hora_str}"
                lista.append(f"{i}. {a['texto']}, {cuando}")
            resultado["respuesta"] = "Tus alarmas: " + ". ".join(lista)

    # ── ALARMAS: eliminar ────────────────────────────────────────────────────────
    elif any(x in comando for x in ["elimina alarma", "borra alarma", "cancela alarma", "elimina la alarma", "borra todas las alarmas", "elimina todas las alarmas"]):
        if any(x in comando for x in ["todas las alarmas", "todas"]):
            m = cargar_memoria(); m["alarmas"] = []; guardar_memoria(m)
            resultado["respuesta"] = "Todas las alarmas eliminadas."
        else:
            numero = None
            for p in comando.split():
                if p.isdigit():
                    numero = int(p); break
                elif p in NUMEROS_TEXTO:
                    numero = NUMEROS_TEXTO[p]; break
            if numero is None:
                resultado["respuesta"] = "Di el numero de la alarma. Mira la lista con 'mis alarmas'."
            else:
                e = eliminar_alarma_por_numero(numero)
                resultado["respuesta"] = f"Alarma eliminada: {e['texto']}" if e else "No encontre esa alarma."

    # ── ALARMAS: crear ───────────────────────────────────────────────────────────
    elif any(x in comando for x in ["alarma", "despiertame", "despierta", "avisame", "recuerdame", "recuerdame"]):
        cn = _convertir_numeros_en_texto(comando)
        cn = _corregir_acentos(cn)

        es_diaria  = any(p in cn for p in ["todos los dias", "cada dia", "diariamente", "a diario"])
        dias_det   = sorted({DIAS_SEMANA[d] for d in DIAS_SEMANA if d in cn})
        es_semanal = bool(dias_det) and any(p in cn for p in ["cada", "todos los"])

        coincidencias = search_dates(cn, languages=["es"], settings={"PREFER_DATES_FROM": "future"})
        texto_fecha, fh_det = coincidencias[0] if coincidencias else ("", None)

        if fh_det is not None:
            hora_exp = _extraer_hora_explicita(cn)
            if hora_exp:
                fh_det = fh_det.replace(hour=hora_exp[0], minute=hora_exp[1], second=0, microsecond=0)
                if fh_det <= datetime.now() and "hoy" not in cn:
                    fh_det += timedelta(days=1)

        if fh_det is None and not es_diaria and not es_semanal:
            if "recuerdame" in comando:
                txt = re.sub(r"\b(jarvis|recuerdame|recuérdame)\b", "", comando).strip()
                if txt:
                    guardar_pendiente(txt)
                    resultado["respuesta"] = "Anotado como pendiente."
                else:
                    resultado["respuesta"] = "¿Que debo recordar?"
            else:
                resultado["respuesta"] = "No entendi para cuando. Di algo como: 'alarma para mañana a las 8 am recoger paquete'."
        elif (es_diaria or es_semanal) and fh_det is None:
            resultado["respuesta"] = "Di a que hora, por ejemplo 'todos los dias a las 7 de la mañana'."
        else:
            # Limpiar el texto del recordatorio
            txt_rec = cn
            if texto_fecha:
                txt_rec = txt_rec.replace(texto_fecha, "")
            for f in ["todos los dias", "todos los dias", "cada dia", "a diario", "todas las"]:
                txt_rec = txt_rec.replace(f, "")
            patron = (r"\b(alarma|despiertame|despierta|avisame|recuerdame|recordatorio|"
                      r"diariamente|cada|todos|los|las|lunes|martes|miercoles|miércoles|"
                      r"jueves|viernes|sabado|sábado|domingo|para|que|de|el|la)\b")
            txt_rec = re.sub(patron, "", txt_rec)
            txt_rec = re.sub(r"\s+", " ", txt_rec).strip() or "Alarma"

            if es_diaria:
                prox = calcular_proxima_ejecucion("diaria", [], fh_det.hour, fh_det.minute)
                guardar_alarma(txt_rec, prox, recurrente=True, tipo="diaria")
                resultado["respuesta"] = f"Listo, todos los dias a las {prox.strftime('%H:%M')} te recuerdo: {txt_rec}"
            elif es_semanal:
                prox = calcular_proxima_ejecucion("semanal", dias_det, fh_det.hour, fh_det.minute)
                nombres = [NOMBRES_DIAS_SEMANA[d].capitalize() for d in dias_det]
                guardar_alarma(txt_rec, prox, recurrente=True, tipo="semanal", dias_semana=dias_det)
                resultado["respuesta"] = f"Listo, cada {', '.join(nombres)} a las {prox.strftime('%H:%M')}: {txt_rec}"
            elif fh_det <= datetime.now():
                resultado["respuesta"] = "Esa hora ya paso. Di una fecha futura."
            else:
                guardar_alarma(txt_rec, fh_det)
                resultado["respuesta"] = f"Alarma para el {fh_det.strftime('%d/%m/%Y a las %H:%M')}: {txt_rec}"

    # ── PENDIENTES: listar ────────────────────────────────────────────────────────
    elif any(x in comando for x in ["mis pendientes", "lista de pendientes", "que tengo pendiente"]):
        pendientes = obtener_pendientes()
        if not pendientes:
            resultado["respuesta"] = "No tienes pendientes."
        else:
            lista = [f"{i}. {p['texto'] if isinstance(p, dict) else p}" for i, p in enumerate(pendientes, 1)]
            resultado["respuesta"] = "Tus pendientes: " + ". ".join(lista)

    # ── PENDIENTES: guardar ───────────────────────────────────────────────────────
    elif any(x in comando for x in ["recuerda", "guarda", "anota", "agrega", "apunta"]):
        txt = comando
        prioridad = "normal"
        if "urgente" in txt:
            prioridad = "urgente"; txt = txt.replace("urgente", "")
        elif "alta prioridad" in txt:
            prioridad = "alta"; txt = txt.replace("alta prioridad", "")
        txt = re.sub(r"\b(recuerda|guarda|anota|agrega|apunta|que|a|mi|el|la|no|olvides)\b", "", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        if not txt:
            resultado["respuesta"] = "¿Que debo recordar?"
        else:
            guardar_pendiente(txt, prioridad)
            resultado["respuesta"] = "Anotado."

    # ── PENDIENTES: eliminar ──────────────────────────────────────────────────────
    elif any(x in comando for x in ["eliminar", "elimina", "borrar", "borra"]) and "alarma" not in comando:
        if any(x in comando for x in ["todo", "todos", "todas"]):
            m = cargar_memoria(); m["pendientes"] = []; guardar_memoria(m)
            resultado["respuesta"] = "Lista de pendientes vaciada."
        else:
            nums = []
            for p in comando.split():
                if p.isdigit(): nums.append(int(p))
                elif p in NUMEROS_TEXTO: nums.append(NUMEROS_TEXTO[p])
            if nums:
                elim = eliminar_varios_pendientes(nums)
                nombres = [e.get("texto", str(e)) if isinstance(e, dict) else str(e) for e in elim]
                resultado["respuesta"] = (f"Eliminado: {', '.join(nombres)}" if nombres else "No encontre esos numeros.")
            else:
                txt = re.sub(r"\b(jarvis|elimina|eliminar|borra|borrar)\b", "", comando).strip()
                e = eliminar_pendiente_por_texto(txt)
                resultado["respuesta"] = f"Eliminado: {e}" if e else "No encontre ese pendiente."

    # ── PENDIENTES: buscar ────────────────────────────────────────────────────────
    elif any(x in comando for x in ["busca pendiente", "buscar pendiente"]):
        busq = re.sub(r"\b(busca|buscar|pendiente|pendientes)\b", "", comando).strip()
        if not busq:
            resultado["respuesta"] = "¿Que palabra busco en los pendientes?"
        else:
            rs = buscar_pendientes_por_texto(busq)
            if not rs:
                resultado["respuesta"] = f"No encontre pendientes con '{busq}'."
            else:
                lista = [f"{i}. {p['texto'] if isinstance(p, dict) else p}" for i, p in enumerate(rs, 1)]
                resultado["respuesta"] = "Encontre: " + ". ".join(lista)

    # ── WHATSAPP ─────────────────────────────────────────────────────────────────
    elif any(x in comando for x in ["whatsapp", "wasap", "whats app"]):
        if not CONTACTOS_WHATSAPP:
            resultado["respuesta"] = "No hay contactos de WhatsApp configurados."
        else:
            contacto = next((n for n in CONTACTOS_WHATSAPP if n in comando), None)
            if not contacto:
                resultado["respuesta"] = f"¿A quien? Contactos: {', '.join(CONTACTOS_WHATSAPP.keys())}."
            else:
                # Extraer el mensaje limpiando palabras clave
                msg = comando
                for f in ["envia un whatsapp a", "manda un whatsapp a", "whatsapp a", "wasap a",
                          contacto, "diciendo que", "diciendo", "que diga", "que le diga"]:
                    msg = msg.replace(f, "")
                msg = re.sub(r"^(que\s+|jarvis\s+)+", "", msg, flags=re.IGNORECASE).strip(" ,.")
                if not msg:
                    resultado["respuesta"] = f"¿Que le digo a {contacto}?"
                else:
                    info = CONTACTOS_WHATSAPP[contacto]
                    threading.Thread(
                        target=_hilo_enviar_whatsapp,
                        args=(info["numero"], msg, contacto, info.get("apikey")),
                        daemon=True,
                    ).start()
                    resultado["respuesta"] = f"Enviando WhatsApp a {contacto}: {msg}"

    # ── CRYPTO ───────────────────────────────────────────────────────────────────
    elif (any(x in comando for x in ["precio", "cotizacion", "cuanto vale", "cuanto cuesta", "valor"])
          and _detectar_por_palabra(comando, CRYPTO_IDS)):
        cripto = _detectar_por_palabra(comando, CRYPTO_IDS)
        info, err = _precio_cripto(CRYPTO_IDS[cripto])
        if err:
            resultado["respuesta"] = f"No pude consultar el precio: {err}"
        else:
            usd    = info.get("usd")
            cop    = info.get("cop")
            cambio = info.get("usd_24h_change")
            dir_   = "subio" if (cambio or 0) >= 0 else "bajo"
            resultado["respuesta"] = (
                f"{cripto.capitalize()} esta en {usd:,.2f} USD"
                + (f" ({cop:,.0f} COP)" if cop else "")
                + (f", {dir_} {abs(cambio):.1f}% en 24h." if cambio else ".")
            )

    # ── ACCIONES ─────────────────────────────────────────────────────────────────
    elif (_detectar_por_palabra(comando, EMPRESAS_CRIPTO)
          and any(x in comando for x in ["accion", "acciones"])):
        empresa = _detectar_por_palabra(comando, EMPRESAS_CRIPTO)
        info, err = _precio_accion(EMPRESAS_CRIPTO[empresa])
        if err:
            resultado["respuesta"] = f"No pude consultar: {err}"
        else:
            resultado["respuesta"] = f"La accion de {empresa.capitalize()} esta en {info['precio']:.2f} {info['moneda']}."

    # ── NOTICIAS CRIPTO ───────────────────────────────────────────────────────────
    elif any(x in comando for x in ["noticias cripto", "novedades cripto"]):
        titulares, err = _noticias_cripto()
        if err:
            resultado["respuesta"] = f"No pude consultar noticias cripto: {err}"
        else:
            resultado["respuesta"] = "Ultimas noticias cripto: " + ". ".join(f"{i}. {t}" for i, t in enumerate(titulares or [], 1))

    # ── NOTICIAS GENERALES ────────────────────────────────────────────────────────
    elif "noticias" in comando:
        tema = re.sub(r"\b(dame las noticias de|noticias de|noticias sobre|dame noticias|noticias)\b", "", comando).strip() or "colombia"
        titulares, err = _noticias(tema)
        if err:
            resultado["respuesta"] = f"Error: {err}"
        else:
            resultado["respuesta"] = f"Noticias sobre {tema}: " + ". ".join(f"{i}. {t}" for i, t in enumerate(titulares or [], 1))

    # ── APPS ANDROID ─────────────────────────────────────────────────────────────
    elif PLATFORM == "android" and any(alias in comando for info in APPS_ANDROID.values() for alias in info["alias"]):
        for clave, info in APPS_ANDROID.items():
            if any(alias in comando for alias in info["alias"]):
                resultado["respuesta"] = _abrir_app_android(info["package"], info["nombre"])
                break

    # ── APPS WINDOWS ─────────────────────────────────────────────────────────────
    elif PLATFORM != "android" and any(alias in comando for info in APPS_WINDOWS.values() for alias in info["alias"]):
        apps_det  = [k for k, v in APPS_WINDOWS.items() if any(a in comando for a in v["alias"])]
        cerrar    = any(p in comando for p in ["cierra", "cerrar"])
        respuestas = []
        for k in apps_det:
            info = APPS_WINDOWS[k]
            if cerrar:
                procs = info["proceso"] if isinstance(info["proceso"], list) else [info["proceso"]]
                for p in procs:
                    _matar_proceso_silencioso(p)
                respuestas.append(f"Cerrando {info['nombre']}")
            else:
                respuestas.append(info["abrir"]())
        resultado["respuesta"] = ". ".join(respuestas)

    # ── ABRIR CUALQUIER OTRA APLICACIÓN O SITIO WEB ──────────────────────────────
    elif any(cmd_p in comando for cmd_p in ["abrir ", "abre "]):
        target = re.sub(r"^(jarvis[,\s]+)?(abrir|abre)\s+", "", comando, flags=re.IGNORECASE).strip()
        if target:
            SITIOS = {
                "netflix": "https://www.netflix.com",
                "facebook": "https://www.facebook.com",
                "instagram": "https://www.instagram.com",
                "tiktok": "https://www.tiktok.com",
                "twitter": "https://www.x.com",
                "x": "https://www.x.com",
                "gmail": "https://mail.google.com",
                "drive": "https://drive.google.com",
                "whatsapp": "https://web.whatsapp.com",
                "mercadolibre": "https://www.mercadolibre.com.co",
                "amazon": "https://www.amazon.com",
            }
            url = SITIOS.get(target, f"https://www.google.com/search?q={target}")
            abrir_url_silenciosa(url)
            resultado["respuesta"] = f"Abriendo {target.capitalize()}"

    # ── BUSQUEDA WEB ──────────────────────────────────────────────────────────────
    elif "busca" in comando:
        q = comando.replace("busca", "").strip()
        if q:
            abrir_url_silenciosa(f"https://www.google.com/search?q={q}")
            resultado["respuesta"] = f"Buscando {q}"
        else:
            resultado["respuesta"] = "¿Que desea buscar?"

    # ── CONVERSACION ──────────────────────────────────────────────────────────────
    elif any(x in comando for x in ["como estas", "como te encuentras"]):
        resultado["respuesta"] = "Funcionando correctamente, senor."
    elif any(x in comando for x in ["quien te creo", "quien te hizo"]):
        resultado["respuesta"] = "Fui desarrollado por Andres Velasquez."
    elif "gracias" in comando:
        resultado["respuesta"] = "Siempre a su servicio."
    elif "buenos dias" in comando:
        resultado["respuesta"] = "Buenos dias senor. Sistemas listos."
    elif "buenas tardes" in comando:
        resultado["respuesta"] = "Buenas tardes senor."
    elif "buenas noches" in comando:
        resultado["respuesta"] = "Buenas noches senor."
    elif any(x in comando for x in ["que puedes hacer", "ayuda"]):
        resultado["respuesta"] = (
            "Puedo: consultar hora, fecha, estado del sistema, "
            "guardar pendientes y alarmas, enviar WhatsApp via CallMeBot, "
            "consultar precios de criptomonedas y acciones, "
            "mostrar noticias, abrir aplicaciones y buscar en Google."
        )
    elif any(x in comando for x in ["presentate", "quien eres"]):
        try:
            from jarvis_core import get_nombre_asistente, get_nombre_usuario
            _n = get_nombre_asistente("JARVIS")
            _u = get_nombre_usuario("senor")
        except Exception:
            _n, _u = "JARVIS", "senor"
        resultado["respuesta"] = f"Soy {_n}, asistente personal de {_u}. A sus ordenes."

    else:
        # Marcador especial: la UI detecta esto y escala a la IA si está habilitada
        resultado["respuesta"] = "__AI_NEEDED__"

    return resultado
