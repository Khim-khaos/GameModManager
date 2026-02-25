# -*- coding: utf-8 -*-
"""
Диалог настроек
"""
import wx
from loguru import logger

class SettingsDialog(wx.Dialog):
    """Диалог настроек приложения"""

    def __init__(self, parent, settings_manager, language_manager):
        super().__init__(parent, title="Настройки", size=(500, 400))
        self.settings_manager = settings_manager
        self.language_manager = language_manager
        self._create_ui()
        self._load_settings()
        self.CenterOnParent()

    def _create_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Путь к SteamCMD
        steamcmd_sizer = wx.BoxSizer(wx.HORIZONTAL)
        steamcmd_label = wx.StaticText(panel, label="Путь к SteamCMD:")
        self.steamcmd_text = wx.TextCtrl(panel)
        steamcmd_browse_btn = wx.Button(panel, label="Обзор")
        steamcmd_browse_btn.Bind(wx.EVT_BUTTON, self._on_browse_steamcmd)
        steamcmd_sizer.Add(steamcmd_label, 0, wx.ALL | wx.CENTER, 5)
        steamcmd_sizer.Add(self.steamcmd_text, 1, wx.ALL | wx.EXPAND, 5)
        steamcmd_sizer.Add(steamcmd_browse_btn, 0, wx.ALL, 5)
        main_sizer.Add(steamcmd_sizer, 0, wx.EXPAND)

        # Язык
        language_sizer = wx.BoxSizer(wx.HORIZONTAL)
        language_label = wx.StaticText(panel, label="Язык:")
        self.language_choice = wx.Choice(panel)
        self._populate_language_choice()
        language_sizer.Add(language_label, 0, wx.ALL | wx.CENTER, 5)
        language_sizer.Add(self.language_choice, 1, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(language_sizer, 0, wx.EXPAND)

        # Тема (упрощенная)
        theme_sizer = wx.BoxSizer(wx.HORIZONTAL)
        theme_label = wx.StaticText(panel, label="Тема:")
        self.theme_choice = wx.Choice(panel, choices=["Светлая", "Темная"])
        self.theme_choice.SetSelection(1)
        theme_sizer.Add(theme_label, 0, wx.ALL | wx.CENTER, 5)
        theme_sizer.Add(self.theme_choice, 1, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(theme_sizer, 0, wx.EXPAND)

        # Автопроверка обновлений
        self.auto_update_cb = wx.CheckBox(panel, label="Автопроверка обновлений")
        main_sizer.Add(self.auto_update_cb, 0, wx.ALL, 5)

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

    def _populate_language_choice(self):
        languages = self.language_manager.get_available_languages()
        choices = [lang['name'] for lang in languages]
        self.language_choice.Clear()
        self.language_choice.AppendItems(choices)
        current_lang = self.language_manager.get_current_language()
        for i, lang in enumerate(languages):
            if lang['code'] == current_lang:
                self.language_choice.SetSelection(i)
                break

    def _load_settings(self):
        steamcmd_path = self.settings_manager.get("steamcmd_path", "")
        self.steamcmd_text.SetValue(steamcmd_path)
        auto_update = self.settings_manager.get("auto_update_check", True)
        self.auto_update_cb.SetValue(auto_update)

    def _on_browse_steamcmd(self, event):
        with wx.FileDialog(
                self, "Выберите steamcmd.exe",
                wildcard="SteamCMD (steamcmd.exe)|steamcmd.exe|Все файлы (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            self.steamcmd_text.SetValue(pathname)

    def _on_ok(self, event):
        steamcmd_path = self.steamcmd_text.GetValue().strip()
        auto_update = self.auto_update_cb.GetValue()
        self.settings_manager.set("steamcmd_path", steamcmd_path)
        self.settings_manager.set("auto_update_check", auto_update)
        selection = self.language_choice.GetSelection()
        if selection != wx.NOT_FOUND:
            languages = self.language_manager.get_available_languages()
            if 0 <= selection < len(languages):
                selected_lang = languages[selection]['code']
                self.settings_manager.set("language", selected_lang)
                self.language_manager.set_language(selected_lang)
        self.EndModal(wx.ID_OK)
