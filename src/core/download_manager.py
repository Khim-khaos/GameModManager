import os
import requests
import shutil
from loguru import logger
from bs4 import BeautifulSoup
from .steam_handler import SteamHandler
from pathlib import Path

class DownloadManager:
    def __init__(self, mod_manager, on_download_complete=None, on_download_progress=None):
        self.mod_manager = mod_manager
        self.steam_handler = self.mod_manager.steam_handler
        self.on_download_complete = on_download_complete
        self.on_download_progress = on_download_progress

    def start(self, update_status_callback=None):
        if not self.mod_manager.download_queue:
            logger.warning("Очередь загрузки пуста")
            return

        for app_id, mod_id in self.mod_manager.download_queue.copy():
            mod_name = self.get_mod_name(mod_id)
            logger.debug(f"Начало обработки мода {mod_id} ({mod_name}) для игры {app_id}")
            if update_status_callback:
                update_status_callback(mod_id, mod_name, "downloading")

            try:
                logger.info(f"Попытка загрузки мода {mod_id} для игры {app_id}")
                success = self.steam_handler.download_mod(app_id, mod_id, progress_callback=None)
                if success:
                    logger.debug(f"Мод {mod_id} успешно скачан, проверка целостности...")
                    if not self.steam_handler.verify_mod(app_id, mod_id):
                        logger.error(f"Проверка целостности мода {mod_id} не прошла")
                        success = False

                if success:
                    # Перемещаем мод в папку mods_path игры
                    game = self.mod_manager.game_manager.get_game(app_id)
                    if game and "mods_path" in game:
                        source_path = os.path.join(os.path.dirname(self.mod_manager.steamcmd_path), "steamapps", "workshop", "content", str(app_id), str(mod_id))
                        dest_path = os.path.join(game["mods_path"], str(mod_id))

                        logger.debug(f"Перемещение мода {mod_id} из {source_path} в {dest_path}")
                        try:
                            if os.path.exists(source_path):
                                if os.path.exists(dest_path):
                                    logger.debug(f"Удаление старой версии мода по пути {dest_path}")
                                    shutil.rmtree(dest_path)
                                shutil.move(source_path, dest_path)
                                logger.info(f"Мод {mod_id} перемещен в {dest_path}")
                                # Проверяем, что мод действительно переместился
                                if os.path.exists(dest_path):
                                    self.mod_manager.add_installed_mod(app_id, mod_id)
                                else:
                                    logger.error(f"Мод {mod_id} не найден в {dest_path} после перемещения")
                                    success = False
                            else:
                                logger.error(f"Исходный путь мода {source_path} не найден")
                                success = False
                        except Exception as e:
                            logger.error(f"Ошибка при перемещении мода {mod_id}: {e}")
                            success = False
                    else:
                        logger.error(f"Игра {app_id} не найдена или не указан mods_path")
                        success = False

                if success:
                    logger.info(f"Мод {mod_name}-{mod_id} успешно загружен для игры {app_id}")
                    if update_status_callback:
                        update_status_callback(mod_id, mod_name, "success")
                    logger.debug("DownloadManager: Вызов on_download_complete (успех)")
                    if self.on_download_complete:
                        self.on_download_complete(True)
                    self.mod_manager.download_queue.remove((app_id, mod_id))
                else:
                    logger.error(f"Не удалось загрузить мод {mod_id} для игры {app_id}")
                    self.log_failed_download(app_id, mod_id, mod_name)
                    if update_status_callback:
                        update_status_callback(mod_id, mod_name, "failed")
                    logger.debug("DownloadManager: Вызов on_download_complete (ошибка)")
                    if self.on_download_complete:
                        self.on_download_complete(False)
                    self.mod_manager.download_queue.remove((app_id, mod_id))

            except Exception as e:
                logger.error(f"Неожиданная ошибка при загрузке мода {mod_id} для игры {app_id}: {e}")
                self.log_failed_download(app_id, mod_id, mod_name)
                if update_status_callback:
                    update_status_callback(mod_id, mod_name, "failed")
                logger.debug("DownloadManager: Вызов on_download_complete (исключение)")
                if self.on_download_complete:
                    self.on_download_complete(False)
                if (app_id, mod_id) in self.mod_manager.download_queue:
                    self.mod_manager.download_queue.remove((app_id, mod_id))

    def get_mod_name(self, mod_id):
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(url, timeout=5, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("div", class_="workshopItemTitle")
            return title.text.strip() if title else f"Мод {mod_id}"
        except Exception as e:
            logger.error(f"Не удалось получить название мода {mod_id}: {e}")
            return f"Мод {mod_id}"

    def log_failed_download(self, app_id, mod_id, mod_name):
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Logs")
        os.makedirs(logs_dir, exist_ok=True)
        file_path = os.path.join(logs_dir, f"failed_download_{mod_id}.txt")
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Не удалось загрузить мод:\n")
            f.write(f"Название: {mod_name}\n")
            f.write(f"ID мода: {mod_id}\n")
            f.write(f"Игра ID: {app_id}\n")
            f.write(f"Ссылка: {url}\n")
        logger.info(f"Создан файл с информацией о неудачной загрузке: {file_path}")
