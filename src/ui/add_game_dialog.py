# src/ui/add_game_dialog.py
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFormLayout, QFileDialog, QHBoxLayout
import os
import traceback

class AddGameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить игру")
        self.game_id_input = QLineEdit()
        self.game_name_input = QLineEdit()
        self.executable_path_input = QLineEdit()
        self.mods_path_input = QLineEdit()
        self.init_ui()

    def init_ui(self):
        try:
            layout = QVBoxLayout(self)
            form_layout = QFormLayout()
            form_layout.addRow(QLabel("ID игры:"), self.game_id_input)
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
            add_button = QPushButton("Добавить")
            add_button.clicked.connect(self.accept)
            cancel_button = QPushButton("Отмена")
            cancel_button.clicked.connect(self.reject)
            buttons_layout.addWidget(add_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)
        except Exception as e:
            print(f"Ошибка в init_ui: {e}")
            traceback.print_exc()

    def select_executable_path(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать исполняемый файл", "", "Executable Files (*.exe *.bat)")
            if file_path:
                self.executable_path_input.setText(file_path)
        except Exception as e:
            print(f"Ошибка в select_executable_path: {e}")
            traceback.print_exc()

    def select_mods_path(self):
        try:
            dir_path = QFileDialog.getExistingDirectory(self, "Выбрать папку с модами")
            if dir_path:
                self.mods_path_input.setText(dir_path)
        except Exception as e:
            print(f"Ошибка в select_mods_path: {e}")
            traceback.print_exc()

    def get_game_data(self):
        try:
            game_id = self.game_id_input.text()
            game_name = self.game_name_input.text()
            executable_path = self.executable_path_input.text()
            mods_path = self.mods_path_input.text()
            print(f"Данные из AddGameDialog: ID={game_id}, Name={game_name}, Exec={executable_path}, Mods={mods_path}")
            return game_id, game_name, executable_path, mods_path
        except Exception as e:
            print(f"Ошибка в get_game_data: {e}")
            traceback.print_exc()
            return None, None, None, None
