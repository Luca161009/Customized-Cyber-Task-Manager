"""
core/hotkey_manager.py
-----------------------
Gestione della scorciatoia globale, con due implementazioni molto diverse
a seconda del sistema operativo:

- WINDOWS: `RegisterHotKey` nativo (via ctypes). Windows notifica
  direttamente la nostra finestra quando la combinazione viene premuta,
  ovunque ci si trovi nel sistema — non serve alcuna configurazione
  esterna da parte dell'utente.

- LINUX: non esiste un equivalente universale di RegisterHotKey che
  funzioni allo stesso modo su GNOME/KDE/XFCE senza privilegi elevati o
  librerie invasive (accesso diretto a /dev/input, che richiede root).
  L'approccio standard e "pulito" su Linux è l'opposto: l'app espone un
  piccolo comando (`python3 main.py --toggle`) che chi la usa collega
  MANUALMENTE a Win+Ctrl+T nelle Impostazioni Scorciatoie da tastiera
  del proprio ambiente desktop (GNOME/KDE/ecc.). Quel comando individua
  il processo residente in tray tramite un pidfile e gli invia il
  segnale Unix SIGUSR1, che la nostra app intercetta per mostrare/
  nascondere la finestra. Questo evita hook globali a basso livello,
  permessi di root, e funziona identico su qualunque desktop Linux.
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer

from core.config import APP_DATA_DIR

IS_WINDOWS = sys.platform == "win32"
PID_FILE = APP_DATA_DIR / "app.pid"


# ======================================================================
# WINDOWS: RegisterHotKey nativo
# ======================================================================
if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes
    from PySide6.QtCore import QAbstractNativeEventFilter

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    WM_HOTKEY = 0x0312
    HOTKEY_ID = 1

    _MOD_MAP = {"ALT": MOD_ALT, "CTRL": MOD_CONTROL, "CONTROL": MOD_CONTROL,
                "SHIFT": MOD_SHIFT, "WIN": MOD_WIN}

    def _vk_from_char(ch: str) -> int:
        return ord(ch.upper())

    class GlobalHotkeyFilter(QAbstractNativeEventFilter):
        def __init__(self, manager):
            super().__init__()
            self._manager = manager

        def nativeEventFilter(self, event_type, message):
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
            except Exception:
                return False, 0
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self._manager.hotkey_pressed.emit()
                return True, 0
            return False, 0

    class HotkeyManager(QObject):
        hotkey_pressed = Signal()

        def __init__(self, hwnd: int, modifiers: list, key: str):
            super().__init__()
            self._hwnd = hwnd
            self._registered = False
            self.set_combination(modifiers, key, register_now=False)

        def set_combination(self, modifiers, key, register_now=True):
            self._mod_flags = MOD_NOREPEAT
            for m in modifiers:
                self._mod_flags |= _MOD_MAP.get(m.upper(), 0)
            self._vk = _vk_from_char(key)
            if register_now:
                self.unregister()
                self.register()

        def register(self) -> bool:
            ok = ctypes.windll.user32.RegisterHotKey(
                self._hwnd, HOTKEY_ID, self._mod_flags, self._vk
            )
            self._registered = bool(ok)
            if not ok:
                print("[HotkeyManager] Impossibile registrare la hotkey (probabilmente già in uso).")
            return self._registered

        def unregister(self):
            if self._registered:
                ctypes.windll.user32.UnregisterHotKey(self._hwnd, HOTKEY_ID)
                self._registered = False


# ======================================================================
# LINUX: pidfile + segnale SIGUSR1
# ======================================================================
else:
    import signal

    class HotkeyManager(QObject):
        """
        Interfaccia compatibile con la versione Windows (stesso segnale
        `hotkey_pressed`, stessi metodi `register`/`unregister`/
        `set_combination`), ma il meccanismo è completamente diverso: qui
        si limita a scrivere un pidfile e ad ascoltare SIGUSR1.
        """

        hotkey_pressed = Signal()

        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self._registered = False
            # Timer "keepalive": senza di esso, l'event loop di Qt può
            # restare bloccato nell'attesa di eventi X11/Wayland per un
            # tempo indefinito, e Python controlla se ci sono segnali in
            # sospeso solo tra un'istruzione bytecode e l'altra. Questo
            # timer garantisce che l'interprete "respiri" abbastanza
            # spesso da notare il segnale quasi subito.
            self._keepalive = QTimer(self)
            self._keepalive.timeout.connect(lambda: None)
            self._keepalive.start(200)

        def set_combination(self, modifiers, key, register_now=True):
            # Su Linux la combinazione di tasti si imposta nelle
            # Impostazioni di sistema (Scorciatoie da tastiera), non qui:
            # questo metodo esiste solo per compatibilità con la UI delle
            # Impostazioni condivisa con la versione Windows.
            pass

        def register(self) -> bool:
            try:
                PID_FILE.parent.mkdir(parents=True, exist_ok=True)
                PID_FILE.write_text(str(os.getpid()))
                signal.signal(signal.SIGUSR1, self._on_signal)
                self._registered = True
            except Exception as exc:
                print(f"[HotkeyManager] Impossibile inizializzare il pidfile: {exc}")
                self._registered = False
            return self._registered

        def unregister(self):
            try:
                if PID_FILE.exists():
                    PID_FILE.unlink()
            except OSError:
                pass
            self._registered = False

        def _on_signal(self, signum, frame):
            self.hotkey_pressed.emit()

    class GlobalHotkeyFilter:
        """Non necessario su Linux: nessun filtro di eventi nativi da installare."""

        def __init__(self, *_args, **_kwargs):
            pass


def send_toggle_signal() -> bool:
    """
    Usata dal comando `python3 main.py --toggle` (da collegare alla
    scorciatoia da tastiera del proprio ambiente desktop): legge il
    pidfile dell'istanza residente e le invia SIGUSR1. Ritorna True se il
    segnale è stato inviato con successo.
    """
    if IS_WINDOWS:
        print("Questo comando serve solo su Linux; su Windows la hotkey è già globale e nativa.")
        return False
    import signal
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGUSR1)
        return True
    except (FileNotFoundError, ValueError):
        print("CyberTaskManager non risulta in esecuzione (pidfile assente o non valido).")
        return False
    except ProcessLookupError:
        print("Il processo registrato non esiste più: elimino il pidfile obsoleto.")
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        return False
