# -*- coding: utf-8 -*-
"""
Вкладка консоли SteamCMD
"""
import wx
import subprocess
import threading
import os
from loguru import logger

class ConsoleTab(wx.Panel):
    """Вкладка консоли SteamCMD"""

    def __init__(self, parent, steam_handler, language_manager):
        super().__init__(parent)
        self.steam_handler = steam_handler
        self.language_manager = language_manager
        self.current_game = None
        self.process = None
        self._create_ui()

    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Прогресс бар
        self.progress = wx.Gauge(self)
        self.progress.Hide()
        main_sizer.Add(self.progress, 0, wx.ALL | wx.EXPAND, 5)

        # Текстовое поле для вывода консоли
        self.console_text = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.console_text.SetFont(font)
        main_sizer.Add(self.console_text, 1, wx.ALL | wx.EXPAND, 5)

        # Кнопки управления
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.run_btn = wx.Button(self, label="Запустить SteamCMD")
        self.run_btn.Bind(wx.EVT_BUTTON, self._on_run)
        button_sizer.Add(self.run_btn, 0, wx.ALL, 5)
        self.stop_btn = wx.Button(self, label="Остановить")
        self.stop_btn.Bind(wx.EVT_BUTTON, self._on_stop)
        self.stop_btn.Enable(False)
        button_sizer.Add(self.stop_btn, 0, wx.ALL, 5)
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)
        self.SetSizer(main_sizer)

    def set_game(self, game):
        self.current_game = game

    def _on_run(self, event):
        if not self.steam_handler.is_available:
            wx.MessageBox("SteamCMD недоступен. Проверьте путь в настройках.", "Ошибка", wx.OK | wx.ICON_ERROR)
            return
        if not self.current_game:
            wx.MessageBox("Выберите игру", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        self.run_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.console_text.Clear()
        self.console_text.AppendText("Запуск SteamCMD...\n")
        self.progress.Show()
        self.progress.Pulse()
        self.Layout()
        thread = threading.Thread(target=self._run_steamcmd, daemon=True)
        thread.start()

    def _run_steamcmd(self):
        try:
            if not self.steam_handler.steamcmd_path or not os.path.exists(self.steam_handler.steamcmd_path):
                wx.CallAfter(self._append_console_text, "Ошибка: Путь к SteamCMD не найден\n")
                wx.CallAfter(self._on_process_finished)
                return

            cmd = [self.steam_handler.steamcmd_path, "+quit"]
            steamcmd_base_path = os.path.dirname(self.steam_handler.steamcmd_path)
            wx.CallAfter(self._append_console_text, "Запуск SteamCMD...\n")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=steamcmd_base_path,
                bufsize=1,
                universal_newlines=True
            )
            self.process = process

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    wx.CallAfter(self._append_console_text, output)
                    self._analyze_output(output)
            process.wait()
            if process.returncode == 0:
                wx.CallAfter(self._append_console_text, "\nSteamCMD завершен успешно.\n")
            else:
                wx.CallAfter(self._append_console_text, f"\nSteamCMD завершен с кодом ошибки: {process.returncode}\n")
            wx.CallAfter(self._on_process_finished)
        except Exception as e:
            error_msg = f"Ошибка запуска SteamCMD: {e}\n"
            wx.CallAfter(self._append_console_text, error_msg)
            wx.CallAfter(self._on_process_finished)

    def _analyze_output(self, output):
        output_lower = output.lower()
        if "downloading" in output_lower or "скачивание" in output_lower or "download" in output_lower:
            wx.CallAfter(self._update_status, "Скачивание...")
        elif "installing" in output_lower or "установка" in output_lower or "install" in output_lower:
            wx.CallAfter(self._update_status, "Установка...")
        elif "complete" in output_lower or "завершено" in output_lower or "success" in output_lower:
            wx.CallAfter(self._update_status, "Завершение...")
        elif "loading" in output_lower or "загрузка" in output_lower:
            wx.CallAfter(self._update_status, "Загрузка...")
        elif "connecting" in output_lower or "подключение" in output_lower:
            wx.CallAfter(self._update_status, "Подключение...")

    def _update_status(self, message):
        try:
            parent = self.GetParent().GetParent()
            if hasattr(parent, 'SetStatusText'):
                parent.SetStatusText(message)
        except:
            pass

    def _append_console_text(self, text):
        try:
            clean_text = ''.join(char if ord(char) < 65536 else '?' for char in text)
            self.console_text.AppendText(clean_text)
            self.console_text.ShowPosition(self.console_text.GetLastPosition())
        except Exception as e:
            self.console_text.AppendText(str(text))
            self.console_text.ShowPosition(self.console_text.GetLastPosition())

    def _on_process_finished(self):
        self.run_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.process = None
        self.progress.Hide()
        self.Layout()
        self._update_status("Готов")

    def _on_stop(self, event):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Ошибка остановки процесса: {e}")
            self.process = None
            self.run_btn.Enable(True)
            self.stop_btn.Enable(False)
            self.console_text.AppendText("\nПроцесс остановлен пользователем.\n")
            self.progress.Hide()
            self.Layout()
            self._update_status("Остановлено пользователем")
