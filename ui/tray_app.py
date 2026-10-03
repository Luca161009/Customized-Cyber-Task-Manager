# ui/tray_app.py
"""Icona nella system tray generata proceduralmente (nessun asset esterno)."""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QAction
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
import sys

from ui.settings_dialog import SettingsDialog
from core.elevation import is_admin, relaunch_as_admin

IS_WINDOWS = sys.platform == "win32"


def build_icon() -> QIcon:
    """Genera un'icona quadrata neon (nessun file .ico da distribuire)."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor(5, 7, 13))
    painter.setPen(QPen(QColor(0, 229, 255), 4))
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 10, 10)

    # Simbolo stilizzato "attività" (tre barre stile task manager)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(0, 229, 255))
    bar_widths = [14, 24, 34]
    x = 14
    for i, h in enumerate(bar_widths):
        painter.drawRoundedRect(x + i * 14, size - 14 - h, 8, h, 2, 2)

    painter.end()
    return QIcon(pixmap)


class TrayApplication:
    def __init__(self, app, main_window, hotkey_manager):
        self.app = app
        self.main_window = main_window
        self.hotkey_manager = hotkey_manager

        self.tray_icon = QSystemTrayIcon(build_icon(), app)
        self.tray_icon.setToolTip("CyberTaskManager — Win+Ctrl+T per aprire")

        menu = QMenu()

        action_toggle = QAction("Mostra / Nascondi", app)
        action_toggle.triggered.connect(self.main_window.toggle_visibility)
        menu.addAction(action_toggle)

        action_settings = QAction("Impostazioni…", app)
        action_settings.triggered.connect(self._open_settings)
        menu.addAction(action_settings)

        if IS_WINDOWS and not is_admin():
            action_elevate = QAction("Riavvia come Amministratore (sensori HW)", app)
            action_elevate.triggered.connect(self._elevate)
            menu.addAction(action_elevate)

        menu.addSeparator()

        action_quit = QAction("Esci definitivamente", app)
        action_quit.triggered.connect(self._quit)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _on_activated(self, reason):
        # Doppio click sull'icona -> mostra/nasconde la finestra
        if reason == QSystemTrayIcon.DoubleClick:
            self.main_window.toggle_visibility()

    def _open_settings(self):
        dlg = SettingsDialog(self._apply_new_hotkey, parent=self.main_window)
        dlg.exec()

    def _apply_new_hotkey(self, modifiers: list[str], key: str):
        self.hotkey_manager.set_combination(modifiers, key, register_now=True)
        self.tray_icon.showMessage(
            "CyberTaskManager",
            f"Nuova hotkey attiva: {' + '.join(modifiers)} + {key}",
            QSystemTrayIcon.Information,
            3000,
        )

    def _elevate(self):
        relaunch_as_admin()
        self._quit()

    def _quit(self):
        self.hotkey_manager.unregister()
        self.main_window.shutdown_workers()
        self.tray_icon.hide()
        self.app.quit()
