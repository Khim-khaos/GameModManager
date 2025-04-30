import PyInstaller.__main__
import os
import shutil


def build_exe():
    dist_dir = "dist/GameModManager"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)

    PyInstaller.__main__.run([
        "GameModManager.spec",
        "--clean",
        "--noconfirm"
    ])
    print("Сборка завершена. Исполняемый файл находится в dist/GameModManager/")


if __name__ == "__main__":
    build_exe()
