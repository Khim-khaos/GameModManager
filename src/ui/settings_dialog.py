from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.settings = settings if settings else {}

        self.steamcmd_path_label = QLabel("Путь до steamcmd.exe:")
        self.steamcmd_path_input = QLineEdit(self.settings.get('steamcmd_path', ''))
        self.steamcmd_path_button = QPushButton("Выбрать")
        self.steamcmd_path_button.clicked.connect(self.select_steamcmd_path)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.steamcmd_path_label)
        layout.addWidget(self.steamcmd_path_input)
        layout.addWidget(self.steamcmd_path_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def select_steamcmd_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите steamcmd.exe")
        self.steamcmd_path_input.setText(file_path)

    def get_settings(self):
        steamcmd_path = self.steamcmd_path_input.text()
        return {'steamcmd_path': steamcmd_path}
