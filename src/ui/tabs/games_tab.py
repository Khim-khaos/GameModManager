from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QHBoxLayout, QMessageBox, QLabel
from core.game_manager import GameManager
from ui.dialogs.add_game_dialog import AddGameDialog
from ui.dialogs.edit_game_dialog import EditGameDialog
from loguru import logger
import requests
from bs4 import BeautifulSoup

class GamesTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.game_manager = GameManager()
        self.selected_game = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.game_list = QListWidget()
        self.update_game_list()
        layout.addWidget(self.game_list)

        self.info_label = QLabel("Информация об игре: выберите игру")
        layout.addWidget(self.info_label)
        self.path_label = QLabel("Путь к исполняемому файлу: -")
        layout.addWidget(self.path_label)
        self.mods_path_label = QLabel("Путь к папке модов: -")
        layout.addWidget(self.mods_path_label)
        self.mods_label = QLabel("Установленные моды:")
        layout.addWidget(self.mods_label)
        self.mods_list = QListWidget()
        layout.addWidget(self.mods_list)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton(self.parent.tr("add_game"))
        self.add_button.clicked.connect(self.add_game)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Редактировать игру")
        self.edit_button.clicked.connect(self.edit_game)
        button_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Удалить игру")
        self.remove_button.clicked.connect(self.remove_game)
        button_layout.addWidget(self.remove_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.game_list.itemClicked.connect(self.on_game_selected)

    def update_game_list(self):
        self.game_list.clear()
        for game in self.game_manager.games:
            try:
                item_text = f"{game['name']} (ID: {game['app_id']}) - Модов: {len(game['mods'])}"
                self.game_list.addItem(item_text)
            except (TypeError, KeyError) as e:
                logger.error(f"Ошибка при отображении игры: {e}, данные: {game}")
                self.game_list.addItem("Ошибка: некорректные данные игры")

    def update_ui_texts(self):
        self.add_button.setText(self.parent.tr("add_game"))
        self.edit_button.setText("Редактировать игру")
        self.remove_button.setText("Удалить игру")
        self.mods_label.setText("Установленные моды:")
        self.update_game_info()

    def get_mod_name(self, mod_id):
        """Получаем название мода из Steam Workshop."""
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("div", class_="workshopItemTitle")
            return title.text.strip() if title else f"Мод {mod_id}"
        except Exception as e:
            logger.error(f"Ошибка при получении названия мода {mod_id}: {e}")
            return f"Мод {mod_id}"

    def update_game_info(self):
        if self.selected_game:
            game = self.game_manager.get_game(self.selected_game)
            if game:
                self.info_label.setText(f"Информация об игре: {game['name']} (ID: {game['app_id']})")
                self.path_label.setText(f"Путь к исполняемому файлу: {game['exe_path']}")
                self.mods_path_label.setText(f"Путь к папке модов: {game['mods_path']}")
                self.mods_list.clear()
                for mod_id in game['mods']:
                    mod_name = self.get_mod_name(mod_id)
                    self.mods_list.addItem(f"{mod_name}-{mod_id}")
            else:
                self.clear_game_info()
        else:
            self.clear_game_info()

    def clear_game_info(self):
        self.info_label.setText("Информация об игре: выберите игру")
        self.path_label.setText("Путь к исполняемому файлу: -")
        self.mods_path_label.setText("Путь к папке модов: -")
        self.mods_list.clear()

    def on_game_selected(self, item):
        try:
            self.selected_game = item.text().split("ID: ")[1].split(")")[0].strip()
            self.update_game_info()
        except IndexError:
            logger.error("Ошибка при выборе игры: неверный формат строки")
            self.selected_game = None
            self.clear_game_info()

    def add_game(self):
        dialog = AddGameDialog(self.parent)
        if dialog.exec():
            name, exe_path, mods_path, app_id = dialog.get_data()
            if not all([name, exe_path, mods_path, app_id]):
                QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены!")
                return
            self.game_manager.add_game(name, exe_path, mods_path, app_id)
            self.update_game_list()
            self.parent.update_game_selector()

    def edit_game(self):
        if not self.selected_game:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для редактирования!")
            return
        dialog = EditGameDialog(self.parent, self.selected_game)
        if dialog.exec():
            self.update_game_list()
            self.update_game_info()
            self.parent.update_game_selector()

    def remove_game(self):
        if not self.selected_game:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для удаления!")
            return
        app_id = self.selected_game
        self.game_manager.games = [g for g in self.game_manager.games if g["app_id"] != app_id]
        self.game_manager.save_games()
        self.update_game_list()
        self.clear_game_info()
        self.selected_game = None
        self.parent.update_game_selector()
        logger.info(f"Игра с ID {app_id} удалена")

