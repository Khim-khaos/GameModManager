# -*- coding: utf-8 -*-
"""
Константы приложения
"""

import os
import sys

# Информация о приложении
APP_NAME = "GameModManager"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Khim_Khaosow"

# Определяем базовые пути в зависимости от режима запуска
if getattr(sys, 'frozen', False):
    # Запущено как EXE файл - PyInstaller копирует файлы в _MEIPASS
    BASE_DIR = os.path.dirname(sys.executable)
    SRC_DIR = os.path.join(BASE_DIR, 'src')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    LOGS_DIR = os.path.join(BASE_DIR, 'Logs')
    # Языковые файлы копируются в _MEIPASS/language
    _MEIPASS = getattr(sys, '_MEIPASS', BASE_DIR)
    LANGUAGE_DIR = os.path.join(_MEIPASS, 'language')
    ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
else:
    # Запущено как скрипт
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SRC_DIR = os.path.join(BASE_DIR, 'src')
    DATA_DIR = os.path.join(SRC_DIR, 'data')
    LOGS_DIR = os.path.join(SRC_DIR, 'Logs')
    LANGUAGE_DIR = os.path.join(SRC_DIR, 'language')
    ASSETS_DIR = os.path.join(SRC_DIR, 'assets')

# Файлы конфигурации
GAMES_CONFIG_FILE = os.path.join(DATA_DIR, 'games.json')
SETTINGS_CONFIG_FILE = os.path.join(DATA_DIR, 'settings.json')
CACHE_FILE = os.path.join(DATA_DIR, 'cache.json')

# Steam URLs
STEAM_WORKSHOP_BASE_URL = "https://steamcommunity.com/workshop/"
STEAM_WORKSHOP_APP_URL = "https://steamcommunity.com/app/{}/workshop/"
STEAM_WORKSHOP_HOMEPAGE = "https://steamcommunity.com/workshop/"

# SteamCMD
STEAMCMD_CONTENT_PATH = "steamapps/workshop/content"
STEAMCMD_TEMP_PATH = "steamapps/workshop/temp"
STEAMCMD_LIBRARY_FILE = "steamapps/libraryfolders.vdf"

# События
class Events:
    GAME_SELECTED = "game_selected"
    GAME_ADDED = "game_added"
    GAME_REMOVED = "game_removed"
    GAME_STARTED = "game_started"
    GAME_STOPPED = "game_stopped"
    MOD_INSTALLED = "mod_installed"
    MOD_REMOVED = "mod_removed"
    LANGUAGE_CHANGED = "language_changed"
    SETTINGS_CHANGED = "settings_changed"

# Цвета по умолчанию
DEFAULT_COLORS = {
    'background': '#2b2b2b',
    'foreground': '#ffffff',
    'accent': '#0078d4',
    'secondary': '#404040'
}
