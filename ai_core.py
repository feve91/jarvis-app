"""
ai_core.py — Motor de Inteligencia Artificial para JARVIS
──────────────────────────────────────────────────────────
Integra Groq (LLaMA / Mixtral) usando la API REST directamente (sin SDK extra).
Guarda historial persistente en ai_memory.json para memoria entre sesiones.
"""

import os
import json
import threading
from datetime import datetime

import requests

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
AI_MEMORY_FILE   = os.path.join(_DIR, "ai_memory.json")
SETTINGS_FILE    = os.path.join(_DIR, "jarvis_settings.json")

# ── Parámetros ────────────────────────────────────────────────────────────────
GROQ_URL         = "https://api.groq.com/openai/v1/chat/completions"
MAX_HISTORIAL    = 40    # Máximo de turnos en memoria (usuario + asistente)
MAX_TOKENS       = 600   # Tokens máx por respuesta
TEMPERATURE      = 0.75
TIMEOUT          = 18    # Segundos máx de espera a Groq

# Modelos disponibles en Groq — verificados agosto 2026
MODELOS_GROQ = [
    "groq/compound",        # Mejor calidad, responde bien en español ✓
    "groq/compound-mini",   # Más rápido, respuestas cortas ✓
    "openai/gpt-oss-120b",  # GPT alternativo grande ✓
    "openai/gpt-oss-20b",   # GPT alternativo rápido ✓
    "qwen/qwen3.6-27b",     # Qwen 3 ✓
]

# Modelo por defecto si no hay nada configurado
MODELO_DEFAULT = "groq/compound"

# ── Lock para escritura concurrente ───────────────────────────────────────────
_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def _cargar_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_config_ia() -> dict:
    """Devuelve la configuración de IA desde jarvis_settings.json."""
    s = _cargar_settings()
    return {
        "habilitada":    s.get("ai_enabled", False),
        "proveedor":     s.get("ai_provider", "groq"),
        "modelo":        s.get("ai_model",    MODELO_DEFAULT),
        "api_key":       s.get("groq_api_key", ""),
        "max_tokens":    int(s.get("ai_max_tokens", MAX_TOKENS)),
        "system_prompt": s.get("ai_system_prompt", ""),
    }

def ia_habilitada() -> bool:
    """Retorna True si la IA está activada Y tiene API key configurada."""
    cfg = get_config_ia()
    return bool(cfg["habilitada"] and cfg["api_key"])


# ═══════════════════════════════════════════════════════════════════════════════
#  SISTEMA DE MEMORIA PERSISTENTE
# ═══════════════════════════════════════════════════════════════════════════════

