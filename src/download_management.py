# src/download_management.py
import subprocess
import os
import threading
import time
import traceback
from PyQt5.QtCore import QObject, pyqtSignal
import shutil


class DownloadManager(QObject):
    download_started = pyqtSignal(str)
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)
    console_output = pyqtSignal(str)

    def __init__(self, steamcmd_path):
        super().__init__()
        self.steamcmd_path = steamcmd_path
        self.is_downloading = False
        self.process = None

    def download_mod(self, game_id, mod_id, mods_path):
        if not self.steamcmd_path or not os.path.exists(self.steamcmd_path):
            self.download_error.emit("Неверный путь до steamcmd.")
            return False

        if self.is_downloading:
            self.download_error.emit("Загрузка уже выполняется.")
            return False

        self.is_downloading = True
        self.download_started.emit(f"Начало загрузки мода {mod_id} для игры {game_id}")

        threading.Thread(target=self._download_mod_thread, args=(game_id, mod_id, mods_path), daemon=True).start()
        return True

    def _download_mod_thread(self, game_id, mod_id, mods_path):
        process = None
        try:
            command = [
                f'"{self.steamcmd_path}"',  # Заключаем путь в кавычки
                "+login", "anonymous",
                "+workshop_download_item", game_id, mod_id,
                "+quit"
            ]

            process = subprocess.Popen(" ".join(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                       shell=True)

            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.console_output.emit(line.strip())
                time.sleep(0.1)

            process.wait()
            if process.returncode == 0:
                self.console_output.emit(f"Загрузка мода {mod_id} завершена.")
                self._move_mod_files(game_id, mod_id, mods_path)
                self.download_finished.emit(f"Загрузка мода {mod_id} для игры {game_id} завершена.")
            else:
                self.console_output.emit(f"Ошибка загрузки мода {mod_id}. Код возврата: {process.returncode}")
                self.download_error.emit(f"Ошибка загрузки мода {mod_id}. Код возврата: {process.returncode}")
        except Exception as e:
            self.console_output.emit(f"Ошибка при загрузке мода: {e}")
            self.download_error.emit(f"Ошибка при загрузке мода: {e}")
            traceback.print_exc()
        finally:
            self.is_downloading = False
            if process:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()

    def _move_mod_files(self, game_id, mod_id, mods_path):
        try:
            workshop_path = os.path.join(os.path.dirname(self.steamcmd_path), "steamapps", "workshop", "content",
                                         str(game_id), str(mod_id))
            if not os.path.exists(workshop_path):
                self.console_output.emit(f"Ошибка: Папка мода {mod_id} не найдена в {workshop_path}")
                self.download_error.emit(f"Ошибка: Папка мода {mod_id} не найдена в {workshop_path}")
                return

            mod_folder_name = os.path.basename(workshop_path)
            destination_path = os.path.join(mods_path, mod_folder_name)

            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)

            shutil.copytree(workshop_path, destination_path)

            self.console_output.emit(f"Мод {mod_id} перемещен в {mods_path}")
        except Exception as e:
            self.console_output.emit(f"Ошибка при перемещении мода: {e}")
            self.download_error.emit(f"Ошибка при перемещении мода: {e}")
            traceback.print_exc()

    def download_mod_list(self, mod_queue, game_manager):
        if self.is_downloading:
            self.download_error.emit("Загрузка уже выполняется.")
            return False

        self.is_downloading = True
        threading.Thread(target=self._download_mod_list_thread, args=(mod_queue, game_manager), daemon=True).start()
        return True

    def _download_mod_list_thread(self, mod_queue, game_manager):
        process = None
        try:
            while not mod_queue.is_empty():
                mod_data = mod_queue.get_next_mod()
                if mod_data:
                    game_id = mod_data["game_id"]
                    mod_id = mod_data["mod_id"]
                    mods_path = mod_data["mods_path"]

                    self.download_started.emit(f"Начало загрузки мода {mod_id} для игры {game_id}")

                    command = [
                        f'"{self.steamcmd_path}"',  # Заключаем путь в кавычки
                        "+login", "anonymous",
                        "+workshop_download_item", game_id, mod_id,
                        "+quit"
                    ]

                    process = subprocess.Popen(" ".join(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                               text=True, shell=True)

                    while True:
                        line = process.stdout.readline()
                        if not line:
                            break
                        self.console_output.emit(line.strip())
                        time.sleep(0.1)

                    process.wait()
                    if process.returncode == 0:
                        self.console_output.emit(f"Загрузка мода {mod_id} завершена.")
                        self._move_mod_files(game_id, mod_id, mods_path)
                        game_manager.add_installed_mod(game_id, mod_id)
                        self.download_finished.emit(f"Загрузка мода {mod_id} для игры {game_id} завершена.")
                    else:
                        self.console_output.emit(f"Ошибка загрузки мода {mod_id}. Код возврата: {process.returncode}")
                        self.download_error.emit(f"Ошибка загрузки мода {mod_id}. Код возврата: {process.returncode}")
                else:
                    break
        except Exception as e:
            self.console_output.emit(f"Ошибка при загрузке модов: {e}")
            self.download_error.emit(f"Ошибка при загрузке модов: {e}")
            traceback.print_exc()
        finally:
            self.is_downloading = False
            if process:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
