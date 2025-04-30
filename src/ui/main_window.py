from PySide6.QtWidgets import QMainWindow, QTabWidget, QMenuBar, QProgressBar, QComboBox, QVBoxLayout, QWidget, \
    QMessageBox, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPalette, QColor, QPixmap, QBrush
from ui.tabs.games_tab import GamesTab
from ui.tabs.browser_tab import BrowserTab
from ui.tabs.console_tab import ConsoleTab
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.add_game_dialog import AddGameDialog
from ui.dialogs.edit_game_dialog import EditGameDialog
from data.config import Config
from core.download_manager import DownloadManager
from core.game_manager import GameManager
from core.mod_manager import ModManager
from loguru import logger
import json
from pathlib import Path
import shutil
import sys

class MainWindow(QMainWindow):
    def __init__(self, mod_manager=None):
        super().__init__()
        self.config = Config()
        self.game_manager = GameManager()
        self.mod_manager = mod_manager
        self.selected_game = None
        self.translations = {}
        self.background_pixmap = None
        self.load_language()
        self.setWindowTitle(self.tr("title"))
        self.resize(800, 600)

        # Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.statusBar().addWidget(self.progress_bar)

        # Менеджер загрузок
        self.download_manager = DownloadManager(self.mod_manager, self.on_download_complete,
                                                self.on_download_progress) if self.mod_manager else None

        # Создание меню
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        settings_action = self.menu_bar.addAction(self.tr("settings"))
        settings_action.triggered.connect(self.open_settings)

        # Основной layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Layout для селектора игр и кнопок управления играми
        game_control_layout = QHBoxLayout()

        # Выпадающий список игр
        self.game_selector = QComboBox()
        self.game_selector.addItem("Выберите игру")
        self.game_selector.setMinimumWidth(300)
        self.game_selector.setMaximumWidth(400)
        self.game_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        if self.mod_manager:
            self.update_game_selector()
        self.game_selector.currentTextChanged.connect(self.on_game_selected_combo)
        game_control_layout.addWidget(self.game_selector)

        # Кнопки управления играми
        self.add_game_button = QPushButton(self.tr("add_game"))
        self.add_game_button.clicked.connect(self.add_game)
        game_control_layout.addWidget(self.add_game_button)

        self.edit_game_button = QPushButton(self.tr("edit_game"))
        self.edit_game_button.clicked.connect(self.edit_game)
        game_control_layout.addWidget(self.edit_game_button)

        self.remove_game_button = QPushButton(self.tr("remove_game"))
        self.remove_game_button.clicked.connect(self.remove_game)
        game_control_layout.addWidget(self.remove_game_button)

        main_layout.addLayout(game_control_layout)

        # Создание вкладок
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.browser_tab = BrowserTab(self, self.mod_manager)
        self.games_tab = GamesTab(self)
        self.console_tab = ConsoleTab(self)

        self.tabs.addTab(self.games_tab, self.tr("tab_games"))
        self.tabs.addTab(self.browser_tab, self.tr("tab_browser"))
        self.tabs.addTab(self.console_tab, self.tr("tab_console"))

        self.setCentralWidget(main_widget)
        if self.mod_manager:
            logger.info("Главное окно инициализировано")

        # Проверяем очередь загрузки при запуске
        if self.mod_manager:
            self.check_pending_downloads()

        # Применяем тему после создания всех виджетов
        self.apply_theme()

    def load_language(self):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        lang_file = base_path / "language" / f"{self.config.get('language')}.json"
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

        # Определяем путь для кэша фона
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent
        cache_dir = base_path / "data" / "background_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Кэширование фоновой картинки
        if background_image and Path(background_image).exists():
            # Копируем файл в кэш
            cache_file = cache_dir / Path(background_image).name
            try:
                shutil.copy(background_image, cache_file)
                logger.info(f"Фоновая картинка скопирована в кэш: {cache_file}")
            except Exception as e:
                logger.error(f"Ошибка при копировании фоновой картинки в кэш: {e}")
            self.background_pixmap = QPixmap(background_image)
            logger.info(f"Фоновая картинка загружена: {background_image}")
        else:
            # Если оригинальный файл не существует, пробуем загрузить из кэша
            if background_image:
                cache_file = cache_dir / Path(background_image).name
                if cache_file.exists():
                    self.background_pixmap = QPixmap(str(cache_file))
                    logger.info(f"Фоновая картинка загружена из кэша: {cache_file}")
                else:
                    self.background_pixmap = None
                    logger.info("Фоновая картинка не найдена ни в оригинале, ни в кэше")
            else:
                self.background_pixmap = None
                logger.info("Фоновая картинка не установлена")

        # Устанавливаем цвета с учётом прозрачности
        if theme == "dark":
            window_color = QColor(53, 53, 53, int(255 * opacity))
            palette.setColor(QPalette.Window, window_color)
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255, 255))
            base_color = QColor(25, 25, 25, int(255 * opacity))
            palette.setColor(QPalette.Base, base_color)
            alternate_base_color = QColor(53, 53, 53, int(255 * opacity))
            palette.setColor(QPalette.AlternateBase, alternate_base_color)
            palette.setColor(QPalette.Text, QColor(255, 255, 255, 255))
            button_color = QColor(53, 53, 53, int(255 * opacity))
            palette.setColor(QPalette.Button, button_color)
            palette.setColor(QPalette.ButtonText, QColor(255, 255, 255, 255))
        else:
            window_color = QColor(255, 255, 255, int(255 * opacity))
            palette.setColor(QPalette.Window, window_color)
            palette.setColor(QPalette.WindowText, QColor(0, 0, 0, 255))
            base_color = QColor(255, 255, 255, int(255 * opacity))
            palette.setColor(QPalette.Base, base_color)
            alternate_base_color = QColor(200, 200, 200, int(255 * opacity))
            palette.setColor(QPalette.AlternateBase, alternate_base_color)
            palette.setColor(QPalette.Text, QColor(0, 0, 0, 255))
            button_color = QColor(200, 200, 200, int(255 * opacity))
            palette.setColor(QPalette.Button, button_color)
            palette.setColor(QPalette.ButtonText, QColor(0, 0, 0, 255))

        # Устанавливаем фоновую картинку
        if self.background_pixmap:
            palette.setBrush(QPalette.Window, QBrush(self.background_pixmap))

        # Применяем палитру ко всем виджетам
        self.setPalette(palette)
        self.tabs.setPalette(palette)
        self.game_selector.setPalette(palette)
        self.add_game_button.setPalette(palette)
        self.edit_game_button.setPalette(palette)
        self.remove_game_button.setPalette(palette)

        # Применяем палитру к дочерним виджетам вкладок
        self.games_tab.setPalette(palette)
        self.browser_tab.setPalette(palette)
        self.console_tab.setPalette(palette)

        # Устанавливаем атрибут прозрачности и стиль для всех вкладок
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.tabs.setAttribute(Qt.WA_TranslucentBackground, True)
        self.games_tab.setAttribute(Qt.WA_TranslucentBackground, True)
        self.browser_tab.setAttribute(Qt.WA_TranslucentBackground, True)
        self.console_tab.setAttribute(Qt.WA_TranslucentBackground, True)

        # Устанавливаем стиль для прозрачности вкладок и их содержимого
        tab_background = f"background-color: rgba(53, 53, 53, {int(255 * opacity)});" if theme == "dark" else f"background-color: rgba(255, 255, 255, {int(255 * opacity)});"
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ {tab_background} }}
            QTabBar::tab {{ color: rgb(255, 255, 255); background-color: rgba(53, 53, 53, {int(255 * opacity)}); }}
            QTabBar::tab:selected {{ background-color: rgba(80, 80, 80, {int(255 * opacity)}); }}
        """ if theme == "dark" else f"""
            QTabWidget::pane {{ {tab_background} }}
            QTabBar::tab {{ color: rgb(0, 0, 0); background-color: rgba(255, 255, 255, {int(255 * opacity)}); }}
            QTabBar::tab:selected {{ background-color: rgba(220, 220, 220, {int(255 * opacity)}); }}
        """)

        # Явно устанавливаем прозрачный фон для содержимого вкладок
        self.games_tab.setStyleSheet(f"background: transparent;")
        self.browser_tab.setStyleSheet(f"background: transparent;")
        self.console_tab.setStyleSheet(f"background: transparent;")

        # Убедимся, что текст остаётся непрозрачным
        self.game_selector.setStyleSheet("QComboBox { color: rgb(255, 255, 255); }" if theme == "dark" else "QComboBox { color: rgb(0, 0, 0); }")
        self.add_game_button.setStyleSheet("QPushButton { color: rgb(255, 255, 255); }" if theme == "dark" else "QPushButton { color: rgb(0, 0, 0); }")
        self.edit_game_button.setStyleSheet("QPushButton { color: rgb(255, 255, 255); }" if theme == "dark" else "QPushButton { color: rgb(0, 0, 0); }")
        self.remove_game_button.setStyleSheet("QPushButton { color: rgb(255, 255, 255); }" if theme == "dark" else "QPushButton { color: rgb(0, 0, 0); }")

        # Принудительно обновляем виджеты
        self.update()
        self.repaint()
        self.tabs.update()
        self.tabs.repaint()
        self.game_selector.update()
        self.game_selector.repaint()
        self.add_game_button.update()
        self.add_game_button.repaint()
        self.edit_game_button.update()
        self.edit_game_button.repaint()
        self.remove_game_button.update()
        self.remove_game_button.repaint()
        self.games_tab.update()
        self.games_tab.repaint()
        self.browser_tab.update()
        self.browser_tab.repaint()
        self.console_tab.update()
        self.console_tab.repaint()

        logger.info(f"Тема применена с прозрачностью: {opacity}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec()

    def on_settings_changed(self):
        logger.debug("Начало обработки изменения настроек")
        self.load_language()
        logger.debug("Язык обновлён")
        self.apply_theme()
        logger.debug("Тема применена")
        self.update_ui()
        logger.debug("UI обновлён")
        if self.mod_manager:
            self.mod_manager.steamcmd_path = self.config.get("steamcmd_path")
            self.download_manager = DownloadManager(self.mod_manager, self.on_download_complete,
                                                    self.on_download_progress)
        logger.debug("Обработка изменения настроек завершена")

        # Если игра выбрана, перезагружаем URL в браузере
        if self.selected_game:
            self.browser_tab.set_game(self.selected_game)

    def update_ui(self):
        self.setWindowTitle(self.tr("title"))
        self.menu_bar.clear()
        settings_action = self.menu_bar.addAction(self.tr("settings"))
        settings_action.triggered.connect(self.open_settings)
        self.tabs.setTabText(0, self.tr("tab_games"))
        self.tabs.setTabText(1, self.tr("tab_browser"))
        self.tabs.setTabText(2, self.tr("tab_console"))
        self.add_game_button.setText(self.tr("add_game"))
        self.edit_game_button.setText(self.tr("edit_game"))
        self.remove_game_button.setText(self.tr("remove_game"))
        self.games_tab.update_ui_texts()
        self.browser_tab.update_ui_texts()
        self.console_tab.update_ui_texts()

        # Принудительно обновляем виджеты
        self.update()
        self.repaint()
        self.tabs.update()
        self.tabs.repaint()
        self.game_selector.update()
        self.game_selector.repaint()
        self.add_game_button.update()
        self.add_game_button.repaint()
        self.edit_game_button.update()
        self.edit_game_button.repaint()
        self.remove_game_button.update()
        self.remove_game_button.repaint()
        self.games_tab.update()
        self.games_tab.repaint()
        self.browser_tab.update()
        self.browser_tab.repaint()
        self.console_tab.update()
        self.console_tab.repaint()

    def update_game_selector(self):
        current_app_id = self.selected_game
        self.game_selector.blockSignals(True)
        self.game_selector.clear()
        self.game_selector.addItem("Выберите игру")
        for game in self.game_manager.games:
            display_text = f"{game['name']} (ID: {game['app_id']})"
            self.game_selector.addItem(display_text)
            self.game_selector.setItemData(self.game_selector.count() - 1, display_text, Qt.ToolTipRole)

        if current_app_id:
            for i in range(self.game_selector.count()):
                item_text = self.game_selector.itemText(i)
                if f"ID: {current_app_id}" in item_text:
                    self.game_selector.setCurrentIndex(i)
                    break
        self.game_selector.blockSignals(False)

    def on_game_selected_combo(self, text):
        if text and text != "Выберите игру":
            try:
                app_id = text.split("ID: ")[1].split(")")[0].strip()
                self.selected_game = app_id
                logger.debug(f"Выбран app_id из комбо: {app_id}")
                self.browser_tab.set_game(app_id)
                self.games_tab.refresh_mods_list()
            except (IndexError, AttributeError):
                logger.error(f"Ошибка при выборе игры из комбо: неверный формат строки '{text}'")
                QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Ошибка",
                                                                 "Не удалось выбрать игру из выпадающего списка!"))
        else:
            self.selected_game = None
            self.games_tab.refresh_mods_list()

    def on_download_complete(self, success):
        logger.debug("MainWindow: Начало on_download_complete")
        self.progress_bar.setVisible(False)
        if success:
            self.games_tab.refresh_mods_list()
            self.browser_tab.update_queue()
            logger.info("Загрузка мода завершена успешно")
            self.console_tab.append_message("Загрузка мода завершена успешно")
        else:
            logger.error("Загрузка мода завершилась с ошибкой")
            self.console_tab.append_message("Ошибка: Не удалось загрузить мод! Подробности в логе.")
        logger.debug("MainWindow: Конец on_download_complete")

    def on_download_progress(self, message):
        self.progress_bar.setVisible(True)
        if "Downloading" in message or "Progress" in message:
            try:
                if "Progress" in message:
                    percent = float(message.split("Progress: ")[1].split("%")[0])
                    self.progress_bar.setValue(int(percent))
                else:
                    self.progress_bar.setRange(0, 0)
            except (ValueError, IndexError):
                self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 0)

    def check_pending_downloads(self):
        pending_downloads = self.mod_manager.check_pending_downloads()
        if not pending_downloads:
            logger.debug("Нет незавершённых загрузок модов")
            return

        mod_list = "\n".join([f"Игра ID: {app_id}, Мод ID: {mod_id}" for app_id, mod_id in pending_downloads])
        reply = QMessageBox.question(
            self,
            "Незавершённые загрузки",
            f"Обнаружены незавершённые загрузки модов:\n{mod_list}\n\nПродолжить загрузку?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            logger.info("Пользователь выбрал продолжить загрузку модов")
            if self.download_manager:
                self.download_manager.start_download()
        else:
            logger.info("Пользователь отказался от продолжения загрузки модов")
            self.mod_manager.download_queue = []
            self.mod_manager.save_queue()

    def add_game(self):
        dialog = AddGameDialog(self)
        if dialog.exec():
            name, exe_path, mods_path, app_id = dialog.get_data()
            if not all([name, exe_path, mods_path, app_id]):
                QMessageBox.warning(self, self.tr("error"), self.tr("all_fields_required"))
                return
            self.game_manager.add_game(name, exe_path, mods_path, app_id)
            self.update_game_selector()

    def edit_game(self):
        if not self.selected_game:
            QMessageBox.warning(self, self.tr("error"), self.tr("select_game_to_edit"))
            return
        dialog = EditGameDialog(self, self.selected_game)
        if dialog.exec():
            self.mod_manager._load_installed_mods()
            self.games_tab.refresh_mods_list()
            self.update_game_selector()

    def remove_game(self):
        if not self.selected_game:
            QMessageBox.warning(self, self.tr("error"), self.tr("select_game_to_remove"))
            return
        app_id = self.selected_game
        self.game_manager.games = [g for g in self.game_manager.games if g["app_id"] != app_id]
        self.game_manager.save_games()
        if app_id in self.mod_manager.installed_mods:
            del self.mod_manager.installed_mods[app_id]
            self.mod_manager.needs_refresh = True
            logger.info(f"Удалены установленные моды для игры {app_id}")
        self.games_tab.refresh_mods_list()
        self.selected_game = None
        self.update_game_selector()
        logger.info(f"Игра с ID {app_id} удалена")
