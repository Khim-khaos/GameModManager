# -*- coding: utf-8 -*-
"""
Конфигурация по умолчанию
"""
import os
import sys

# Пути к файлам конфигурации
if getattr(sys, 'frozen', False):
    # Запущено как EXE файл
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), "data")
else:
    # Запущено как скрипт
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

SETTINGS_CONFIG_FILE = os.path.join(DATA_DIR, "settings.json")
GAMES_CONFIG_FILE = os.path.join(DATA_DIR, "games.json")
PROCESS_CACHE_FILE = os.path.join(DATA_DIR, "process_cache.json")

DEFAULT_SETTINGS = {
    "steamcmd_path": "",
    "language": "en",
    "theme": {
        "background": "#2b2b2b",
        "foreground": "#ffffff",
        "accent": "#0078d4",
        "secondary": "#404040"
    },
    "auto_update_check": True,
    "download_timeout": 300,
    "max_concurrent_downloads": 3
}

DEFAULT_GAMES = []
