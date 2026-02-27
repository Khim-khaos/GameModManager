# -*- coding: utf-8 -*-
"""
Главное окно приложения
"""
import wx
import os
import subprocess
import threading
# wx.html2 импортируется внутри BrowserTab, здесь он не нужен напрямую
from loguru import logger
from src.event_bus import event_bus
from src.core.game_manager import GameManager
from src.core.mod_manager import ModManager
from src.core.settings_manager import SettingsManager
from src.core.language_manager import LanguageManager
from src.core.i18n import _
from src.core.steam_handler import SteamHandler
from src.core.download_manager import DownloadManager
from src.core.status_monitor import StatusMonitor
from src.ui.dialogs.add_game_dialog import AddGameDialog
# --- Импорт новых диалогов ---
from src.ui.dialogs.edit_game_dialog import EditGameDialog
# -----------------------------
from src.ui.dialogs.settings_dialog import SettingsDialog
# --- Импорт новых сервисов ---
from src.core.steam_workshop_service import SteamWorkshopService
from src.core.task_manager import TaskManager
# ----------------------------
from src.ui.tabs.mods_tab import ModsTab
from src.ui.tabs.browser_tab import BrowserTab
from src.ui.tabs.logs_tab import LogsTab

class MainWindow(wx.Frame):
    """Главное окно приложения"""

    def __init__(self, settings_manager=None, language_manager=None):
        super().__init__(None, title="GameModManager", size=(1200, 800))
        
        # Используем переданные менеджеры или создаем новые
        self.settings_manager = settings_manager or SettingsManager()
        self.language_manager = language_manager or LanguageManager()
        
        # Устанавливаем глобальный менеджер языков если он не был установлен
        from src.core.i18n import i18n
        if i18n._language_manager is None:
            i18n.set_language_manager(self.language_manager)

        # Инициализация менеджеров
        self.game_manager = GameManager()
        self.mod_manager = ModManager()

        # Инициализация SteamCMD
        steamcmd_path = self.settings_manager.get("steamcmd_path", "")
        self.steam_handler = SteamHandler(steamcmd_path)
        self.download_manager = DownloadManager(self.steam_handler)

        # --- Инициализация новых сервисов ---
        self.steam_workshop_service = SteamWorkshopService()
        self.task_manager = TaskManager()
        self.status_monitor = StatusMonitor(self.game_manager, update_interval=3.0)
        # -----------------------------------

        # Текущая выбранная игра
        self.current_game = None
        self.game_process = None

        # Создание UI
        self._create_ui()
        self._setup_event_handlers()

        # Центрирование окна
        self.Center()

    def _create_ui(self):
        self.CreateStatusBar()
        self.SetStatusText(_("ui.ready"))
        self._create_menu()
        self._create_game_selector_panel()
        self._create_notebook_tabs()

    def _create_menu(self):
        # Меню убрано, так как все кнопки вынесены в основной интерфейс
        pass

    def _create_game_selector_panel(self):
        self.game_selector_panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.game_choice = wx.Choice(self.game_selector_panel, choices=[])
        self.game_choice.Bind(wx.EVT_CHOICE, self._on_game_selected)
        sizer.Add(self.game_choice, 1, wx.EXPAND | wx.ALL, 5)

        self.add_game_btn = wx.Button(self.game_selector_panel, label=_("ui.add_game"))
        self.add_game_btn.Bind(wx.EVT_BUTTON, self._on_add_game)
        sizer.Add(self.add_game_btn, 0, wx.ALL, 5)

        # --- НОВЫЕ КНОПКИ ---
        self.edit_game_btn = wx.Button(self.game_selector_panel, label=_("ui.edit_game"))
        self.edit_game_btn.Bind(wx.EVT_BUTTON, self._on_edit_game)
        self.edit_game_btn.Enable(False) # Отключена, если игра не выбрана
        sizer.Add(self.edit_game_btn, 0, wx.ALL, 5)

        self.remove_game_btn = wx.Button(self.game_selector_panel, label=_("ui.remove_game"))
        self.remove_game_btn.Bind(wx.EVT_BUTTON, self._on_remove_game)
        self.remove_game_btn.Enable(False) # Отключена, если игра не выбрана
        sizer.Add(self.remove_game_btn, 0, wx.ALL, 5)
        # ---------------------

        self.launch_game_btn = wx.Button(self.game_selector_panel, label=_("ui.launch_game"))
        self.launch_game_btn.Bind(wx.EVT_BUTTON, self._on_launch_game)
        self.launch_game_btn.Enable(False)
        sizer.Add(self.launch_game_btn, 0, wx.ALL, 5)

        # --- Добавляем кнопки настроек и выхода ---
        self.settings_btn = wx.Button(self.game_selector_panel, label=_("ui.settings"))
        self.settings_btn.Bind(wx.EVT_BUTTON, self._on_settings)
        sizer.Add(self.settings_btn, 0, wx.ALL, 5)

        self.exit_btn = wx.Button(self.game_selector_panel, label=_("ui.exit"))
        self.exit_btn.Bind(wx.EVT_BUTTON, self._on_exit)
        sizer.Add(self.exit_btn, 0, wx.ALL, 5)
        # -----------------------------------------

        self.game_selector_panel.SetSizer(sizer)
        self._update_game_list()

    def _create_notebook_tabs(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.game_selector_panel, 0, wx.EXPAND)
        self.notebook = wx.Notebook(self)
        # --- ИСПРАВЛЕНИЕ: Передаем новые сервисы в ModsTab ---
        self.mods_tab = ModsTab(
            self.notebook,
            self.mod_manager,
            self.language_manager,
            self.steam_workshop_service,
            self.task_manager
        )
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
        self.notebook.AddPage(self.mods_tab, _("ui.mods"))
        # --- ИСПРАВЛЕНИЕ: Передаем mod_manager в BrowserTab ---
        self.browser_tab = BrowserTab(self.notebook, self.download_manager, self.language_manager, self.mod_manager)
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
        self.notebook.AddPage(self.browser_tab, _("ui.browser"))
        self.logs_tab = LogsTab(self.notebook, self.language_manager)
        self.notebook.AddPage(self.logs_tab, _("ui.logs"))
        main_sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(main_sizer)

    def _setup_event_handlers(self):
        event_bus.subscribe("game_added", self._on_game_list_changed)
        event_bus.subscribe("game_removed", self._on_game_list_changed)
        # --- Подписка на новое событие ---
        event_bus.subscribe("game_updated", self._on_game_list_changed)
        # ---------------------------------
        event_bus.subscribe("game_started", self._on_game_status_callback)
        event_bus.subscribe("game_stopped", self._on_game_status_callback)
        event_bus.subscribe("open_mod_in_browser", self._on_open_mod_in_browser)
        event_bus.subscribe("mods_updated", self._on_mods_updated)
        
        # Подписка на событие смены языка
        event_bus.subscribe("language_changed", self._on_language_changed)
        
        # Запускаем мониторинг статуса игр
        self.status_monitor.add_status_callback(self._on_game_status_callback)
        self.status_monitor.start()

    # --- ИСПРАВЛЕННЫЙ _update_game_list ---
    def _update_game_list(self):
        """Обновляет выпадающий список игр."""
        games = self.game_manager.get_games()
        game_names = [game.name for game in games]
        self.game_choice.Clear()
        self.game_choice.AppendItems(game_names)
        if game_names:
            self.game_choice.SetSelection(0)
            self._select_game_by_index(0)
        else:
            # Если игр нет, сбрасываем выбор и отключаем кнопки
            self.current_game = None
            self.launch_game_btn.Enable(False)
            self.edit_game_btn.Enable(False)
            self.remove_game_btn.Enable(False)
            if hasattr(self, 'mods_tab'):
                self.mods_tab.set_game(None)
            if hasattr(self, 'browser_tab'):
                self.browser_tab.set_game(None)
            logger.debug("[MainWindow] " + _("system.game_list_empty"))

    # --- КОНЕЦ ИСПРАВЛЕННОГО _update_game_list ---

    # --- ИСПРАВЛЕННЫЙ _select_game_by_index ---
    def _select_game_by_index(self, index: int):
        """Выбирает игру по индексу и обновляет UI."""
        games = self.game_manager.get_games()
        if 0 <= index < len(games):
            self.current_game = games[index]
            self.launch_game_btn.Enable(True)

            # Обновляем текст кнопки и статус в зависимости от состояния игры
            if self.current_game.is_running:
                # Проверяем, действительно ли процесс запущен
                if self._is_game_process_running():
                    self.launch_game_btn.SetLabel("Остановить игру")
                    self.SetStatusText("Игра запущена")
                else:
                    # Сбросим статус игры, если процесс не запущен
                    self.current_game.is_running = False
                    self.game_manager.update_game(self.current_game.steam_id, self.current_game.to_dict())
                    self.launch_game_btn.SetLabel(_("ui.launch_game"))
                    self.SetStatusText(_("ui.ready"))
            else:
                self.launch_game_btn.SetLabel(_("ui.launch_game"))
                self.SetStatusText(_("ui.ready"))

            # --- Включаем кнопки редактирования и удаления ---
            self.edit_game_btn.Enable(True)
            self.remove_game_btn.Enable(True)
            # -------------------------------------------------
            if hasattr(self, 'mods_tab'):
                self.mods_tab.set_game(self.current_game)
            if hasattr(self, 'browser_tab'):
                self.browser_tab.set_game(self.current_game)
            logger.info("[MainWindow] " + _("system.game_selected", name=self.current_game.name))
        else:
            self.current_game = None
            self.launch_game_btn.Enable(False)
            self.launch_game_btn.SetLabel(_("ui.launch_game"))
            self.SetStatusText(_("ui.ready"))
            # --- Отключаем кнопки редактирования и удаления ---
            self.edit_game_btn.Enable(False)
            self.remove_game_btn.Enable(False)
            # --------------------------------------------------
            # Опционально: сбросить UI вкладок, если игра была удалена
            # if hasattr(self, 'mods_tab'):
            #     self.mods_tab.set_game(None)
            # if hasattr(self, 'browser_tab'):
            #     self.browser_tab.set_game(None)

    # --- КОНЕЦ ИСПРАВЛЕННОГО _select_game_by_index ---

    def _on_game_selected(self, event):
        selection = self.game_choice.GetSelection()
        self._select_game_by_index(selection)

    def _on_add_game(self, event):
        dialog = AddGameDialog(self, self.language_manager)
        if dialog.ShowModal() == wx.ID_OK:
            game_data = dialog.get_game_data()
            if game_data:
                from src.models.game import Game
                try:
                    game = Game(**game_data)
                    self.game_manager.add_game(game)
                except ValueError as e:
                    wx.MessageBox(f"Ошибка: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

    # --- НОВЫЕ МЕТОДЫ ---
    def _on_edit_game(self, event):
        """Обработчик нажатия кнопки 'Редактировать игру'."""
        if not self.current_game:
            return

        dialog = EditGameDialog(self, self.language_manager, self.current_game)
        if dialog.ShowModal() == wx.ID_OK:
            updated_data = dialog.get_updated_game_data()
            if updated_data:
                old_steam_id = dialog.get_original_steam_id()
                success = self.game_manager.update_game(old_steam_id, updated_data)
                if not success:
                    # Если update_game вернул False, возможно, ID уже существует
                    # GameManager уже залогировал ошибку
                    wx.MessageBox("Не удалось обновить игру. Проверьте, не используется ли уже новый Steam ID.", "Ошибка", wx.OK | wx.ICON_ERROR)
                # _update_game_list будет вызван через событие game_updated/game_removed+game_added
        dialog.Destroy()

    def _on_remove_game(self, event):
        """Обработчик нажатия кнопки 'Удалить игру'."""
        if not self.current_game:
            return

        res = wx.MessageBox(
            f"Вы уверены, что хотите удалить игру '{self.current_game.name}' из списка?\n"
            f"(Файлы игры не будут удалены с вашего компьютера)",
            "Подтверждение удаления",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        if res == wx.YES:
            steam_id_to_remove = self.current_game.steam_id
            # Сохраняем индекс текущей игры, чтобы потом выбрать следующую/предыдущую
            # current_index = self.game_choice.GetSelection() # Не используется напрямую
            self.game_manager.remove_game(steam_id_to_remove)
            # _update_game_list будет вызван через событие game_removed
            # Логика выбора новой игры теперь в _update_game_list

    # --------------------

    def _on_launch_game(self, event):
        """Обработчик запуска/отключения игры"""
        if not self.current_game:
            wx.MessageBox("Сначала выберите игру", "Ошибка", wx.OK | wx.ICON_WARNING)
            return

        try:
            executable_path = self.current_game.executable_path
            if not os.path.exists(executable_path):
                wx.MessageBox(f"Исполняемый файл не найден:\n{executable_path}", "Ошибка", wx.OK | wx.ICON_ERROR)
                return

            if self.current_game.is_running:
                # Остановить игру
                success = self._stop_game()
                if success:
                    self.current_game.is_running = False
                    self.game_manager.update_game(self.current_game.steam_id, self.current_game.to_dict())
                    self.launch_game_btn.SetLabel(_("ui.launch_game"))
                    self.SetStatusText("Игра остановлена")
                    logger.info(f"Игра '{self.current_game.name}' остановлена")
                else:
                    wx.MessageBox("Не удалось остановить игру", "Ошибка", wx.OK | wx.ICON_ERROR)
            else:
                # Запустить игру
                success = self._start_game()
                if success:
                    self.current_game.is_running = True
                    self.game_manager.update_game(self.current_game.steam_id, self.current_game.to_dict())
                    self.launch_game_btn.SetLabel("Остановить игру")
                    self.SetStatusText("Игра запущена")
                    logger.info(f"Игра '{self.current_game.name}' запущена")
                else:
                    wx.MessageBox("Не удалось запустить игру", "Ошибка", wx.OK | wx.ICON_ERROR)

        except Exception as e:
            logger.error(f"Ошибка при работе с игрой: {e}")
            wx.MessageBox(f"Ошибка: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)

    def _start_game(self) -> bool:
        """Запускает игру в отдельном процессе"""
        try:
            import subprocess
            game_dir = os.path.dirname(self.current_game.executable_path)

            self.game_process = subprocess.Popen(
                [self.current_game.executable_path],
                cwd=game_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
            )

            # Запускаем мониторинг процесса в отдельном потоке
            threading.Thread(target=self._monitor_game_process, daemon=True).start()

            logger.info(f"Игра '{self.current_game.name}' запущена с PID {self.game_process.pid}")
            return True

        except Exception as e:
            logger.error(f"Ошибка запуска игры: {e}")
            return False

    def _stop_game(self) -> bool:
        """Останавливает запущенную игру"""
        try:
            if hasattr(self, 'game_process') and self.game_process:
                if self.game_process.poll() is None:  # Процесс еще работает
                    self.game_process.terminate()
                    try:
                        self.game_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.game_process.kill()  # Принудительное завершение
                        self.game_process.wait()

                    logger.info(f"Игра '{self.current_game.name}' остановлена")
                    return True
            return False

        except Exception as e:
            logger.error(f"Ошибка остановки игры: {e}")
            return False

    def _monitor_game_process(self):
        """Мониторит процесс игры и обновляет UI при его завершении"""
        try:
            if hasattr(self, 'game_process') and self.game_process:
                # Ждем завершения процесса
                self.game_process.wait()

                # Игра завершилась
                wx.CallAfter(self._on_game_process_exited)

        except Exception as e:
            logger.error(f"Ошибка мониторинга процесса игры: {e}")

    def _on_game_process_exited(self):
        """Вызывается, когда процесс игры завершился"""
        try:
            if self.current_game:
                self.current_game.is_running = False
                self.game_manager.update_game(self.current_game.steam_id, self.current_game.to_dict())
                self.launch_game_btn.SetLabel(_("ui.launch_game"))
                self.SetStatusText(_("ui.ready"))
                logger.info(f"Игра '{self.current_game.name}' завершилась")

                # Очищаем ссылку на процесс
                if hasattr(self, 'game_process'):
                    self.game_process = None

        except Exception as e:
            logger.error(f"Ошибка обновления статуса игры: {e}")

    def _is_game_process_running(self) -> bool:
        """Проверяет, запущен ли процесс игры"""
        if hasattr(self, 'game_process') and self.game_process:
            return self.game_process.poll() is None
        return False

    # --- ИСПРАВЛЕННЫЙ _on_game_list_changed ---
    def _on_game_list_changed(self, data):
        """Вызывается при добавлении, удалении или обновлении игры."""
        # Сохраняем имя текущей игры, если она есть
        current_game_name = self.current_game.name if self.current_game else None
        self._update_game_list()
        # Пытаемся восстановить выбор, если игра всё ещё в списке
        if current_game_name:
            games = self.game_manager.get_games()
            for i, game in enumerate(games):
                if game.name == current_game_name:
                    self.game_choice.SetSelection(i)
                    self._select_game_by_index(i)
                    break

    # --- КОНЕЦ ИСПРАВЛЕННОГО _on_game_list_changed ---

    # --- ИСПРАВЛЕННЫЙ _on_open_mod_in_browser ---
    def _on_open_mod_in_browser(self, url):
        """
        Открывает URL мода во вкладке "Браузер".
        """
        logger.debug(f"[MainWindow/OpenMod] Получен URL для открытия: {url}")
        # --- ИСПРАВЛЕНИЕ ОШИБКИ ---
        # Вместо жестко заданного индекса 1, найдем страницу BrowserTab
        # Проверим, существует ли browser_tab и находится ли он в notebook
        if hasattr(self, 'browser_tab') and self.browser_tab:
            # Найдем индекс вкладки BrowserTab
            tab_index = self.notebook.FindPage(self.browser_tab)
            if tab_index != wx.NOT_FOUND:
                logger.debug("[MainWindow/OpenMod] Вкладка 'Браузер' найдена, переключаемся.")
                self.notebook.SetSelection(tab_index) # Переключаемся на вкладку
                # Загружаем URL в WebView этой вкладки
                self.browser_tab.webview.LoadURL(url)
                self.browser_tab.url_text.SetValue(url)
                logger.info(f"[MainWindow/OpenMod] URL {url} загружен во вкладку 'Браузер'.")
            else:
                logger.warning("[MainWindow/OpenMod] Вкладка 'Браузер' не найдена в notebook.")
                # Альтернатива: открыть во внешнем браузере
                wx.LaunchDefaultBrowser(url)
        else:
            logger.warning("[MainWindow/OpenMod] Объект browser_tab не найден.")
            # Альтернатива: открыть во внешнем браузере
            wx.LaunchDefaultBrowser(url)

    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    # --- КОНЕЦ ИСПРАВЛЕННОГО _on_open_mod_in_browser ---

    def _on_language_changed(self, lang_code):
        pass  # Здесь можно добавить обновление интерфейса

    def _on_mods_updated(self, game):
        if hasattr(self, 'mods_tab') and self.current_game == game:
            # self.mods_tab._load_mods() # Этот метод больше не существует или приватный
            # Вместо этого, ModsTab должен сам слушать событие mods_updated
            # Или можно вызвать публичный метод, если он есть, например set_game
            # Но лучше пусть ModsTab сам обрабатывает событие
            pass

    def _on_game_status_changed(self, steam_id):
        """Обработчик изменения статуса игры через события"""
        wx.CallAfter(self._update_game_status_ui)
    
    def _on_game_status_callback(self, steam_id: str, is_running: bool):
        """Callback от мониторинга статуса"""
        wx.CallAfter(self._update_game_status_ui)
    
    def _update_game_status_ui(self):
        """Обновление UI статуса игры"""
        try:
            if self.current_game:
                is_running = self.game_manager.is_game_running(self.current_game.steam_id)
                # Здесь можно обновить индикатор статуса в интерфейсе
                # Например, изменить цвет или добавить иконку
                logger.debug(f"Статус игры {self.current_game.name}: {'Запущена' if is_running else 'Остановлена'}")
        except Exception as e:
            logger.error(f"Ошибка обновления статуса UI: {e}")

    # --- Добавлен недостающий метод _on_settings ---
    def _on_settings(self, event):
        """Обработчик нажатия кнопки 'Настройки'."""
        dialog = SettingsDialog(self, self.settings_manager, self.language_manager)
        dialog.ShowModal()
        dialog.Destroy()
        logger.debug("[MainWindow] Диалог настроек закрыт.")

    # ---------------------------------------------

    def _on_language_changed(self, new_language):
        """Обработчик смены языка"""
        logger.info(f"[MainWindow] Language changed to: {new_language}")
        
        # Обновляем все тексты UI
        self._update_ui_texts()
        
        # Обновляем тексты во всех вкладках
        if hasattr(self, 'mods_tab') and hasattr(self.mods_tab, '_update_ui_texts'):
            self.mods_tab._update_ui_texts()
        
        if hasattr(self, 'browser_tab') and hasattr(self.browser_tab, '_update_ui_texts'):
            self.browser_tab._update_ui_texts()
            
        if hasattr(self, 'logs_tab') and hasattr(self.logs_tab, '_update_ui_texts'):
            self.logs_tab._update_ui_texts()

    def _update_ui_texts(self):
        """Обновляет все тексты в UI"""
        # Обновляем статус бар
        self.SetStatusText(_("ui.ready"))
        
        # Обновляем кнопки
        if hasattr(self, 'settings_btn'):
            self.settings_btn.SetLabel(_("ui.settings"))
        if hasattr(self, 'exit_btn'):
            self.exit_btn.SetLabel(_("ui.exit"))
        if hasattr(self, 'add_game_btn'):
            self.add_game_btn.SetLabel(_("ui.add_game"))
        if hasattr(self, 'edit_game_btn'):
            self.edit_game_btn.SetLabel(_("ui.edit_game"))
        if hasattr(self, 'remove_game_btn'):
            self.remove_game_btn.SetLabel(_("ui.remove_game"))
        if hasattr(self, 'launch_game_btn'):
            self.launch_game_btn.SetLabel(_("ui.launch_game"))
            
        # Обновляем вкладки
        if hasattr(self, 'notebook'):
            for i in range(self.notebook.GetPageCount()):
                page_text = ""
                if i == 0:
                    page_text = _("ui.mods")
                elif i == 1:
                    page_text = _("ui.browser")
                elif i == 2:
                    page_text = _("ui.logs")
                self.notebook.SetPageText(i, page_text)

    def _on_exit(self, event):
        self.Close()

    def Close(self, force=False):
        # Останавливаем мониторинг статуса
        if hasattr(self, 'status_monitor'):
            self.status_monitor.stop()
        
        # Завершаем работу TaskManager при закрытии приложения
        if hasattr(self, 'task_manager'):
            self.task_manager.shutdown(wait=False) # Не блокируем UI при закрытии

        # Отписываемся от всех событий при закрытии
        event_bus.unsubscribe("game_added", self._on_game_list_changed)
        event_bus.unsubscribe("game_removed", self._on_game_list_changed)
        event_bus.unsubscribe("game_updated", self._on_game_list_changed)
        event_bus.unsubscribe("language_changed", self._on_language_changed)
        event_bus.unsubscribe("open_mod_in_browser", self._on_open_mod_in_browser)
        event_bus.unsubscribe("mods_updated", self._on_mods_updated)
        super().Close(force)
