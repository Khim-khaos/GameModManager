import json
from pathlib import Path
from loguru import logger

class GameManager:
    def __init__(self):
        self.games_file = Path(__file__).parent.parent / "data" / "games.json"
        self.games = self.load_games()

    def load_games(self):
        if not self.games_file.exists():
            logger.info("Файл games.json не существует, создается пустой список")
            self.save_games([])  # Создаем файл с пустым списком
            return []
        try:
            with open(self.games_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    logger.warning("Неверный формат games.json, ожидался список")
                    self.save_games([])  # Перезаписываем некорректный файл
                    return []
        except json.JSONDecodeError:
            logger.error("Ошибка декодирования games.json, возвращается пустой список")
            self.save_games([])  # Перезаписываем поврежденный файл
            return []
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке games.json: {e}")
            return []

    def save_games(self, games=None):
        if games is None:
            games = self.games
        with open(self.games_file, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=4, ensure_ascii=False)

    def add_game(self, name, exe_path, mods_path, app_id):
        game = {
            "name": name,
            "exe_path": exe_path,
            "mods_path": mods_path,
            "app_id": app_id,
            "mods": []
        }
        self.games.append(game)
        self.save_games()
        logger.info(f"Добавлена игра: {name} (ID: {app_id})")

    def get_game(self, app_id):
        return next((game for game in self.games if game["app_id"] == app_id), None)