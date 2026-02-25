# -*- coding: utf-8 -*-
"""
Диалог добавления игры
"""
import wx
import requests
from loguru import logger

class AddGameDialog(wx.Dialog):
    """Диалог добавления новой игры"""

    def __init__(self, parent, language_manager):
        super().__init__(parent, title="Добавить игру", size=(500, 400))
        self.language_manager = language_manager
        self.game_data = {}
        self._create_ui()
        self.CenterOnParent()

    def _create_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Название игры
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(panel, label="Название игры:")
        self.name_text = wx.TextCtrl(panel)
        name_sizer.Add(name_label, 0, wx.ALL | wx.CENTER, 5)
        name_sizer.Add(self.name_text, 1, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(name_sizer, 0, wx.EXPAND)

        # Steam ID
        steam_id_sizer = wx.BoxSizer(wx.HORIZONTAL)
        steam_id_label = wx.StaticText(panel, label="Steam ID:")
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
        self.steam_id_text.Bind(wx.EVT_TEXT, self._on_steam_id_changed)

    def _on_steam_id_changed(self, event):
        steam_id = self.steam_id_text.GetValue().strip()
        if steam_id.isdigit():
            self._fetch_game_name(steam_id)

    def _fetch_game_name(self, steam_id: str):
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={steam_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get(steam_id, {}).get("success"):
                    game_name = data[steam_id]["data"]["name"]
                    self.name_text.SetValue(game_name)
        except Exception as e:
            logger.debug(f"Не удалось получить название игры: {e}")

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

        self.game_data = {
            "name": name,
            "steam_id": steam_id,
            "executable_path": exe_path,
            "mods_path": mods_path
        }
        self.EndModal(wx.ID_OK)

    def get_game_data(self):
        return self.game_data.copy() if self.game_data else None
