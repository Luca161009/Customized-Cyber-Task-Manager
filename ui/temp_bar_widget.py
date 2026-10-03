# ui/temp_bar_widget.py
"""
Barra verticale per le temperature con gradiente termico:
  < 30°C  -> verde
  ~ 40°C  -> giallo
  > 50°C  -> arancione
  oltre   -> rosso

Se il valore non è disponibile (sensore protetto/non presente), la
barra resta "spenta" (grigio scuro, vuota) invece di mostrare testo
d'errore o un numero inventato: nessun dato falso, solo un'indicazione
visiva neutra.
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont
from PySide6.QtWidgets import QWidget


def _color_for_temp(temp: float) -> QColor:
    if temp < 30:
        return QColor("#00E676")   # verde
    elif temp < 40:
        return QColor("#C6FF00")   # verde-giallo
    elif temp < 50:
        return QColor("#FFD600")   # giallo
    elif temp < 65:
        return QColor("#FF9100")   # arancione
    else:
        return QColor("#FF1744")   # rosso


class TemperatureBar(QWidget):
    def __init__(self, label: str, min_temp: float = 20.0, max_temp: float = 90.0, parent=None):
        super().__init__(parent)
        self._label = label
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._value = None  # None = sensore non disponibile
        self.setMinimumSize(46, 120)

    def set_value(self, value):
        self._value = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        track_top = 18
        track_bottom = h - 20
        track_h = max(1, track_bottom - track_top)
        track_rect = QRectF(w / 2 - 9, track_top, 18, track_h)

        # Binario di sfondo
        painter.setPen(QPen(QColor("#0097A7"), 1))
        painter.setBrush(QColor(10, 16, 26))
        painter.drawRoundedRect(track_rect, 6, 6)

        if self._value is not None:
            ratio = (self._value - self._min_temp) / (self._max_temp - self._min_temp)
            ratio = max(0.02, min(1.0, ratio))
            fill_h = track_h * ratio
            fill_rect = QRectF(track_rect.x(), track_bottom - fill_h, track_rect.width(), fill_h)

            color = _color_for_temp(self._value)
            gradient = QLinearGradient(0, fill_rect.bottom(), 0, fill_rect.top())
            gradient.setColorAt(0.0, color.darker(130))
            gradient.setColorAt(1.0, color)
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(fill_rect, 5, 5)

            value_text = f"{self._value:.0f}°"
        else:
            value_text = "--"

        # Etichetta valore (sopra la barra)
        painter.setPen(QColor("#D7F6FF"))
        font = QFont("Consolas", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, w, 16), Qt.AlignCenter, value_text)

        # Etichetta nome (sotto la barra)
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#6B8CA8"))
        painter.drawText(QRectF(0, h - 16, w, 16), Qt.AlignCenter, self._label)
