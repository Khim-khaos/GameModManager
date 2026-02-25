# -*- coding: utf-8 -*-
"""
Система событий для связи между компонентами
"""

from typing import Dict, List, Callable, Any
from loguru import logger

class EventBus:
    """Центральная система событий"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Подписаться на событие"""
        self._listeners.setdefault(event_type, []).append(callback)
        logger.debug(f"Подписка на событие: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Отписаться от события"""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Отписка от события: {event_type}")
            except ValueError:
                pass

    def emit(self, event_type: str, data: Any = None):
        """Отправить событие"""
        if event_type in self._listeners:
            logger.debug(f"Отправка события: {event_type}")
            for callback in list(self._listeners[event_type]):  # Копия списка для безопасности
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Ошибка в обработчике события {event_type}: {e}")

# Глобальный экземпляр
event_bus = EventBus()
