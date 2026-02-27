import sys
import os
import wx
import atexit

from src.core.task_manager import task_manager

# Добавляем src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Создаем директорию данных при запуске EXE
def ensure_data_directory():
    """Создает директорию данных для настроек и игр"""
    if getattr(sys, 'frozen', False):
        # Запущено как EXE файл
        base_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(base_dir, 'data')
    else:
        # Запущено как скрипт
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'src', 'data')
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Также создаем директорию для логов
    logs_dir = os.path.join(os.path.dirname(data_dir), 'src', 'Logs')
    if not getattr(sys, 'frozen', False):
        os.makedirs(logs_dir, exist_ok=True)
    
    return data_dir

from src.ui.main_window import MainWindow
from src.core.logger import setup_logger
from src.core.settings_manager import SettingsManager
from src.core.language_manager import LanguageManager
from src.core.i18n import i18n

class GameModManagerApp(wx.App):
    def OnInit(self):
        # Создаем директорию данных
        ensure_data_directory()
        
        # Настраиваем логирование
        setup_logger()

        # Инициализируем менеджеры (можно использовать для ранней загрузки языков/настроек)
        self.settings_manager = SettingsManager()
        self.language_manager = LanguageManager()
        
        # Устанавливаем глобальный менеджер языков для i18n
        i18n.set_language_manager(self.language_manager)
        
        # Загружаем язык из настроек и применяем его
        saved_language = self.settings_manager.get("language", "en")
        print(f"[DEBUG] Loading language from settings: {saved_language}")
        self.language_manager.set_language(saved_language)
        print(f"[DEBUG] Current language after setting: {self.language_manager.get_current_language()}")

        # Создаем главное окно
        frame = MainWindow(self.settings_manager, self.language_manager)
        frame.Show()
        return True

if __name__ == '__main__':
    app = GameModManagerApp()
    app.MainLoop()
    atexit.register(task_manager.shutdown)
