from PySide6.QtCore import QProcess
from loguru import logger
import os

class SteamHandler:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.process = None

    def download_mod(self, app_id, mod_id, mods_path, console_tab):
        steamcmd_path = self.settings_manager.settings.get("steamcmd_path", "")
        if not steamcmd_path or not os.path.exists(steamcmd_path):
            logger.error("SteamCMD не найден")
            return False

        self.process = QProcess(console_tab)
        self.process.setProgram(steamcmd_path)
        command = f"+login anonymous +workshop_download_item {app_id} {mod_id} +quit"
        self.process.setArguments(command.split())
        self.process.setWorkingDirectory(mods_path)
        self.process.start()
        logger.info(f"Начата загрузка мода {mod_id} для игры {app_id}")
        return True
