# download_management.py
class DownloadManager:
    def __init__(self):
        self.downloads = {}

    def start_download(self, game_id, mod_id):
        # Логика начала загрузки
        print(f"Начало загрузки мода {mod_id} для игры {game_id}")
        self.downloads[mod_id] = {"status": "downloading", "progress": 0}

    def update_progress(self, mod_id, progress):
        if mod_id in self.downloads:
            self.downloads[mod_id]["progress"] = progress

    def finish_download(self, mod_id):
        if mod_id in self.downloads:
            self.downloads[mod_id]["status"] = "completed"

    def get_download_status(self, mod_id):
        return self.downloads.get(mod_id, {"status": "not started", "progress": 0})
