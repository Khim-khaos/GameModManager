from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QFileDialog, QHBoxLayout
from core.game_manager import GameManager
from loguru import logger

class EditGameDialog(QDialog):
    def __init__(self, parent, app_id):
        super().__init__(parent)
        self.parent = parent
        self.app_id = app_id
        self.game_manager = GameManager()
        self.game = self.game_manager.get_game(app_id)  # Исправлено: self.game_manager вместо self heaven_manager
        if not self.game:
            QMessageBox.critical(self, "Ошибка", "Игра не найдена!")
            self.reject()
            return
        self.setWindowTitle(f"Редактировать игру: {self.game['name']}")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.name_input = QLineEdit(self.game["name"])
        layout.addWidget(QLabel("Название игры:"))
        layout.addWidget(self.name_input)

        # Путь к исполняемому файлу
        exe_layout = QHBoxLayout()
        self.exe_input = QLineEdit(self.game["exe_path"])
        exe_browse = QPushButton("Обзор")
        exe_browse.clicked.connect(self.browse_exe)
        exe_layout.addWidget(self.exe_input)
        exe_layout.addWidget(exe_browse)
        layout.addWidget(QLabel("Путь к исполняемому файлу:"))
        layout.addLayout(exe_layout)

        # Путь к папке модов
        mods_layout = QHBoxLayout()
        self.mods_input = QLineEdit(self.game["mods_path"])
        mods_browse = QPushButton("Обзор")
        mods_browse.clicked.connect(self.browse_mods)
        mods_layout.addWidget(self.mods_input)
        mods_layout.addWidget(mods_browse)
        layout.addWidget(QLabel("Путь к папке модов:"))
        layout.addLayout(mods_layout)

        self.app_id_input = QLineEdit(self.game["app_id"])
        self.app_id_input.setReadOnly(True)
        layout.addWidget(QLabel("ID приложения Steam:"))
        layout.addWidget(self.app_id_input)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_changes)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать исполняемый файл", "", "Исполняемые файлы (*.exe)")
        if path:
            self.exe_input.setText(path)

    def browse_mods(self):
        path = QFileDialog.getExistingDirectory(self, "Выбрать папку модов")
        if path:
            self.mods_input.setText(path)

    def save_changes(self):
        new_name = self.name_input.text()
        new_exe_path = self.exe_input.text()
        new_mods_path = self.mods_input.text()

        if not all([new_name, new_exe_path, new_mods_path]):
            QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены!")
            return

        self.game["name"] = new_name
        self.game["exe_path"] = new_exe_path
        self.game["mods_path"] = new_mods_path
        self.game_manager.save_games()
        logger.info(f"Игра {self.app_id} отредактирована: {new_name}")
        self.accept()
