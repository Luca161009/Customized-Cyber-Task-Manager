# core/wifi_monitor.py
"""
Stato del Wi-Fi (SSID connesso e qualità del segnale %) letto tramite
il comando di sistema `netsh wlan show interfaces`, disponibile su
qualunque Windows senza librerie aggiuntive.

Interamente avvolto in try/except: se non c'è una scheda Wi-Fi, se è
spenta/disattivata, o se il comando fallisce per qualsiasi motivo, il
monitor restituisce semplicemente dati vuoti invece di generare un
errore o bloccare l'app.

IMPORTANTE: il sottoprocesso viene lanciato con CREATE_NO_WINDOW. Senza
questo flag, un `subprocess` avviato da un'app senza console (come
pythonw.exe) può far comparire una finestra nera lampeggiante ad ogni
lettura — esattamente ciò che l'intero progetto vuole evitare.
"""

"""
core/wifi_monitor.py
----------------------
Stato del Wi-Fi (SSID connesso e qualità del segnale %), con due
implementazioni diverse a seconda del sistema operativo:

- WINDOWS: comando `netsh wlan show interfaces`.
- LINUX: prova prima `nmcli` (NetworkManager, il gestore di rete di
  default su Debian con GNOME), e se non è disponibile prova `iw` come
  fallback (comune su installazioni minimali senza NetworkManager).

Interamente avvolto in try/except a più livelli: se non c'è una scheda
Wi-Fi, se è spenta/disattivata, o se nessuno dei comandi è disponibile,
il monitor restituisce semplicemente dati vuoti invece di generare un
errore o bloccare l'app.

Su Windows, il sottoprocesso viene lanciato con CREATE_NO_WINDOW: senza
questo flag, un `subprocess` avviato da un'app senza console (come
pythonw.exe) può far comparire una finestra nera lampeggiante ad ogni
lettura — esattamente ciò che l'intero progetto vuole evitare. Su Linux
questo problema non esiste (nessuna console "nera" da mostrare).
"""

import re
import subprocess
import sys
import time

from PySide6.QtCore import QThread, Signal

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000

_SSID_RE = re.compile(r"^\s*SSID\s*:\s*(.+)$", re.MULTILINE)
# "Segnale" in Windows in italiano, "Signal" in Windows in inglese
_SIGNAL_RE = re.compile(r"^\s*(?:Segnale|Signal)\s*:\s*(\d+)\s*%", re.MULTILINE)


def _query_wifi_windows() -> dict:
    result = {"connected": False, "ssid": None, "signal_percent": None}
    try:
        proc = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=2,
            creationflags=CREATE_NO_WINDOW,
        )
        output = proc.stdout or ""
    except Exception:
        return result

    ssid_match = _SSID_RE.search(output)
    signal_match = _SIGNAL_RE.search(output)

    if ssid_match:
        ssid = ssid_match.group(1).strip()
        if ssid:
            result["ssid"] = ssid
            result["connected"] = True
    if signal_match:
        try:
            result["signal_percent"] = int(signal_match.group(1))
        except ValueError:
            pass
    return result


def _query_wifi_linux() -> dict:
    result = {"connected": False, "ssid": None, "signal_percent": None}

    # --- Metodo 1: nmcli (NetworkManager) ---
    try:
        proc = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"],
            capture_output=True, text=True, timeout=2,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[0] == "yes":
                    ssid = parts[1].strip()
                    if ssid:
                        result["connected"] = True
                        result["ssid"] = ssid
                        try:
                            result["signal_percent"] = int(parts[2])
                        except ValueError:
                            pass
                    return result
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass
    except Exception:
        pass

    # --- Metodo 2 (fallback): iw, per sistemi senza NetworkManager ---
    try:
        iface = None
        proc = subprocess.run(["iw", "dev"], capture_output=True, text=True, timeout=2)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("Interface"):
                iface = line.split()[1]
                break
        if iface:
            proc = subprocess.run(
                ["iw", "dev", iface, "link"], capture_output=True, text=True, timeout=2
            )
            output = proc.stdout
            if output and "Not connected" not in output:
                ssid_match = re.search(r"^\s*SSID:\s*(.+)$", output, re.MULTILINE)
                signal_match = re.search(r"signal:\s*(-?\d+)\s*dBm", output)
                if ssid_match:
                    result["connected"] = True
                    result["ssid"] = ssid_match.group(1).strip()
                if signal_match:
                    dbm = int(signal_match.group(1))
                    # Conversione approssimata dBm -> percentuale (scala comune)
                    result["signal_percent"] = max(0, min(100, 2 * (dbm + 100)))
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass
    except Exception:
        pass

    return result


def _query_wifi() -> dict:
    if IS_WINDOWS:
        return _query_wifi_windows()
    return _query_wifi_linux()


class WifiMonitor(QThread):
    status_ready = Signal(dict)

    def __init__(self, interval_ms: int = 2500, parent=None):
        super().__init__(parent)
        self.interval_s = interval_ms / 1000.0
        self._running = True
        self._paused = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            if not self._paused:
                try:
                    status = _query_wifi()
                except Exception:
                    status = {"connected": False, "ssid": None, "signal_percent": None}
                self.status_ready.emit(status)
            time.sleep(self.interval_s)
