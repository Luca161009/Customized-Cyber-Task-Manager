"""
core/hardware_monitor.py
--------------------------
Raccolta dati hardware in un QThread separato per non bloccare mai la UI
(fondamentale per mantenere fluida l'animazione 3D e i grafici).

Fonti dati:
- CPU / RAM / Dischi -> psutil (multipiattaforma, nessun permesso speciale)
- GPU NVIDIA (anche doppia, es. integrata + dedicata) -> pynvml
- GPU generiche (nome/produttore) -> WMI (Win32_VideoController)
- Temperature CPU/GPU e RPM ventole -> namespace WMI
  "root\\LibreHardwareMonitor" (o "root\\OpenHardwareMonitor").
  Questi valori richiedono che LibreHardwareMonitor (o OpenHardwareMonitor)
  sia in esecuzione IN BACKGROUND CON PERMESSI AMMINISTRATIVI, perché
  l'accesso ai sensori SMBus/EC della scheda madre è protetto dal kernel.
  Se il provider WMI non è disponibile, i campi vengono mostrati come "N/D"
  invece di far crashare l'app.
"""

import sys
import time

import psutil
from PySide6.QtCore import QThread, Signal

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import wmi
    except ImportError:
        wmi = None
else:
    wmi = None

# NOTA: le temperature/ventole (via WMI/LibreHardwareMonitor) sono state
# spostate in core/sensor_monitor.py, su un thread dedicato più lento.
# Le query COM/WMI possono bloccare il GIL di Python per centinaia di ms;
# tenerle qui, nel loop veloce di CPU/RAM, causava scatti periodici
# nell'intera interfaccia (inclusa l'animazione 3D).

try:
    import pynvml

    pynvml.nvmlInit()
    _NVML_OK = True
except Exception:
    _NVML_OK = False


class HardwareMonitor(QThread):
    """Esegue il polling periodico e pubblica i dati con il segnale `stats_ready`."""

    stats_ready = Signal(dict)

    def __init__(self, interval_ms: int = 1200, parent=None):
        super().__init__(parent)
        self.interval_s = interval_ms / 1000.0
        self._running = True
        self._paused = False

        # Connessione WMI solo per i NOMI delle GPU (veloce, non i sensori)
        self._wmi_video = None
        if IS_WINDOWS and wmi is not None:
            try:
                self._wmi_video = wmi.WMI()
            except Exception:
                self._wmi_video = None

        # Priming di psutil.cpu_percent (la prima chiamata restituisce sempre 0.0)
        psutil.cpu_percent(percpu=True)

    def stop(self):
        self._running = False

    def pause(self):
        """Sospende il polling (nessuna chiamata a WMI/NVML/psutil) quando
        la finestra è nascosta: l'app resta residente solo per ascoltare
        la hotkey, senza consumare risorse."""
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        while self._running:
            if not self._paused:
                try:
                    data = self._collect()
                    self.stats_ready.emit(data)
                except Exception as exc:  # non deve mai uccidere il thread
                    print(f"[HardwareMonitor] Errore durante il polling: {exc}")
            time.sleep(self.interval_s)

    # ------------------------------------------------------------------
    def _collect(self) -> dict:
        return {
            "cpu": self._collect_cpu(),
            "ram": self._collect_ram(),
            "disks": self._collect_disks(),
            "gpus": self._collect_gpus(),
        }

    def _collect_cpu(self) -> dict:
        freq = psutil.cpu_freq()
        return {
            "percent_total": psutil.cpu_percent(percpu=False),
            "percent_per_core": psutil.cpu_percent(percpu=True),
            "freq_current_mhz": round(freq.current, 0) if freq else None,
            "freq_max_mhz": round(freq.max, 0) if freq and freq.max else None,
            "core_count_logical": psutil.cpu_count(logical=True),
            "core_count_physical": psutil.cpu_count(logical=False),
        }

    def _collect_ram(self) -> dict:
        vm = psutil.virtual_memory()
        return {
            "percent": vm.percent,
            "used_gb": round(vm.used / (1024 ** 3), 2),
            "total_gb": round(vm.total / (1024 ** 3), 2),
        }

    def _collect_disks(self) -> list[dict]:
        disks = []
        for part in psutil.disk_partitions(all=False):
            if IS_WINDOWS and ("cdrom" in part.opts or part.fstype == ""):
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "percent": usage.percent,
                }
            )
        return disks

    def _collect_gpus(self) -> list[dict]:
        gpus = []

        # --- GPU NVIDIA (dettagliate: uso, memoria, temperatura, clock) ---
        if _NVML_OK:
            try:
                count = pynvml.nvmlDeviceGetCount()
                for i in range(count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode("utf-8", errors="ignore")
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    try:
                        temp = pynvml.nvmlDeviceGetTemperature(
                            handle, pynvml.NVML_TEMPERATURE_GPU
                        )
                    except Exception:
                        temp = None
                    gpus.append(
                        {
                            "name": name,
                            "load_percent": util.gpu,
                            "mem_used_gb": round(mem.used / (1024 ** 3), 2),
                            "mem_total_gb": round(mem.total / (1024 ** 3), 2),
                            "temp_c": temp,
                            "source": "NVML",
                        }
                    )
            except Exception:
                pass

        # --- Fallback / GPU integrate (Intel/AMD) via WMI: solo nome (Windows) ---
        if IS_WINDOWS and self._wmi_video is not None:
            try:
                already = {g["name"] for g in gpus}
                for controller in self._wmi_video.Win32_VideoController():
                    name = controller.Name or "GPU sconosciuta"
                    if name in already:
                        continue
                    gpus.append(
                        {
                            "name": name,
                            "load_percent": None,  # non esposto in modo affidabile via WMI standard
                            "mem_used_gb": None,
                            "mem_total_gb": (
                                round(controller.AdapterRAM / (1024 ** 3), 2)
                                if getattr(controller, "AdapterRAM", None)
                                else None
                            ),
                            "temp_c": None,
                            "source": "WMI",
                        }
                    )
            except Exception:
                pass

        # --- Fallback / GPU integrate (Intel/AMD) via lspci: solo nome (Linux) ---
        if not IS_WINDOWS and not gpus:
            try:
                import subprocess
                proc = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=2
                )
                for line in proc.stdout.splitlines():
                    lline = line.lower()
                    if "vga compatible controller" in lline or "3d controller" in lline:
                        # Formato tipico: "01:00.0 VGA compatible controller: NVIDIA Corporation ..."
                        name = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
                        gpus.append(
                            {
                                "name": name or "GPU sconosciuta",
                                "load_percent": None,  # lspci non espone carico/VRAM in uso
                                "mem_used_gb": None,
                                "mem_total_gb": None,
                                "temp_c": None,
                                "source": "lspci",
                            }
                        )
            except (FileNotFoundError, OSError):
                pass
            except Exception:
                pass

        if not gpus:
            gpus.append(
                {
                    "name": "Nessuna GPU rilevata",
                    "load_percent": None,
                    "mem_used_gb": None,
                    "mem_total_gb": None,
                    "temp_c": None,
                    "source": "N/D",
                }
            )
        return gpus
