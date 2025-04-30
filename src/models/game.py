class Game:
    def __init__(self, name, app_id, exe_path, mods_path, mods=None):
        self.name = name
        self.app_id = app_id
        self.exe_path = exe_path
        self.mods_path = mods_path
        self.mods = mods or []
