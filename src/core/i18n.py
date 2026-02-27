# -*- coding: utf-8 -*-
"""
Модуль для международизации (i18n)
Предоставляет глобальный доступ к менеджеру языков
"""

from typing import Optional
from loguru import logger

class I18n:
    """Класс для международизации"""
    
    def __init__(self):
        self._language_manager = None
    
    def set_language_manager(self, language_manager):
        """Устанавливает менеджер языков"""
        self._language_manager = language_manager
        logger.debug("[I18n] Language manager set")
    
    def get_text(self, key: str, **kwargs) -> str:
        """Получение переведенного текста по ключу"""
        if self._language_manager is None:
            # Если менеджер языков еще не установлен, возвращаем ключ
            logger.warning(f"[I18n] Language manager not set, returning key: {key}")
            return key
        
        return self._language_manager.get_text(key, **kwargs)
    
    def get_current_language(self) -> str:
        """Получение текущего языка"""
        if self._language_manager is None:
            return "en"
        return self._language_manager.get_current_language()

# Глобальный экземпляр для доступа из любого места
i18n = I18n()

def _(key: str, **kwargs) -> str:
    """Удобная функция для перевода (как в gettext)"""
    return i18n.get_text(key, **kwargs)
