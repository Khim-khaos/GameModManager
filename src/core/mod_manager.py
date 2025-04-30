from core.steam_handler import SteamHandler
from ui.dialogs.dependency_dialog import DependencyDialog
from bs4 import BeautifulSoup
import aiohttp
import json
import os
import hashlib
from loguru import logger


class ModManager:
    """Менеджер модов для управления загрузкой, проверкой и состоянием модов."""

    def __init__(self):
        self.queue = []
        self.steam_handler = None
        self.cache_path = "data/mod_cache.json"
        self.mod_cache = self.load_cache()

    def load_cache(self):
        """Загружает кэш модов из файла."""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки кэша модов: {e}")
            return {}

    def save_cache(self):
        """Сохраняет кэш модов в файл."""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.mod_cache, f, indent=4, ensure_ascii=False)
            logger.info("Кэш модов сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша модов: {e}")

    def set_steam_handler(self, steam_handler):
        """Устанавливает обработчик SteamCMD."""
        self.steam_handler = steam_handler

    def add_to_queue(self, game, mod_id):
        """Добавляет мод в очередь загрузки."""
        self.queue.append({"game": game, "mod_id": mod_id})
        logger.info(f"Мод {mod_id} добавлен в очередь")

    def clear_queue(self):
        """Очищает очередь загрузки."""
        self.queue.clear()
        logger.info("Очередь очищена")

    async def check_dependencies(self, app_id, mod_id, parent=None):
        """Проверяет зависимости мода, используя кэш или парсинг страницы."""
        if mod_id in self.mod_cache:
            logger.info(f"Использован кэш для мода {mod_id}")
            return self.mod_cache[mod_id].get("dependencies", [])

        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    dep_section = soup.find("div", class_="requiredItems")
                    dependencies = []
                    if dep_section:
                        dep_links = dep_section.find_all("a")
                        dependencies = [link["href"].split("id=")[-1] for link in dep_links]
                    self.mod_cache[mod_id] = self.mod_cache.get(mod_id, {})
                    self.mod_cache[mod_id]["dependencies"] = dependencies
                    self.save_cache()
                    if dependencies and parent:
                        dialog = DependencyDialog(dependencies, parent)
                        if dialog.exec():
                            return dialog.selected_dependencies
                    return dependencies
        return []

    async def get_mod_info(self, mod_id):
        """Получает информацию о моде (название, описание) из Steam Workshop."""
        if mod_id in self.mod_cache and "name" in self.mod_cache[mod_id] and "description" in self.mod_cache[mod_id]:
            logger.info(f"Использован кэш для информации о моде {mod_id}")
            return self.mod_cache[mod_id]

        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    name = soup.find("div", class_="workshopItemTitle")
                    description = soup.find("div", class_="workshopItemDescription")
                    mod_info = {
                        "name": name.text.strip() if name else "Неизвестный мод",
                        "description": description.text.strip() if description else "Описание отсутствует",
                        "dependencies": self.mod_cache.get(mod_id, {}).get("dependencies", [])
                    }
                    self.mod_cache[mod_id] = mod_info
                    self.save_cache()
                    return mod_info
        return {"name": "Неизвестный мод", "description": "Ошибка загрузки", "dependencies": []}

    def download_mod(self, game, mod_id, console_tab):
        """Запускает загрузку мода через SteamCMD."""
        if self.steam_handler:
            success = self.steam_handler.download_mod(game.app_id, mod_id, game.mods_path, console_tab)
            if success:
                self.check_mod_integrity(game.mods_path, mod_id)
            return success
        return False

    def check_mod_integrity(self, mods_path, mod_id):
        """Проверяет целостность загруженного мода."""
        mod_path = os.path.join(mods_path, mod_id)
        if not os.path.exists(mod_path):
            logger.error(f"Мод {mod_id} не найден в {mod_path}")
            return False

        # Простая проверка: вычисляем хэш содержимого папки мода
        hash_md5 = hashlib.md5()
        for root, _, files in os.walk(mod_path):
            for file in sorted(files):
                with open(os.path.join(root, file), "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
        mod_hash = hash_md5.hexdigest()
        logger.info(f"Хэш мода {mod_id}: {mod_hash}")
        # Здесь можно добавить сравнение с ожидаемым хэшем, если он доступен
        return True

    def toggle_mod(self, game, mod_id, enable=True):
        """Включает или отключает мод, переименовывая его папку."""
        mod_path = os.path.join(game.mods_path, mod_id)
        disabled_path = os.path.join(game.mods_path, f"{mod_id}_disabled")
        if enable and os.path.exists(disabled_path):
            os.rename(disabled_path, mod_path)
            logger.info(f"Мод {mod_id} включен для игры {game.name}")
        elif not enable and os.path.exists(mod_path):
            os.rename(mod_path, disabled_path)
            logger.info(f"Мод {mod_id} отключен для игры {game.name}")
