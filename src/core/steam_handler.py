import subprocess
import os
from loguru import logger
import shutil
from pathlib import Path
import tempfile
import time
import threading
import queue

class SteamHandler:
    def __init__(self, steamcmd_path):
        self.steamcmd_path = steamcmd_path
        if not os.path.exists(self.steamcmd_path):
            logger.error(f"SteamCMD не найден по пути: {self.steamcmd_path}")
            raise FileNotFoundError(f"SteamCMD не найден: {self.steamcmd_path}")

    def _create_script(self, commands):
        """Создаёт временный файл скрипта с командами для SteamCMD."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            for command in commands:
                temp_file.write(f"{command}\n")
            script_path = temp_file.name
        logger.debug(f"Создан временный скрипт: {script_path}")
        return script_path

    def _read_stream(self, stream, output_queue):
        """Читает поток (stdout или stderr) и помещает строки в очередь."""
        while True:
            line = stream.readline()
            if not line:  # Поток закрыт
                break
            output_queue.put(line.strip())

    def _clean_temp_folders(self):
        """Очищает содержимое папки workshop, кроме подпапки content."""
        workshop_path = Path(self.steamcmd_path).parent / "steamapps" / "workshop"
        if not workshop_path.exists():
            logger.debug(f"Папка {workshop_path} не существует, пропускаем очистку")
            return

        # Проходим по всем элементам в папке workshop
        for item in workshop_path.iterdir():
            # Пропускаем папку content
            if item.name == "content":
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    logger.debug(f"Удалена временная папка {item}")
                else:
                    os.remove(item)
                    logger.debug(f"Удалён временный файл {item}")
            except Exception as e:
                logger.warning(f"Не удалось удалить {item}: {e}")

    def _run_steamcmd_script(self, script_path, max_wait_time=1800):  # Максимальное время ожидания 30 минут
        """Запускает SteamCMD с указанным скриптом и ждёт завершения с динамическим ожиданием."""
        cmd = [
            self.steamcmd_path,
            "+force_install_dir", os.path.dirname(self.steamcmd_path),
            "+runscript", script_path
        ]
        logger.debug(f"Запуск SteamCMD: {' '.join(cmd)}")

        start_time = time.time()
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        stdout_lines = []
        stderr_lines = []

        try:
            # Запускаем SteamCMD
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='cp1251',
                errors='replace'
            )

            # Запускаем потоки для чтения stdout и stderr
            stdout_thread = threading.Thread(target=self._read_stream, args=(process.stdout, stdout_queue))
            stderr_thread = threading.Thread(target=self._read_stream, args=(process.stderr, stderr_queue))
            stdout_thread.start()
            stderr_thread.start()

            # Ожидаем завершения загрузки
            success = False
            while time.time() - start_time < max_wait_time:
                # Читаем stdout
                try:
                    while True:
                        line = stdout_queue.get_nowait()
                        stdout_lines.append(line)
                        logger.debug(f"SteamCMD stdout: {line}")
                        if "Success. Downloaded item" in line:
                            success = True
                            break
                        if "ERROR!" in line or "Failed" in line:
                            logger.error(f"SteamCMD ошибка: {line}")
                            break
                except queue.Empty:
                    pass

                # Читаем stderr
                try:
                    while True:
                        line = stderr_queue.get_nowait()
                        stderr_lines.append(line)
                        logger.error(f"SteamCMD stderr: {line}")
                except queue.Empty:
                    pass

                # Проверяем, завершилась ли загрузка
                if success or "ERROR!" in "".join(stdout_lines):
                    break

                # Проверяем, завершился ли процесс
                if process.poll() is not None:
                    break

                time.sleep(0.1)

            # Если время истекло
            elapsed_time = time.time() - start_time
            if time.time() - start_time >= max_wait_time:
                logger.error(f"SteamCMD не завершился в течение {max_wait_time} секунд (прошло {elapsed_time:.2f} секунд)")
                process.terminate()
                stdout_thread.join()
                stderr_thread.join()
                return "\n".join(stdout_lines), "\n".join(stderr_lines), False

            # Если нашли успех или ошибку
            if success:
                logger.debug(f"SteamCMD успешно завершил загрузку за {elapsed_time:.2f} секунд")
            else:
                logger.error(f"SteamCMD завершился с ошибкой после {elapsed_time:.2f} секунд")

            # Ждём завершения потоков
            stdout_thread.join()
            stderr_thread.join()
            process.wait()

            return "\n".join(stdout_lines), "\n".join(stderr_lines), success

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Ошибка при запуске SteamCMD после {elapsed_time:.2f} секунд: {e}")
            return "\n".join(stdout_lines), "\n".join(stderr_lines), False
        finally:
            # Очищаем временные папки после выполнения
            self._clean_temp_folders()
            try:
                os.remove(script_path)
                logger.debug(f"Временный скрипт удалён: {script_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный скрипт {script_path}: {e}")

    def download_mod(self, app_id, mod_id, progress_callback=None, max_retries=3, max_wait_time=1800):
        """Скачивает мод с помощью SteamCMD через скрипт с динамическим ожиданием."""
        retry_count = 0
        while retry_count < max_retries:
            logger.info(f"Попытка {retry_count + 1}/{max_retries} загрузки мода {mod_id} для игры {app_id}")

            # Очищаем папку workshop/content перед скачиванием
            workshop_path = Path(self.steamcmd_path).parent / "steamapps" / "workshop" / "content" / str(app_id) / str(mod_id)
            if workshop_path.exists():
                logger.debug(f"Очистка папки {workshop_path} перед скачиванием")
                shutil.rmtree(workshop_path, ignore_errors=True)

            # Создаём скрипт для скачивания
            script_commands = [
                "login anonymous",
                f"workshop_download_item {app_id} {mod_id}",
                "quit"
            ]
            script_path = self._create_script(script_commands)
            stdout, stderr, success = self._run_steamcmd_script(script_path, max_wait_time)

            if success:
                logger.info(f"Мод {mod_id} успешно скачан для игры {app_id}")
                download_path = os.path.join(os.path.dirname(self.steamcmd_path), "steamapps", "workshop", "content", str(app_id), str(mod_id))
                if os.path.exists(download_path):
                    logger.debug(f"Файл мода найден по пути: {download_path}")
                    return True
                else:
                    logger.error(f"Файл мода не найден по пути: {download_path}")
                    success = False

            if not success:
                retry_count += 1
                logger.warning(f"Не удалось скачать мод {mod_id} на попытке {retry_count}, повторная попытка...")
                if retry_count == max_retries:
                    logger.error(f"Не удалось скачать мод {mod_id} после {max_retries} попыток")
                    logger.error(f"stdout:\n{stdout}")
                    logger.error(f"stderr:\n{stderr}")
                    return False

        return False

    def verify_mod(self, app_id, mod_id):
        mod_path = os.path.join(os.path.dirname(self.steamcmd_path), "steamapps", "workshop", "content", str(app_id), str(mod_id))
        logger.debug(f"Проверка целостности мода {mod_id} по пути: {mod_path}")
        if os.path.exists(mod_path):
            logger.info(f"Проверка целостности мода {mod_id}: успешно")
            return True
        logger.error(f"Мод {mod_id} не найден по пути: {mod_path}")
        return False

    def close_session(self):
        """Заглушка для совместимости, так как сессия не используется."""
        logger.info("Закрытие сессии SteamCMD не требуется при использовании скриптов")
