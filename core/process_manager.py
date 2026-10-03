"""
core/process_manager.py
-------------------------
Elenco compatto dei processi attivi (PID, nome, %CPU, RAM, stato) e
funzione di terminazione sicura. Eseguito anch'esso in un QThread per
evitare micro-scatti sull'interfaccia quando i processi sono molti.
"""

import psutil
from PySide6.QtCore import QThread, Signal


class ProcessListWorker(QThread):
    processes_ready = Signal(list)

    def __init__(self, interval_ms: int = 2000, parent=None):
        super().__init__(parent)
        self.interval_s = interval_ms / 1000.0
        self._running = True
        self._paused = False
        # Priming: la prima lettura di cpu_percent per processo è sempre 0.0
        for p in psutil.process_iter(["pid"]):
            try:
                p.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        while self._running:
            if self._paused:
                self.msleep(int(self.interval_s * 1000))
                continue
            rows = []
            for p in psutil.process_iter(
                ["pid", "name", "memory_info", "status", "username", "create_time"]
            ):
                try:
                    cpu = p.cpu_percent(None)
                    mem_mb = p.info["memory_info"].rss / (1024 ** 2) if p.info["memory_info"] else 0
                    rows.append(
                        {
                            "pid": p.info["pid"],
                            "name": p.info["name"] or "?",
                            "cpu": round(cpu, 1),
                            "ram_mb": round(mem_mb, 1),
                            "status": p.info["status"],
                            "create_time": p.info["create_time"] or 0.0,
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            rows.sort(key=lambda r: r["cpu"], reverse=True)
            self.processes_ready.emit(rows)
            self.msleep(int(self.interval_s * 1000))


def kill_process(pid: int) -> tuple[bool, str]:
    """Termina un processo per PID. Ritorna (successo, messaggio)."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
        return True, f"Processo {pid} terminato."
    except psutil.NoSuchProcess:
        return False, "Il processo non esiste più."
    except psutil.AccessDenied:
        return False, "Permessi insufficienti (esegui l'app come amministratore)."
    except Exception as exc:
        return False, f"Errore: {exc}"
