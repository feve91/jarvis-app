"""
JARVIS Mobile — Punto de entrada de la aplicación Kivy
"""

import sys
import io
import os
import threading

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("JARVIS.AI.Assistant.v2")
    except Exception:
        pass

# ── Redirigir stdout/stderr a devnull si corren sin consola (evita AllocConsole de Windows) ──
if sys.stdout is None or not hasattr(sys.stdout, 'buffer'):
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
else:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

if sys.stderr is None or not hasattr(sys.stderr, 'buffer'):
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
else:
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# ── Deshabilitar consola de Kivy y simulación multitouch ───────────────────────
os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.config import Config
Config.set('kivy', 'console_log', '0')
Config.set('kivy', 'log_enable', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('graphics', 'background_color', '0 0.02 0.08 1')

# ── Ícono de ventana / barra de tareas — DEBE ir antes de importar Window ────
import os as _os
_ASSETS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'assets')
_ICO    = _os.path.join(_ASSETS, 'jarvis_reactor_arc.ico')
if not _os.path.exists(_ICO):
    _ICO = _os.path.join(_ASSETS, 'jarvis_mascara_futurista_azul.ico')
if _os.path.exists(_ICO):
    Config.set('kivy', 'window_icon', _ICO)

from kivy.app import App

from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock

# ── Importar pantallas ─────────────────────────────────────────────────────────
from ui.chat_screen import ChatScreen
from ui.home_screen import HomeScreen, SplashScreen
from ui.settings_screen import SettingsScreen
from ui.agenda_screen import AgendaScreen, mostrar_popup_evento
from ui.docs_screen import DocsScreen

# ── Módulos de negocios y gestión ──────────────────────────────────────────────
from negocios.prestamos_screen   import PrestamosScreen
from negocios.parqueadero_screen import ParqueaderoScreen
from negocios.tenis_screen       import TenisScreen
from negocios.vehiculos_screen   import VehiculosScreen
from ui.prioridad_screen         import PrioridadScreen

# ── Configuración de ventana — responsive por tipo de dispositivo ────────────
if platform in ("android", "ios"):
    # Móvil/tablet: pantalla completa, Kivy gestiona el tamaño
    pass

