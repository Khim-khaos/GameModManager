# -*- coding: utf-8 -*-
"""
Модель игры
"""

from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class Game:
    """Модель игры"""

    name: str
    steam_id: str
    executable_path: str
    mods_path: str
    is_running: bool = False

    def __post_init__(self):
        if not self.name:
            raise ValueError("Название игры не может быть пустым")
        if not self.steam_id:
            raise ValueError("Steam ID не может быть пустым")
        if not self.executable_path:
            raise ValueError("Путь к исполняемому файлу не может быть пустым")
        if not self.mods_path:
            raise ValueError("Путь к папке модов не может быть пустым")

    def is_valid(self) -> bool:
        return os.path.exists(self.executable_path) and os.path.exists(self.mods_path)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'steam_id': self.steam_id,
            'executable_path': self.executable_path,
            'mods_path': self.mods_path,
            'is_running': self.is_running
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Game':
        return cls(
            name=data['name'],
            steam_id=data['steam_id'],
            executable_path=data['executable_path'],
            mods_path=data['mods_path'],
            is_running=data.get('is_running', False)
        )
