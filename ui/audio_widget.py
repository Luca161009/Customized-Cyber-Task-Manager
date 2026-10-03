# ui/audio_widget.py
"""
Visualizzatore audio "equalizzatore" a barre verticali affiancate, in
stile classico da lettore musicale — non una singola barra che si
riempie, ma tante barre indipendenti che salgono e scendono seguendo lo
spettro reale dell'audio (calcolato con la FFT in core/audio_monitor.py).

Ogni barra ha un piccolo effetto di "caduta morbida" (decay) tra un
aggiornamento e l'altro, per un movimento fluido tipico degli
equalizzatori, anche se i dati arrivano a intervalli regolari (~120ms).
"""

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QWidget

N_BARS = 30
DECAY = 0.82  # quanto "cade" ogni barra ad ogni tick se non riceve un valore più alto


class AudioEqualizerBar(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._targets = [0.0] * N_BARS
        self._display = [0.0] * N_BARS
        self._available = True
        self.setMinimumHeight(60)

        # Timer indipendente dai dati in arrivo: garantisce un'animazione
        # fluida della caduta anche se i nuovi valori arrivano più lenti.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)  # ~25 FPS

    def set_bars(self, bars):
        """bars: lista di float 0.0-1.0, oppure None se la sorgente non è disponibile."""
        if bars is None:
            self._available = False
            self._targets = [0.0] * N_BARS
            return
        self._available = True
        n = len(bars)
        if n == N_BARS:
            self._targets = list(bars)
        elif n > 0:
            # adatta una lunghezza diversa campionando in modo semplice
            self._targets = [bars[min(int(i * n / N_BARS), n - 1)] for i in range(N_BARS)]

    def set_unavailable(self):
        self._available = False
        self._targets = [0.0] * N_BARS

    def _tick(self):
        for i in range(N_BARS):
            target = self._targets[i] if self._available else 0.0
            if target > self._display[i]:
                self._display[i] = target
            else:
                self._display[i] *= DECAY
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        label_h = 14
        bars_top = label_h + 2
        bars_h = max(1.0, h - bars_top - 2)

        font = QFont("Consolas", 8)
        painter.setFont(font)
        painter.setPen(QColor("#6B8CA8"))
        painter.drawText(QRectF(0, 0, w, label_h), Qt.AlignLeft | Qt.AlignVCenter, self._label)

        gap = 1.5
        bar_w = (w - gap * (N_BARS - 1)) / N_BARS

        for i in range(N_BARS):
            level = max(0.0, min(1.0, self._display[i]))
            bar_h = max(2.0, level * bars_h)
            x = i * (bar_w + gap)
            rect = QRectF(x, bars_top + (bars_h - bar_h), bar_w, bar_h)

            if not self._available:
                color = QColor(255, 255, 255, 22)
            elif level < 0.55:
                color = QColor(0, 229, 255, 230)
            elif level < 0.82:
                color = QColor(235, 220, 0, 230)
            else:
                color = QColor(255, 60, 60, 230)

            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 2, 2)

        painter.end()
