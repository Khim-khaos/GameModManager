from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
from qtawesome import icon


class EditGameDialog(QDialog):
    """Диалог для редактирования информации об игре."""

    def __init__(self, game, game_manager, language_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle(language_manager.get("edit_game", "Редактировать игру"))
        self.game = game
        self.game_manager = game_manager
        self.language_manager = language_manager
        self.layout = QFormLayout(self)

        self.name_label = QLabel(language_manager.get("game_name", "Название игры:"))
        self.name_input = QLineEdit(game.name)
        self.layout.addRow(self.name_label, self.name_input)

        self.app_id_label = QLabel(language_manager.get("app_id", "App ID:"))
        self.app_id_input = QLineEdit(game.app_id)
        self.layout.addRow(self.app_id_label, self.app_id_input)

        self.exe_path_label = QLabel(language_manager.get("exe_path", "Путь к .exe:"))
        self.exe_path_input = QLineEdit(game.exe_path)
        self.exe_browse = QPushButton(icon("fa5.folder-open"), language_manager.get("browse", "Обзор"))
        self.exe_browse.clicked.connect(self.browse_exe)
        self.layout.addRow(self.exe_path_label, self.exe_path_input)
        self.layout.addRow("", self.exe_browse)

        self.mods_path_label = QLabel(language_manager.get("mods_path", "Путь к папке модов:"))
        self.mods_path_input = QLineEdit(game.mods_path)
        self.mods_browse = QPushButton(icon("fa5.folder-open"), language_manager.get("browse", "Обзор"))
        self.mods_browse.clicked.connect(self.browse_mods)
        self.layout.addRow(self.mods_path_label, self.mods_path_input)
        self.layout.addRow("", self.mods_browse)

        self.save_button = QPushButton(icon("fa5.save"), language_manager.get("save", "Сохранить"))
        self.save_button.clicked.connect(self.save_game)
        self.layout.addRow("", self.save_button)

    def browse_exe(self):
        """Открывает диалог для выбора исполняемого файла игры."""
        path, _ = QFileDialog.getOpenFileName(
            self, self.language_manager.get("select_exe", "Выберите .exe игры"), "", "Executables (*.exe)"
        )
        if path:
            self.exe_path_input.setText(path)

    def browse_mods(self):
        """Открывает диалог для выбора папки модов."""
        path = QFileDialog.getExistingDirectory(self,
                                                self.language_manager.get("select_mods_folder", "Выберите папку модов"))
        if path:
            self.mods_path_input.setText(path)

    def save_game(self):
        """Сохраняет отредактированную информацию об игре."""
        self.game.name = self.name_input.text()
        self.game.app_id = self.app_id_input.text()
        self.game.exe_path = self.exe_path_input.text()
        self.game.mods_path = self.mods_path_input.text()
        if self.game.name and self.game.app_id and self.game.exe_path and self.game.mods_path:
            self.game_manager.save_games()
            self.accept()
        else:
            QMessageBox.warning(self, self.language_manager.get("error", "Ошибка"),
                                self.language_manager.get("fill_all_fields", "Заполните все поля"))
