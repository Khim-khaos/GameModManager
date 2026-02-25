# src/ui/dialogs/download_progress_dialog.py
# -*- coding: utf-8 -*-
"""Диалог прогресса загрузки модов с логами SteamCMD"""
import wx
import threading
import time
import re # Импортируем re для парсинга логов
from loguru import logger

class DownloadProgressDialog(wx.Dialog):
    """Модальный диалог для отображения прогресса и логов загрузки модов."""

    def __init__(self, parent, download_manager, game):
        """
        :param parent: Родительское окно.
        :param download_manager: Экземпляр DownloadManager.
        :param game: Объект Game, для которого происходит загрузка.
        """
        super().__init__(parent, title=f"Загрузка модов для {game.name}", size=(700, 500),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.download_manager = download_manager
        self.game = game
        self.is_cancelled = False
        self.success = False

        # Счетчики для парсинга логов
        self.total_mods = len(self.download_manager._download_queue)
        self.downloaded_mods = 0
        self.error_mods = 0

        # Регулярные выражения для парсинга строк лога SteamCMD
        self._success_pattern = re.compile(r'Success\. Downloaded item (\d+)')
        self._error_pattern = re.compile(r'(?:ERROR!|Failure\.|Failed to) Download item (\d+)')

        self._create_ui()
        self.CenterOnParent()

        # Запуск загрузки в отдельном потоке
        threading.Thread(target=self._run_download, daemon=True).start()

    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Статус и счетчики
        self.status_text = wx.StaticText(self, label="Подготовка к загрузке...")
        main_sizer.Add(self.status_text, 0, wx.ALL | wx.EXPAND, 5)

        self.counters_text = wx.StaticText(self, label=self._get_counters_text())
        main_sizer.Add(self.counters_text, 0, wx.ALL | wx.EXPAND, 5)

        # Прогресс-бар
        self.gauge = wx.Gauge(self, range=100)
        main_sizer.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 5)

        # Логи
        self.log_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.log_text.SetFont(font)
        main_sizer.Add(self.log_text, 1, wx.ALL | wx.EXPAND, 5)

        # Кнопки
        btn_sizer = wx.StdDialogButtonSizer()
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "Отмена")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self._on_cancel)
        btn_sizer.AddButton(self.cancel_btn)
        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.SetSizer(main_sizer)

    def _get_counters_text(self):
        return f"Всего: {self.total_mods} | Загружено: {self.downloaded_mods} | Ошибок: {self.error_mods}"

    def _update_counters(self):
        """Обновление текста счетчиков в UI."""
        # Проверка существования объекта перед вызовом wx.CallAfter не обязательна,
        # но добавим для полноты картины. Основная проверка будет внутри _update_counters_ui
        if self:
            wx.CallAfter(self._update_counters_ui)

    def _update_counters_ui(self):
        """Фактическое обновление счетчиков в UI (вызывается через wx.CallAfter)."""
        # Проверяем, существует ли диалог и его элементы
        if self and hasattr(self, 'counters_text') and self.counters_text:
            try:
                self.counters_text.SetLabel(self._get_counters_text())
            except RuntimeError:
                # Объект мог быть уничтожен между проверкой и вызовом
                pass

    def _append_log_line(self, line):
        """Добавление строки в лог с временной меткой"""
        # Эта функция вызывается через wx.CallAfter, поэтому она сама по себе безопасна
        # от "уничтожения" во время планирования. Проверки нужны внутри _append_log_line_ui.
        wx.CallAfter(self._append_log_line_ui, line)

    def _append_log_line_ui(self, line):
        """Фактическое добавление строки в лог (вызывается через wx.CallAfter)."""
        # Проверяем, существуют ли диалог и TextCtrl
        if self and hasattr(self, 'log_text') and self.log_text:
            try:
                timestamp = time.strftime("%H:%M:%S")
                formatted_line = f"[{timestamp}] {line}"
                self.log_text.AppendText(formatted_line + "\n")
                # Прокручиваем вниз
                self.log_text.ShowPosition(self.log_text.GetLastPosition())
            except RuntimeError as e:
                # Это и есть ошибка, которую мы хотим поймать:
                # "wrapped C/C++ object of type TextCtrl has been deleted"
                logger.debug(f"[DownloadProgress] Попытка обновления уничтоженного log_text: {e}")
                # Игнорируем ошибку, так как объект уже уничтожен
                pass

    def _parse_and_update_from_line(self, line: str):
        """Парсит строку лога SteamCMD и обновляет счетчики/UI."""
        # Проверяем на успех
        success_match = self._success_pattern.search(line)
        if success_match:
            mod_id = success_match.group(1)
            self.downloaded_mods += 1
            logger.debug(f"[DownloadProgress/Parser] Успешно загружен мод {mod_id}")
            # Передаем в _append_log_line, который использует wx.CallAfter
            self._append_log_line(f"-> УСПЕХ: Мод {mod_id} загружен.")
            # Обновляем счетчики через wx.CallAfter
            wx.CallAfter(self._update_counters_ui)
            wx.CallAfter(self._update_progress_ui)
            return

        # Проверяем на ошибку
        error_match = self._error_pattern.search(line)
        if error_match:
            mod_id = error_match.group(1)
            self.error_mods += 1
            logger.debug(f"[DownloadProgress/Parser] Ошибка загрузки мода {mod_id}")
            self._append_log_line(f"-> ОШИБКА: Мод {mod_id} не загружен.")
            wx.CallAfter(self._update_counters_ui)
            wx.CallAfter(self._update_progress_ui)
            return

        # Если строка не о успехе/ошибке, просто логируем её
        self._append_log_line(f"-> {line}")

    def _update_progress(self):
        """Обновляет значение прогресс-бара на основе счетчиков."""
        processed = self.downloaded_mods + self.error_mods
        total = max(self.total_mods, 1) # Избегаем деления на 0
        progress_percent = int((processed / total) * 100)
        # Используем wx.CallAfter для обновления UI
        wx.CallAfter(self._update_progress_ui, progress_percent)

    def _update_progress_ui(self, progress_percent=None):
        """Фактическое обновление прогресс-бара (вызывается через wx.CallAfter)."""
        # Если progress_percent не передан, вычисляем его
        if progress_percent is None:
            processed = self.downloaded_mods + self.error_mods
            total = max(self.total_mods, 1)
            progress_percent = int((processed / total) * 100)

        if self and hasattr(self, 'gauge') and self.gauge:
            try:
                self.gauge.SetValue(min(progress_percent, 100)) # Ограничиваем 100
            except RuntimeError:
                pass # Игнорируем, если gauge уничтожен

    def _run_download(self):
        """Основной метод загрузки, выполняющийся в отдельном потоке."""
        try:
            logger.info("[DownloadProgress] Начало загрузки модов в диалоге.")

            # Определяем callback для передачи логов из DownloadManager/SteamHandler
            def log_callback(line: str):
                # Этот callback будет вызываться из другого потока (SteamHandler)
                # Поэтому используем wx.CallAfter для безопасного обновления UI
                # Передаем в _append_log_line, который уже использует wx.CallAfter
                self._append_log_line(line)

            # Вызываем модифицированный метод download_mods_queue с callback
            self.success = self.download_manager.download_mods_queue(self.game, log_callback=log_callback)

            # Логика после завершения
            logger.info(f"[DownloadProgress] Загрузка завершена. Успешно: {self.success}")
            # Финальные сообщения уже добавлены через log_callback

        except Exception as e:
            logger.error(f"[DownloadProgress] Ошибка в процессе загрузки: {e}")
            self._append_log_line(f"!!! ОШИБКА: {e}") # _append_log_line использует wx.CallAfter
            self.success = False
        finally:
            # Завершение диалога
            wx.CallAfter(self._on_download_finished)

    def _on_download_finished(self):
        """Обновление UI после завершения загрузки"""
        logger.info("[DownloadProgress] Диалог завершения загрузки обновлен.")
        # Проверяем существование элементов перед обновлением
        if self and hasattr(self, 'cancel_btn') and self.cancel_btn:
            self.cancel_btn.SetLabel("Закрыть")
        if self and hasattr(self, 'status_text') and self.status_text:
            if self.success:
                self.status_text.SetLabel("Загрузка завершена успешно!")
            else:
                self.status_text.SetLabel("Загрузка завершена с ошибками или отменена.")
        # Убедимся, что прогресс 100% в конце
        wx.CallAfter(self._update_progress_ui, 100)
        # Финальное обновление счетчиков
        wx.CallAfter(self._update_counters_ui)

    def _on_cancel(self, event):
        """Обработчик нажатия кнопки Отмена/Закрыть."""
        if self.cancel_btn.GetLabel() == "Отмена":
            logger.info("[DownloadProgress] Пользователь нажал 'Отмена'.")
            self.is_cancelled = True
            if self and hasattr(self, 'status_text') and self.status_text:
                self.status_text.SetLabel("Отмена загрузки...")
            if self and hasattr(self, 'cancel_btn') and self.cancel_btn:
                self.cancel_btn.Enable(False)
            # Примечание: реальная отмена зависит от реализации subprocess в SteamHandler
            # Поскольку download_mods_queue блокирует поток, настоящая "отмена" сложна.
            # Можно лишь установить флаг и проверять его внутри SteamHandler (если он это поддерживает).
        else:
            logger.info("[DownloadProgress] Диалог закрыт пользователем.")
            self.EndModal(wx.ID_OK if self.success else wx.ID_CANCEL)

    def is_download_successful(self):
        """Возвращает True, если загрузка завершилась успешно."""
        return self.success
