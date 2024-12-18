# src/ui/main_window.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QTabWidget, \
    QMessageBox, QSplitter, QTextEdit, QInputDialog
from PyQt5.QtCore import Qt, QSettings
from src.game_manager import GameManager
from src.mod_queue import ModQueue
from src.browser import Browser
from src.download_management import DownloadManager
from src.ui.add_game_dialog import AddGameDialog
from src.ui.edit_game_dialog import EditGameDialog
from src.ui.settings_dialog import SettingsDialog
import os
import subprocess
import traceback


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Mod Manager")
        self.setGeometry(100, 100, 800, 600)

        self.settings = QSettings("GameModManager", "Settings")
        self.steamcmd_path = self.settings.value("steamcmd_path", "")

        self.game_manager = GameManager()
        self.mod_queue = ModQueue()
        self.download_manager = DownloadManager(self.steamcmd_path)
        self.download_manager.console_output.connect(self.update_console)
        self.download_manager.download_started.connect(self.show_message)
        self.download_manager.download_finished.connect(self.show_message)
        self.download_manager.download_error.connect(self.show_message)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.init_ui()

    def init_ui(self):
        # Левая панель (список игр и модов)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Кнопки управления играми
        game_buttons_layout = QHBoxLayout()
        self.add_game_button = QPushButton("Добавить игру")
        self.add_game_button.clicked.connect(self.open_add_game_dialog)
        self.edit_game_button = QPushButton("Редактировать игру")
        self.edit_game_button.clicked.connect(self.open_edit_game_dialog)
        self.remove_game_button = QPushButton("Удалить игру")
        self.remove_game_button.clicked.connect(self.remove_selected_game)
        game_buttons_layout.addWidget(self.add_game_button)
        game_buttons_layout.addWidget(self.edit_game_button)
        game_buttons_layout.addWidget(self.remove_game_button)
        left_layout.addLayout(game_buttons_layout)

        # Список игр
        self.game_list = QListWidget()
        self.game_list.itemSelectionChanged.connect(self.update_mod_list)
        left_layout.addWidget(self.game_list)

        # Список установленных модов
        self.installed_mods_list = QListWidget()
        left_layout.addWidget(self.installed_mods_list)

        # Список модов в очереди
        self.mod_queue_list = QListWidget()
        left_layout.addWidget(self.mod_queue_list)

        # Кнопки управления модами
        mod_buttons_layout = QHBoxLayout()
        self.download_mod_button = QPushButton("Загрузить мод")
        self.download_mod_button.clicked.connect(self.add_mod_to_queue_dialog)
        self.download_mod_list_button = QPushButton("Загрузить все моды")
        self.download_mod_list_button.clicked.connect(self.download_mod_list)
        self.remove_mod_button = QPushButton("Удалить мод")
        self.remove_mod_button.clicked.connect(self.remove_selected_installed_mod)
        mod_buttons_layout.addWidget(self.download_mod_button)
        mod_buttons_layout.addWidget(self.download_mod_list_button)
        mod_buttons_layout.addWidget(self.remove_mod_button)
        left_layout.addLayout(mod_buttons_layout)

        # Кнопка запуска игры
        self.launch_game_button = QPushButton("Запустить игру")
        self.launch_game_button.clicked.connect(self.launch_selected_game)
        left_layout.addWidget(self.launch_game_button)

        # Кнопка настроек
        self.settings_button = QPushButton("Настройки")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        left_layout.addWidget(self.settings_button)

        # Центральная панель (браузер и консоль)
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)

        self.tab_widget = QTabWidget()

        # Браузер
        self.browser = Browser()
        self.tab_widget.addTab(self.browser, "Браузер")
        self.browser.add_mod_to_queue_requested.connect(self.add_mod_to_queue_from_browser)
        self.browser.add_collection_to_queue_requested.connect(self.add_collection_to_queue_from_browser)

        # Консоль
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.tab_widget.addTab(self.console, "Консоль")

        center_layout.addWidget(self.tab_widget)

        # Разделитель
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.setSizes([200, 600])  # Начальные размеры

        self.main_layout.addWidget(splitter)

        self.load_games()

    def load_games(self):
        self.game_list.clear()
        games = self.game_manager.get_all_games()
        for game_id, game_data in games.items():
            self.game_list.addItem(f"{game_data['name']} ({game_id})")

    def open_add_game_dialog(self):
        try:
            dialog = AddGameDialog(self)
            if dialog.exec_():
                game_id, game_name, executable_path, mods_path = dialog.get_game_data()
                print(
                    f"Данные из AddGameDialog в MainWindow: ID={game_id}, Name={game_name}, Exec={executable_path}, Mods={mods_path}")
                if self.game_manager.add_game(game_id, game_name, executable_path, mods_path):
                    self.load_games()
                else:
                    QMessageBox.warning(self, "Ошибка", "Игра с таким ID уже существует.")
        except Exception as e:
            print(f"Ошибка в open_add_game_dialog: {e}")
            traceback.print_exc()

    def open_edit_game_dialog(self):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для редактирования.")
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        game_data = self.game_manager.get_game(game_id)
        if not game_data:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить данные об игре.")
            return

        dialog = EditGameDialog(self, game_data)
        if dialog.exec_():
            game_name, executable_path, mods_path = dialog.get_game_data()
            if self.game_manager.edit_game(game_id, game_name, executable_path, mods_path):
                self.load_games()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось отредактировать игру.")

    def remove_selected_game(self):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для удаления.")
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        if self.game_manager.remove_game(game_id):
            self.load_games()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить игру.")

    def update_mod_list(self):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            self.installed_mods_list.clear()
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        installed_mods = self.game_manager.get_installed_mods(game_id)
        self.installed_mods_list.clear()
        for mod_id in installed_mods:
            self.installed_mods_list.addItem(str(mod_id))

        # Обновляем URL браузера при выборе игры
        game_data = self.game_manager.get_game(game_id)
        if game_data:
            self.browser.load_url(f"https://steamcommunity.com/app/{game_id}/workshop/")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self, self.steamcmd_path)
        if dialog.exec_():
            self.steamcmd_path = dialog.get_steamcmd_path()
            self.download_manager.steamcmd_path = self.steamcmd_path

    def add_mod_to_queue_dialog(self):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для загрузки мода.")
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        game_data = self.game_manager.get_game(game_id)
        if not game_data:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить данные об игре.")
            return

        mod_id, ok = QInputDialog.getText(self, "Загрузка мода", "Введите ID мода:")
        if ok and mod_id:
            self.mod_queue.add_mod(game_id, mod_id, game_data["mods_path"])
            self.update_mod_queue_list()
            QMessageBox.information(self, "Мод добавлен", f"Мод {mod_id} добавлен в очередь загрузки.")

    def add_mod_to_queue_from_browser(self, mod_id):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для загрузки мода.")
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        game_data = self.game_manager.get_game(game_id)
        if not game_data:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить данные об игре.")
            return

        self.mod_queue.add_mod(game_id, mod_id, game_data["mods_path"])
        self.update_mod_queue_list()
        QMessageBox.information(self, "Мод добавлен", f"Мод {mod_id} добавлен в очередь загрузки.")

    def add_collection_to_queue_from_browser(self, mod_ids):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для загрузки модов.")
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        game_data = self.game_manager.get_game(game_id)
        if not game_data:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить данные об игре.")
            return

        for mod_id in mod_ids:
            self.mod_queue.add_mod(game_id, mod_id, game_data["mods_path"])
        self.update_mod_queue_list()
        QMessageBox.information(self, "Коллекция добавлена", f"Коллекция модов добавлена в очередь загрузки.")

    def update_mod_queue_list(self):
        self.mod_queue_list.clear()
        for mod_data in self.mod_queue.get_all_mods():
            self.mod_queue_list.addItem(f"Мод {mod_data['mod_id']} для игры {mod_data['game_id']}")

    def download_mod_list(self):
        if self.mod_queue.is_empty():
            QMessageBox.warning(self, "Ошибка", "Очередь загрузки пуста.")
            return

        if self.download_manager.download_mod_list(self.mod_queue, self.game_manager):
            QMessageBox.information(self, "Загрузка начата", "Загрузка модов из очереди начата.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось начать загрузку модов.")

    def remove_selected_installed_mod(self):
        selected_game_item = self.game_list.currentItem()
        selected_mod_item = self.installed_mods_list.currentItem()
        if not selected_game_item or not selected_mod_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру и мод для удаления.")
            return

        game_id = selected_game_item.text().split('(')[-1].replace(')', '')
        mod_id = selected_mod_item.text()
        if self.game_manager.remove_installed_mod(game_id, mod_id):
            self.update_mod_list()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить мод.")

    def launch_selected_game(self):
        selected_item = self.game_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для запуска.")
            return

        game_id = selected_item.text().split('(')[-1].replace(')', '')
        game_data = self.game_manager.get_game(game_id)
        if not game_data:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить данные об игре.")
            return

        executable_path = game_data["executable_path"]
        if not os.path.exists(executable_path):
            QMessageBox.warning(self, "Ошибка", "Неверный путь до исполняемого файла игры.")
            return

        try:
            subprocess.Popen(executable_path)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось запустить игру: {e}")

    def update_console(self, message):
        self.console.append(message)

    def show_message(self, message):
        QMessageBox.information(self, "Сообщение", message)
