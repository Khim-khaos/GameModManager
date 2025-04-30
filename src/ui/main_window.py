from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QTabWidget, QComboBox, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QUrl, QRect
from PySide6.QtWebEngineWidgets import QWebEngineView
from ui.tabs.games_tab import GamesTab
from ui.tabs.browser_tab import BrowserTab
from ui.tabs.console_tab import ConsoleTab
from ui.tabs.logs_tab import LogsTab
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.add_game_dialog import AddGameDialog
from core.game_manager import GameManager
from core.steam_handler import SteamHandler
from core.mod_manager import ModManager
from core.download_manager import DownloadManager
from core.language_manager import LanguageManager
from qtawesome import icon
from loguru import logger
import os
import asyncio


class MainWindow(QMainWindow):
    """Главное окно приложения GameModManager."""

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.language_manager = LanguageManager(settings_manager)
        self.game_manager = GameManager()
        self.mod_manager = ModManager()
        self.steam_handler = SteamHandler(settings_manager)
        self.mod_manager.set_steam_handler(self.steam_handler)
        self.download_manager = DownloadManager(self.mod_manager)
        self.setWindowTitle(self.language_manager.get("window_title"))
        self.load_window_geometry()

        # Основной контейнер
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Панель выбора игры и добавления
        self.top_layout = QHBoxLayout()
        self.game_selector = QComboBox()
        self.game_selector.addItem(self.language_manager.get("select_game"), None)
        for game in self.game_manager.get_games():
            self.game_selector.addItem(f"{game.name} ({game.app_id})", game)
        self.game_selector.currentIndexChanged.connect(self.on_game_selected)
        self.add_game_button = QPushButton(
            icon("fa5.plus"), self.language_manager.get("add_game", "Добавить игру")  # Исправлено
        )
        self.add_game_button.clicked.connect(self.add_game)
        self.top_layout.addWidget(self.game_selector)
        self.top_layout.addWidget(self.add_game_button)
        self.layout.addLayout(self.top_layout)

        # Вкладки
        self.tabs = QTabWidget()
        self.games_tab = GamesTab(self)
        self.browser_tab = BrowserTab(self)
        self.console_tab = ConsoleTab(self)
        self.logs_tab = LogsTab(self)
        self.tabs.addTab(self.games_tab, icon("fa5.gamepad"), self.language_manager.get("tab_games"))
        self.tabs.addTab(self.browser_tab, icon("fa5.globe"), self.language_manager.get("tab_browser"))
        self.tabs.addTab(self.console_tab, icon("fa5.terminal"), self.language_manager.get("tab_console"))
        self.tabs.addTab(self.logs_tab, icon("fa5.file-alt"), self.language_manager.get("tab_logs"))
        self.layout.addWidget(self.tabs)

        # Кнопка настроек
        self.settings_button = QPushButton(
            icon("fa5.cog"), self.language_manager.get("settings")
        )
        self.settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(self.settings_button)

        # Домашняя страница (по умолчанию)
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("https://steamcommunity.com/workshop/"))
        self.tabs.setCurrentIndex(0)
        self.apply_settings()

    def add_game(self):
        """Открывает диалог добавления новой игры."""
        dialog = AddGameDialog(self.game_manager, self.language_manager, self)
        if dialog.exec():
            self.game_selector.clear()
            self.game_selector.addItem(self.language_manager.get("select_game"), None)
            for game in self.game_manager.get_games():
                self.game_selector.addItem(f"{game.name} ({game.app_id})", game)
            logger.info("Новая игра добавлена")

    def on_game_selected(self):
        """Обновляет вкладки при выборе игры."""
        selected_game = self.game_selector.currentData()
        self.games_tab.update_game(selected_game)
        self.browser_tab.update_game(selected_game)
        self.console_tab.update_game(selected_game)
        if selected_game:
            asyncio.run(self.download_manager.process_queue(self.console_tab, self))

    def open_settings(self):
        """Открывает диалог настроек."""
        dialog = SettingsDialog(self.settings_manager, self.language_manager, self)
        if dialog.exec():
            self.apply_settings()
            self.language_manager.reload()
            self.update_ui_texts()

    def apply_settings(self):
        """Применяет настройки интерфейса."""
        settings = self.settings_manager.settings
        theme = settings.get("theme", "light")
        opacity = settings.get("opacity", 1.0)
        font_size = settings.get("font_size", 12)
        background = settings.get("background", "")

        # Выбор цветовой схемы
        if theme == "dark":
            base_color = "background-color: #2e2e2e; color: #ffffff;"
        else:
            base_color = "background-color: #ffffff; color: #000000;"

        self.setStyleSheet(f"""
            QMainWindow {{
                {base_color}
                background-image: url({background});
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover;
            }}
            QWidget {{
                font-size: {font_size}px;
                opacity: {opacity};
            }}
            QTabWidget::pane {{
                border: 1px solid #cccccc;
            }}
            QTabBar::tab {{
                {base_color}
                padding: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: #0078d7;
                color: #ffffff;
            }}
        """)
        logger.info("Настройки интерфейса применены")

    def update_ui_texts(self):
        """Обновляет тексты интерфейса."""
        self.setWindowTitle(self.language_manager.get("window_title"))
        self.game_selector.setItemText(0, self.language_manager.get("select_game"))
        self.add_game_button.setText(self.language_manager.get("add_game", "Добавить игру"))
        self.tabs.setTabText(0, self.language_manager.get("tab_games"))
        self.tabs.setTabText(1, self.language_manager.get("tab_browser"))
        self.tabs.setTabText(2, self.language_manager.get("tab_console"))
        self.tabs.setTabText(3, self.language_manager.get("tab_logs"))
        self.settings_button.setText(self.language_manager.get("settings"))
        logger.info("Тексты интерфейса обновлены")

    def load_window_geometry(self):
        """Загружает геометрию окна из настроек."""
        settings = self.settings_manager.settings
        width = settings.get("window_width", 1200)
        height = settings.get("window_height", 800)
        x = settings.get("window_x", 100)
        y = settings.get("window_y", 100)
        self.setGeometry(x, y, width, height)
        logger.info("Загружена геометрия окна")

    def closeEvent(self, event):
        """Сохраняет геометрию окна при закрытии."""
        geometry = self.geometry()
        self.settings_manager.settings.update({
            "window_x": geometry.x(),
            "window_y": geometry.y(),
            "window_width": geometry.width(),
            "window_height": geometry.height()
        })
        self.settings_manager.save_settings()
        logger.info("Геометрия окна сохранена")
        super().closeEvent(event)
