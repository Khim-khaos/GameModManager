# src/game_manager.py
import json
import os
import traceback

class GameManager:
    def __init__(self, data_path="src/data/games.json"):
        self.data_path = data_path
        self.games = self.load_games()

    def load_games(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print("Ошибка: Не удалось декодировать JSON. Файл games.json может быть поврежден или пуст.")
                    return {}
        else:
            return {}

    def save_games(self):
        try:
            with open(self.data_path, 'w') as f:
                json.dump(self.games, f, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении игр: {e}")
            traceback.print_exc()

    def add_game(self, game_id, game_name, executable_path, mods_path):
        if game_id in self.games:
            print(f"Ошибка: Игра с ID {game_id} уже существует.")
            return False
        self.games[game_id] = {
            "name": game_name,
            "executable_path": executable_path,
            "mods_path": mods_path,
            "installed_mods": []
        }
        self.save_games()
        print(f"Игра добавлена: ID={game_id}, Name={game_name}, Exec={executable_path}, Mods={mods_path}")
        return True

    def get_game(self, game_id):
        return self.games.get(game_id)

    def get_all_games(self):
        return self.games

    def edit_game(self, game_id, game_name, executable_path, mods_path):
        if game_id not in self.games:
            print(f"Ошибка: Игра с ID {game_id} не найдена.")
            return False
        self.games[game_id]["name"] = game_name
        self.games[game_id]["executable_path"] = executable_path
        self.games[game_id]["mods_path"] = mods_path
        self.save_games()
        print(f"Игра отредактирована: ID={game_id}, Name={game_name}, Exec={executable_path}, Mods={mods_path}")
        return True

    def remove_game(self, game_id):
        if game_id not in self.games:
            print(f"Ошибка: Игра с ID {game_id} не найдена.")
            return False
        del self.games[game_id]
        self.save_games()
        print(f"Игра удалена: ID={game_id}")
        return True

    def add_installed_mod(self, game_id, mod_id):
        if game_id not in self.games:
            print(f"Ошибка: Игра с ID {game_id} не найдена.")
            return False
        if mod_id not in self.games[game_id]["installed_mods"]:
            self.games[game_id]["installed_mods"].append(mod_id)
            self.save_games()
            print(f"Мод {mod_id} добавлен для игры {game_id}")
            return True
        else:
            print(f"Мод {mod_id} уже установлен для игры {game_id}")
            return False

    def remove_installed_mod(self, game_id, mod_id):
        if game_id not in self.games:
            print(f"Ошибка: Игра с ID {game_id} не найдена.")
            return False
        if mod_id in self.games[game_id]["installed_mods"]:
            self.games[game_id]["installed_mods"].remove(mod_id)
            self.save_games()
            print(f"Мод {mod_id} удален для игры {game_id}")
            return True
        else:
            print(f"Мод {mod_id} не установлен для игры {game_id}")
            return False

    def get_installed_mods(self, game_id):
        if game_id not in self.games:
            print(f"Ошибка: Игра с ID {game_id} не найдена.")
            return []
        return self.games[game_id]["installed_mods"]
