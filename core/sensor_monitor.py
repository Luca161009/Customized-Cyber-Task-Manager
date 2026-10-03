"""
core/sensor_monitor.py
------------------------
Thread DEDICATO a temperature CPU/GPU e RPM ventole, separato dal resto
dell'hardware monitor.

Perché un thread a parte: le query WMI (usate per leggere i sensori da
LibreHardwareMonitor/OpenHardwareMonitor) passano per chiamate COM che,
a differenza delle chiamate psutil "normali", NON rilasciano sempre il
GIL di Python mentre sono in corso. Se una query così lenta (anche solo
200-800ms, dipende dal sistema) viene eseguita ogni 1-2 secondi insieme
al resto, blocca periodicamente l'intero interprete — inclusa la
renderizzazione 3D e l'interfaccia — dando la sensazione di "scatti a
intermittenza". Isolandola su un thread con un intervallo molto più
lento (di default 4 secondi, le temperature non cambiano comunque così
in fretta da giustificare letture più frequenti), l'eventuale micro-
blocco diventa raro e quasi impercettibile invece che continuo.
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


class SensorMonitor(QThread):
    sensors_ready = Signal(dict)

    def __init__(self, interval_ms: int = 4000, parent=None):
        super().__init__(parent)
        self.interval_s = interval_ms / 1000.0
        self._running = True
        self._paused = False

        self._wmi_sensors = None
        if IS_WINDOWS and wmi is not None:
            for namespace in ("root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor"):
                try:
                    self._wmi_sensors = wmi.WMI(namespace=namespace)
                    break
                except Exception:
                    continue

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
                    data = self._collect()
                    self.sensors_ready.emit(data)
                except Exception as exc:
                    print(f"[SensorMonitor] Errore durante il polling: {exc}")
            time.sleep(self.interval_s)

    # ------------------------------------------------------------------
    def _collect(self) -> dict:
        """
        Prova più fonti in cascata, ciascuna protetta da try/except
        indipendente, così un sensore bloccato da Windows non compromette
        gli altri né l'app:

        1) WMI LibreHardwareMonitor/OpenHardwareMonitor (fonte migliore,
           richiede l'app di terze parti avviata come admin)
        2) psutil.sensors_temperatures() / sensors_fans() (fallback nativo)

        Se nessuna fonte è disponibile, i valori restano `None`: la UI
        mostra una barra "spenta" invece di testo d'errore o numeri finti.
        """
        result = {"cpu_temp_c": None, "gpu_temp_c": None, "fans_rpm": []}

        if self._wmi_sensors is not None:
            try:
                sensors = self._wmi_sensors.Sensor()
                cpu_temps, gpu_temps, fans = [], [], []
                for s in sensors:
                    try:
                        sensor_type = s.SensorType
                        name = s.Name
                        value = s.Value
                    except Exception:
                        continue
                    if value is None:
                        continue
                    if sensor_type == "Temperature":
                        lname = name.lower()
                        if "cpu" in lname:
                            cpu_temps.append(value)
                        elif "gpu" in lname:
                            gpu_temps.append(value)
                    elif sensor_type == "Fan":
                        fans.append({"name": name, "rpm": round(value)})
                if cpu_temps:
                    result["cpu_temp_c"] = round(sum(cpu_temps) / len(cpu_temps), 1)
                if gpu_temps:
                    result["gpu_temp_c"] = round(sum(gpu_temps) / len(gpu_temps), 1)
                if fans:
                    result["fans_rpm"] = fans
            except Exception:
                pass

        if result["cpu_temp_c"] is None:
            try:
                temps = psutil.sensors_temperatures()
                for key, entries in temps.items():
                    lkey = key.lower()
                    for entry in entries:
                        if entry.current is None:
                            continue
                        if "cpu" in lkey or "core" in lkey or "package" in lkey:
                            result["cpu_temp_c"] = round(entry.current, 1)
                            break
                    if result["cpu_temp_c"] is not None:
                        break
            except Exception:
                pass

        if not result["fans_rpm"]:
            try:
                fans_data = psutil.sensors_fans()
                for key, entries in fans_data.items():
                    for entry in entries:
                        if entry.current:
                            result["fans_rpm"].append(
                                {"name": key, "rpm": round(entry.current)}
                            )
            except Exception:
                pass

        return result
