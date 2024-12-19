from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt

class EditGameDialog(QDialog):
    def __init__(self, parent=None, game_data=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать игру")
        self.setModal(True)
        self.game_data = game_data

        self.game_name_label = QLabel("Название игры:")
        self.game_name_input = QLineEdit(game_data.get('name', ''))

        self.executable_path_label = QLabel("Путь к исполняемому файлу:")
        self.executable_path_input = QLineEdit(game_data.get('executable_path', ''))
        self.executable_path_button = QPushButton("Обзор")
        self.executable_path_button.clicked.connect(self.browse_executable_path)

        self.mods_path_label = QLabel("Путь к папке с модами:")
        self.mods_path_input = QLineEdit(game_data.get('mods_path', ''))
        self.mods_path_button = QPushButton("Обзор")
        self.mods_path_button.clicked.connect(self.browse_mods_path)

        self.steamcmd_path_label = QLabel("Путь к steamcmd:")
        self.steamcmd_path_input = QLineEdit(game_data.get('steamcmd_path', ''))
        self.steamcmd_path_button = QPushButton("Обзор")
        self.steamcmd_path_button.clicked.connect(self.browse_steamcmd_path)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.game_name_label)
        layout.addWidget(self.game_name_input)
        layout.addWidget(self.executable_path_label)
        layout.addWidget(self.executable_path_input)
        layout.addWidget(self.executable_path_button)
        layout.addWidget(self.mods_path_label)
        layout.addWidget(self.mods_path_input)
        layout.addWidget(self.mods_path_button)
        layout.addWidget(self.steamcmd_path_label)
        layout.addWidget(self.steamcmd_path_input)
        layout.addWidget(self.steamcmd_path_button)
        layout.addWidget(self.ok_button)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

    def browse_executable_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите исполняемый файл")
        if file_path:
            self.executable_path_input.setText(file_path)

    def browse_mods_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите папку с модами")
        if dir_path:
            self.mods_path_input.setText(dir_path)

    def browse_steamcmd_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите steamcmd.exe")
        if file_path:
            self.steamcmd_path_input.setText(file_path)

    def get_game_data(self):
        game_name = self.game_name_input.text()
        executable_path = self.executable_path_input.text()
        mods_path = self.mods_path_input.text()
        steamcmd_path = self.steamcmd_path_input.text()
        return game_name, executable_path, mods_path, steamcmd_path, None
