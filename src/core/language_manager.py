import json
import os
from loguru import logger

class LanguageManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        lang = self.settings_manager.settings.get("language", "rus")
        lang_file = f"language/{lang}.json"
        try:
            if os.path.exists(lang_file):
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                logger.info(f"Загружен перевод для языка: {lang}")
            else:
                logger.warning(f"Файл перевода {lang_file} не найден")
        except Exception as e:
            logger.error(f"Ошибка загрузки перевода: {e}")

    def get(self, key, default=None):
        return self.translations.get(key, default or key)

    def reload(self):
        self.load_translations()
