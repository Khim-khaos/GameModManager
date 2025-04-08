from PySide6.QtWidgets import QMainWindow, QTabWidget, QMenuBar, QMessageBox, QProgressBar, QComboBox, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QPixmap, QBrush
from ui.tabs.games_tab import GamesTab
from ui.tabs.browser_tab import BrowserTab
from ui.tabs.console_tab import ConsoleTab
from ui.dialogs.settings_dialog import SettingsDialog
from data.config import Config
from core.download_manager import DownloadManager
from core.game_manager import GameManager
from core.mod_manager import ModManager
from loguru import logger
import json
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.game_manager = GameManager()
        self.mod_manager = ModManager(self.config.get("steamcmd_path"))
        self.load_language()
        self.setWindowTitle(self.tr("title"))
        self.resize(800, 600)
        self.apply_theme()

        # Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.statusBar().addWidget(self.progress_bar)

        # Менеджер загрузок
        self.download_manager = DownloadManager(self.mod_manager, self.on_download_complete, self.on_download_progress)

        # Создание меню
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        settings_action = self.menu_bar.addAction(self.tr("settings"))
        settings_action.triggered.connect(self.open_settings)

        # Основной layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Выпадающий список игр
        self.game_selector = QComboBox()
        self.game_selector.addItem("Выберите игру")
        self.update_game_selector()
        self.game_selector.currentTextChanged.connect(self.on_game_selected_combo)
        main_layout.addWidget(self.game_selector)

        # Создание вкладок (сначала BrowserTab, затем GamesTab)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.browser_tab = BrowserTab(self, self.mod_manager)  # Сначала создаём BrowserTab
        self.games_tab = GamesTab(self)  # Затем GamesTab
        self.console_tab = ConsoleTab(self)

        self.tabs.addTab(self.games_tab, self.tr("tab_games"))
        self.tabs.addTab(self.browser_tab, self.tr("tab_browser"))
        self.tabs.addTab(self.console_tab, self.tr("tab_console"))

        # Связь выбора игры
        self.games_tab.game_list.itemClicked.connect(self.on_game_selected_list)

        self.setCentralWidget(main_widget)
        logger.info("Главное окно инициализировано")

    def load_language(self):
        lang_file = f"language/{self.config.get('language')}.json"
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл языка {lang_file} не найден!")
            self.translations = {}

    def tr(self, key):
        return self.translations.get(key, key)

    def apply_theme(self):
        palette = QPalette()
        theme = self.config.get("theme")
        background_image = self.config.get("background_image")
        opacity = self.config.get("opacity", 1.0)

        if theme == "dark":
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
        else:
            palette.setColor(QPalette.Window, Qt.white)
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, Qt.white)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, Qt.lightGray)
            palette.setColor(QPalette.ButtonText, Qt.black)

        self.setPalette(palette)

        if background_image and Path(background_image).exists():
            palette.setBrush(QPalette.Window, QBrush(QPixmap(background_image)))
            self.setPalette(palette)
            logger.info(f"Задний фон установлен: {background_image}")
        else:
            logger.info("Задний фон не установлен или файл не найден")

        self.setWindowOpacity(float(opacity))
        logger.info(f"Прозрачность установлена: {opacity}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.load_language()
            self.apply_theme()
            self.update_ui()
            self.mod_manager.steamcmd_path = self.config.get("steamcmd_path")
            self.download_manager = DownloadManager(self.mod_manager, self.on_download_complete, self.on_download_progress)

    def update_ui(self):
        self.setWindowTitle(self.tr("title"))
        self.menu_bar.clear()
        settings_action = self.menu_bar.addAction(self.tr("settings"))
        settings_action.triggered.connect(self.open_settings)
        self.tabs.setTabText(0, self.tr("tab_games"))
        self.tabs.setTabText(1, self.tr("tab_browser"))
        self.tabs.setTabText(2, self.tr("tab_console"))
        self.games_tab.update_ui_texts()
        self.browser_tab.update_ui_texts()
        self.console_tab.update_ui_texts()

    def update_game_selector(self):
        self.game_selector.clear()
        self.game_selector.addItem("Выберите игру")
        for game in self.game_manager.games:
            self.game_selector.addItem(f"{game['name']} (ID: {game['app_id']})")

    def on_game_selected_combo(self, text):
        if text and text != "Выберите игру":
            try:
                app_id = text.split("ID: ")[1].split(")")[0].strip()
                logger.debug(f"Выбран app_id из комбо: {app_id}")
                self.browser_tab.set_game(app_id)
                self.games_tab.selected_game = app_id
                self.games_tab.update_game_info()
            except (IndexError, AttributeError):
                logger.error(f"Ошибка при выборе игры из комбо: неверный формат строки '{text}'")
                QMessageBox.warning(self, "Ошибка", "Не удалось выбрать игру из выпадающего списка!")

    def on_game_selected_list(self, item):
        if item:
            text = item.text()
            try:
                app_id = text.split("ID: ")[1].split(")")[0].strip()
                logger.debug(f"Выбран app_id из списка: {app_id}")
                self.browser_tab.set_game(app_id)
                for i in range(self.game_selector.count()):
                    if app_id in self.game_selector.itemText(i):
                        self.game_selector.setCurrentIndex(i)
                        break
            except (IndexError, AttributeError):
                logger.error(f"Ошибка при выборе игры из списка: неверный формат строки '{text}'")
                QMessageBox.warning(self, "Ошибка", "Не удалось выбрать игру из списка!")

    def on_download_complete(self, success):
        self.progress_bar.setVisible(False)
        if success:
            self.games_tab.update_game_list()
            self.games_tab.update_game_info()
            self.browser_tab.update_queue()
            self.update_game_selector()
            logger.info("Загрузка мода завершена успешно")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить мод!")
            logger.error("Загрузка мода завершилась с ошибкой")

    def on_download_progress(self, message):
        self.progress_bar.setVisible(True)
        if "Progress" in message:
            try:
                percent = int(message.split("%")[0].split()[-1])
                self.progress_bar.setValue(percent)
            except (ValueError, IndexError):
                self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 0)
