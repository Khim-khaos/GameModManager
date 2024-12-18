# src/ui/settings_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtCore import QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None, initial_steamcmd_path=""):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setGeometry(200, 200, 400, 150)

        self.settings = QSettings("GameModManager", "Settings")
        self.steamcmd_path = self.settings.value("steamcmd_path", initial_steamcmd_path)

        layout = QVBoxLayout(self)

        label = QLabel("Путь до steamcmd:")
        layout.addWidget(label)

        self.steamcmd_path_edit = QLineEdit(self.steamcmd_path)
        layout.addWidget(self.steamcmd_path_edit)

        browse_button = QPushButton("Обзор")
        browse_button.clicked.connect(self.browse_steamcmd)
        layout.addWidget(browse_button)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def browse_steamcmd(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите steamcmd.exe", "", "Executable Files (*.exe)")
        if file_path:
            self.steamcmd_path_edit.setText(file_path)

    def save_settings(self):
        self.steamcmd_path = self.steamcmd_path_edit.text()
        self.settings.setValue("steamcmd_path", self.steamcmd_path)
        self.accept()

    def get_steamcmd_path(self):
        return self.steamcmd_path
