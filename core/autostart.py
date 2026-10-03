"""
core/autostart.py
-------------------
Attiva/disattiva l'avvio automatico all'accesso, con due meccanismi
completamente diversi a seconda del sistema operativo:

- WINDOWS: chiave di registro utente
  HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
  (non richiede privilegi amministrativi).

- LINUX: file .desktop nella cartella XDG autostart dell'utente
  (~/.config/autostart/), lo standard rispettato da GNOME, KDE, XFCE e
  dalla maggior parte degli altri ambienti desktop.

Se serve che l'app parta GIA' con permessi elevati (Windows, per i
sensori), vedi il Task Scheduler nel README. Su Linux i sensori
funzionano normalmente SENZA privilegi elevati se lm-sensors è
configurato (vedi README, sezione Sensori).
"""

import sys
from pathlib import Path

APP_NAME = "CyberTaskManager"
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg
    RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
else:
    AUTOSTART_DIR = Path.home() / ".config" / "autostart"
    DESKTOP_FILE = AUTOSTART_DIR / "cybertaskmanager.desktop"


def is_autostart_enabled() -> bool:
    if IS_WINDOWS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except FileNotFoundError:
            return False
    else:
        return DESKTOP_FILE.exists()


def set_autostart(enabled: bool, command: str) -> bool:
    """
    Windows: `command` è il percorso dell'eseguibile o
    'pythonw.exe "C:\\...\\main.py"' se eseguito da sorgente.
    Linux: `command` è tipo '/usr/bin/python3 /home/utente/CyberTaskManager/main.py'.
    """
    if IS_WINDOWS:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enabled:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError:
            return False
    else:
        try:
            if enabled:
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                DESKTOP_FILE.write_text(
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Name={APP_NAME}\n"
                    f"Exec={command}\n"
                    "X-GNOME-Autostart-enabled=true\n"
                    "Terminal=false\n"
                )
            else:
                if DESKTOP_FILE.exists():
                    DESKTOP_FILE.unlink()
            return True
        except OSError:
            return False
