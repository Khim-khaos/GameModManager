import sys
import os
import wx
import atexit

from src.core.task_manager import task_manager

# Добавляем src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.main_window import MainWindow
from src.core.logger import setup_logger
from src.core.settings_manager import SettingsManager
from src.core.language_manager import LanguageManager

class GameModManagerApp(wx.App):
    def OnInit(self):
        # Настраиваем логирование
        setup_logger()

        # Инициализируем менеджеры (можно использовать для ранней загрузки языков/настроек)
        self.settings_manager = SettingsManager()
        self.language_manager = LanguageManager()

        # Создаем главное окно
        frame = MainWindow()
        frame.Show()
        return True

if __name__ == '__main__':
    app = GameModManagerApp()
    app.MainLoop()
    atexit.register(task_manager.shutdown)
