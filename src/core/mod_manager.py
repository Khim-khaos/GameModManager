from pathlib import Path
from core.steam_handler import SteamHandler
from core.game_manager import GameManager
from loguru import logger
import shutil


class ModManager:
    def __init__(self, steamcmd_path):
        self.steamcmd_path = steamcmd_path
        self.steam_handler = SteamHandler(steamcmd_path)
        self.game_manager = GameManager()
        self.download_queue = []

    def add_to_queue(self, app_id, mod_id):
        self.download_queue.append((app_id, mod_id))
        logger.info(f"Мод {mod_id} добавлен в очередь для игры {app_id}")

    def download_next(self, progress_callback=None):
        if not self.download_queue:
            logger.warning("Очередь загрузки пуста")
            return False

        app_id, mod_id = self.download_queue.pop(0)
        success = self.steam_handler.download_mod(app_id, mod_id, progress_callback)

        if success:
            # Перемещаем мод в папку mods_path игры
            game = self.game_manager.get_game(app_id)
            if game and "mods_path" in game:
                source_path = Path(self.steamcmd_path).parent / "steamapps" / "workshop" / "content" / str(
                    app_id) / str(mod_id)
                dest_path = Path(game["mods_path"]) / str(mod_id)

                try:
                    if source_path.exists():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)  # Создаем папку назначения, если её нет
                        if dest_path.exists():
                            shutil.rmtree(dest_path)  # Удаляем старую версию мода, если она есть
                        shutil.move(source_path, dest_path)
                        logger.info(f"Мод {mod_id} перемещен в {dest_path}")
                        # Обновляем список модов в игре
                        if mod_id not in game["mods"]:
                            game["mods"].append(mod_id)
                            self.game_manager.save_games()
                    else:
                        logger.error(f"Исходный путь мода {source_path} не найден")
                        success = False
                except Exception as e:
                    logger.error(f"Ошибка при перемещении мода {mod_id}: {e}")
                    success = False
            else:
                logger.error(f"Игра {app_id} не найдена или не указан mods_path")
                success = False

        return success

    def get_installed_mods(self, app_id):
        game = self.game_manager.get_game(app_id)
        return game["mods"] if game and "mods" in game else []

