# -*- coding: utf-8 -*-
"""
Вкладка логов
"""
import wx
import os
import threading
import time
from loguru import logger
from src.constants import LOGS_DIR

class LogsTab(wx.Panel):
    """Вкладка просмотра логов"""

    def __init__(self, parent, language_manager):
        super().__init__(parent)
        self.language_manager = language_manager
        self.current_log_file = None
        self.log_watcher = None
        self._create_ui()
        self._update_file_list()

    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Выбор файла лога
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        file_label = wx.StaticText(self, label="Файл лога:")
        self.file_choice = wx.Choice(self)
        self.file_choice.Bind(wx.EVT_CHOICE, self._on_file_selected)
        self.refresh_btn = wx.Button(self, label="Обновить")
        self.refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        file_sizer.Add(file_label, 0, wx.ALL | wx.CENTER, 5)
        file_sizer.Add(self.file_choice, 1, wx.ALL | wx.EXPAND, 5)
        file_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        main_sizer.Add(file_sizer, 0, wx.EXPAND)

        # Текстовое поле для отображения логов
        self.log_text = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.log_text.SetFont(font)
        main_sizer.Add(self.log_text, 1, wx.ALL | wx.EXPAND, 5)

        # Кнопки управления
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.clear_btn = wx.Button(self, label="Очистить лог")
        self.clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        button_sizer.Add(self.clear_btn, 0, wx.ALL, 5)
        self.auto_refresh_cb = wx.CheckBox(self, label="Автообновление")
        self.auto_refresh_cb.SetValue(True)
        self.auto_refresh_cb.Bind(wx.EVT_CHECKBOX, self._on_auto_refresh)
        button_sizer.Add(self.auto_refresh_cb, 0, wx.ALL | wx.CENTER, 5)
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        self.SetSizer(main_sizer)

    def _update_file_list(self):
        self.file_choice.Clear()
        if os.path.exists(LOGS_DIR):
            log_files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
            self.file_choice.AppendItems(log_files)
            if log_files:
                self.file_choice.SetSelection(0)
                self._load_logs(log_files[0])
            else:
                self.log_text.SetValue("Нет доступных файлов логов")
        else:
            self.log_text.SetValue("Папка с логами не найдена")

    def _load_logs(self, filename="app.log"):
        log_path = os.path.join(LOGS_DIR, filename)
        self.current_log_file = log_path
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.log_text.SetValue(content)
                    self.log_text.ShowPosition(self.log_text.GetLastPosition())
                if self.auto_refresh_cb.GetValue():
                    self._start_log_watching()
            except Exception as e:
                self.log_text.SetValue(f"Ошибка чтения файла лога: {e}")
        else:
            self.log_text.SetValue("Файл лога не найден")

    def _start_log_watching(self):
        self._stop_log_watching()
        self.log_watcher = LogWatcher(self.current_log_file, self._on_log_updated)
        self.log_watcher.start()

    def _stop_log_watching(self):
        if self.log_watcher:
            self.log_watcher.stop()
            self.log_watcher = None

    def _on_log_updated(self, new_content):
        wx.CallAfter(self.log_text.AppendText, new_content)
        wx.CallAfter(self.log_text.ShowPosition, self.log_text.GetLastPosition())

    def _on_file_selected(self, event):
        selection = self.file_choice.GetSelection()
        if selection != wx.NOT_FOUND:
            filename = self.file_choice.GetString(selection)
            self._stop_log_watching()
            self._load_logs(filename)

    def _on_refresh(self, event):
        self._update_file_list()

    def _on_auto_refresh(self, event):
        if self.auto_refresh_cb.GetValue():
            if self.current_log_file:
                self._start_log_watching()
        else:
            self._stop_log_watching()

    def _on_clear(self, event):
        selection = self.file_choice.GetSelection()
        if selection != wx.NOT_FOUND:
            filename = self.file_choice.GetString(selection)
            log_path = os.path.join(LOGS_DIR, filename)
            if os.path.exists(log_path):
                confirm = wx.MessageBox(
                    f"Вы уверены, что хотите очистить файл лога '{filename}'?",
                    "Подтверждение очистки",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
                )
                if confirm == wx.YES:
                    try:
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write("")
                        self._load_logs(filename)
                        logger.info(f"Файл лога {filename} очищен")
                    except Exception as e:
                        wx.MessageBox(f"Ошибка очистки файла: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)

    def Destroy(self):
        self._stop_log_watching()
        return super().Destroy()


class LogWatcher:
    """Наблюдатель за файлом лога"""

    def __init__(self, file_path, callback):
        self.file_path = file_path
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_position = 0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._watch, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _watch(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                f.seek(0, 2)
                self.last_position = f.tell()
        except:
            self.last_position = 0

        while self.running:
            try:
                if os.path.exists(self.file_path):
                    current_size = os.path.getsize(self.file_path)
                    if current_size > self.last_position:
                        with open(self.file_path, 'r', encoding='utf-8') as f:
                            f.seek(self.last_position)
                            new_data = f.read()
                            self.last_position = f.tell()
                            if new_data:
                                self.callback(new_data)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка наблюдения за логом: {e}")
                time.sleep(1)
