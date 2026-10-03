# ui/wifi_widget.py
"""
Pannello Wi-Fi: icona a "stanghette" (come quella di Windows, con il
numero di barre piene proporzionale alla qualità del segnale), nome
della rete connessa, e un mini-grafico neon dello storico del segnale
(riusa lo stesso NeonLineChart di CPU/RAM).

Se non c'è connessione Wi-Fi (cavo Ethernet, adattatore assente/spento),
mostra semplicemente l'icona spenta e "Non connesso", senza errori.
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from ui.chart_widget import NeonLineChart

N_WIFI_BARS = 4


class WifiIcon(QWidget):
    """Icona a stanghette: 4 barre crescenti, colorate in base al segnale."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percent = None  # None = non connesso
        self.setFixedSize(34, 22)

    def set_percent(self, percent):
        self._percent = percent
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        bars_on = 0
        if self._percent is not None:
            bars_on = max(1, min(N_WIFI_BARS, int(self._percent / (100 / N_WIFI_BARS)) + 1))

        if self._percent is None:
            color_on = QColor(90, 100, 110)
        elif self._percent < 35:
            color_on = QColor(255, 60, 60)
        elif self._percent < 65:
            color_on = QColor(235, 220, 0)
        else:
            color_on = QColor(0, 229, 255)
        color_off = QColor(255, 255, 255, 25)

        bar_w = 5
        gap = 3
        base_y = h - 2
        for i in range(N_WIFI_BARS):
            bar_h = (i + 1) * (h - 4) / N_WIFI_BARS
            x = i * (bar_w + gap)
            rect = QRectF(x, base_y - bar_h, bar_w, bar_h)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color_on if i < bars_on and self._percent is not None else color_off)
            painter.drawRoundedRect(rect, 1.5, 1.5)

        painter.end()


class WifiPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        head = QHBoxLayout()
        self.icon = WifiIcon()
        head.addWidget(self.icon)

        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        self.ssid_label = QLabel("Non connesso")
        self.ssid_label.setStyleSheet("color:#00E5FF; font-weight:bold; font-size:12px;")
        self.percent_label = QLabel("—")
        self.percent_label.setObjectName("dimLabel")
        text_box.addWidget(self.ssid_label)
        text_box.addWidget(self.percent_label)
        head.addLayout(text_box)
        head.addStretch()
        layout.addLayout(head)

        self.chart = NeonLineChart(max_points=40, color="#00E5FF")
        self.chart.setMinimumHeight(40)
        layout.addWidget(self.chart)

    def set_status(self, status: dict):
        connected = status.get("connected", False)
        ssid = status.get("ssid")
        percent = status.get("signal_percent")

        self.icon.set_percent(percent if connected else None)
        if connected and ssid:
            self.ssid_label.setText(ssid[:22])
        else:
            self.ssid_label.setText("Non connesso")

        if connected and percent is not None:
            self.percent_label.setText(f"Segnale: {percent}%")
            self.chart.push_value(percent)
        else:
            self.percent_label.setText("—")
            self.chart.push_value(0)
