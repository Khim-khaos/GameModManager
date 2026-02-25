# src/core/download_manager.py
import os
import shutil
from typing import List, Callable, Optional # Добавлены Callable, Optional
from loguru import logger
from src.models.mod import Mod
from src.models.game import Game
from src.core.steam_handler import SteamHandler

class DownloadManager:
    """Менеджер загрузок"""

    def __init__(self, steam_handler: SteamHandler):
        self.steam_handler = steam_handler
        self._download_queue: List[Mod] = []

    def add_to_queue(self, mod: Mod):
        """Добавление мода в очередь загрузки"""
        if not any(m.mod_id == mod.mod_id for m in self._download_queue):
            self._download_queue.append(mod)
            logger.info(f"[DownloadManager] Мод {mod.name} ({mod.mod_id}) добавлен в очередь.")
        else:
            logger.warning(f"[DownloadManager] Мод {mod.mod_id} уже находится в очереди.")

    def remove_from_queue(self, mod_id: str):
        """Удаление мода из очереди загрузки"""
        self._download_queue = [mod for mod in self._download_queue if mod.mod_id != mod_id]
        logger.debug(f"Мод с ID {mod_id} удален из очереди загрузки")

    def clear_queue(self):
        """Очистка всей очереди загрузки"""
        count = len(self._download_queue)
        self._download_queue.clear()
        logger.info(f"Очередь загрузки очищена. Удалено {count} модов.")

    def get_queue(self) -> List[Mod]:
        """Получение копии очереди загрузки"""
        return self._download_queue.copy()

    def is_in_queue(self, mod_id: str) -> bool:
        """Проверяет, находится ли мод с заданным ID в очереди."""
        return any(mod.mod_id == mod_id for mod in self._download_queue)

    # Модифицируем download_mods_queue для поддержки log_callback
    def download_mods_queue(self, game: Game, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Загрузка модов из очереди. Блокирует вызывающий поток."""
        if not self.steam_handler.is_initialized:
            logger.error("SteamCMD не инициализирован")
            if log_callback:
                log_callback("!!! ОШИБКА: SteamCMD не инициализирован.")
            return False

        if not os.path.exists(game.mods_path):
            try:
                os.makedirs(game.mods_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Не удалось создать папку модов: {e}")
                if log_callback:
                    log_callback(f"!!! ОШИБКА: Не удалось создать папку модов: {e}")
                return False

        mods_to_download = self._download_queue
        if not mods_to_download:
            logger.info("Очередь загрузки пуста")
            if log_callback:
                log_callback("-> Очередь загрузки пуста.")
            return True

        app_id = game.steam_id
        login_cmd = self.steam_handler.get_login_command() # Проверено, что метод существует

        mod_ids = [mod.mod_id for mod in mods_to_download]
        logger.info(f"Начинается загрузка {len(mod_ids)} модов для игры {game.name} (AppID: {app_id})")
        if log_callback:
            log_callback(f"-> Начинается загрузка {len(mod_ids)} модов для игры {game.name} (AppID: {app_id})")

        # Передаем log_callback в SteamHandler
        success = self.steam_handler.download_mods(app_id, mod_ids, log_callback=log_callback)
        if success:
            success = self._move_downloaded_mods(game)
            if success:
                logger.info("Все моды успешно загружены и перемещены.")
                if log_callback:
                    log_callback("=== Все моды успешно загружены и перемещены! ===")
                self._download_queue.clear()
                return True
            else:
                logger.error("Ошибка при перемещении модов")
                if log_callback:
                    log_callback("!!! ОШИБКА: Ошибка при перемещении модов.")
        else:
            logger.error("Ошибка при скачивании модов через SteamCMD")
            # Сообщение об ошибке уже должно быть передано через log_callback из SteamHandler
        return False

    def _move_downloaded_mods(self, game: Game) -> bool:
        """Перемещение скачанных модов в папку игры"""
        try:
            steamcmd_base_path = os.path.dirname(self.steam_handler.steamcmd_path)
            steamcmd_content_path = os.path.join(steamcmd_base_path, "steamapps", "workshop", "content", game.steam_id)

            logger.debug(f"Путь к скачанным модам: {steamcmd_content_path}")
            if os.path.exists(steamcmd_content_path):
                success_count = 0
                error_count = 0
                for mod in self._download_queue:
                    mod_source_path = os.path.join(steamcmd_content_path, mod.mod_id)
                    mod_dest_path = os.path.join(game.mods_path, mod.mod_id)
                    if os.path.exists(mod_source_path):
                        try:
                            if os.path.exists(mod_dest_path):
                                shutil.rmtree(mod_dest_path)
                            shutil.move(mod_source_path, mod_dest_path)
                            mod.local_path = mod_dest_path
                            success_count += 1
                            logger.debug(f"Мод {mod.mod_id} перемещен в {mod_dest_path}")
                        except Exception as e:
                            logger.error(f"Ошибка перемещения мода '{mod.name}' (ID: {mod.mod_id}): {e}")
                            error_count += 1
                    else:
                        logger.warning(f"Папка исходного мода не найдена: {mod_source_path}")
                        error_count += 1
                logger.info(f"Перемещение модов завершено. Успешно: {success_count}, Ошибок: {error_count}")
                return error_count == 0
            else:
                logger.warning(f"Папка с контентом не найдена: {steamcmd_content_path}")
                return False
        except Exception as e:
            logger.error(f"Ошибка перемещения модов: {e}")
            return False

    @property
    def download_queue(self) -> List[Mod]:
        """Свойство для получения очереди (для обратной совместимости)"""
        return self.get_queue()
