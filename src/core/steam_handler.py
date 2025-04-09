import subprocess
import os
from loguru import logger
import requests
from bs4 import BeautifulSoup

class SteamHandler:
    def __init__(self, steamcmd_path):
        self.steamcmd_path = steamcmd_path

    def download_mod(self, app_id, mod_id):
        """Скачивает мод через SteamCMD и проверяет его целостность."""
        cmd = [
            self.steamcmd_path,
            "+login anonymous",
            f"+workshop_download_item {app_id} {mod_id}",
            "+quit"
        ]
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            output = process.stdout + process.stderr
            logger.info(f"SteamCMD: {output}")

            if "ERROR! Download item" in output or "Failure" in output:
                logger.error(f"Ошибка скачивания мода {mod_id} для игры {app_id}: {output}")
                self.log_failed_download(app_id, mod_id)
                return False

            # Проверяем целостность мода
            if self.verify_mod(app_id, mod_id):
                logger.info(f"Мод {mod_id} успешно скачан для игры {app_id}")
                return True
            else:
                logger.error(f"Мод {mod_id} не прошёл проверку целостности")
                self.log_failed_download(app_id, mod_id)
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка выполнения SteamCMD для мода {mod_id}: {e.stderr}")
            self.log_failed_download(app_id, mod_id)
            return False
        except Exception as e:
            logger.error(f"Неизвестная ошибка при скачивании мода {mod_id}: {e}")
            self.log_failed_download(app_id, mod_id)
            return False

    def verify_mod(self, app_id, mod_id):
        """Проверяет, что мод скачан корректно."""
        mod_path = os.path.join(self.steamcmd_path, "steamapps", "workshop", "content", str(app_id), str(mod_id))
        logger.debug(f"Проверка целостности мода {mod_id} по пути: {mod_path}")
        if os.path.exists(mod_path) and os.listdir(mod_path):
            return True
        logger.error(f"Проверка целостности мода {mod_id}: файлы не найдены по пути {mod_path}")
        return False

    def log_failed_download(self, app_id, mod_id):
        """Сохраняет информацию о несохранённом моде в файл."""
        try:
            # Получаем название мода
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(url, timeout=5, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("div", class_="workshopItemTitle")
            mod_name = title.text.strip() if title else f"Мод {mod_id}"

            # Записываем в файл
            with open("failed_downloads.txt", "a", encoding="utf-8") as f:
                f.write(f"Название: {mod_name}\nID: {mod_id}\nСсылка: {url}\nИгра: {app_id}\n\n")
            logger.info(f"Информация о несохранённом моде {mod_id} записана в failed_downloads.txt")
        except Exception as e:
            logger.error(f"Ошибка при записи информации о несохранённом моде {mod_id}: {e}")

