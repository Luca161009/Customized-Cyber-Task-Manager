# ui/main_window.py
"""
Finestra principale fullscreen.

Layout (dall'alto in basso):
  - Header: titolo a sinistra, scritta personalizzata centrata,
    orario/data + pulsante minimizza a destra.
  - Riga superiore: MIC + SISTEMA (audio) affiancati al modello 3D,
    poi spazio libero, poi il pannello Wi-Fi in alto a destra.
  - CPU / RAM con grafici a linee.
  - SSD / GPU0 / GPU1 / Temperature+Ventole in un'unica riga compatta.
  - In basso: colonna sinistra con "Cronologia Applicazioni" e "App di
    Avvio", e a destra la tabella processi (più stretta, più spazio
    complessivo a tutta questa sezione).

Gestione "risorse a riposo": tutti i worker (hardware veloce, sensori
lenti, processi, audio, wifi) partono già avviati ma IN PAUSA finché la
finestra non viene mostrata (hotkey Win+Ctrl+T), e tornano in pausa non
appena la finestra si nasconde di nuovo.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox, QAbstractItemView, QSizePolicy, QListWidget
)

from core.hardware_monitor import HardwareMonitor
from core.sensor_monitor import SensorMonitor
from core.process_manager import ProcessListWorker, kill_process
from core.audio_monitor import AudioMonitor
from core.wifi_monitor import WifiMonitor
from core.startup_apps import list_startup_apps
from core.config import config
from ui.gauge_widget import MetricCard
from ui.chart_widget import NeonLineChart
from ui.temp_bar_widget import TemperatureBar
from ui.audio_widget import AudioEqualizerBar
from ui.laptop_widget import LaptopShowroomWidget
from ui.wifi_widget import WifiPanel
from ui.styles import QSS, NEON_BLUE


def _panel(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    """Pannello standard con titolo opzionale, riutilizzato ovunque."""
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 8, 12, 10)
    layout.setSpacing(6)
    if title:
        label = QLabel(title)
        label.setObjectName("panelTitle")
        layout.addWidget(label)
    return frame, layout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CYBER // TASK MANAGER")
        self.setStyleSheet(QSS)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self._build_ui()
        self._create_workers()  # creati e avviati, ma in pausa da subito
        self._load_startup_apps()

        QShortcut(QKeySequence("Esc"), self, activated=self.hide)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 12, 20, 14)
        root.setSpacing(8)

        # ================= HEADER =================
        # Titolo a sinistra; scritta personalizzata ESATTAMENTE al centro
        # (due stretch identici la circondano, indipendentemente dalla
        # larghezza del titolo e del gruppo orario/pulsante); orario,
        # data e pulsante minimizza raggruppati a destra.
        header = QHBoxLayout()
        title = QLabel("⟦ CYBER TASK MANAGER ⟧")
        title.setStyleSheet(f"color:{NEON_BLUE}; font-size:18px; font-weight:bold; letter-spacing:3px;")
        header.addWidget(title)

        header.addStretch(1)
        owner_label = QLabel("LAPTOP WORKSTATION FUJITSU CELSIUS DI MICKY")
        owner_label.setStyleSheet(f"color:{NEON_BLUE}; font-size:13px; letter-spacing:1px; font-weight:bold;")
        header.addWidget(owner_label)
        header.addStretch(1)

        right_group = QHBoxLayout()
        right_group.setSpacing(14)
        datetime_box = QVBoxLayout()
        datetime_box.setSpacing(0)
        self.clock_label = QLabel("--:--:--")
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setAlignment(Qt.AlignRight)
        self.date_label = QLabel("")
        self.date_label.setObjectName("dimLabel")
        self.date_label.setAlignment(Qt.AlignRight)
        datetime_box.addWidget(self.clock_label)
        datetime_box.addWidget(self.date_label)
        right_group.addLayout(datetime_box)

        self.btn_hide = QPushButton("MINIMIZZA [ESC]")
        self.btn_hide.clicked.connect(self.hide)
        right_group.addWidget(self.btn_hide)
        header.addLayout(right_group)
        root.addLayout(header)

        # ================= RIGA SUPERIORE =================
        # Layout a 3 "colonne" con la QUALE il pannello 3D è garantito
        # SEMPRE al centro esatto della riga: le colonne laterali (audio a
        # sinistra, wifi a destra) ricevono lo STESSO stretch factor, quindi
        # Qt le forza alla stessa larghezza qualunque sia il loro contenuto
        # — a differenza di un HBoxLayout con solo uno stretch da un lato,
        # che centra il 3D solo rispetto ai vicini, non rispetto allo schermo.
        top_row = QGridLayout()
        top_row.setHorizontalSpacing(10)
        top_row.setColumnStretch(0, 1)  # colonna sinistra (audio)
        top_row.setColumnStretch(1, 0)  # colonna centrale (3D): dimensione naturale
        top_row.setColumnStretch(2, 1)  # colonna destra (wifi) — STESSO stretch della 0

        audio_group = QHBoxLayout()
        audio_group.setSpacing(8)

        audio_mic_frame, audio_mic_layout = _panel("AUDIO — MIC INTERNO")
        self.audio_mic_bar = AudioEqualizerBar("MIC")
        audio_mic_layout.addWidget(self.audio_mic_bar)
        audio_mic_frame.setFixedWidth(240)
        audio_mic_frame.setMaximumHeight(120)
        audio_group.addWidget(audio_mic_frame)

        audio_sys_frame, audio_sys_layout = _panel("AUDIO — SISTEMA (OUTPUT)")
        self.audio_sys_bar = AudioEqualizerBar("OUT")
        audio_sys_layout.addWidget(self.audio_sys_bar)
        audio_sys_frame.setFixedWidth(240)
        audio_sys_frame.setMaximumHeight(120)
        audio_group.addWidget(audio_sys_frame)

        audio_group_widget = QWidget()
        audio_group_widget.setLayout(audio_group)
        top_row.addWidget(audio_group_widget, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)

        showroom_frame, showroom_layout = _panel("WORKSTATION 3D // LIVE")
        showroom_layout.setContentsMargins(4, 6, 4, 4)
        self.laptop_widget = LaptopShowroomWidget()
        showroom_layout.addWidget(self.laptop_widget)
        showroom_frame.setFixedSize(400, 240)
        top_row.addWidget(showroom_frame, 0, 1, Qt.AlignCenter)

        wifi_frame, wifi_layout = _panel("RETE WI-FI")
        self.wifi_panel = WifiPanel()
        wifi_layout.addWidget(self.wifi_panel)
        wifi_frame.setFixedWidth(260)
        wifi_frame.setMaximumHeight(120)
        top_row.addWidget(wifi_frame, 0, 2, Qt.AlignRight | Qt.AlignVCenter)

        root.addLayout(top_row)

        # ================= CPU / RAM CON GRAFICI =================
        chart_row = QHBoxLayout()
        chart_row.setSpacing(12)

        self.cpu_frame, cpu_layout = _panel("CPU")
        cpu_head = QHBoxLayout()
        self.cpu_value_label = QLabel("--%")
        self.cpu_value_label.setObjectName("bigMetric")
        cpu_head.addWidget(self.cpu_value_label)
        cpu_head.addStretch()
        self.cpu_sub_label = QLabel("")
        self.cpu_sub_label.setObjectName("dimLabel")
        cpu_head.addWidget(self.cpu_sub_label)
        cpu_layout.addLayout(cpu_head)
        self.cpu_chart = NeonLineChart(color="#00E5FF")
        cpu_layout.addWidget(self.cpu_chart)
        self.cpu_extra_label = QLabel("")
        self.cpu_extra_label.setObjectName("dimLabel")
        cpu_layout.addWidget(self.cpu_extra_label)
        chart_row.addWidget(self.cpu_frame, stretch=1)

        self.ram_frame, ram_layout = _panel("RAM")
        ram_head = QHBoxLayout()
        self.ram_value_label = QLabel("--%")
        self.ram_value_label.setObjectName("bigMetric")
        ram_head.addWidget(self.ram_value_label)
        ram_head.addStretch()
        self.ram_sub_label = QLabel("")
        self.ram_sub_label.setObjectName("dimLabel")
        ram_head.addWidget(self.ram_sub_label)
        ram_layout.addLayout(ram_head)
        self.ram_chart = NeonLineChart(color="#00E5FF")
        ram_layout.addWidget(self.ram_chart)
        chart_row.addWidget(self.ram_frame, stretch=1)

        root.addLayout(chart_row)

        # ================= SSD / GPU / TEMPERATURE — RIGA COMPATTA =================
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)
        for col in range(5):
            metrics_grid.setColumnStretch(col, 1)

        self.card_disk = MetricCard("SSD / DISCO")
        self.card_gpu0 = MetricCard("GPU 0")
        self.card_gpu1 = MetricCard("GPU 1")
        metrics_grid.addWidget(self.card_disk, 0, 0)
        metrics_grid.addWidget(self.card_gpu0, 0, 1)
        metrics_grid.addWidget(self.card_gpu1, 0, 2)

        sensors_frame, sensors_layout = _panel("TEMP / VENTOLE")
        sensors_row = QHBoxLayout()
        sensors_row.setSpacing(14)
        self.temp_cpu_bar = TemperatureBar("CPU")
        self.temp_gpu_bar = TemperatureBar("GPU")
        sensors_row.addWidget(self.temp_cpu_bar)
        sensors_row.addWidget(self.temp_gpu_bar)
        self.fans_label = QLabel("Ventole: —")
        self.fans_label.setObjectName("dimLabel")
        self.fans_label.setWordWrap(True)
        self.fans_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sensors_row.addWidget(self.fans_label, stretch=1)
        sensors_layout.addLayout(sensors_row)
        metrics_grid.addWidget(sensors_frame, 0, 3, 1, 2)  # doppia larghezza, stessa altezza

        root.addLayout(metrics_grid)

        # ================= SEZIONE INFERIORE =================
        # Colonna sinistra: Cronologia Applicazioni + App di Avvio.
        # Tabella processi più stretta, spostata a destra.
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        history_frame, history_layout = _panel("CRONOLOGIA APPLICAZIONI")
        self.history_list = QListWidget()
        self.history_list.setObjectName("compactList")
        history_layout.addWidget(self.history_list)
        left_col.addWidget(history_frame, stretch=1)

        startup_frame, startup_layout = _panel("APP DI AVVIO")
        self.startup_list = QListWidget()
        self.startup_list.setObjectName("compactList")
        startup_layout.addWidget(self.startup_list)
        left_col.addWidget(startup_frame, stretch=1)

        left_col_widget = QWidget()
        left_col_widget.setLayout(left_col)
        left_col_widget.setFixedWidth(320)
        bottom_row.addWidget(left_col_widget)

        proc_frame, proc_layout = _panel()
        proc_title_row = QHBoxLayout()
        proc_title = QLabel("PROCESSI ATTIVI")
        proc_title.setObjectName("panelTitle")
        proc_title_row.addWidget(proc_title)
        proc_title_row.addStretch()
        self.btn_kill = QPushButton("TERMINA PROCESSO")
        self.btn_kill.setObjectName("dangerButton")
        self.btn_kill.clicked.connect(self._on_kill_clicked)
        proc_title_row.addWidget(self.btn_kill)
        proc_layout.addLayout(proc_title_row)

        self.process_table = QTableWidget(0, 5)
        self.process_table.setHorizontalHeaderLabels(["PID", "Nome", "CPU %", "RAM (MB)", "Stato"])
        self.process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.process_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.process_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.process_table.verticalHeader().setVisible(False)
        self.process_table.verticalHeader().setDefaultSectionSize(20)
        self.process_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        proc_layout.addWidget(self.process_table)
        bottom_row.addWidget(proc_frame, stretch=1)

        # Molto più spazio a tutta questa sezione rispetto al resto
        root.addLayout(bottom_row, stretch=6)

    # ------------------------------------------------------------------
    def _create_workers(self):
        """
        I worker vengono avviati subito (QThread.start()) ma restano in
        pausa: da residente in tray l'app non fa alcun polling. Si
        "risvegliano" solo quando la finestra diventa visibile.
        """
        self.hw_monitor = HardwareMonitor(interval_ms=config.get("hardware_refresh_ms", 1200))
        self.hw_monitor.stats_ready.connect(self._on_stats)
        self.hw_monitor.pause()
        self.hw_monitor.start()

        # Thread separato e più lento per i sensori (temp/ventole): vedi
        # core/sensor_monitor.py per il motivo (query WMI/COM lente che
        # altrimenti causerebbero scatti periodici nell'interfaccia).
        self.sensor_monitor = SensorMonitor(interval_ms=4000)
        self.sensor_monitor.sensors_ready.connect(self._on_sensors)
        self.sensor_monitor.pause()
        self.sensor_monitor.start()

        self.proc_worker = ProcessListWorker(interval_ms=config.get("process_refresh_ms", 2000))
        self.proc_worker.processes_ready.connect(self._on_processes)
        self.proc_worker.pause()
        self.proc_worker.start()

        self.audio_monitor = AudioMonitor(interval_ms=120)
        self.audio_monitor.bars_ready.connect(self._on_audio_bars)
        self.audio_monitor.pause()
        self.audio_monitor.start()

        self.wifi_monitor = WifiMonitor(interval_ms=2500)
        self.wifi_monitor.status_ready.connect(self._on_wifi_status)
        self.wifi_monitor.pause()
        self.wifi_monitor.start()

    def shutdown_workers(self):
        for worker in (
            self.hw_monitor, self.sensor_monitor, self.proc_worker,
            self.audio_monitor, self.wifi_monitor,
        ):
            worker.stop()
        for worker in (
            self.hw_monitor, self.sensor_monitor, self.proc_worker,
            self.audio_monitor, self.wifi_monitor,
        ):
            worker.wait(1000)

    def _load_startup_apps(self):
        try:
            apps = list_startup_apps()
        except Exception:
            apps = []
        self.startup_list.clear()
        if not apps:
            self.startup_list.addItem("Nessuna app in avvio automatico rilevata.")
            return
        for app in apps[:40]:
            self.startup_list.addItem(f"{app['name']}  ·  {app['source']}")

    # ------------------------------------------------------------------
    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%A %d %B %Y").upper())

    def _on_stats(self, data: dict):
        cpu = data["cpu"]
        self.cpu_value_label.setText(f"{cpu['percent_total']:.0f}%")
        freq_txt = f"{cpu['freq_current_mhz']:.0f} MHz" if cpu["freq_current_mhz"] else "-- MHz"
        self.cpu_sub_label.setText(freq_txt)
        self.cpu_extra_label.setText(
            f"{cpu['core_count_physical']} core fisici / {cpu['core_count_logical']} logici"
        )
        self.cpu_chart.push_value(cpu["percent_total"])

        ram = data["ram"]
        self.ram_value_label.setText(f"{ram['percent']:.0f}%")
        self.ram_sub_label.setText(f"{ram['used_gb']} / {ram['total_gb']} GB")
        self.ram_chart.push_value(ram["percent"])

        disks = data["disks"]
        if disks:
            main_disk = max(disks, key=lambda d: d["total_gb"])
            extra = " | ".join(f"{d['mountpoint']} {d['percent']:.0f}%" for d in disks[:4])
            self.card_disk.update_value(
                main_disk["percent"],
                f"{main_disk['percent']:.0f}%",
                f"{main_disk['used_gb']} / {main_disk['total_gb']} GB",
                extra,
            )

        gpus = data["gpus"]
        cards = [self.card_gpu0, self.card_gpu1]
        for i, card in enumerate(cards):
            if i < len(gpus):
                g = gpus[i]
                load = g["load_percent"]
                val_txt = f"{load:.0f}%" if load is not None else "—"
                mem_txt = (
                    f"{g['mem_used_gb']:.1f} / {g['mem_total_gb']:.1f} GB"
                    if g["mem_used_gb"] is not None
                    else (f"{g['mem_total_gb']:.1f} GB VRAM" if g["mem_total_gb"] else "")
                )
                card.title_label.setText(g["name"][:26].upper())
                card.update_value(load, val_txt, mem_txt)
            else:
                card.title_label.setText(f"GPU {i}")
                card.update_value(None, "—", "non rilevata")

    def _on_sensors(self, sensors: dict):
        self.temp_cpu_bar.set_value(sensors["cpu_temp_c"])
        self.temp_gpu_bar.set_value(sensors["gpu_temp_c"])
        fans = sensors["fans_rpm"]
        if fans:
            self.fans_label.setText(
                "  •  ".join(f"{f['name']}: {f['rpm']} RPM" for f in fans[:4])
            )
        else:
            self.fans_label.setText(
                "Ventole non lette (nessun sensore accessibile in questo momento)."
            )

    def _on_audio_bars(self, mic_bars, out_bars):
        self.audio_mic_bar.set_bars(mic_bars)
        self.audio_sys_bar.set_bars(out_bars)

    def _on_wifi_status(self, status: dict):
        self.wifi_panel.set_status(status)

    def _on_processes(self, rows: list):
        self.process_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.process_table.setItem(r, 0, QTableWidgetItem(str(row["pid"])))
            self.process_table.setItem(r, 1, QTableWidgetItem(row["name"]))
            self.process_table.setItem(r, 2, QTableWidgetItem(f"{row['cpu']:.1f}"))
            self.process_table.setItem(r, 3, QTableWidgetItem(f"{row['ram_mb']:.1f}"))
            self.process_table.setItem(r, 4, QTableWidgetItem(row["status"]))

        # "Cronologia Applicazioni": i processi con l'orario di avvio più
        # recente in questa sessione (non è la vera cronologia storica di
        # Windows, che richiederebbe API interne non pubbliche — è
        # un'approssimazione onesta basata sui processi realmente in corso).
        recent = sorted(rows, key=lambda r: r.get("create_time", 0), reverse=True)[:15]
        self.history_list.clear()
        for row in recent:
            try:
                started = datetime.fromtimestamp(row["create_time"]).strftime("%H:%M:%S")
            except (OSError, OverflowError, ValueError):
                started = "--:--:--"
            self.history_list.addItem(f"{started}  ·  {row['name']}")

    def _on_kill_clicked(self):
        selected = self.process_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona un processo dalla tabella.")
            return
        row = selected[0].row()
        pid_item = self.process_table.item(row, 0)
        name_item = self.process_table.item(row, 1)
        pid = int(pid_item.text())

        confirm = QMessageBox.question(
            self, "Conferma terminazione",
            f"Terminare il processo '{name_item.text()}' (PID {pid})?",
        )
        if confirm != QMessageBox.Yes:
            return

        ok, msg = kill_process(pid)
        if ok:
            QMessageBox.information(self, "Fatto", msg)
        else:
            QMessageBox.warning(self, "Errore", msg)

    # ------------------------------------------------------------------
    def toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showFullScreen()
            self.raise_()
            self.activateWindow()

    def showEvent(self, event):
        # Si "risveglia": il monitoraggio riparte solo ora
        self.hw_monitor.resume()
        self.sensor_monitor.resume()
        self.proc_worker.resume()
        self.audio_monitor.resume()
        self.wifi_monitor.resume()
        super().showEvent(event)

    def hideEvent(self, event):
        # Torna residente/dormiente: nessun polling mentre è nascosta
        self.hw_monitor.pause()
        self.sensor_monitor.pause()
        self.proc_worker.pause()
        self.audio_monitor.pause()
        self.wifi_monitor.pause()
        super().hideEvent(event)

    def closeEvent(self, event):
        # Il pulsante di chiusura sulla finestra NON termina l'app: la
        # nasconde soltanto. L'uscita reale avviene dalla system tray.
        event.ignore()
        self.hide()
