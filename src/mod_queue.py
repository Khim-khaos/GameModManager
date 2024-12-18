# src/mod_queue.py
class ModQueue:
    def __init__(self):
        self.queue = []

    def add_mod(self, game_id, mod_id, mods_path):
        self.queue.append({"game_id": game_id, "mod_id": mod_id, "mods_path": mods_path})

    def get_next_mod(self):
        if self.queue:
            return self.queue.pop(0)
        return None

    def is_empty(self):
        return not self.queue

    def clear(self):
        self.queue = []

    def get_queue(self):
        return self.queue
