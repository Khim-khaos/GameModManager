# -*- coding: utf-8 -*-
"""
Менеджер игр
"""
import os
import json
import psutil
from typing import List, Optional
from loguru import logger
from src.constants import GAMES_CONFIG_FILE
from src.models.game import Game
from src.event_bus import event_bus

class GameManager:
    """Менеджер игр"""

    def __init__(self):
        self._games: List[Game] = []
        self._load_games()

    def _load_games(self):
        """Загрузка списка игр из файла"""
        try:
            if os.path.exists(GAMES_CONFIG_FILE):
                with open(GAMES_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    games_data = json.load(f)
                    self._games = [Game.from_dict(data) for data in games_data]
                logger.info(f"Загружено {len(self._games)} игр")
            else:
                self._games = []
                self._save_games()
                logger.info("Создан пустой файл игр")
        except Exception as e:
            logger.error(f"Ошибка загрузки игр: {e}")
            self._games = []

    def _save_games(self):
        """Сохранение списка игр в файл"""
        try:
            games_data = [game.to_dict() for game in self._games]
            with open(GAMES_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(games_data, f, indent=4, ensure_ascii=False)
            logger.debug("Список игр сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения игр: {e}")

    def add_game(self, game: Game):
        """Добавление новой игры"""
        if not self.get_game_by_steam_id(game.steam_id):
            self._games.append(game)
            self._save_games()
            event_bus.emit("game_added", game)
            logger.info(f"Добавлена игра: {game.name}")
        else:
            logger.warning(f"Игра с Steam ID {game.steam_id} уже существует")

    def remove_game(self, steam_id: str):
        """Удаление игры по Steam ID"""
        game = self.get_game_by_steam_id(steam_id)
        if game:
            self._games.remove(game)
            self._save_games()
            event_bus.emit("game_removed", steam_id)
            logger.info(f"Удалена игра: {game.name}")

    def get_games(self) -> List[Game]:
        """Получение списка всех игр"""
        return self._games.copy()

    def get_game_by_steam_id(self, steam_id: str) -> Optional[Game]:
        """Получение игры по Steam ID"""
        for game in self._games:
            if game.steam_id == steam_id:
                return game
        return None

    def get_game_by_name(self, name: str) -> Optional[Game]:
        """Получение игры по названию"""
        for game in self._games:
            if game.name == name:
                return game
        return None

    def update_game(self, old_steam_id: str, updated_game_data: dict) -> bool:
        """
        Обновление данных существующей игры.

        :param old_steam_id: Steam ID игры, которую нужно обновить.
        :param updated_game_data: Словарь с новыми данными (name, steam_id, executable_path, mods_path).
        :return: True, если обновление прошло успешно, иначе False.
        """
        old_game = self.get_game_by_steam_id(old_steam_id)
        if not old_game:
            logger.warning(f"Игра с Steam ID {old_steam_id} не найдена для обновления")
            return False

        new_steam_id = updated_game_data.get("steam_id")

        # Проверка: если ID изменился, новая игра с таким ID не должна существовать
        if new_steam_id != old_steam_id and self.get_game_by_steam_id(new_steam_id):
            logger.error(f"Игра с новым Steam ID {new_steam_id} уже существует")
            # Можно вызвать wx.MessageBox здесь, но лучше, если это будет в UI
            return False

        try:
            # Создаем новый объект Game из обновленных данных
            updated_game = Game(**updated_game_data)

            # Удаляем старую игру
            self._games.remove(old_game)
            # Добавляем обновленную игру
            self._games.append(updated_game)

            self._save_games()
            logger.info(f"Игра обновлена: '{old_game.name}' ({old_steam_id}) -> '{updated_game.name}' ({updated_game.steam_id})")

            # Эмитируем события. Если ID изменился, это два разных события.
            if old_steam_id != new_steam_id:
                event_bus.emit("game_removed", old_steam_id)
                event_bus.emit("game_added", updated_game) # Передаем объект
            else:
                event_bus.emit("game_updated", updated_game.steam_id) # Передаем ID

            return True
        except ValueError as e:
            logger.error(f"Ошибка валидации данных игры при обновлении: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении игры {old_steam_id}: {e}")
            return False

    def launch_game(self, steam_id: str) -> bool:
        """Запуск игры"""
        game = self.get_game_by_steam_id(steam_id)
        if game and os.path.exists(game.executable_path):
            try:
                # Здесь должна быть логика запуска игры
                # Для примера просто помечаем как запущенную
                game.is_running = True
                self._save_games()
                event_bus.emit("game_launched", steam_id)
                logger.info(f"Игра {game.name} запущена")
                return True
            except Exception as e:
                logger.error(f"Ошибка запуска игры {game.name}: {e}")
                return False
        return False

    def stop_game(self, steam_id: str) -> bool:
        """Остановка игры"""
        game = self.get_game_by_steam_id(steam_id)
        if game:
            try:
                # Здесь должна быть логика остановки игры
                # Для примера просто помечаем как остановленную
                game.is_running = False
                self._save_games()
                event_bus.emit("game_stopped", steam_id)
                logger.info(f"Игра {game.name} остановлена")
                return True
            except Exception as e:
                logger.error(f"Ошибка остановки игры {game.name}: {e}")
                return False
        return False

    def is_game_running(self, steam_id: str) -> bool:
        """Проверка, запущена ли игра"""
        game = self.get_game_by_steam_id(steam_id)
        if game:
            # Здесь должна быть логика проверки запущенного процесса
            # Пока используем флаг из модели
            return game.is_running
        return False
