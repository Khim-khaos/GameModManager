from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QHBoxLayout, QMessageBox
from PySide6.QtCore import QProcess
from qtawesome import icon
from core.mod_manager import ModManager
from ui.dialogs.mod_info_dialog import ModInfoDialog
from loguru import logger
import os
import asyncio


class GamesTab(QWidget):
    """Вкладка для отображения информации об игре и управления модами."""

    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.mod_manager = ModManager()
        self.current_game = None
        self.layout = QVBoxLayout(self)

        # Информация об игре
        self.game_info = QLabel(
            self.main_window.language_manager.get("select_game", "Выберите игру для просмотра информации"))
        self.layout.addWidget(self.game_info)

        # Кнопка запуска игры
        self.launch_button = QPushButton(
            icon("fa5.play"), self.main_window.language_manager.get("launch_game", "Запустить игру")
        )
        self.launch_button.clicked.connect(self.launch_game)
        self.launch_button.setEnabled(False)
        self.layout.addWidget(self.launch_button)

        # Список установленных модов
        self.mods_label = QLabel(self.main_window.language_manager.get("installed_mods", "Установленные моды:"))
        self.layout.addWidget(self.mods_label)
        self.mods_list = QListWidget()
        self.mods_list.itemDoubleClicked.connect(self.show_mod_info)
        self.layout.addWidget(self.mods_list)

        # Кнопки управления модами
        self.mods_buttons_layout = QHBoxLayout()
        self.toggle_mod_button = QPushButton(
            icon("fa5.toggle-off"), self.main_window.language_manager.get("toggle_mod", "Отключить мод")  # Исправлено
        )
        self.toggle_mod_button.clicked.connect(self.toggle_mod)
        self.toggle_mod_button.setEnabled(False)
        self.delete_mod_button = QPushButton(
            icon("fa5.trash"), self.main_window.language_manager.get("delete_mod", "Удалить мод")
        )
        self.delete_mod_button.clicked.connect(self.delete_mod)
        self.delete_mod_button.setEnabled(False)
        self.update_mod_button = QPushButton(
            icon("fa5.sync"), self.main_window.language_manager.get("update_mod", "Обновить мод")
        )
        self.update_mod_button.clicked.connect(self.update_mod)
        self.update_mod_button.setEnabled(False)
        self.info_mod_button = QPushButton(
            icon("fa5.info-circle"), self.main_window.language_manager.get("mod_info", "Информация о моде")
        )
        self.info_mod_button.clicked.connect(self.show_mod_info)
        self.info_mod_button.setEnabled(False)
        self.mods_buttons_layout.addWidget(self.toggle_mod_button)
        self.mods_buttons_layout.addWidget(self.delete_mod_button)
        self.mods_buttons_layout.addWidget(self.update_mod_button)
        self.mods_buttons_layout.addWidget(self.info_mod_button)
        self.layout.addLayout(self.mods_buttons_layout)

    def update_game(self, game):
        """Обновляет информацию об игре и список модов."""
        self.current_game = game
        self.mods_list.clear()
        if game:
            self.game_info.setText(
                f"Игра: {game.name}\nID: {game.app_id}\nПуть: {game.exe_path}\nМоды: {game.mods_path}"
            )
            self.launch_button.setEnabled(True)
            self.toggle_mod_button.setEnabled(True)
            self.delete_mod_button.setEnabled(True)
            self.update_mod_button.setEnabled(True)
            self.info_mod_button.setEnabled(True)
            # Загрузка установленных модов
            mods_dir = game.mods_path
            if os.path.exists(mods_dir):
                for mod_folder in os.listdir(mods_dir):
                    if mod_folder.isdigit():
                        self.mods_list.addItem(f"Мод ID: {mod_folder} [Включен]")
                    elif mod_folder.endswith("_disabled"):
                        mod_id = mod_folder.split("_disabled")[0]
                        self.mods_list.addItem(f"Мод ID: {mod_id} [Отключен]")
            logger.info(f"Обновлена информация для игры: {game.name}")
        else:
            self.game_info.setText(
                self.main_window.language_manager.get("select_game", "Выберите игру для просмотра информации"))
            self.launch_button.setEnabled(False)
            self.toggle_mod_button.setEnabled(False)
            self.delete_mod_button.setEnabled(False)
            self.update_mod_button.setEnabled(False)
            self.info_mod_button.setEnabled(False)

    def launch_game(self):
        """Запускает выбранную игру."""
        if self.current_game and self.current_game.exe_path:
            process = QProcess(self)
            process.start(self.current_game.exe_path)
            logger.info(f"Запуск игры: {self.current_game.name}")

    def toggle_mod(self):
        """Включает или отключает выбранный мод."""
        selected = self.mods_list.currentItem()
        if selected and self.current_game:
            mod_id = selected.text().split("ID: ")[1].split(" [")[0]
            is_enabled = "[Включен]" in selected.text()
            self.mod_manager.toggle_mod(self.current_game, mod_id, not is_enabled)
            self.update_game(self.current_game)

    def delete_mod(self):
        """Удаляет выбранный мод."""
        selected = self.mods_list.currentItem()
        if selected and self.current_game:
            mod_id = selected.text().split("ID: ")[1].split(" [")[0]
            mod_path = os.path.join(self.current_game.mods_path, mod_id)
            disabled_path = os.path.join(self.current_game.mods_path, f"{mod_id}_disabled")
            if os.path.exists(mod_path):
                import shutil
                shutil.rmtree(mod_path)
                self.mods_list.takeItem(self.mods_list.row(selected))
                logger.info(f"Мод {mod_id} удален для игры {self.current_game.name}")
            elif os.path.exists(disabled_path):
                import shutil
                shutil.rmtree(disabled_path)
                self.mods_list.takeItem(self.mods_list.row(selected))
                logger.info(f"Мод {mod_id} удален для игры {self.current_game.name}")
            else:
                QMessageBox.warning(
                    self, self.main_window.language_manager.get("error", "Ошибка"),
                    self.main_window.language_manager.get("mod_not_found", f"Мод {mod_id} не найден")
                )

    def update_mod(self):
        """Обновляет выбранный мод."""
        selected = self.mods_list.currentItem()
        if selected and self.current_game:
            mod_id = selected.text().split("ID: ")[1].split(" [")[0]
            self.mod_manager.download_mod(self.current_game, mod_id, self.main_window.console_tab)
            logger.info(f"Обновление мода {mod_id} для игры {self.current_game.name}")

    def show_mod_info(self):
        """Отображает информацию о выбранном моде."""
        selected = self.mods_list.currentItem()
        if selected and self.current_game:
            mod_id = selected.text().split("ID: ")[1].split(" [")[0]
            mod_info = asyncio.run(self.mod_manager.get_mod_info(mod_id))
            dialog = ModInfoDialog(mod_info, self.main_window.language_manager, self)
            dialog.exec()
