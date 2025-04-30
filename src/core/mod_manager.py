from pathlib import Path
from core.steam_handler import SteamHandler
from core.game_manager import GameManager
from loguru import logger
import shutil
import os
import time
import json
import sys

class ModManager:
    def __init__(self, steamcmd_path):
        # Определяем базовый путь (где находится .exe или скрипт)
        if getattr(sys, 'frozen', False):
            # Если запущен .exe, используем путь к .exe
            base_path = Path(sys.executable).parent
        else:
            # Если запущен скрипт, используем текущую директорию
            base_path = Path.cwd()

        self.steamcmd_path = steamcmd_path
        self.steam_handler = SteamHandler(steamcmd_path)
        self.game_manager = GameManager()
        self.download_queue = []
        self.installed_mods = {}
        self.needs_refresh = True
        self.queue_file = base_path / "download_queue.json"  # Относительный путь
        self.load_queue()
        self._load_installed_mods()

    def load_queue(self):
        if self.queue_file.exists():
            try:
                with open(self.queue_file, "r", encoding="utf-8") as f:
                    self.download_queue = json.load(f)
                logger.info(f"Очередь загрузки загружена из {self.queue_file}: {self.download_queue}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке очереди из {self.queue_file}: {e}")
                self.download_queue = []
        else:
            logger.debug("Файл очереди загрузки не найден, инициализируем пустую очередь")
            self.download_queue = []

    def save_queue(self):
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(self.download_queue, f, indent=4)
            logger.debug(f"Очередь загрузки сохранена в {self.queue_file}: {self.download_queue}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении очереди в {self.queue_file}: {e}")

    def _load_installed_mods(self):
        if not self.needs_refresh:
            logger.debug("Используется кэшированный список установленных модов")
            return

        logger.debug("Начало загрузки установленных модов")
        for game in self.game_manager.games:
            app_id = game["app_id"]
            if "mods_path" not in game:
                logger.warning(f"Игра {app_id} не имеет указанного mods_path, пропускаем загрузку модов")
                continue
            mods_path = Path(game["mods_path"])
            logger.debug(f"Проверка модов для игры {app_id} в папке: {mods_path}")
            if not mods_path.exists():
                logger.error(f"Папка mods_path {mods_path} не существует")
                continue
            if not os.access(mods_path, os.R_OK):
                logger.error(f"Нет прав доступа для чтения папки {mods_path}")
                continue

            mods_from_filesystem = []
            for item in mods_path.iterdir():
                if item.is_dir():
                    mod_id = item.name
                    mods_from_filesystem.append(mod_id)
                    logger.info(f"Обнаружен мод {mod_id} в папке {mods_path}")

            mods_from_config = game.get("mods", [])
            verified_mods = list(set(mods_from_config + mods_from_filesystem))
            final_mods = {}
            for mod_id in verified_mods:
                mod_path = mods_path / str(mod_id)
                logger.debug(f"Проверка мода {mod_id} по пути: {mod_path}")
                if mod_path.exists() and mod_path.is_dir():
                    installed_date = os.path.getmtime(mod_path)
                    final_mods[mod_id] = {
                        "path": str(mod_path),
                        "installed_date": installed_date
                    }
                    logger.info(f"Мод {mod_id} подтверждён для игры {app_id} в {mod_path}, дата установки: {installed_date}")
                else:
                    logger.warning(f"Мод {mod_id} для игры {app_id} не найден в {mod_path}, исключаем из списка")

            self.installed_mods[app_id] = final_mods
            logger.debug(f"Загружены установленные моды для игры {app_id}: {list(final_mods.keys())}")
            game["mods"] = list(final_mods.keys())

        self.game_manager.save_games()
        self.needs_refresh = False

    def get_installed_mods(self, app_id):
        if app_id not in self.installed_mods or self.needs_refresh:
            self._load_installed_mods()
        return list(self.installed_mods.get(app_id, {}).keys())

    def get_installed_mod_info(self, app_id, mod_id):
        return self.installed_mods.get(app_id, {}).get(mod_id, None)

    def add_to_queue(self, app_id, mod_id):
        self.download_queue.append((app_id, mod_id))
        self.needs_refresh = True
        self.save_queue()  # Сохраняем очередь после добавления
        logger.info(f"Мод {mod_id} добавлен в очередь для игры {app_id}")

    def add_installed_mod(self, app_id, mod_id):
        game = self.game_manager.get_game(app_id)
        if not game or "mods_path" not in game:
            logger.error(f"Игра {app_id} не найдена или не указан mods_path")
            return

        mods_path = Path(game["mods_path"])
        mod_path = mods_path / str(mod_id)
        logger.debug(f"Добавление мода {mod_id} для игры {app_id}, проверка пути: {mod_path}")
        if not mod_path.exists():
            logger.error(f"Мод {mod_id} не найден в {mod_path}, не добавляем в список установленных")
            return

        if app_id not in self.installed_mods:
            self.installed_mods[app_id] = {}
        self.installed_mods[app_id][mod_id] = {
            "path": str(mod_path),
            "installed_date": time.time()
        }
        logger.info(f"Мод {mod_id} добавлен в список установленных для игры {app_id}")

        if "mods" not in game:
            game["mods"] = []
        if mod_id not in game["mods"]:
            game["mods"].append(mod_id)
            self.game_manager.save_games()
            logger.debug(f"Мод {mod_id} синхронизирован с GameManager для игры {app_id}")

        self.needs_refresh = True

    def download_next(self, progress_callback=None):
        if not self.download_queue:
            logger.warning("Очередь загрузки пуста")
            return False

        app_id, mod_id = self.download_queue.pop(0)
        success = self.steam_handler.download_mod(app_id, mod_id, progress_callback)

        if success:
            game = self.game_manager.get_game(app_id)
            if game and "mods_path" in game:
                source_path = Path(self.steamcmd_path).parent / "steamapps" / "workshop" / "content" / str(app_id) / str(mod_id)
                dest_path = Path(game["mods_path"]) / str(mod_id)

                try:
                    if source_path.exists():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.move(source_path, dest_path)
                        logger.info(f"Мод {mod_id} перемещён в {dest_path}")
                        self.add_installed_mod(app_id, mod_id)
                    else:
                        logger.error(f"Исходный путь мода {source_path} не найден")
                        success = False
                except Exception as e:
                    logger.error(f"Ошибка при перемещении мода {mod_id}: {e}")
                    success = False
            else:
                logger.error(f"Игра {app_id} не найдена или не указан mods_path")
                success = False

        self.save_queue()  # Сохраняем очередь после удаления элемента
        return success

    def check_pending_downloads(self):
        """Проверяет, есть ли моды в очереди, которые ещё не установлены."""
        if not self.download_queue:
            return []

        pending_downloads = []
        for app_id, mod_id in self.download_queue:
            if app_id not in self.installed_mods or mod_id not in self.installed_mods[app_id]:
                pending_downloads.append((app_id, mod_id))
        return pending_downloads
