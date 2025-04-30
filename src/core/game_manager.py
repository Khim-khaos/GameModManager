import json
import os
from models.game import Game
from loguru import logger

class GameManager:
    def __init__(self):
        self.games_path = "data/games.json"
        self.games = []
        self.load_games()

    def load_games(self):
        try:
            if os.path.exists(self.games_path):
                with open(self.games_path, "r", encoding="utf-8") as f:
                    games_data = json.load(f)
                    self.games = [Game(**data) for data in games_data]
                logger.info("Игры загружены")
            else:
                self.save_games()
        except Exception as e:
            logger.error(f"Ошибка загрузки игр: {e}")

    def save_games(self):
        try:
            os.makedirs(os.path.dirname(self.games_path), exist_ok=True)
            with open(self.games_path, "w", encoding="utf-8") as f:
                json.dump([game.__dict__ for game in self.games], f, indent=4, ensure_ascii=False)
            logger.info("Игры сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения игр: {e}")

    def add_game(self, name, app_id, exe_path, mods_path):
        game = Game(name=name, app_id=app_id, exe_path=exe_path, mods_path=mods_path)
        self.games.append(game)
        self.save_games()
        return game

    def get_games(self):
        return self.games
