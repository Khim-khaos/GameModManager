# -*- coding: utf-8 -*-
"""
Диалог редактирования игры
"""
import wx
import requests
from loguru import logger
from src.models.game import Game
from src.core.i18n import _

class EditGameDialog(wx.Dialog):
    """Диалог редактирования существующей игры"""

    def __init__(self, parent, language_manager, initial_game: Game):
        """
        Инициализирует диалог редактирования игры.

        :param parent: Родительское окно.
        :param language_manager: Менеджер языков (для будущих локализаций).
        :param initial_game: Объект Game, данные которого будут отображены для редактирования.
        """
        super().__init__(parent, title=_("game.edit_game") + f": {initial_game.name}", size=(500, 400))
        self.language_manager = language_manager
        self.initial_game = initial_game  # Сохраняем исходный объект для сравнения ID
        self.updated_game_data = None
        self._create_ui()
        self._populate_fields(initial_game) # Заполняем поля данными из initial_game
        self.CenterOnParent()

    def _create_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Название игры
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(panel, label=_("dialogs.add_game.name") + ":")
        self.name_text = wx.TextCtrl(panel)
        name_sizer.Add(name_label, 0, wx.ALL | wx.CENTER, 5)
        name_sizer.Add(self.name_text, 1, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(name_sizer, 0, wx.EXPAND)

        # Steam ID
        steam_id_sizer = wx.BoxSizer(wx.HORIZONTAL)
        steam_id_label = wx.StaticText(panel, label=_("dialogs.add_game.steam_id") + ":")
        self.steam_id_text = wx.TextCtrl(panel)
        steam_id_sizer.Add(steam_id_label, 0, wx.ALL | wx.CENTER, 5)
        steam_id_sizer.Add(self.steam_id_text, 1, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(steam_id_sizer, 0, wx.EXPAND)

        # Путь к исполняемому файлу
        exe_sizer = wx.BoxSizer(wx.HORIZONTAL)
        exe_label = wx.StaticText(panel, label="Путь к exe:")
        self.exe_text = wx.TextCtrl(panel)
        exe_browse_btn = wx.Button(panel, label="Обзор")
        exe_browse_btn.Bind(wx.EVT_BUTTON, self._on_browse_exe)
        exe_sizer.Add(exe_label, 0, wx.ALL | wx.CENTER, 5)
        exe_sizer.Add(self.exe_text, 1, wx.ALL | wx.EXPAND, 5)
        exe_sizer.Add(exe_browse_btn, 0, wx.ALL, 5)
        main_sizer.Add(exe_sizer, 0, wx.EXPAND)

        # Путь к папке модов
        mods_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mods_label = wx.StaticText(panel, label="Папка модов:")
        self.mods_text = wx.TextCtrl(panel)
        mods_browse_btn = wx.Button(panel, label="Обзор")
        mods_browse_btn.Bind(wx.EVT_BUTTON, self._on_browse_mods)
        mods_sizer.Add(mods_label, 0, wx.ALL | wx.CENTER, 5)
        mods_sizer.Add(self.mods_text, 1, wx.ALL | wx.EXPAND, 5)
        mods_sizer.Add(mods_browse_btn, 0, wx.ALL, 5)
        main_sizer.Add(mods_sizer, 0, wx.EXPAND)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, "ОК")
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Отмена")
        button_sizer.Add(ok_btn, 0, wx.ALL, 5)
        button_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        panel.SetSizer(main_sizer)
        ok_btn.SetDefault()

        # Привязка событий
        # Можно оставить привязку для автоматического заполнения имени, если ID меняется
        # self.steam_id_text.Bind(wx.EVT_TEXT, self._on_steam_id_changed)

    def _populate_fields(self, game: Game):
        """Заполняет поля диалога данными из объекта Game."""
        self.name_text.SetValue(game.name)
        self.steam_id_text.SetValue(game.steam_id)
        self.exe_text.SetValue(game.executable_path)
        self.mods_text.SetValue(game.mods_path)

    # --- Методы для обработки событий (остаются такими же, как в AddGameDialog) ---
    # def _on_steam_id_changed(self, event):
    #     # Можно реализовать, если нужно автоматически обновлять имя при изменении ID
    #     # steam_id = self.steam_id_text.GetValue().strip()
    #     # if steam_id.isdigit():
    #     #     self._fetch_game_name(steam_id)
    #     event.Skip() # Пропускаем событие, если не обрабатываем

    # def _fetch_game_name(self, steam_id: str):
    #     # Логика получения имени игры по ID (аналогично AddGameDialog)
    #     # ... (реализация такая же)

    def _on_browse_exe(self, event):
        with wx.FileDialog(
                self, "Выберите исполняемый файл игры",
                wildcard="Исполняемые файлы (*.exe)|*.exe|Все файлы (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            self.exe_text.SetValue(pathname)

    def _on_browse_mods(self, event):
        with wx.DirDialog(
                self, "Выберите папку модов",
                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        ) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = dirDialog.GetPath()
            self.mods_text.SetValue(pathname)

    def _on_ok(self, event):
        name = self.name_text.GetValue().strip()
        steam_id = self.steam_id_text.GetValue().strip()
        exe_path = self.exe_text.GetValue().strip()
        mods_path = self.mods_text.GetValue().strip()

        if not name:
            wx.MessageBox("Пожалуйста, введите название игры", "Ошибка", wx.OK | wx.ICON_ERROR)
            return
        if not steam_id:
            wx.MessageBox("Пожалуйста, введите Steam ID", "Ошибка", wx.OK | wx.ICON_ERROR)
            return
        if not exe_path:
            wx.MessageBox("Пожалуйста, выберите путь к исполняемому файлу", "Ошибка", wx.OK | wx.ICON_ERROR)
            return
        if not mods_path:
            wx.MessageBox("Пожалуйста, выберите папку модов", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        # Создаем словарь с обновленными данными
        self.updated_game_data = {
            "name": name,
            "steam_id": steam_id,
            "executable_path": exe_path,
            "mods_path": mods_path
        }
        self.EndModal(wx.ID_OK)

    def get_updated_game_data(self):
        """
        Возвращает словарь с обновленными данными игры.
        Возвращает None, если диалог был отменен.
        """
        return self.updated_game_data.copy() if self.updated_game_data else None

    def get_original_steam_id(self):
        """Возвращает Steam ID игры, которую редактировали."""
        return self.initial_game.steam_id
