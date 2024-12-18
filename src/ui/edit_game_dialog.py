# src/ui/edit_game_dialog.py
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFormLayout, QFileDialog, QHBoxLayout
import os

class EditGameDialog(QDialog):
    def __init__(self, parent=None, game_data=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать игру")
        self.game_name_input = QLineEdit()
        self.executable_path_input = QLineEdit()
        self.mods_path_input = QLineEdit()
        if game_data:
            self.game_name_input.setText(game_data["name"])
            self.executable_path_input.setText(game_data["executable_path"])
            self.mods_path_input.setText(game_data["mods_path"])
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Название игры:"), self.game_name_input)

        # Путь до исполняемого файла
        executable_layout = QHBoxLayout()
        executable_layout.addWidget(QLabel("Путь до исполняемого файла:"))
        executable_layout.addWidget(self.executable_path_input)
        executable_button = QPushButton("Выбрать")
        executable_button.clicked.connect(self.select_executable_path)
        executable_layout.addWidget(executable_button)
        form_layout.addRow(executable_layout)

        # Путь до папки с модами
        mods_layout = QHBoxLayout()
        mods_layout.addWidget(QLabel("Путь до папки с модами:"))
        mods_layout.addWidget(self.mods_path_input)
        mods_button = QPushButton("Выбрать")
        mods_button.clicked.connect(self.select_mods_path)
        mods_layout.addWidget(mods_button)
        form_layout.addRow(mods_layout)

        layout.addLayout(form_layout)

        buttons_layout = QVBoxLayout()
        edit_button = QPushButton("Редактировать")
        edit_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

    def select_executable_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать исполняемый файл", "", "Executable Files (*.exe *.bat)")
        if file_path:
            self.executable_path_input.setText(file_path)

    def select_mods_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выбрать папку с модами")
        if dir_path:
            self.mods_path_input.setText(dir_path)

    def get_game_data(self):
        game_name = self.game_name_input.text()
        executable_path = self.executable_path_input.text()
        mods_path = self.mods_path_input.text()
        return game_name, executable_path, mods_path
