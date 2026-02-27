# -*- coding: utf-8 -*-
"""
Мониторинг статуса игр в фоновом потоке
"""
import time
import threading
from typing import Callable, Optional
from loguru import logger
from src.core.game_manager import GameManager


class StatusMonitor:
    """Фоновый мониторинг статуса игр"""
    
    def __init__(self, game_manager: GameManager, update_interval: float = 5.0):
        self.game_manager = game_manager
        self.update_interval = update_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._status_callbacks: list = []
    
    def add_status_callback(self, callback: Callable[[str, bool], None]):
        """Добавление callback для изменения статуса игр"""
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[str, bool], None]):
        """Удаление callback"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def start(self):
        """Запуск фонового мониторинга"""
        if self._running:
            logger.warning("Мониторинг статуса уже запущен")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Мониторинг статуса игр запущен (интервал: {self.update_interval}с)")
    
    def stop(self):
        """Остановка мониторинга"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Мониторинг статуса игр остановлен")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self._running:
            try:
                # Обновляем статус всех игр
                updated_games = self.game_manager.update_all_games_status()
                
                # Вызываем callbacks для измененных игр
                for game in updated_games:
                    for callback in self._status_callbacks:
                        try:
                            callback(game.steam_id, game.is_running)
                        except Exception as e:
                            logger.error(f"Ошибка в callback статуса: {e}")
                
                # Пауза до следующей проверки
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(self.update_interval)
    
    def force_update(self):
        """Принудительное обновление статуса"""
        try:
            updated_games = self.game_manager.update_all_games_status()
            logger.debug(f"Принудительно обновлен статус {len(updated_games)} игр")
            return updated_games
        except Exception as e:
            logger.error(f"Ошибка принудительного обновления: {e}")
            return []
    
    @property
    def is_running(self) -> bool:
        """Проверка, запущен ли мониторинг"""
        return self._running
