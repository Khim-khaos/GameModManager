from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QListWidget, QHBoxLayout, QDialog, QLabel, QLineEdit, QFileDialog, QMessageBox, QSplitter, QTextEdit
from PyQt5.QtCore import Qt, QUrl
from src.game_manager import GameManager
from src.mod_queue import ModQueue
from src.browser import Browser
from src.ui.add_game_dialog import AddGameDialog
from src.ui.edit_game_dialog import EditGameDialog
from src.ui.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Mod Manager")
        self.setGeometry(100, 100, 1200, 800)

        self.game_manager = GameManager()
        self.mod_queue = ModQueue(self.game_manager)
        self.browser = Browser()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Левая панель
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)

        self.games_list = QListWidget()
        self.left_layout.addWidget(self.games_list)

        self.buttons_layout = QHBoxLayout()
        self.add_game_button = QPushButton("Добавить игру")
        self.edit_game_button = QPushButton("Редактировать игру")
        self.remove_game_button = QPushButton("Удалить игру")
        self.settings_button = QPushButton("Настройки")
        self.buttons_layout.addWidget(self.add_game_button)
        self.buttons_layout.addWidget(self.edit_game_button)
        self.buttons_layout.addWidget(self.remove_game_button)
        self.buttons_layout.addWidget(self.settings_button)
        self.left_layout.addLayout(self.buttons_layout)

        self.installed_mods_label = QLabel("Установленные моды:")
        self.left_layout.addWidget(self.installed_mods_label)
        self.installed_mods_list = QListWidget()
        self.left_layout.addWidget(self.installed_mods_list)

        self.mods_to_download_label = QLabel("Моды для загрузки:")
        self.left_layout.addWidget(self.mods_to_download_label)
        self.mods_to_download_list = QListWidget()
        self.left_layout.addWidget(self.mods_to_download_list)

        self.add_mod_button = QPushButton("Добавить мод в загрузку")
        self.left_layout.addWidget(self.add_mod_button)
        self.add_mod_button.clicked.connect(self.add_mod_from_browser)

        self.install_mods_button = QPushButton("Установить моды")
        self.left_layout.addWidget(self.install_mods_button)
        self.install_mods_button.clicked.connect(self.install_mods)

        # Консоль
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.left_layout.addWidget(self.console_output)

        # Разделитель
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.browser)
        self.splitter.setSizes([300, 900]) # Устанавливаем начальные размеры

        self.main_layout.addWidget(self.splitter)

        self.add_game_button.clicked.connect(self.show_add_game_dialog)
        self.edit_game_button.clicked.connect(self.show_edit_game_dialog)
        self.remove_game_button.clicked.connect(self.remove_game)
        self.settings_button.clicked.connect(self.show_settings_dialog)
        self.games_list.itemSelectionChanged.connect(self.load_workshop)
        self.games_list.itemSelectionChanged.connect(self.update_installed_mods_list)

        self.load_games()

    def load_games(self):
        self.games_list.clear()
        games = self.game_manager.get_all_games()
        for game_id, game_data in games.items():
            self.games_list.addItem(f"{game_data['name']} ({game_id})")

    def show_add_game_dialog(self):
        dialog = AddGameDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            game_id, game_name, executable_path, mods_path, _ = dialog.get_game_data()
            self.game_manager.add_game(game_id, game_name, executable_path, mods_path, self.game_manager.settings.get('steamcmd_path', ''))
            self.load_games()

    def show_edit_game_dialog(self):
        selected_item = self.games_list.currentItem()
        if selected_item:
            selected_text = selected_item.text()
            game_id = selected_text.split('(')[-1].replace(')', '')
            game_data = self.game_manager.get_game(game_id)
            if game_data:
                dialog = EditGameDialog(self, game_data)
                if dialog.exec_() == QDialog.Accepted:
                    game_name, executable_path, mods_path, _ = dialog.get_game_data()
                    self.game_manager.edit_game(game_id, game_name, executable_path, mods_path, self.game_manager.settings.get('steamcmd_path', ''))
                    self.load_games()

    def remove_game(self):
        selected_item = self.games_list.currentItem()
        if selected_item:
            selected_text = selected_item.text()
            game_id = selected_text.split('(')[-1].replace(')', '')
            reply = QMessageBox.question(self, 'Удаление игры', f'Вы уверены, что хотите удалить игру {game_id}?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.game_manager.remove_game(game_id)
                self.load_games()

    def load_workshop(self):
        selected_item = self.games_list.currentItem()
        if selected_item:
            selected_text = selected_item.text()
            game_id = selected_text.split('(')[-1].replace(')', '')
            self.browser.load_url(f"https://steamcommunity.com/app/{game_id}/workshop/")

    def show_settings_dialog(self):
        dialog = SettingsDialog(self, self.game_manager.settings)
        if dialog.exec_() == QDialog.Accepted:
            self.game_manager.settings = dialog.get_settings()
            self.game_manager.save_settings()

    def add_mod_to_download_list(self, game_id, mod_id):
        self.mods_to_download_list.addItem(f"Мод {mod_id} для игры {game_id}")

    def add_mod_from_browser(self):
        selected_item = self.games_list.currentItem()
        if selected_item:
            selected_text = selected_item.text()
            game_id = selected_text.split('(')[-1].replace(')', '')
            url = self.browser.view.url().toString()
            if "steamcommunity.com/sharedfiles/filedetails/" in url:
                mod_id = url.split("?id=")[1]
                self.add_mod_to_download_list(game_id, mod_id)
            else:
                QMessageBox.warning(self, "Ошибка", "Откройте страницу мода в мастерской Steam.")

    def update_installed_mods_list(self):
        selected_item = self.games_list.currentItem()
        if selected_item:
            selected_text = selected_item.text()
            game_id = selected_text.split('(')[-1].replace(')', '')
            game_data = self.game_manager.get_game(game_id)
            if game_data:
                self.installed_mods_list.clear()
                for mod_data in game_data.get('installed_mods', []):
                    self.installed_mods_list.addItem(f"{mod_data['name']} ({mod_data['id']})")

    def install_mods(self):
        self.mod_queue.start_processing()
        for i in range(self.mods_to_download_list.count()):
            item_text = self.mods_to_download_list.item(i).text()
            mod_id = item_text.split(" ")[1]
            game_id = item_text.split(" ")[-1]
            self.mod_queue.add_mod_to_queue(game_id, mod_id, self.console_output)
        self.mods_to_download_list.clear()
