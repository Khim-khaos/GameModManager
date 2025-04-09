import json
from pathlib import Path
from loguru import logger

class Config:
    def __init__(self):
        self.config_file = Path(__file__).parent.parent / "data" / "config.json"
        self.data = {
            "steamcmd_path": "",
            "language": "rus",
            "theme": "dark",
            "background_image": "",
            "opacity": 1.0
        }
        self.load_config()

    def load_config(self):
        if not self.config_file.exists():
            logger.info("Файл config.json не существует, создается с настройками по умолчанию")
            self.save_config()
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.warning("Файл config.json пуст, используются настройки по умолчанию")
                    self.save_config()
                else:
                    self.data = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Ошибка декодирования config.json, используются настройки по умолчанию")
            self.save_config()
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке config.json: {e}")
            self.save_config()

    def save_config(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        logger.info("Конфигурация сохранена")

    def get(self, key, default=None):
        return self.data.get(key, default)  # Используем dict.get с поддержкой значения по умолчанию

    def set(self, key, value):
        self.data[key] = value
        self.save_config()

