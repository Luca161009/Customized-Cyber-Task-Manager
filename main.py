#!/usr/bin/env python3
"""
main.py
========
CyberTaskManager — Task Manager Cyberpunk a tutto schermo (build Linux).

Avvio normale:
    python3 main.py

Su Linux non esiste un equivalente diretto della RegisterHotKey di
Windows: la combinazione Win+Ctrl+T va configurata come scorciatoia
personalizzata nel proprio ambiente desktop (GNOME/KDE/XFCE...), puntata
a questo stesso comando con un argomento speciale:

    python3 main.py --toggle

Quel comando non apre una nuova istanza: trova quella già in esecuzione
in system tray e le dice di mostrarsi/nascondersi. Le istruzioni
dettagliate per configurare la scorciatoia sono nel README.md.
"""

import sys

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox

from core.config import config
from core.hotkey_manager import HotkeyManager, GlobalHotkeyFilter, send_toggle_signal
from ui.main_window import MainWindow
from ui.tray_app import TrayApplication

IS_WINDOWS = sys.platform == "win32"
SINGLE_INSTANCE_KEY = "CyberTaskManager-SingleInstance-9F3A21"


def ensure_single_instance() -> QSharedMemory:
    """
    Impedisce che vengano avviate più istanze contemporaneamente
    (altrimenti si registrerebbero hotkey/pidfile duplicati in conflitto).
    """
    shared_mem = QSharedMemory(SINGLE_INSTANCE_KEY)
    if shared_mem.attach():
        QMessageBox.warning(
            None,
            "CyberTaskManager",
            "L'applicazione è già in esecuzione (controlla la system tray).",
        )
        sys.exit(0)
    shared_mem.create(1)
    return shared_mem


def main():
    # --toggle: comando leggerissimo pensato per essere collegato alla
    # scorciatoia da tastiera del desktop environment (solo Linux). Non
    # crea nessuna finestra, nessun QApplication: legge il pidfile e
    # invia il segnale, poi esce subito.
    if not IS_WINDOWS and len(sys.argv) > 1 and sys.argv[1] == "--toggle":
        send_toggle_signal()
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # l'app resta viva anche a finestra chiusa

    shared_mem = ensure_single_instance()  # noqa: F841 (mantenere in vita per tutta la sessione)

    main_window = MainWindow()
    if not config.get("start_minimized_to_tray", True):
        main_window.showFullScreen()

    if IS_WINDOWS:
        # Widget invisibile: serve solo a fornire un HWND nativo valido a
        # cui agganciare la RegisterHotKey di Windows.
        hidden_host = QWidget()
        hidden_host.resize(0, 0)
        hidden_host.move(-10000, -10000)
        hidden_host.show()
        hidden_host.hide()
        hwnd = int(hidden_host.winId())
        hotkey_manager = HotkeyManager(
            hwnd=hwnd,
            modifiers=config.get("hotkey_modifiers", ["WIN", "CTRL"]),
            key=config.get("hotkey_key", "T"),
        )
        hotkey_manager.register()
        native_filter = GlobalHotkeyFilter(hotkey_manager)
        app.installNativeEventFilter(native_filter)
    else:
        # Linux: nessun HWND, nessun filtro di eventi nativi. Il
        # meccanismo è pidfile + SIGUSR1 (vedi core/hotkey_manager.py).
        hotkey_manager = HotkeyManager()
        hotkey_manager.register()

    hotkey_manager.hotkey_pressed.connect(main_window.toggle_visibility)

    tray = TrayApplication(app, main_window, hotkey_manager)  # noqa: F841

    exit_code = app.exec()

    hotkey_manager.unregister()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
