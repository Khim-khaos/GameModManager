from queue import Queue
import threading
import subprocess
import re
import os
import shutil
from src.game_manager import GameManager
from PyQt5.QtCore import Qt


class ModQueue:
    def __init__(self, game_manager):
        self.queue = Queue()
        self.is_running = False
        self.thread = None
        self.game_manager = game_manager

    def add_mod_to_queue(self, game_id, mod_id, console_output=None):
        self.queue.put((game_id, mod_id, console_output))

    def start_processing(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._process_queue)
            self.thread.start()

    def _process_queue(self):
        while self.is_running:
            try:
                game_id, mod_id, console_output = self.queue.get(timeout=1)
                self.download_mod(game_id, mod_id, console_output)
                self.queue.task_done()
            except Exception:
                if self.queue.empty():
                    self.is_running = False
                    break

    def download_mod(self, game_id, mod_id, console_output):
        game_data = self.game_manager.get_game(game_id)
        if not game_data:
            print(f"Игра с ID {game_id} не найдена.")
            return

        steamcmd_path = self.game_manager.settings.get('steamcmd_path')
        mods_path = game_data.get('mods_path')

        if not steamcmd_path or not mods_path:
            print("Путь до steamcmd или папки с модами не указан.")
            return

        try:
            command = [
                steamcmd_path,
                "+login", "anonymous",
                "+workshop_download_item", game_id, mod_id,
                "+quit"
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    if console_output:
                        console_output.append(output.strip())

            _, stderr = process.communicate()
            if stderr:
                if console_output:
                    console_output.append(stderr.strip())

            output_text = process.stdout.read()
            mod_name = self.extract_mod_name(output_text)
            downloaded_mod_path = self.extract_downloaded_mod_path(output_text)

            if console_output:
                console_output.append(f"Название мода: {mod_name}")
                console_output.append(f"Путь загруженного мода: {downloaded_mod_path}")
                console_output.append(f"Путь папки модов игры: {mods_path}")

            if mod_name and downloaded_mod_path:
                self.create_symlink(downloaded_mod_path, mods_path, mod_name, console_output)
                self.game_manager.add_installed_mod(game_id, {"id": mod_id, "name": mod_name})
                if console_output:
                    console_output.append(
                        f"Мод {mod_name} ({mod_id}) успешно загружен и создана символическая ссылка для игры {game_id}")
                print(f"Мод {mod_name} ({mod_id}) успешно загружен и создана символическая ссылка для игры {game_id}")
            elif mod_name:
                if console_output:
                    console_output.append(f"Мод {mod_id} успешно загружен, но путь не найден для игры {game_id}")
                print(f"Мод {mod_id} успешно загружен, но путь не найден для игры {game_id}")
            else:
                if console_output:
                    console_output.append(f"Мод {mod_id} успешно загружен, но имя не найдено для игры {game_id}")
                print(f"Мод {mod_id} успешно загружен, но имя не найдено для игры {game_id}")
        except subprocess.CalledProcessError as e:
            if console_output:
                console_output.append(f"Ошибка загрузки мода {mod_id} для игры {game_id}: {e.stderr}")
            print(f"Ошибка загрузки мода {mod_id} для игры {game_id}: {e.stderr}")

    def extract_mod_name(self, output):
        match = re.search(r"Success. Downloaded item (\d+) to '.*\\steamapps\\workshop\\content\\\d+\\(\d+)\\(.*)'",
                          output)
        if match:
            return match.group(3)
        return None

    def extract_downloaded_mod_path(self, output):
        match = re.search(r"Success. Downloaded item (\d+) to '(.*)'", output)
        if match:
            return match.group(2)
        return None

    def create_symlink(self, downloaded_mod_path, mods_path, mod_name, console_output):
        destination_path = os.path.join(mods_path, mod_name)
        if os.path.exists(destination_path):
            if os.path.islink(destination_path):
                os.unlink(destination_path)
            else:
                shutil.rmtree(destination_path)
        try:
            command = [
                "mklink",
                "/D",
                os.path.normpath(destination_path),
                os.path.normpath(downloaded_mod_path)
            ]
            if console_output:
                console_output.append(f"Команда mklink: {' '.join(command)}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate()
            if stderr:
                if console_output:
                    console_output.append(f"Ошибка при создании символической ссылки: {stderr.strip()}")
                print(f"Ошибка при создании символической ссылки: {stderr.strip()}")
            else:
                if console_output:
                    console_output.append(f"Символическая ссылка создана: {stdout.strip()}")
                print(f"Символическая ссылка создана: {stdout.strip()}")
        except Exception as e:
            if console_output:
                console_output.append(f"Ошибка при создании символической ссылки: {e}")
            print(f"Ошибка при создании символической ссылки: {e}")

    def stop_processing(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
