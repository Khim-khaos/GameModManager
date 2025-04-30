import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.settings_manager import SettingsManager
from loguru import logger

if __name__ == "__main__":
    # Настройка логирования
    logger.add("Logs/app.log", rotation="10 MB", level="DEBUG")

    # Инициализация приложения
    app = QApplication(sys.argv)

    # Загрузка настроек
    settings_manager = SettingsManager()
    settings_manager.load_settings()

    # Создание главного окна
    window = MainWindow(settings_manager)
    window.show()

    # Запуск приложения
    sys.exit(app.exec())