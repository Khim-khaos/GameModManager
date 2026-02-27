# -*- coding: utf-8 -*-
"""
Менеджер модов
"""
import os
import shutil
from datetime import datetime
from typing import List, Optional
from loguru import logger
from src.models.mod import Mod
from src.models.game import Game
# from src.event_bus import event_bus # Закомментировано, так как не используется напрямую


class ModManager:
    """Менеджер модов"""

    def __init__(self):
        self._mods: List[Mod] = []
        self.current_game: Optional[Game] = None # Сохраняем ссылку на текущую игру

    def load_mods_for_game(self, game: Game) -> List[Mod]:
        """
        Загрузка всех модов (включённых и отключённых) для игры.
        Ожидается, что game.mods_path указывает на папку, где лежат моды напрямую.
        Отключенные моды находятся в подпапке 'archive'.
        """
        # --- ВАЖНО: Сохраняем ссылку на текущую игру ---
        self.current_game = game
        # -----------------------------------------------

        mods = []
        mods_path = game.mods_path
        archive_path = os.path.join(mods_path, "archive")

        logger.debug(f"[ModManager/load_mods_for_game] Начало загрузки модов для игры '{game.name}' (ID: {game.steam_id})")
        logger.debug(f"[ModManager/load_mods_for_game] mods_path: '{mods_path}'")
        logger.debug(f"[ModManager/load_mods_for_game] archive_path: '{archive_path}'")

        # Проверяем существование основной папки модов
        if not os.path.exists(mods_path):
            logger.warning(f"[ModManager/load_mods_for_game] Папка модов не существует: '{mods_path}'")
        elif not os.path.isdir(mods_path):
            logger.error(f"[ModManager/load_mods_for_game] mods_path '{mods_path}' не является папкой.")
        else:
            logger.debug(f"[ModManager/load_mods_for_game] Папка модов существует: '{mods_path}'")
            try:
                # Загружаем включённые моды (в основной папке)
                items_in_mods_path = os.listdir(mods_path)
                logger.debug(f"[ModManager/load_mods_for_game] Содержимое mods_path: {items_in_mods_path}")

                for item in items_in_mods_path:
                    item_path = os.path.join(mods_path, item)
                    # Проверяем, что это папка, она не 'archive' и не скрытая системная (для Windows)
                    if os.path.isdir(item_path) and item != "archive":
                        # Дополнительная проверка: исключаем очевидно системные папки/файлы
                        # Можно добавить больше условий, если нужно
                        if item.startswith('.'):
                            logger.debug(f"[ModManager/load_mods_for_game] Пропущена скрытая папка/файл: '{item}'")
                            continue

                        mod = self._create_mod(item, item_path, is_enabled=True)
                        if mod:
                            mods.append(mod)
                            logger.debug(f"[ModManager/load_mods_for_game] Найден включённый мод: ID={mod.mod_id}, Путь={mod.local_path}")
                        else:
                            logger.warning(f"[ModManager/load_mods_for_game] Не удалось создать мод для папки: '{item_path}'")
                    elif item == "archive":
                        logger.debug(f"[ModManager/load_mods_for_game] Найдена папка 'archive'.")
                    else:
                        logger.debug(f"[ModManager/load_mods_for_game] Пропущен элемент (не папка или 'archive'): '{item}'")

            except PermissionError as e:
                logger.error(f"[ModManager/load_mods_for_game] Ошибка доступа к папке модов '{mods_path}': {e}")
            except Exception as e:
                logger.error(f"[ModManager/load_mods_for_game] Неожиданная ошибка при сканировании папки модов '{mods_path}': {e}")

        # Загружаем отключённые моды (в папке archive)
        if not os.path.exists(archive_path):
            logger.debug(f"[ModManager/load_mods_for_game] Папка отключённых модов (archive) не существует: '{archive_path}'")
        elif not os.path.isdir(archive_path):
            logger.error(f"[ModManager/load_mods_for_game] archive_path '{archive_path}' не является папкой.")
        else:
            logger.debug(f"[ModManager/load_mods_for_game] Папка отключённых модов существует: '{archive_path}'")
            try:
                items_in_archive_path = os.listdir(archive_path)
                logger.debug(f"[ModManager/load_mods_for_game] Содержимое archive_path: {items_in_archive_path}")

                for item in items_in_archive_path:
                    item_path = os.path.join(archive_path, item)
                    if os.path.isdir(item_path):
                        # Дополнительная проверка: исключаем очевидно системные папки/файлы
                        if item.startswith('.'):
                            logger.debug(f"[ModManager/load_mods_for_game] Пропущена скрытая папка/файл в archive: '{item}'")
                            continue

                        mod = self._create_mod(item, item_path, is_enabled=False)
                        if mod:
                            mods.append(mod)
                            logger.debug(f"[ModManager/load_mods_for_game] Найден отключённый мод: ID={mod.mod_id}, Путь={mod.local_path}")
                        else:
                            logger.warning(f"[ModManager/load_mods_for_game] Не удалось создать мод для папки в archive: '{item_path}'")
                    else:
                        logger.debug(f"[ModManager/load_mods_for_game] Пропущен элемент в archive (не папка): '{item}'")

            except PermissionError as e:
                logger.error(f"[ModManager/load_mods_for_game] Ошибка доступа к папке архива '{archive_path}': {e}")
            except Exception as e:
                logger.error(f"[ModManager/load_mods_for_game] Неожиданная ошибка при сканировании папки архива '{archive_path}': {e}")

        self._mods = mods
        logger.info(f"[ModManager/load_mods_for_game] Загрузка модов завершена. Найдено {len(mods)} модов (включая отключённые) для игры: '{game.name}' (ID: {game.steam_id})")
        if mods:
            logger.debug(f"[ModManager/load_mods_for_game] Список загруженных модов: {[m.mod_id for m in mods]}")
        return self._mods.copy()

    def _create_mod(self, mod_id: str, path: str, is_enabled: bool) -> Optional[Mod]:
        """Создаёт объект Mod с датой установки"""
        # Базовая валидация ID мода (должен быть числом)
        if not mod_id.isdigit():
            logger.warning(f"[ModManager/_create_mod] Пропущен мод с некорректным ID (не число): '{mod_id}' (Путь: {path})")
            return None

        try:
            install_date = datetime.fromtimestamp(os.path.getctime(path))
            # Добавляем локальную дату обновления (время последнего изменения папки)
            local_update_date = datetime.fromtimestamp(os.path.getmtime(path))
        except (OSError, ValueError, OverflowError) as e: # Расширяем обработку ошибок
            logger.warning(f"[ModManager/_create_mod] Не удалось получить дату создания для папки '{path}' (ID: {mod_id}): {e}. Установлена None.")
            install_date = None
            local_update_date = None

        mod = Mod(
            mod_id=mod_id,
            name=mod_id, # Имя может быть обновлено позже через Steam API
            author="Неизвестен", # Автор может быть обновлён позже через Steam API
            local_path=path,
            is_enabled=is_enabled,
            workshop_url=f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}",
            install_date=install_date,
            local_update_date=local_update_date
        )
        logger.debug(f"[ModManager/_create_mod] Создан объект Mod: ID={mod.mod_id}, Включен={mod.is_enabled}, Путь={mod.local_path}")
        return mod

    # --- Добавленные методы ---
    def get_installed_mods(self, steam_id: str) -> List[Mod]:
        """
        Получение списка всех установленных модов для текущей загруженной игры.
        Предполагается, что load_mods_for_game уже был вызван для нужной игры.
        steam_id передается для согласованности сигнатуры, но не используется,
        так как фильтрация происходит по текущему состоянию self._mods.
        """
        # В текущей реализации, self._mods уже содержит моды для нужной игры
        # после вызова load_mods_for_game. Этот метод просто возвращает их.
        # Если потребуется фильтрация по steam_id, логика должна быть изменена.
        logger.debug(f"[ModManager] get_installed_mods вызван для steam_id={steam_id}, возвращаем {len(self._mods)} модов.")
        return self._mods.copy()

    def get_enabled_mods(self, steam_id: str) -> List[Mod]:
        """
        Получение списка включённых модов для текущей загруженной игры.
        Предполагается, что load_mods_for_game уже был вызван.
        """
        # Фильтруем текущий список self._mods
        enabled_mods = [mod for mod in self._mods if mod.is_enabled]
        logger.debug(f"[ModManager] get_enabled_mods вызван для steam_id={steam_id}, возвращаем {len(enabled_mods)} модов.")
        return enabled_mods

    def get_disabled_mods(self, steam_id: str) -> List[Mod]:
        """
        Получение списка отключённых модов для текущей загруженной игры.
        Предполагается, что load_mods_for_game уже был вызван.
        """
        # Фильтруем текущий список self._mods
        disabled_mods = [mod for mod in self._mods if not mod.is_enabled]
        logger.debug(f"[ModManager] get_disabled_mods вызван для steam_id={steam_id}, возвращаем {len(disabled_mods)} модов.")
        return disabled_mods
    # --- Конец добавленных методов ---

    def get_mod_by_id(self, mod_id: str) -> Optional[Mod]:
        """Получение мода по ID"""
        # Используем next с генератором для эффективности
        found_mod = next((mod for mod in self._mods if mod.mod_id == mod_id), None)
        if found_mod:
            logger.debug(f"[ModManager/get_mod_by_id] Найден мод с ID {mod_id}.")
        else:
            logger.debug(f"[ModManager/get_mod_by_id] Мод с ID {mod_id} не найден.")
        return found_mod

    # --- ИСПРАВЛЕННЫЕ Методы enable_mod и disable_mod ---
    def enable_mod(self, game_steam_id: str, mod_id: str) -> bool:
        """
        Включение мода.
        game_steam_id передается для согласованности, но не используется напрямую.
        """
        mod = self.get_mod_by_id(mod_id)
        if mod and not mod.is_enabled:
            logger.info(f"[ModManager/Enable] Попытка включения мода {mod.name} ({mod.mod_id})...")

            # --- ЛОГИКА ВКЛЮЧЕНИЯ ---
            # 1. Проверяем, известна ли текущая игра
            if not self.current_game:
                logger.error(f"[ModManager/Enable] Неизвестна текущая игра для мода {mod_id}.")
                return False

            # 2. Определяем целевой путь (в основной папке модов игры)
            target_mods_path = self.current_game.mods_path
            target_path = os.path.join(target_mods_path, mod.mod_id)

            # 3. Проверяем, существует ли папка в archive
            if os.path.exists(mod.local_path) and mod.local_path != target_path:
                # Мод находится в архиве, нужно его переместить
                try:
                    # Создаем папку mods_path, если её нет
                    os.makedirs(target_mods_path, exist_ok=True)
                    # Перемещаем папку мода
                    shutil.move(mod.local_path, target_path)
                    logger.info(f"[ModManager/Enable] Мод {mod.mod_id} перемещен из '{mod.local_path}' в '{target_path}'.")
                    # 4. Обновляем путь и флаг в объекте Mod
                    mod.local_path = target_path
                    mod.is_enabled = True
                    # event_bus.emit("mod_enabled", mod_id) # Опционально
                    logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) включен.")
                    return True
                except Exception as e:
                    logger.error(f"[ModManager/Enable] Ошибка перемещения мода {mod.mod_id} из '{mod.local_path}' в '{target_path}': {e}")
                    return False
            elif os.path.exists(mod.local_path) and mod.local_path == target_path:
                # Мод уже в нужном месте, просто включаем
                mod.is_enabled = True
                logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) уже находится в основной папке, флаг установлен.")
                return True
            else:
                # Папка мода не найдена
                logger.warning(f"[ModManager/Enable] Папка мода {mod.mod_id} не найдена по пути '{mod.local_path}'.")
                # Можно попробовать создать заглушку или вернуть False
                return False
        elif mod and mod.is_enabled:
            logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) уже включен.")
            return True # Считаем успешным, если уже включен
        else:
            logger.warning(f"[ModManager] Не удалось включить мод {mod_id}: мод не найден или ошибка.")
            return False

    def disable_mod(self, game_steam_id: str, mod_id: str) -> bool:
        """
        Отключение мода.
        game_steam_id передается для согласованности, но не используется напрямую.
        """
        mod = self.get_mod_by_id(mod_id)
        if mod and mod.is_enabled:
            logger.info(f"[ModManager/Disable] Попытка отключения мода {mod.name} ({mod.mod_id})...")

            # --- ЛОГИКА ОТКЛЮЧЕНИЯ ---
            # 1. Проверяем, известна ли текущая игра
            if not self.current_game:
                logger.error(f"[ModManager/Disable] Неизвестна текущая игра для мода {mod_id}.")
                return False

            # 2. Определяем целевой путь (в папке archive)
            target_mods_path = self.current_game.mods_path
            archive_path = os.path.join(target_mods_path, "archive")
            target_path = os.path.join(archive_path, mod.mod_id)

            # 3. Проверяем, существует ли папка в основной директории
            if os.path.exists(mod.local_path) and mod.local_path != target_path:
                # Мод находится в основной папке, нужно его переместить
                try:
                    # Создаем папку archive, если её нет
                    os.makedirs(archive_path, exist_ok=True)
                    # Перемещаем папку мода
                    shutil.move(mod.local_path, target_path)
                    logger.info(f"[ModManager/Disable] Мод {mod.mod_id} перемещен из '{mod.local_path}' в '{target_path}'.")
                    # 4. Обновляем путь и флаг в объекте Mod
                    mod.local_path = target_path
                    mod.is_enabled = False
                    # event_bus.emit("mod_disabled", mod_id) # Опционально
                    logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) отключен.")
                    return True
                except Exception as e:
                    logger.error(f"[ModManager/Disable] Ошибка перемещения мода {mod.mod_id} из '{mod.local_path}' в '{target_path}': {e}")
                    return False
            elif os.path.exists(mod.local_path) and mod.local_path == target_path:
                # Мод уже в архиве, просто отключаем
                mod.is_enabled = False
                logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) уже находится в архиве, флаг установлен.")
                return True
            else:
                # Папка мода не найдена
                logger.warning(f"[ModManager/Disable] Папка мода {mod.mod_id} не найдена по пути '{mod.local_path}'.")
                # Можно попробовать создать заглушку или вернуть False
                return False
        elif mod and not mod.is_enabled:
            logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) уже отключен.")
            return True # Считаем успешным, если уже отключен
        else:
            logger.warning(f"[ModManager] Не удалось отключить мод {mod_id}: мод не найден или ошибка.")
            return False
    # --- КОНЕЦ ИСПРАВЛЕНИЙ ---

    def remove_mod(self, game_steam_id: str, mod_id: str) -> bool:
        """
        Удаление мода.
        game_steam_id передается для согласованности, но не используется напрямую.
        """
        mod = self.get_mod_by_id(mod_id)
        if mod:
            logger.info(f"[ModManager] Попытка удаления мода {mod.name} ({mod.mod_id})...")
            try:
                path_to_remove = mod.local_path
                if os.path.exists(path_to_remove):
                    shutil.rmtree(path_to_remove)
                    logger.info(f"[ModManager] Папка мода '{path_to_remove}' удалена.")
                else:
                    logger.warning(f"[ModManager] Папка мода '{path_to_remove}' не существует при попытке удаления.")

                self._mods.remove(mod)
                # event_bus.emit("mod_removed", mod_id) # Опционально, если нужно событие
                logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) удален из списка и с диска.")
                return True
            except Exception as e:
                logger.error(f"[ModManager] Ошибка удаления мода {mod.name} ({mod.mod_id}) по пути '{mod.local_path}': {e}")
        else:
            logger.warning(f"[ModManager] Попытка удаления несуществующего мода {mod_id}.")
        return False

    def check_for_updates(self) -> List[str]:
        """Проверка обновлений для модов"""
        updated_mods = []
        logger.debug("[ModManager] Проверка обновлений для модов (заглушка)")
        # TODO: Реализовать логику проверки обновлений
        return updated_mods

    def install_mod(self, mod: Mod, game: Game) -> bool:
        """Установка мода"""
        try:
            # Если мод уже есть — обновляем
            existing = self.get_mod_by_id(mod.mod_id)
            if existing:
                logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) уже существует, обновляем путь и статус.")
                existing.is_enabled = True # Или оставляем как есть?
                existing.local_path = mod.local_path
                # Можно обновить и другие поля, если они важны
                # existing.author = mod.author
                # existing.workshop_url = mod.workshop_url
                # existing.install_date = mod.install_date # Обновлять дату?
            else:
                self._mods.append(mod)
                logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) добавлен в список.")
            # event_bus.emit("mod_installed", mod.mod_id) # Опционально, если нужно событие
            logger.info(f"[ModManager] Мод {mod.name} ({mod.mod_id}) 'установлен' для игры {game.name}")
            return True
        except Exception as e:
            logger.error(f"[ModManager] Ошибка 'установки' мода {mod.name} ({mod.mod_id}): {e}")
            return False

# Примечание: Если ModsTab вызывает load_mods_for_game(game), а затем get_enabled_mods(game.steam_id),
# это будет работать корректно, так как self._mods будет содержать моды для последней загруженной игры.
# Однако это не потокобезопасно и может быть неочевидно. В будущем стоит рассмотреть
# возможность возвращать моды напрямую из load_mods_for_game или использовать
# отдельные экземпляры ModManager для каждой игры.
