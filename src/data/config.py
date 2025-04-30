import json
from pathlib import Path
from loguru import logger
import sys

class Config:
    def __init__(self):
        # Определяем базовый путь для работы с .exe
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        self.config_file = base_path / "data" / "config.json"
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
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save_config()

    def get_available_languages(self):
        """Возвращает список доступных языков: [(имя_файла, нормальное_название), ...]"""
        # Определяем путь к папке language
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        language_dir = base_path / "language"
        languages = []
        if not language_dir.exists():
            logger.error("Папка language не найдена!")
            return languages

        for lang_file in language_dir.glob("*.json"):
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    lang_data = json.load(f)
                    lang_name = lang_data.get("language_name", lang_file.stem)
                    languages.append((lang_file.stem, lang_name))
            except Exception as e:
                logger.error(f"Ошибка при чтении файла языка {lang_file}: {e}")
        return languages
