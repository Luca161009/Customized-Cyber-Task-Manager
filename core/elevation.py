"""
core/elevation.py
-------------------
Verifica se il processo corrente ha privilegi amministrativi (necessari
per leggere temperature CPU/GPU e RPM ventole tramite WMI/LibreHardwareMonitor)
e permette di rilanciare l'app con elevazione UAC su richiesta esplicita
dell'utente (dal menu della tray), evitando di forzare un prompt UAC ad
ogni singolo avvio.
"""

import ctypes
import sys


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    """Rilancia l'eseguibile/script corrente con permessi elevati (UAC)."""
    if sys.platform != "win32":
        return
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{sys.argv[0]}" {params}', None, 1
    )
