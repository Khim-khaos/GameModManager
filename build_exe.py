# -*- coding: utf-8 -*-
"""
Скрипт для сборки исполняемого файла
"""
import sys
import os
from cx_Freeze import setup, Executable

# Определяем базу в зависимости от платформы
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Для GUI приложений на Windows

# Определяем директории для включения
include_files = [
    ('src/assets/', 'assets/'),
    ('src/language/', 'language/'),
    ('README.md', 'README.md'),
]

# Параметры сборки
build_exe_options = {
    "packages": [
        "wx", "wx.html2", "loguru", "requests", "psutil"
    ],
    "excludes": [
        # Исключаем ненужные модули для уменьшения размера
    ],
    "include_files": include_files,
    "include_msvcrt": True,
}

# Определяем целевой исполняемый файл
target = Executable(
    script="main.py",
    base=base,
    target_name="GameModManager.exe" if sys.platform == "win32" else "GameModManager",
    icon=None,  # Можно добавить путь к .ico файлу
)

# Настройки установки
setup(
    name="GameModManager",
    version="1.0.0",
    description="Менеджер модов для Steam игр",
    options={"build_exe": build_exe_options},
    executables=[target]
)
