# -*- coding: utf-8 -*-
"""
Менеджер языков
"""
import os
import json
from typing import Dict, List
from loguru import logger
from src.constants import LANGUAGE_DIR
from src.event_bus import event_bus

class LanguageManager:
    """Менеджер языков"""

    def __init__(self):
        self._languages: Dict[str, Dict[str, str]] = {}
        self._current_language: str = "en"
        self._load_languages()

    def _load_languages(self):
        """Загрузка всех доступных языков"""
        if not os.path.exists(LANGUAGE_DIR):
            logger.warning("Папка с языками не найдена")
            return

        for filename in os.listdir(LANGUAGE_DIR):
            if filename.endswith('.json'):
                lang_code = filename[:-5]
                try:
                    with open(os.path.join(LANGUAGE_DIR, filename), 'r', encoding='utf-8') as f:
                        lang_data = json.load(f)
                        self._languages[lang_code] = lang_data
                        logger.debug(f"Загружен язык: {lang_code}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки языка {filename}: {e}")

    def get_available_languages(self) -> List[Dict[str, str]]:
        """Получение списка доступных языков"""
        return [
            {'code': code, 'name': data.get('language_name', code)}
            for code, data in self._languages.items()
        ]

    def set_language(self, lang_code: str):
        """Установка текущего языка"""
        if lang_code in self._languages:
            self._current_language = lang_code
            event_bus.emit("language_changed", lang_code)
            logger.info(f"Язык изменен на: {lang_code}")
        else:
            logger.warning(f"Язык {lang_code} не найден")

    def get_text(self, key: str, **kwargs) -> str:
        """Получение переведенного текста по ключу"""
        keys = key.split('.')
        current_data = self._languages.get(self._current_language, {})
        for k in keys:
            if isinstance(current_data, dict) and k in current_data:
                current_data = current_data[k]
            else:
                return key
        if isinstance(current_data, str):
            try:
                return current_data.format(**kwargs)
            except KeyError:
                return current_data
        return str(current_data)

    def get_current_language(self) -> str:
        """Получение кода текущего языка"""
        return self._current_language
