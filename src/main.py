import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.dialogs.settings_dialog import SettingsDialog
from core.mod_manager import ModManager
from data.config import Config
from loguru import logger

if __name__ == "__main__":
    logger.info("Запуск приложения GameModManager")
    app = QApplication(sys.argv)
    config = Config()

    # Проверяем, указан ли путь к SteamCMD
    steamcmd_path = config.get("steamcmd_path")
    if not steamcmd_path or not os.path.exists(steamcmd_path):
        logger.warning("Путь к SteamCMD не указан или неверный, открытие окна настроек")
        temp_window = MainWindow(mod_manager=None)
        settings_dialog = SettingsDialog(temp_window)
        if settings_dialog.exec():
            steamcmd_path = config.get("steamcmd_path")
            if not steamcmd_path or not os.path.exists(steamcmd_path):
                logger.error("Путь к SteamCMD всё ещё не указан, завершение работы")
                sys.exit(1)
        else:
            logger.info("Пользователь отменил настройки, завершение работы")
            sys.exit(1)

    # Создаём ModManager с валидным путём
    mod_manager = ModManager(steamcmd_path)

    # Создаём основное окно
    window = MainWindow(mod_manager=mod_manager)
    window.show()

    # Запускаем приложение
    exit_code = app.exec()

    sys.exit(exit_code)
