import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from loguru import logger

# Настройка логирования
logger.add("Logs/app.log", rotation="500 KB", level="INFO")

if __name__ == "__main__":
    logger.info("Запуск приложения GameModManager")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

