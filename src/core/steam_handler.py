# src/core/steam_handler.py
import os
import subprocess
import tempfile
import shutil
import time
from typing import List, Callable, Optional
from loguru import logger
from src.core.process_monitor import CacheManager

class SteamHandler:
    """Обработчик SteamCMD"""

    def __init__(self, steamcmd_path: str):
        self.steamcmd_path = steamcmd_path
        self.is_initialized = self._check_steamcmd()
        self.cache_manager = CacheManager()

    def _check_steamcmd(self) -> bool:
        """Проверка доступности SteamCMD"""
        return bool(self.steamcmd_path and os.path.exists(self.steamcmd_path))

    def get_login_command(self) -> List[str]:
        """Возвращает команду для входа в SteamCMD."""
        return ["+login", "anonymous"]

    # Метод is_initialized как callable оставляем для совместимости
    def is_initialized(self):
        """Проверка, инициализирован ли SteamCMD (для совместимости)"""
        return self.is_initialized

    def create_download_script(self, app_id: str, mod_ids: List[str]) -> str:
        """Создание скрипта для скачивания модов"""
        # Используем force_install_dir, чтобы быть уверенным в пути
        # Хотя для workshop это может не применяться напрямую, хорошая практика
        script_content = f"""@ShutdownOnFailedCommand 1
@NoPromptForPassword 1
login anonymous
"""
        for mod_id in mod_ids:
            script_content += f"workshop_download_item {app_id} {mod_id} validate\n" # Добавляем validate
        script_content += "quit\n"
        return script_content

    # Модифицируем download_mods для поддержки log_callback и кэширования
    def download_mods(self, app_id: str, mod_ids: List[str], log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Скачивание модов через SteamCMD с поддержкой кэширования.

        :param app_id: ID приложения Steam.
        :param mod_ids: Список ID модов для загрузки.
        :param log_callback: Опциональная функция обратного вызова для передачи строк лога.
                             Вызывается как log_callback(line).
        :return: True, если процесс завершился успешно (код 0), иначе False.
        """
        if not self.is_initialized:
            logger.error("SteamCMD не инициализирован")
            if log_callback:
                log_callback("!!! ОШИБКА: SteamCMD не инициализирован.")
            return False

        if not mod_ids:
            logger.info("Нет модов для загрузки")
            if log_callback:
                log_callback("-> Нет модов для загрузки.")
            return True

        # Проверяем кэш перед загрузкой
        cache_key = self.cache_manager.get_steam_mods_cache_key(app_id, mod_ids)
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result is not None:
            logger.info(f"Используем кэшированный результат для {len(mod_ids)} модов")
            if log_callback:
                log_callback(f"-> Используем кэшированные данные для {len(mod_ids)} модов")
                if cached_result.get('success'):
                    log_callback("=== Моды уже загружены (из кэша) ===")
                else:
                    log_callback("!!! Предыдущая загрузка не удалась (из кэша) !!!")
            return cached_result.get('success', False)

        # --- ДОПОЛНИТЕЛЬНАЯ ОЧИСТКА КЭША ПЕРЕД ЗАГРУЗКОЙ ---
        # Выполняем очистку перед каждой загрузкой для минимизации проблем с кэшем
        steamcmd_base_path = os.path.dirname(self.steamcmd_path)
        self.clean_cache(steamcmd_base_path, app_id, log_callback=log_callback)
        # --- КОНЕЦ ДОПОЛНИТЕЛЬНОЙ ОЧИСТКИ ---

        script_content = self.create_download_script(app_id, mod_ids)
        # Используем кодировку, совместимую с Windows
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            cmd = [self.steamcmd_path, f"+runscript {script_path}"]
            logger.info(f"Запуск SteamCMD с командой: {' '.join(cmd)}")
            if log_callback:
                log_callback(f"-> Запуск SteamCMD: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1, # Построчная буферизация
                universal_newlines=True,
                # Указываем рабочую директорию, чтобы пути были относительны
                cwd=steamcmd_base_path
            )

            # Читаем вывод построчно и передаем через callback
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    line = line.rstrip('\n\r')
                    if line:
                        logger.debug(f"[SteamCMD] {line}")
                        if log_callback:
                            try:
                                # Передаем строку в UI-поток через callback
                                log_callback(line)
                            except Exception as cb_e:
                                logger.error(f"Ошибка в log_callback: {cb_e}")

            process.wait()
            success = process.returncode == 0
            
            # Сохраняем результат в кэш на 5 минут (300 секунд)
            self.cache_manager.set(cache_key, {'success': success}, ttl=300.0)
            
            logger.info(f"SteamCMD завершен с кодом: {process.returncode}")
            if log_callback:
                if success:
                    log_callback("=== SteamCMD завершен успешно. ===")
                else:
                    log_callback(f"!!! SteamCMD завершен с ошибкой. Код: {process.returncode}")
            return success

        except Exception as e:
            # Сохраняем ошибку в кэш на 1 минуту (60 секунд)
            self.cache_manager.set(cache_key, {'success': False, 'error': str(e)}, ttl=60.0)
            logger.error(f"Ошибка при запуске SteamCMD: {e}")
            if log_callback:
                log_callback(f"!!! ОШИБКА запуска SteamCMD: {e}")
            return False
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except OSError as remove_e:
                    logger.warning(f"Не удалось удалить временный скрипт {script_path}: {remove_e}")

    def check_game_status(self, app_id: str, log_callback: Optional[Callable[[str], None]] = None) -> Optional[dict]:
        """
        Проверка статуса игры через Steam с кэшированием.
        
        :param app_id: ID приложения Steam.
        :param log_callback: Опциональная функция обратного вызова.
        :return: Словарь с информацией о статусе или None в случае ошибки.
        """
        cache_key = self.cache_manager.get_steam_game_info_cache_key(app_id)
        cached_info = self.cache_manager.get(cache_key)
        
        if cached_info is not None:
            logger.debug(f"Используем кэшированную информацию об игре {app_id}")
            if log_callback:
                log_callback(f"-> Информация об игре {app_id} из кэша")
            return cached_info
        
        # Здесь можно добавить реальный запрос к Steam API
        # Пока возвращаем базовую информацию и кэшируем на 10 минут
        game_info = {
            'app_id': app_id,
            'name': f'Game {app_id}',
            'status': 'unknown',
            'last_checked': time.time()
        }
        
        # Кэшируем на 10 минут (600 секунд)
        self.cache_manager.set(cache_key, game_info, ttl=600.0)
        
        logger.debug(f"Получена информация об игре {app_id}")
        return game_info

    def invalidate_cache(self, app_id: str = None, mod_ids: List[str] = None):
        """
        Инвалидация кэша для конкретной игры или модов.
        
        :param app_id: ID приложения (опционально).
        :param mod_ids: Список ID модов (опционально).
        """
        if app_id and mod_ids:
            cache_key = self.cache_manager.get_steam_mods_cache_key(app_id, mod_ids)
            self.cache_manager.invalidate(cache_key)
            logger.info(f"Кэш инвалидирован для модов игры {app_id}")
        
        if app_id:
            cache_key = self.cache_manager.get_steam_game_info_cache_key(app_id)
            self.cache_manager.invalidate(cache_key)
            logger.info(f"Кэш инвалидирован для игры {app_id}")

    # Модифицируем clean_cache для удаления дополнительных файлов/папок
    def clean_cache(self, steamcmd_base_path: str, app_id: str, log_callback: Optional[Callable[[str], None]] = None):
        """
        Очистка кэша SteamCMD для конкретного приложения.
        Удаляет стандартные файлы кэша, а также дополнительные папки и файлы,
        как указано в запросе.
        """
        if log_callback:
            log_callback("-> Очистка кэша SteamCMD...")
        logger.info("Начало очистки кэша SteamCMD...")
        errors = []

        try:
            # 1. Стандартная очистка (temp и acf)
            temp_path = os.path.join(steamcmd_base_path, "steamapps", "workshop", "temp")
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
                os.makedirs(temp_path, exist_ok=True) # Пересоздаем пустую папку
                logger.debug("Очищена/пересоздана папка temp")
                if log_callback:
                    log_callback("-> Очищена папка temp")

            acf_path = os.path.join(steamcmd_base_path, "steamapps", "workshop", f"appworkshop_{app_id}.acf")
            if os.path.exists(acf_path):
                os.remove(acf_path)
                logger.debug("Удален файл appworkshop.acf")
                if log_callback:
                    log_callback("-> Удален файл appworkshop.acf")
        except Exception as e:
            error_msg = f"Ошибка стандартной очистки: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        try:
            # 2. Дополнительная очистка, как запрошено
            # Удаление папки \steamcmd\appcache
            appcache_path = os.path.join(steamcmd_base_path, "appcache")
            if os.path.exists(appcache_path):
                shutil.rmtree(appcache_path)
                logger.debug("Удалена папка appcache")
                if log_callback:
                    log_callback("-> Удалена папка appcache")

            # Удаление файла \steamcmd\steamapps\libraryfolders.vdf
            libraryfolders_path = os.path.join(steamcmd_base_path, "steamapps", "libraryfolders.vdf")
            if os.path.exists(libraryfolders_path):
                os.remove(libraryfolders_path)
                logger.debug("Удален файл libraryfolders.vdf")
                if log_callback:
                    log_callback("-> Удален файл libraryfolders.vdf")

            # Удаление всего содержимого \steamcmd\steamapps\workshop, кроме папки content
            workshop_path = os.path.join(steamcmd_base_path, "steamapps", "workshop")
            if os.path.exists(workshop_path):
                for item in os.listdir(workshop_path):
                    item_path = os.path.join(workshop_path, item)
                    # Пропускаем папку 'content'
                    if item != 'content':
                        try:
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            logger.debug(f"Удален элемент workshop: {item}")
                            if log_callback:
                                log_callback(f"-> Удален элемент workshop: {item}")
                        except Exception as item_e:
                            error_msg = f"Ошибка удаления {item}: {item_e}"
                            logger.warning(error_msg)
                            errors.append(error_msg) # Предупреждение, не ошибка всей функции
        except Exception as e:
            error_msg = f"Ошибка дополнительной очистки: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        if errors:
            logger.warning(f"Очистка кэша завершена с предупреждениями: {errors}")
            if log_callback:
                log_callback(f"-> Очистка кэша завершена с предупреждениями.")
        else:
            logger.info("Очистка кэша SteamCMD завершена успешно.")
            if log_callback:
                log_callback("-> Очистка кэша SteamCMD завершена успешно.")

