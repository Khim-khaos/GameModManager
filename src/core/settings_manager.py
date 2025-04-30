import json
import os
from loguru import logger


class SettingsManager:
    """Менеджер настроек для загрузки и сохранения конфигурации приложения."""

    def __init__(self):
        self.settings_path = "data/settings.json"
        self.default_settings = {
            "steamcmd_path": "",
            "language": "rus",
            "background": "",
            "opacity": 1.0,
            "font_size": 12,
            "theme": "light",
            "window_x": 100,
            "window_y": 100,
            "window_width": 1200,
            "window_height": 800
        }
        self.settings = self.default_settings.copy()
        self.load_settings()

    def load_settings(self):
        """Загружает настройки из файла или создает новый с настройками по умолчанию."""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.settings.update(json.loads(content))
                        logger.info("Настройки загружены")
                    else:
                        logger.warning("Файл настроек пуст, используются настройки по умолчанию")
                        self.save_settings()
            else:
                logger.info("Файл настроек не найден, создается новый")
                self.save_settings()
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON в настройках: {e}")
            self.save_settings()  # Пересоздаем файл с настройками по умолчанию
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
            self.save_settings()

    def save_settings(self):
        """Сохраняет настройки в файл."""
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logger.info("Настройки сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
