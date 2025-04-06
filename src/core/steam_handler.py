import subprocess
from pathlib import Path
from loguru import logger

class SteamHandler:
    def __init__(self, steamcmd_path):
        self.steamcmd_path = Path(steamcmd_path)
        self.steamcmd_dir = self.steamcmd_path.parent  # Директория, где находится steamcmd.exe

    def download_mod(self, app_id, mod_id, progress_callback=None):
        if not self.steamcmd_path.exists():
            logger.error(f"SteamCMD не найден по пути: {self.steamcmd_path}")
            return False
        cmd = [
            str(self.steamcmd_path),
            "+login anonymous",
            f"+workshop_download_item {app_id} {mod_id}",
            "+quit"
        ]
        logger.info(f"Запуск SteamCMD с командой: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while process.poll() is None:
            line = process.stdout.readline().strip()
            if line:
                logger.info(f"SteamCMD: {line}")
                if progress_callback:
                    progress_callback(line)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            logger.info(f"Мод {mod_id} успешно скачан для игры {app_id}")
            return self.verify_mod(app_id, mod_id)
        else:
            logger.error(f"Ошибка при скачивании мода {mod_id}: {stderr}")
            return False

    def verify_mod(self, app_id, mod_id):
        # Путь к скачанному моду относительно директории SteamCMD
        mod_path = self.steamcmd_dir / "steamapps" / "workshop" / "content" / str(app_id) / str(mod_id)
        logger.debug(f"Проверка целостности мода {mod_id} по пути: {mod_path}")
        if mod_path.exists() and any(mod_path.iterdir()):
            logger.info(f"Проверка целостности мода {mod_id}: успешно")
            return True
        logger.error(f"Проверка целостности мода {mod_id}: файлы не найдены по пути {mod_path}")
        return False
