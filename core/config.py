"""
core/config.py
---------------
Gestione della configurazione persistente dell'applicazione (file JSON
salvato nella cartella utente). Contiene la combinazione di tasti per
la hotkey globale, la preferenza di avvio automatico e alcune opzioni
di refresh dei sensori.
"""

import json
import os
from pathlib import Path

APP_NAME = "CyberTaskManager"

# Cartella dati applicazione: %APPDATA%\CyberTaskManager su Windows,
# fallback su home utente per altri sistemi (utile in fase di sviluppo).
def _app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        path = Path(base) / APP_NAME
    else:
        path = Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


CONFIG_PATH = _app_data_dir() / "config.json"
APP_DATA_DIR = _app_data_dir()  # esposta per altri moduli (es. pidfile su Linux)

DEFAULT_CONFIG = {
    # Modificatori: combinazione fisica del tasto di scelta rapida globale.
    # Valori ammessi per i modificatori: WIN, CTRL, ALT, SHIFT
    "hotkey_modifiers": ["WIN", "CTRL"],
    "hotkey_key": "T",
    "start_with_windows": False,
    "hardware_refresh_ms": 1200,
    "process_refresh_ms": 2000,
    "start_minimized_to_tray": True,
}


class ConfigManager:
    """Carica/salva la configurazione in modo sicuro (fallback ai default)."""

    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.data.update(saved)
            except (json.JSONDecodeError, OSError):
                # File corrotto: si prosegue con i default senza bloccare l'app
                pass
        else:
            self.save()

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


config = ConfigManager()
