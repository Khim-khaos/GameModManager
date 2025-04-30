import PyInstaller.__main__
import os
from pathlib import Path

def build_exe():
    # Путь к главному скрипту
    main_script = "src/main.py"

    # Папки и файлы, которые нужно включить
    additional_files = [
        ("src/data", "src/data"),  # Включаем папку data
        ("src/language", "src/language"),  # Включаем папку language
        ("src/ui", "src/ui"),  # Включаем папку ui
        ("src/core", "src/core"),  # Включаем папку core
        ("src/Logs", "src/Logs"),  # Включаем папку Logs
    ]

    # Формируем аргументы для PyInstaller
    args = [
        main_script,
        "--name=GameModManager",  # Имя исполняемого файла
        "--onefile",  # Создаём один .exe файл
        "--windowed",  # Для GUI-приложения (без консоли)
        "--distpath=dist",  # Папка для выходного файла
        "--workpath=build",  # Папка для временных файлов
    ]

    # Добавляем дополнительные файлы/папки
    for src, dst in additional_files:
        args.append(f"--add-data={src}{os.pathsep}{dst}")

    # Запускаем PyInstaller
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build_exe()