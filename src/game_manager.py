import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
GAMES_FILE = os.path.join(DATA_DIR, 'games.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

class GameManager:
    def __init__(self):
        self.games = self.load_games()
        self.settings = self.load_settings()

    def load_games(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(GAMES_FILE):
            return {}
        with open(GAMES_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_games(self):
        with open(GAMES_FILE, 'w') as f:
            json.dump(self.games, f, indent=4)

    def load_settings(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(SETTINGS_FILE):
            return {}
        with open(SETTINGS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_settings(self):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def add_game(self, game_id, game_name, executable_path, mods_path, steamcmd_path):
        self.games[game_id] = {
            'name': game_name,
            'executable_path': executable_path,
            'mods_path': mods_path,
            'steamcmd_path': steamcmd_path,
            'installed_mods': []
        }
        self.save_games()

    def edit_game(self, game_id, game_name, executable_path, mods_path, steamcmd_path):
        if game_id in self.games:
            self.games[game_id]['name'] = game_name
            self.games[game_id]['executable_path'] = executable_path
            self.games[game_id]['mods_path'] = mods_path
            self.games[game_id]['steamcmd_path'] = steamcmd_path
            self.save_games()

    def remove_game(self, game_id):
        if game_id in self.games:
            del self.games[game_id]
            self.save_games()

    def get_game(self, game_id):
        return self.games.get(game_id)

    def get_all_games(self):
        return self.games

    def add_installed_mod(self, game_id, mod_data):
        if game_id in self.games:
            if mod_data not in self.games[game_id]['installed_mods']:
                self.games[game_id]['installed_mods'].append(mod_data)
                self.save_games()

    def remove_installed_mod(self, game_id, mod_id):
        if game_id in self.games:
            self.games[game_id]['installed_mods'] = [mod for mod in self.games[game_id]['installed_mods'] if mod['id'] != mod_id]
            self.save_games()
