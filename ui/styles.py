# ui/styles.py
"""Palette colori e QSS globale per il tema Cyberpunk."""

NEON_BLUE = "#00E5FF"
NEON_BLUE_DIM = "#0097A7"
BG_DARK = "#05070D"
BG_PANEL = "#0B1220"
BG_PANEL_LIGHT = "#101A2E"
DANGER_RED = "#FF3B5C"
WARN_AMBER = "#FFB300"
TEXT_MAIN = "#D7F6FF"
TEXT_DIM = "#6B8CA8"

QSS = f"""
QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_MAIN};
    font-family: 'Consolas', 'Segoe UI', monospace;
    font-size: 13px;
}}

QFrame#panel {{
    background-color: {BG_PANEL};
    border: 2px solid {NEON_BLUE_DIM};
    border-radius: 10px;
}}

QFrame#panel:hover {{
    border: 2px solid {NEON_BLUE};
}}

QLabel#panelTitle {{
    color: {NEON_BLUE};
    font-weight: bold;
    font-size: 14px;
    letter-spacing: 2px;
    padding-bottom: 4px;
    border-bottom: 1px solid {NEON_BLUE_DIM};
}}

QLabel#bigMetric {{
    color: {NEON_BLUE};
    font-size: 26px;
    font-weight: bold;
}}

QLabel#dimLabel {{
    color: {TEXT_DIM};
    font-size: 11px;
}}

QLabel#clockLabel {{
    color: {NEON_BLUE};
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 3px;
}}

QProgressBar {{
    background-color: {BG_PANEL_LIGHT};
    border: 2px solid {NEON_BLUE_DIM};
    border-radius: 6px;
    text-align: center;
    color: {TEXT_MAIN};
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: {NEON_BLUE};
    border-radius: 5px;
}}

QListWidget#compactList {{
    background-color: {BG_PANEL_LIGHT};
    border: 2px solid {NEON_BLUE_DIM};
    border-radius: 6px;
    color: {TEXT_DIM};
    font-size: 11px;
    padding: 2px;
}}

QListWidget#compactList::item {{
    padding: 3px 4px;
    border-bottom: 1px solid rgba(0, 151, 167, 60);
}}

QListWidget#compactList::item:selected {{
    background-color: {NEON_BLUE_DIM};
    color: #FFFFFF;
}}

QTableWidget {{
    background-color: {BG_PANEL};
    gridline-color: {BG_PANEL_LIGHT};
    border: 2px solid {NEON_BLUE_DIM};
    border-radius: 8px;
    selection-background-color: {NEON_BLUE_DIM};
    selection-color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: {BG_PANEL_LIGHT};
    color: {NEON_BLUE};
    padding: 4px;
    border: none;
    border-bottom: 1px solid {NEON_BLUE_DIM};
    font-weight: bold;
}}

QPushButton {{
    background-color: {BG_PANEL_LIGHT};
    color: {NEON_BLUE};
    border: 2px solid {NEON_BLUE};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {NEON_BLUE_DIM};
    color: #FFFFFF;
}}

QPushButton:pressed {{
    background-color: {NEON_BLUE};
    color: #000000;
}}

QPushButton#dangerButton {{
    border-color: {DANGER_RED};
    color: {DANGER_RED};
}}

QPushButton#dangerButton:hover {{
    background-color: {DANGER_RED};
    color: #FFFFFF;
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {BG_PANEL_LIGHT};
    border: 2px solid {NEON_BLUE_DIM};
    border-radius: 5px;
    padding: 4px;
    color: {TEXT_MAIN};
}}

QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {NEON_BLUE_DIM};
    border-radius: 5px;
    min-height: 20px;
}}

QCheckBox {{
    spacing: 8px;
}}

QMenu {{
    background-color: {BG_PANEL};
    color: {TEXT_MAIN};
    border: 2px solid {NEON_BLUE_DIM};
}}

QMenu::item:selected {{
    background-color: {NEON_BLUE_DIM};
}}

QListWidget {{
    background-color: {BG_PANEL_LIGHT};
    border: none;
    color: {TEXT_MAIN};
    font-size: 11px;
}}

QListWidget::item {{
    padding: 3px 4px;
    border-bottom: 1px solid rgba(0, 151, 167, 60);
}}

QListWidget::item:selected {{
    background-color: {NEON_BLUE_DIM};
}}
"""
