from loguru import logger
import requests
from bs4 import BeautifulSoup
import os

class DownloadManager:
    def __init__(self, steam_handler):
        self.steam_handler = steam_handler

    def start(self):
        """Запускает процесс скачивания модов (вызывается из UI)."""
        logger.info("Запущен процесс скачивания модов")
        # В текущей реализации UI (browser_tab.py) вызывает download_mod напрямую,
        # поэтому этот метод может быть использован для других сценариев в будущем.
        # Пока он просто логирует начало процесса.

    def download_mod(self, app_id, mod_id):
        """Скачивает мод через SteamHandler и возвращает результат."""
        try:
            success = self.steam_handler.download_mod(app_id, mod_id)
            if not success:
                logger.error(f"Не удалось скачать мод {mod_id} для игры {app_id}")
                self.log_failed_download(app_id, mod_id)
            return success
        except Exception as e:
            logger.error(f"Ошибка в DownloadManager для мода {mod_id} игры {app_id}: {e}")
            self.log_failed_download(app_id, mod_id)
            return False

    def log_failed_download(self, app_id, mod_id):
        """Сохраняет информацию о несохранённом моде в файл."""
        try:
            # Получаем название мода
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("div", class_="workshopItemTitle")
            mod_name = title.text.strip() if title else f"Мод {mod_id}"

            # Записываем в файл
            with open("failed_downloads.txt", "a", encoding="utf-8") as f:
                f.write(f"Название: {mod_name}\nID: {mod_id}\nСсылка: {url}\nИгра: {app_id}\n\n")
            logger.info(f"Информация о несохранённом моде {mod_id} записана в failed_downloads.txt")
        except Exception as e:
            logger.error(f"Ошибка при записи информации о несохранённом моде {mod_id}: {e}")