else:
    # ── Detectar resolución real de pantalla (Windows/Linux/macOS) ────────────
    screen_w, screen_h = 1920, 1080   # fallback

    try:
        import ctypes
        # Forzar conciencia de DPI para obtener píxeles físicos reales
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # Per-Monitor DPI v2
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    except Exception:
        # Linux / macOS: intentar con tkinter
        try:
            import tkinter as _tk
            _r = _tk.Tk(); _r.withdraw()
            screen_w = _r.winfo_screenwidth()
            screen_h = _r.winfo_screenheight()
            _r.destroy()
        except Exception:
            pass

    # ── Clasificar dispositivo y calcular tamaño óptimo ───────────────────────
    #
    #  El objetivo es mantener una proporción de smartphone (9:19.5 ≈ 0.46)
    #  adaptando la altura a lo que cabe en pantalla con un margen decente.
    #
    ASPECT = 9 / 19.5          # Relación ancho/alto  (≈ 0.462)
    MARGIN = 0.90              # Usar el 90% de la altura disponible

    target_h = int(screen_h * MARGIN)
    target_w = int(target_h * ASPECT)

    # Si el ancho calculado supera el 45% de la pantalla, ajustar al ancho
    if target_w > screen_w * 0.45:
        target_w = int(screen_w * 0.45)
        target_h = int(target_w / ASPECT)

    # Límites mínimos y máximos para que la UI sea usable
    target_w = max(360, min(target_w, 560))
    target_h = max(620, min(target_h, 960))

    # Recalcular para mantener proporción si los límites lo alteraron
    if target_h > int(target_w / ASPECT * 1.05):   # si height quedó demasiado grande
        target_h = int(target_w / ASPECT)

    Window.size = (target_w, target_h)

    # ── Centrar la ventana en la pantalla ─────────────────────────────────────
    margin_top  = 30    # píxeles desde la barra de tareas/bordes
    win_left    = max(0, (screen_w - target_w) // 2)
    win_top     = max(margin_top, (screen_h - target_h) // 2)
    Window.left = win_left
    Window.top  = win_top

    print(f"[WINDOW] Pantalla: {screen_w}x{screen_h} → Ventana: {target_w}x{target_h} "
          f"centrada en ({win_left}, {win_top})")

# Igualar clearcolor con C_FONDO para que no haya diferencia de color
# entre el fondo SDL2 y el primer frame renderizado
Window.clearcolor = (0.00, 0.02, 0.08, 1)   # Azul oscuro = C_FONDO

# ── Instalar pygame si no está (para reproducir MP3 del TTS) ─────────────────
try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except Exception as _e:
    print(f"[PYGAME] No disponible: {_e}")


class JarvisApp(App):
    """Aplicación principal - nombre configurable desde settings."""

    @property
    def title(self):
        try:
            from jarvis_core import get_nombre_asistente
            return get_nombre_asistente("JARVIS")
        except Exception:
            return "JARVIS"

    # Íconos reales del proyecto original (en orden de preferencia)
    _iconos = [
        os.path.join(os.path.dirname(__file__), "assets", "jarvis_reactor_arc.ico"),
        os.path.join(os.path.dirname(__file__), "assets", "jarvis_mascara_futurista.ico"),
        os.path.join(os.path.dirname(__file__), "assets", "icon.png"),
    ]
    icon = next((r for r in _iconos if os.path.exists(r)), "")

    def build(self):
        # Solicitar permisos en Android
        if platform == "android":
            self._solicitar_permisos_android()

        # ── Fondo de circuitos LED (persiste en TODAS las pantallas) ──────────
        from kivy.uix.floatlayout import FloatLayout
        from ui.circuit_bg import CircuitBackground

        raiz = FloatLayout()

        # Líneas de circuito blancas — detrás de todo
        self._circuit = CircuitBackground(
            n_active=18,
            speed_range=(1.5, 5),
            color=(1.0, 1.0, 1.0),
            base_alpha=0.14,          # sutil: no tapa el contenido
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        raiz.add_widget(self._circuit)

        # ── Gestor de pantallas — Splash → Chat → Home → Settings ────────────
        sm = ScreenManager(transition=FadeTransition(duration=0.3))
        sm.add_widget(SplashScreen(name="splash"))      # Logo animado
        sm.add_widget(ChatScreen(name="chat"))           # Chat principal
        sm.add_widget(HomeScreen(name="home"))           # Dashboard
        sm.add_widget(SettingsScreen(name="settings"))  # Configuracion
        sm.add_widget(AgendaScreen(name="agenda"))       # Calendario
        sm.add_widget(DocsScreen(name="docs"))           # Documentacion
        sm.add_widget(PrestamosScreen(name="prestamos"))    # Módulo préstamos
        sm.add_widget(ParqueaderoScreen(name="parqueadero"))# Módulo parqueadero
        sm.add_widget(TenisScreen(name="tenis"))            # Módulo tenis
        sm.add_widget(PrioridadScreen(name="prioridad"))    # Módulo prioridad
        sm.add_widget(VehiculosScreen(name="vehiculos"))    # Módulo vehículos
        sm.current = "splash"   # Empieza con el logo

        raiz.add_widget(sm)

        # Verificar alarmas y eventos de agenda cada 30 segundos
        Clock.schedule_interval(self._verificar_eventos, 30)
        return raiz

    def on_start(self):
        """Se llama cuando la app está completamente cargada."""
        print("[JARVIS] App iniciada.")
        Clock.schedule_once(self._iniciar_servicio, 1)
        Clock.schedule_once(self._verificar_eventos, 5)
        # Forzar ícono del reactor en la barra de tareas de Windows
        Clock.schedule_once(self._forzar_icono_windows, 0.5)
        # Traer ventana al frente de todas las demás en pantalla (dos llamadas para asegurar)
        Clock.schedule_once(self._traer_al_frente_windows, 0.3)
        Clock.schedule_once(self._traer_al_frente_windows, 1.0)

    def _traer_al_frente_windows(self, dt):
        """Trae la ventana de JARVIS al primer plano de la pantalla en Windows bypassando restricciones de Windows 11."""
        try:
            from kivy.core.window import Window
            Window.raise_window()
        except Exception:
            pass

        try:
            if sys.platform == "win32":
                import ctypes, ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                found = ctypes.wintypes.HWND(0)

                def _enum_cb(h, _):
                    buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(h, buf, 256)
                    if "SDL" in buf.value:
                        found.value = h
                        return False
                    return True

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
                user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

                hwnd = found.value
                if hwnd:
                    user32.ShowWindow(hwnd, 9) # SW_RESTORE
                    user32.ShowWindow(hwnd, 5) # SW_SHOW

                    fore_hwnd = user32.GetForegroundWindow()
                    fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
                    app_thread = kernel32.GetCurrentThreadId()

                    if fore_thread and fore_thread != app_thread:
                        user32.AttachThreadInput(fore_thread, app_thread, True)
                        user32.BringWindowToTop(hwnd)
                        user32.SetForegroundWindow(hwnd)
                        user32.AttachThreadInput(fore_thread, app_thread, False)
                    else:
                        user32.BringWindowToTop(hwnd)
                        user32.SetForegroundWindow(hwnd)
                    print("[JARVIS] Ventana traída al frente con éxito (AttachThreadInput).")
        except Exception as e:
            print(f"[JARVIS] Error al traer ventana al frente: {e}")

    def _forzar_icono_windows(self, dt):
        """Fuerza el ícono del reactor en barra de tareas y título (Windows)."""
        try:
            import ctypes, ctypes.wintypes

            ico_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'assets', 'jarvis_reactor_arc.ico'
            )
            if not os.path.exists(ico_path):
                ico_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'assets', 'jarvis_mascara_futurista_azul.ico'
                )
            if not os.path.exists(ico_path):
                print("[JARVIS] Ícono no encontrado")
                return

            LR_LOADFROMFILE = 0x00000010
            LR_DEFAULTSIZE  = 0x00000040

            hicon_big = ctypes.windll.user32.LoadImageW(
                None, ico_path, 1, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
            )
            hicon_sm = ctypes.windll.user32.LoadImageW(
                None, ico_path, 1, 16, 16, LR_LOADFROMFILE
            )

            if not hicon_big:
                print("[JARVIS] LoadImageW falló — ícono no cargado")
                return

            # Buscar HWND por clase SDL_app (más fiable que por título)
            hwnd = None
            found = ctypes.wintypes.HWND(0)

            def _enum_cb(h, _):
                buf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(h, buf, 256)
                if 'SDL' in buf.value:
                    found.value = h
                    return False   # parar enumeración
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                              ctypes.wintypes.HWND,
                                              ctypes.wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
            hwnd = found.value

            if not hwnd:
                # último recurso: buscar por PID del proceso actual
                import os as _os
                pid = _os.getpid()
                def _enum_pid(h, _):
                    w_pid = ctypes.wintypes.DWORD(0)
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        h, ctypes.byref(w_pid)
                    )
                    if w_pid.value == pid and ctypes.windll.user32.IsWindowVisible(h):
                        found.value = h
                        return False
                    return True
                ctypes.windll.user32.EnumWindows(WNDENUMPROC(_enum_pid), 0)
                hwnd = found.value

            if not hwnd:
                print("[JARVIS] HWND no encontrado")
                return

            WM_SETICON     = 0x0080
            ICON_SMALL     = 0
            ICON_BIG       = 1
            GCLP_HICON     = -14
            GCLP_HICONSM   = -34

            # Aplicar al handle de ventana
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG,  hicon_big)
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_sm)

            # Aplicar a toda la clase de ventana (persiste aunque cambie el foco)
            ctypes.windll.user32.SetClassLongPtrW(hwnd, GCLP_HICON,   hicon_big)
            ctypes.windll.user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, hicon_sm)

            print(f"[JARVIS] Ícono reactor aplicado (hwnd={hwnd:#x})")

        except Exception as e:
            print(f"[JARVIS] Error icono: {e}")

    def _verificar_eventos(self, dt):
        """Revisa alarmas y eventos de agenda que ya son hora de mostrar."""
        try:
            from jarvis_core import cargar_memoria, guardar_memoria, calcular_proxima_ejecucion
            from datetime import datetime as _dt
            m   = cargar_memoria()
            ahora = _dt.now()
            vencidas = [a for a in m.get("alarmas", [])
                        if _dt.fromisoformat(a["fecha_hora"]) <= ahora]
            for alarm in vencidas:
                titulo  = f"ALARMA — {alarm.get('texto', 'Recordatorio')}"
                mensaje = _dt.fromisoformat(alarm["fecha_hora"]).strftime("%H:%M")
                Clock.schedule_once(lambda dt, t=titulo, ms=mensaje:
                                    mostrar_popup_evento(t, ms), 0)
            # Reprogramar recurrentes / eliminar vencidas
            nuevas = []
            for a in m.get("alarmas", []):
                if a in vencidas:
                    if a.get("recurrente"):
                        fh = _dt.fromisoformat(a["fecha_hora"])
                        sig = calcular_proxima_ejecucion(
                            a.get("tipo"), a.get("dias_semana", []),
                            fh.hour, fh.minute, ahora=ahora)
                        a["fecha_hora"] = sig.isoformat()
                        nuevas.append(a)
                else:
                    nuevas.append(a)
            m["alarmas"] = nuevas
            # Eventos de agenda de hoy que ya son hora
            hoy_str = ahora.strftime("%d/%m/%Y")
            for ev in m.get("agenda", []):
                if ev.get("fecha") == hoy_str and not ev.get("notificado"):
                    try:
                        hev = _dt.strptime(f"{hoy_str} {ev['hora']}", "%d/%m/%Y %H:%M")
                        if hev <= ahora:
                            Clock.schedule_once(lambda dt, t=ev["titulo"], h=ev["hora"]:
                                                mostrar_popup_evento(f"AGENDA — {t}", h), 0)
                            ev["notificado"] = True
                    except Exception:
                        pass
            guardar_memoria(m)
        except Exception as ex:
            print(f"[VERIFICAR] {ex}")

    def _iniciar_servicio(self, dt):
        """Inicia el Foreground Service de Android."""
        if platform == "android":
            try:
                from android import AndroidService
                self.service = AndroidService(
                    "JARVIS",
                    "Activo en segundo plano — Bot de Telegram y alarmas",
                )
                self.service.start("")
                print("[JARVIS] Servicio de fondo iniciado.")
            except Exception as e:
                print(f"[JARVIS] Error iniciando servicio: {e}")
                # Si el servicio falla, ejecutar Telegram en hilo del proceso principal
                self._iniciar_telegram_hilo()
        else:
            # En PC, ejecutar el servicio en un hilo normal para desarrollo
            self._iniciar_telegram_hilo()

    def _iniciar_telegram_hilo(self):
        """Ejecuta el servicio en un hilo con event loop propio."""
        threading.Thread(target=self._run_service_module, daemon=True).start()

    def _run_service_module(self):
        import asyncio
        import importlib.util
        import logging
        import os

        app_dir = os.path.dirname(os.path.abspath(__file__))
        service_path = os.path.join(app_dir, "service", "main.py")
        log_path     = os.path.join(app_dir, "jarvis_service.log")

        # ── Log a archivo para poder ver errores cuando corre sin consola ───
        fh = logging.FileHandler(log_path, encoding="utf-8", mode="w")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("[SVC] %(levelname)s — %(message)s"))
        logging.getLogger().addHandler(fh)

        def svc_print(msg):
            print(msg, flush=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")

        svc_print("[SERVICE] Hilo iniciado")

        # ── Event loop totalmente aislado del loop de Kivy ──────────────────
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            spec = importlib.util.spec_from_file_location("service_main", service_path)
            if not spec:
                svc_print("[SERVICE] ERROR: No se encontró service/main.py")
                return
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            svc_print("[SERVICE] Módulo cargado. Ejecutando main_service()...")
            loop.run_until_complete(mod.main_service())
        except Exception as e:
            svc_print(f"[SERVICE] ERROR en hilo: {e}")
            import traceback
            with open(log_path, "a", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        finally:
            try:
                loop.close()
            except Exception:
                pass
            svc_print("[SERVICE] Hilo terminado")



    def _solicitar_permisos_android(self):
        """Solicita permisos de Android en tiempo de ejecución."""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.INTERNET,
                Permission.RECEIVE_BOOT_COMPLETED,
                Permission.VIBRATE,
                Permission.POST_NOTIFICATIONS,
                Permission.FOREGROUND_SERVICE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        except Exception as e:
            print(f"[PERMISOS] Error: {e}")

    def on_pause(self):
        """Android llama esto cuando la app va a segundo plano.
        Devolver True mantiene el servicio corriendo."""
        return True

    def on_resume(self):
        """Android llama esto cuando la app vuelve al frente."""
        pass

    def on_stop(self):
        """Se llama cuando el usuario cierra la app.
        El servicio de fondo sigue corriendo."""
        print("[JARVIS] App cerrada. El servicio sigue activo en segundo plano.")


if __name__ == "__main__":
    try:
        JarvisApp().run()
    except Exception as e:
        import traceback
        from datetime import datetime
        log_file = os.path.join(os.path.dirname(__file__), "crash_main.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH {datetime.now()} ---\n")
            traceback.print_exc(file=f)
