#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки исполняемого файла с помощью PyInstaller
"""
import os
import sys
import shutil
from PyInstaller.__main__ import run

def clean_build():
    """Очистка предыдущей сборки"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Удаление директории: {dir_name}")
            shutil.rmtree(dir_name)

def build_exe():
    """Сборка исполняемого файла"""
    
    # Проверяем существование директорий перед добавлением
    data_files = []
    
    # Добавляем language директорию
    if os.path.exists('src/language'):
        data_files.append('--add-data=src/language;language')
    
    # Добавляем README если существует
    if os.path.exists('README.md'):
        data_files.append('--add-data=README.md;.')
    
    # Параметры для PyInstaller
    pyinstaller_args = [
        'main.py',
        '--name=GameModManager',
        '--windowed',  # GUI приложение без консоли
        '--onefile',   # Один файл
        '--clean',     # Очистка кэша
        '--noconfirm', # Не спрашивать подтверждение
        
        # Включение необходимых пакетов
        '--hidden-import=wx',
        '--hidden-import=wx.html2',
        '--hidden-import=wx.html2.WebView',
        '--hidden-import=requests',
        '--hidden-import=bs4',
        '--hidden-import=beautifulsoup4',
        '--hidden-import=loguru',
        '--hidden-import=psutil',
        '--hidden-import=steam',
        '--hidden-import=json',
        '--hidden-import=threading',
        '--hidden-import=concurrent.futures',
        '--hidden-import=urllib3',
        '--hidden-import=certifi',
        '--hidden-import=charset_normalizer',
        '--hidden-import=msgspec',
        '--hidden-import=natsort',
        '--hidden-import=networkx',
        '--hidden-import=packaging',
        '--hidden-import=platformdirs',
        '--hidden-import=pygit2',
        '--hidden-import=pygithub',
        '--hidden-import=pyperclip',
        '--hidden-import=sqlalchemy',
        '--hidden-import=toposort',
        '--hidden-import=watchdog',
        '--hidden-import=xmltodict',
        
        # Включение всех модулей проекта
        '--hidden-import=src.ui.main_window',
        '--hidden-import=src.ui.tabs.mods_tab',
        '--hidden-import=src.ui.tabs.browser_tab',
        '--hidden-import=src.ui.tabs.logs_tab',
        '--hidden-import=src.ui.tabs.console_tab',
        '--hidden-import=src.ui.dialogs.add_game_dialog',
        '--hidden-import=src.ui.dialogs.settings_dialog',
        '--hidden-import=src.ui.dialogs.dependency_confirmation_dialog',
        '--hidden-import=src.ui.dialogs.collection_confirmation_dialog',
        '--hidden-import=src.ui.dialogs.download_progress_dialog',
        '--hidden-import=src.ui.dialogs.edit_game_dialog',
        '--hidden-import=src.core.game_manager',
        '--hidden-import=src.core.mod_manager',
        '--hidden-import=src.core.settings_manager',
        '--hidden-import=src.core.language_manager',
        '--hidden-import=src.core.steam_handler',
        '--hidden-import=src.core.download_manager',
        '--hidden-import=src.core.logger',
        '--hidden-import=src.core.task_manager',
        '--hidden-import=src.core.steam_workshop_service',
        '--hidden-import=src.models.game',
        '--hidden-import=src.models.mod',
        '--hidden-import=src.event_bus',
        '--hidden-import=src.constants',
        '--hidden-import=src.decorators',
        '--hidden-import=src.data.config',
        
        # Исключение ненужных модулей
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=PIL',
        '--exclude-module=numpy',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        '--exclude-module=jupyter',
        '--exclude-module=IPython',
        '--exclude-module=notebook',
        '--exclude-module=pytest',
        '--exclude-module=sphinx',
        '--exclude-module=flask',
        '--exclude-module=django',
        
        # Иконка (если есть)
        # '--icon=assets/icon.ico',
    ]
    
    # Добавляем данные если они существуют
    pyinstaller_args.extend(data_files)
    
    print("Начинаю сборку GameModManager...")
    print("Параметры:", ' '.join(pyinstaller_args))
    
    try:
        run(pyinstaller_args)
        print("\n✅ Сборка завершена успешно!")
        print(f"Исполняемый файл находится в: {os.path.abspath('dist/GameModManager.exe')}")
        
        # Показываем размер файла
        exe_path = 'dist/GameModManager.exe'
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Размер файла: {size_mb:.1f} MB")
            
    except Exception as e:
        print(f"\n❌ Ошибка при сборке: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Очистка предыдущей сборки
    clean_build()
    
    # Сборка
    build_exe()
