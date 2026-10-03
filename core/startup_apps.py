# core/startup_apps.py
"""
Elenco (sola lettura) delle applicazioni impostate per l'avvio
automatico di Windows: chiavi di registro Run/RunOnce (utente e
macchina) e le scorciatoie nella cartella "Esecuzione automatica"
(sia per l'utente corrente sia per tutti gli utenti).

Interamente avvolto in try/except a più livelli: se una chiave di
registro o una cartella non è accessibile (permessi, chiave assente),
viene semplicemente saltata, senza generare errori.

Nota: è una lista informativa, non permette di disattivare le voci
(a differenza della scheda "Avvio" del Task Manager di Windows, che
richiede API più invasive) — pensata come pannello di consultazione
rapida nella dashboard.
"""

import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg

    _RUN_KEYS = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
else:
    _RUN_KEYS = []
    _LINUX_AUTOSTART_DIRS = [
        Path.home() / ".config" / "autostart",
        Path("/etc/xdg/autostart"),
    ]


def _read_registry_run_keys() -> list:
    apps = []
    if not IS_WINDOWS:
        return apps
    for hive, path in _RUN_KEYS:
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        apps.append({"name": name, "command": str(value), "source": "Registro"})
                        i += 1
                    except OSError:
                        break  # fine delle voci in questa chiave
        except OSError:
            continue  # chiave assente o non accessibile: si passa oltre
    return apps


def _read_startup_folders() -> list:
    apps = []
    folders = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        folders.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup"))
    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        folders.append(os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs\Startup"))

    for folder in folders:
        try:
            for fname in os.listdir(folder):
                if fname.lower().endswith((".lnk", ".exe", ".bat", ".url")):
                    apps.append({
                        "name": os.path.splitext(fname)[0],
                        "command": os.path.join(folder, fname),
                        "source": "Cartella avvio",
                    })
        except OSError:
            continue
    return apps


def _read_linux_autostart_desktop_files() -> list:
    """
    Legge i file .desktop in ~/.config/autostart/ e /etc/xdg/autostart/
    (standard XDG rispettato da GNOME/KDE/XFCE). Parsing manuale e
    volutamente tollerante: un file .desktop malformato viene semplicemente
    saltato, non blocca la lettura degli altri.
    """
    apps = []
    for folder in _LINUX_AUTOSTART_DIRS:
        try:
            if not folder.is_dir():
                continue
            for entry in folder.glob("*.desktop"):
                try:
                    text = entry.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                name = None
                hidden = False
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("Name=") and name is None:
                        name = line.split("=", 1)[1].strip()
                    elif line.startswith("Hidden=") and line.split("=", 1)[1].strip().lower() == "true":
                        hidden = True
                    elif (
                        line.startswith("X-GNOME-Autostart-enabled=")
                        and line.split("=", 1)[1].strip().lower() == "false"
                    ):
                        hidden = True

                if hidden or not name:
                    continue
                apps.append({"name": name, "command": str(entry), "source": "Autostart XDG"})
        except OSError:
            continue
    return apps


def list_startup_apps() -> list:
    """Ritorna la lista delle app in avvio automatico. Non lancia mai eccezioni."""
    try:
        if IS_WINDOWS:
            apps = _read_registry_run_keys() + _read_startup_folders()
        else:
            apps = _read_linux_autostart_desktop_files()
    except Exception:
        return []

    seen = set()
    unique = []
    for app in apps:
        key = app["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(app)
    return unique
