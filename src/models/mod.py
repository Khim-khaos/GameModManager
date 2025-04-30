class Mod:
    def __init__(self, mod_id, name="", dependencies=None):
        self.mod_id = mod_id
        self.name = name
        self.dependencies = dependencies or []
