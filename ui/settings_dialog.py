# ui/settings_dialog.py
"""Finestra di dialogo per personalizzare hotkey e avvio automatico."""

import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QGroupBox, QMessageBox
)

from core.config import config
from core import autostart

IS_WINDOWS = sys.platform == "win32"


class SettingsDialog(QDialog):
    def __init__(self, hotkey_apply_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni // CyberTaskManager")
        self.setFixedSize(440, 320)
        self._hotkey_apply_callback = hotkey_apply_callback

        layout = QVBoxLayout(self)

        # --- Gruppo Hotkey ---
        if IS_WINDOWS:
            hk_group = QGroupBox("Scorciatoia globale (mostra/nascondi)")
            hk_layout = QHBoxLayout(hk_group)

            self.chk_win = QCheckBox("Win")
            self.chk_ctrl = QCheckBox("Ctrl")
            self.chk_alt = QCheckBox("Alt")
            self.chk_shift = QCheckBox("Shift")
            current_mods = config.get("hotkey_modifiers", ["WIN", "CTRL"])
            self.chk_win.setChecked("WIN" in current_mods)
            self.chk_ctrl.setChecked("CTRL" in current_mods)
            self.chk_alt.setChecked("ALT" in current_mods)
            self.chk_shift.setChecked("SHIFT" in current_mods)

            self.key_edit = QLineEdit(config.get("hotkey_key", "T"))
            self.key_edit.setMaxLength(1)
            self.key_edit.setFixedWidth(40)

            for w in (self.chk_win, self.chk_ctrl, self.chk_alt, self.chk_shift):
                hk_layout.addWidget(w)
            hk_layout.addWidget(QLabel("+"))
            hk_layout.addWidget(self.key_edit)
            layout.addWidget(hk_group)

            note = QLabel(
                "Nota: Ctrl+Shift+Esc resta invariata e apre sempre il\n"
                "Task Manager nativo di Windows."
            )
            note.setObjectName("dimLabel")
            layout.addWidget(note)
        else:
            # Su Linux la combinazione non si registra da qui: va impostata
            # come scorciatoia personalizzata del proprio ambiente desktop,
            # puntata al comando "python3 main.py --toggle" (vedi README).
            hk_group = QGroupBox("Scorciatoia globale (mostra/nascondi)")
            hk_layout = QVBoxLayout(hk_group)
            info = QLabel(
                "Su Linux la scorciatoia si configura nelle Impostazioni di\n"
                "sistema del tuo ambiente desktop (GNOME/KDE/XFCE), non qui.\n\n"
                "Collega la combinazione desiderata al comando:\n"
                "python3 main.py --toggle\n\n"
                "Istruzioni dettagliate nel README.md, sezione \"Scorciatoia\n"
                "globale\"."
            )
            info.setWordWrap(True)
            info.setObjectName("dimLabel")
            hk_layout.addWidget(info)
            layout.addWidget(hk_group)

        # --- Gruppo Avvio ---
        start_group = QGroupBox("Avvio")
        start_layout = QVBoxLayout(start_group)
        autostart_label = (
            "Avvia automaticamente con Windows" if IS_WINDOWS
            else "Avvia automaticamente all'accesso (autostart Linux)"
        )
        self.chk_autostart = QCheckBox(autostart_label)
        self.chk_autostart.setChecked(autostart.is_autostart_enabled())
        start_layout.addWidget(self.chk_autostart)

        self.chk_minimized = QCheckBox("Avvia minimizzato nella system tray")
        self.chk_minimized.setChecked(config.get("start_minimized_to_tray", True))
        start_layout.addWidget(self.chk_minimized)
        layout.addWidget(start_group)

        layout.addStretch()

        # --- Pulsanti ---
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Salva")
        self.btn_cancel = QPushButton("Annulla")
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

    def _save(self):
        config.set("start_minimized_to_tray", self.chk_minimized.isChecked())

        if IS_WINDOWS:
            mods = []
            if self.chk_win.isChecked():
                mods.append("WIN")
            if self.chk_ctrl.isChecked():
                mods.append("CTRL")
            if self.chk_alt.isChecked():
                mods.append("ALT")
            if self.chk_shift.isChecked():
                mods.append("SHIFT")
            key = (self.key_edit.text() or "T").upper()

            if not mods or not key.isalnum():
                QMessageBox.warning(
                    self, "Combinazione non valida",
                    "Seleziona almeno un modificatore e un tasto alfanumerico."
                )
                return

            config.set("hotkey_modifiers", mods)
            config.set("hotkey_key", key)
            self._hotkey_apply_callback(mods, key)

            exe = sys.executable
            script = sys.argv[0]
            command = f'"{exe}" "{script}"' if not exe.lower().endswith("cybertaskmanager.exe") else f'"{exe}"'
            autostart.set_autostart(self.chk_autostart.isChecked(), command)
        else:
            # Su Linux: comando "python3 /percorso/main.py" nel file .desktop
            exe = sys.executable
            script = sys.argv[0]
            command = f'{exe} {script}'
            autostart.set_autostart(self.chk_autostart.isChecked(), command)

        self.accept()