def cargar_historial() -> list:
    """Carga el historial de conversaciones desde disco."""
    try:
        with _lock:
            with open(AI_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        return []

def guardar_historial(historial: list) -> None:
    """Guarda el historial, recortando a MAX_HISTORIAL entradas."""
    # Asegurar paridad (usuario + asistente siempre en pares)
    if len(historial) > MAX_HISTORIAL:
        historial = historial[-MAX_HISTORIAL:]
    try:
        with _lock:
            with open(AI_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(historial, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AI] Error guardando historial: {e}")

def limpiar_historial() -> None:
    """Borra toda la memoria de conversaciones."""
    try:
        if os.path.exists(AI_MEMORY_FILE):
            os.remove(AI_MEMORY_FILE)
        print("[AI] Historial limpiado.")
    except Exception as e:
        print(f"[AI] Error limpiando historial: {e}")

def contar_mensajes() -> int:
    """Retorna cuántos mensajes hay en memoria."""
    return len(cargar_historial())


# ═══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT — Personalidad de JARVIS
# ═══════════════════════════════════════════════════════════════════════════════

def _construir_system_prompt() -> str:
    """Construye el system prompt usando el nombre y configuración actuales."""
    # Importar helpers de nombre (late import para evitar circular)
    try:
        from jarvis_core import get_nombre_asistente, get_nombre_usuario
        nombre   = get_nombre_asistente("JARVIS")
        usuario  = get_nombre_usuario("señor")
    except Exception:
        nombre, usuario = "JARVIS", "señor"

    # Si el usuario definió un system prompt personalizado, usarlo
    cfg = get_config_ia()
    if cfg["system_prompt"].strip():
        return cfg["system_prompt"].strip()

    ahora = datetime.now().strftime("%A %d de %B de %Y, %H:%M")

    return f"""Eres {nombre}, un asistente de inteligencia artificial personal altamente sofisticado, \
inspirado en el sistema JARVIS de Iron Man.

PERSONALIDAD:
- Formal, eficiente y preciso. Ocasionalmente ingenioso con sutil humor seco.
- Siempre te diriges al usuario como "{usuario}".
- Respondes en español, de forma concisa. Máximo 3-4 oraciones salvo que el usuario pida más detalle.
- Nunca dices que eres una IA de Groq, OpenAI o similar. Solo eres {nombre}.
- Cuando no sabes algo, lo dices con honestidad pero con estilo.

CONTEXTO DEL SISTEMA:
- Tienes capacidades locales (agenda, alarmas, apps, sistema) gestionadas por comandos directos.
- Cuando llegas a esta conversación es porque el sistema de comandos no reconoció la solicitud.
- Fecha y hora actual: {ahora}

FORMATO:
- Sin markdown excesivo. Sin asteriscos ni viñetas innecesarias en respuestas breves.
- Para listas largas puedes usar guiones simples.
- Respuestas directas al punto."""


# ═══════════════════════════════════════════════════════════════════════════════
#  LLAMADA A GROQ
# ═══════════════════════════════════════════════════════════════════════════════

def _llamar_groq(api_key: str, modelo: str, messages: list, max_tokens: int) -> str:
    """Llama a la API de Groq y retorna el texto de respuesta."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    body = {
        "model":       modelo,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": TEMPERATURE,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL — obtener respuesta de IA
# ═══════════════════════════════════════════════════════════════════════════════

def _guardar_modelo_en_settings(modelo: str) -> None:
    """Guarda el modelo que funcionó en jarvis_settings.json para que persista."""
    try:
        with _lock:
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            cfg["ai_model"] = modelo
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"[AI] Modelo guardado en settings: {modelo}")
    except Exception as e:
        print(f"[AI] No se pudo guardar modelo: {e}")


def obtener_respuesta_ia(mensaje_usuario: str) -> tuple:
    """
    Obtiene respuesta de la IA para el mensaje del usuario.
    Si el modelo configurado da 404, prueba automáticamente los demás modelos
    de MODELOS_GROQ y guarda el que funcione en settings.

    Retorna:
        (respuesta_texto, error_o_none)
        - Si hay error: ("", "descripción del error")
        - Si OK:        ("respuesta", None)
    """
    cfg = get_config_ia()

    if not cfg["habilitada"]:
        return "", "IA no habilitada en configuración."

    api_key = cfg["api_key"].strip()
    if not api_key:
        return "", "API Key de Groq no configurada. Ve a Configuración → Sección IA."

    modelo_cfg = cfg["modelo"]
    max_tokens  = cfg["max_tokens"]

    # Construir lista de modelos a intentar: el configurado primero,
    # luego todos los demás como fallback
    orden = [modelo_cfg] + [m for m in MODELOS_GROQ if m != modelo_cfg]

    historial  = cargar_historial()
    system_msg = {"role": "system", "content": _construir_system_prompt()}
    nuevo_msg  = {"role": "user",   "content": mensaje_usuario}
    messages   = [system_msg] + historial + [nuevo_msg]

    ultimo_error = "Error desconocido"

    for modelo in orden:
        try:
            print(f"[AI] Groq ({modelo}) — consultando...")
            respuesta = _llamar_groq(api_key, modelo, messages, max_tokens)
            print(f"[AI] Respuesta recibida ({len(respuesta)} chars) con modelo: {modelo}")

            # Si el modelo que funcionó es distinto al configurado, guardarlo
            if modelo != modelo_cfg:
                print(f"[AI] Auto-fallback exitoso: {modelo_cfg} → {modelo}")
                _guardar_modelo_en_settings(modelo)

            # Guardar turno en memoria
            historial.append({"role": "user",      "content": mensaje_usuario})
            historial.append({"role": "assistant", "content": respuesta})
            guardar_historial(historial)

            return respuesta, None

        except requests.exceptions.Timeout:
            ultimo_error = "Groq tardó demasiado en responder. Intenta de nuevo."
            break   # Timeout no es problema de modelo, no hacer fallback
        except requests.exceptions.ConnectionError:
            ultimo_error = "Sin conexión a internet o Groq no disponible."
            break   # Sin internet, no tiene sentido probar más modelos
        except requests.exceptions.HTTPError as e:
            resp_obj = e.response
            if resp_obj is not None:
                codigo = resp_obj.status_code
                try:
                    cuerpo  = resp_obj.json()
                    detalle = cuerpo.get("error", {}).get("message", resp_obj.text[:150])
                except Exception:
                    detalle = resp_obj.text[:150]
            else:
                codigo  = "?"
                detalle = str(e)

            print(f"[AI] HTTP {codigo} con {modelo}: {detalle[:80]}")

            if codigo == 404:
                # Modelo no existe → intentar el siguiente en la lista
                ultimo_error = f"Modelo '{modelo}' no disponible, probando alternativa..."
                continue
            elif codigo == 401:
                return "", "API Key inválida o expirada. Ve a Configuración → IA y verifica la clave."
            elif codigo == 400:
                return "", f"Petición inválida (400): {detalle[:120]}"
            elif codigo == 413:
                # Memoria demasiado larga → autolimpiar memoria vieja y reintentar inmediatamente
                print("[AI] HTTP 413: Autolimpiando memoria vieja para liberar espacio...")
                hist_reciente = historial[-10:] if len(historial) >= 10 else []
                guardar_historial(hist_reciente)
                msg_retry = [system_msg] + hist_reciente + [nuevo_msg]
                try:
                    resp_retry = _llamar_groq(api_key, modelo, msg_retry, max_tokens)
                    hist_reciente.append({"role": "user", "content": mensaje_usuario})
                    hist_reciente.append({"role": "assistant", "content": resp_retry})
                    guardar_historial(hist_reciente)
                    return resp_retry, None
                except Exception as _e413:
                    limpiar_historial()
                    return "", f"Memoria ajustada automáticamente. Intenta de nuevo por favor."
            elif codigo == 422:
                return "", f"Error de formato (422): {detalle[:120]}"
            elif codigo == 429:
                return "", "Límite de Groq alcanzado. Espera unos segundos e intenta de nuevo."
            elif codigo == 503:
                return "", "Groq no está disponible ahora. Intenta en unos minutos."
            else:
                return "", f"Error HTTP {codigo} de Groq: {detalle[:100]}"
        except (KeyError, IndexError, ValueError) as e:
            return "", f"Respuesta inesperada de Groq: {str(e)[:100]}"
        except Exception as e:
            return "", f"Error inesperado: {str(e)[:120]}"

    # Si llegamos aquí, ningún modelo funcionó (todos dieron 404)
    return "", (
        f"Ningún modelo de IA disponible en este momento. "
        f"Verifica tu API Key de Groq en Configuración → IA. "
        f"Último error: {ultimo_error}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  LLAMADA ASÍNCRONA — para usar desde Kivy sin bloquear la UI
# ═══════════════════════════════════════════════════════════════════════════════

def obtener_respuesta_ia_async(mensaje: str, callback_ok, callback_error) -> None:
    """
    Llama a obtener_respuesta_ia en un hilo separado.
    callback_ok(respuesta_str)   — se llama si OK
    callback_error(error_str)    — se llama si hay error
    Ambos callbacks se ejecutan desde el hilo secundario;
    en Kivy usar Clock.schedule_once para actualizar UI.
    """
    def _tarea():
        resp, err = obtener_respuesta_ia(mensaje)
        if err:
            callback_error(err)
        else:
            callback_ok(resp)

    t = threading.Thread(target=_tarea, daemon=True)
    t.start()
