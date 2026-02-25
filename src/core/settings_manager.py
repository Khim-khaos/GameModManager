# -*- coding: utf-8 -*-
"""
Менеджер настроек приложения
"""
import os
import json
from typing import Dict, Any
from loguru import logger
from src.constants import SETTINGS_CONFIG_FILE
from src.data.config import DEFAULT_SETTINGS

class SettingsManager:
    """Менеджер настроек"""

    def __init__(self):
        self._settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists(SETTINGS_CONFIG_FILE):
                with open(SETTINGS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
                logger.info("Настройки загружены из файла")
            else:
                self._settings = DEFAULT_SETTINGS.copy()
                self._save_settings()
                logger.info("Создан файл настроек по умолчанию")
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
            self._settings = DEFAULT_SETTINGS.copy()

    def _save_settings(self):
        """Сохранение настроек в файл"""
        try:
            os.makedirs(os.path.dirname(SETTINGS_CONFIG_FILE), exist_ok=True)
            with open(SETTINGS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            logger.debug("Настройки сохранены в файл")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")

    def get(self, key: str, default=None):
        """Получение значения настройки"""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Установка значения настройки"""
        self._settings[key] = value
        self._save_settings()
        logger.debug(f"Настройка {key} изменена на {value}")

    def get_all(self) -> Dict[str, Any]:
        """Получение всех настроек"""
        return self._settings.copy()

    def update(self, settings_dict: Dict[str, Any]):
        """Обновление нескольких настроек"""
        self._settings.update(settings_dict)
        self._save_settings()
        logger.debug("Настройки обновлены")
