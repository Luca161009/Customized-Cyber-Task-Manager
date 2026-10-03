# ui/gauge_widget.py
"""
Widget riutilizzabile "MetricCard": un pannello con titolo, valore
numerico grande e barra di avanzamento in stile neon. Usato per
CPU, RAM, SSD, GPU, temperature.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt


class MetricCard(QFrame):
    def __init__(self, title: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._unit = unit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("panelTitle")
        layout.addWidget(self.title_label)

        row = QHBoxLayout()
        self.value_label = QLabel(f"-- {unit}")
        self.value_label.setObjectName("bigMetric")
        row.addWidget(self.value_label)
        row.addStretch()
        self.sub_label = QLabel("")
        self.sub_label.setObjectName("dimLabel")
        self.sub_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        row.addWidget(self.sub_label)
        layout.addLayout(row)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

        self.extra_label = QLabel("")
        self.extra_label.setObjectName("dimLabel")
        layout.addWidget(self.extra_label)

    def update_value(self, percent: float | None, value_text: str, sub_text: str = "", extra_text: str = ""):
        if percent is None:
            self.bar.setValue(0)
        else:
            self.bar.setValue(int(max(0, min(100, percent))))
        self.value_label.setText(value_text)
        self.sub_label.setText(sub_text)
        self.extra_label.setText(extra_text)
