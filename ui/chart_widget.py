# ui/chart_widget.py
"""
Grafico a linea neon con effetto "glow", per mostrare l'andamento nel
tempo di una metrica (CPU %, RAM %). Nessuna libreria di plotting
esterna: disegno diretto con QPainter per restare leggero e coerente
con il tema cyberpunk.
"""

from collections import deque

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget


class NeonLineChart(QWidget):
    def __init__(self, max_points: int = 60, color: str = "#00E5FF", parent=None):
        super().__init__(parent)
        self._max_points = max_points
        self._values = deque([0.0] * max_points, maxlen=max_points)
        self._color = QColor(color)
        self.setMinimumHeight(48)

    def push_value(self, value: float):
        value = max(0.0, min(100.0, value))
        self._values.append(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        # --- Griglia di sfondo leggera ---
        grid_pen = QPen(QColor(255, 255, 255, 18))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = h * i / 4
            painter.drawLine(0, int(y), w, int(y))

        # --- Costruzione del percorso della linea ---
        n = len(self._values)
        if n < 2:
            return
        step_x = w / (n - 1)

        path = QPainterPath()
        points = []
        for i, val in enumerate(self._values):
            x = i * step_x
            y = h - (val / 100.0) * (h - 4) - 2
            points.append(QPointF(x, y))
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)

        # --- Area sotto la curva (sfumatura) ---
        area_path = QPainterPath(path)
        area_path.lineTo(points[-1].x(), h)
        area_path.lineTo(points[0].x(), h)
        area_path.closeSubpath()

        gradient = QLinearGradient(0, 0, 0, h)
        fill_color = QColor(self._color)
        fill_color.setAlpha(80)
        gradient.setColorAt(0, fill_color)
        transparent = QColor(self._color)
        transparent.setAlpha(0)
        gradient.setColorAt(1, transparent)
        painter.fillPath(area_path, gradient)

        # --- Effetto glow: più passate della stessa linea, penna più larga
        # e più trasparente sotto, penna sottile e piena sopra ---
        glow_pen = QPen(self._color)
        glow_pen.setWidth(6)
        glow_color = QColor(self._color)
        glow_color.setAlpha(45)
        glow_pen.setColor(glow_color)
        glow_pen.setCapStyle(Qt.RoundCap)
        glow_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(glow_pen)
        painter.drawPath(path)

        core_pen = QPen(self._color)
        core_pen.setWidth(2)
        core_pen.setCapStyle(Qt.RoundCap)
        core_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(core_pen)
        painter.drawPath(path)

        # --- Punto finale in evidenza ---
        painter.setBrush(self._color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(points[-1], 3, 3)
