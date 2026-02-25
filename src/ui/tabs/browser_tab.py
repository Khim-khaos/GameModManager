# -*- coding: utf-8 -*-
"""
Вкладка браузера Steam Workshop
"""
import wx
import wx.html2
import re
import requests
from bs4 import BeautifulSoup
import threading
import json
import os
from loguru import logger

# Предполагаем, что event_bus существует
try:
    from src.event_bus import event_bus
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False
    logger.warning("event_bus не найден")

# --- Добавляем импорт новых диалогов ---
from src.ui.dialogs.download_progress_dialog import DownloadProgressDialog
from src.ui.dialogs.dependency_confirmation_dialog import DependencyConfirmationDialog
from src.ui.dialogs.collection_confirmation_dialog import CollectionConfirmationDialog
# --------------------------------------
from src.constants import STEAM_WORKSHOP_HOMEPAGE

class BrowserTab(wx.Panel):
    """Вкладка браузера Steam Workshop"""

    def __init__(self, parent, download_manager, language_manager, mod_manager): # <- Добавлен mod_manager
        super().__init__(parent)
        self.download_manager = download_manager
        self.language_manager = language_manager
        # --- Добавлен mod_manager ---
        self.mod_manager = mod_manager
        # ---------------------------
        self.current_game = None
        # Кэш установленных mod_id для текущей игры
        self.installed_mod_ids = set()
        self._create_ui()
        # Подписываемся на событие обновления модов, чтобы обновить кэш
        if HAS_EVENT_BUS:
            event_bus.subscribe("mods_updated", self._on_mods_updated)

    def _create_ui(self):
        # Создаем SplitterWindow для возможности изменения размера
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(100) # Минимальный размер панели

        self._create_download_queue_panel(self.splitter) # Левая панель
        self._create_browser_panel(self.splitter)       # Правая панель

        # Изначально устанавливаем позицию сплиттера (например, 300 пикселей для очереди)
        # Это можно сделать динамически или запомнить предпочтение пользователя
        self.splitter.SplitVertically(self.queue_panel, self.browser_panel, 300)

        # Создаем главный сайзер и добавляем в него сплиттер
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.splitter, 1, wx.EXPAND)
        self.SetSizer(main_sizer)

    def _create_download_queue_panel(self, parent):
        # Теперь parent - это splitter
        self.queue_panel = wx.Panel(parent) # <-- Сохраняем ссылку на панель
        queue_sizer = wx.BoxSizer(wx.VERTICAL)
        # --- Обновляем заголовок для отображения количества ---
        self.queue_title = wx.StaticText(self.queue_panel, label="Очередь загрузки (0 модов)") # <- Динамический заголовок
        font = self.queue_title.GetFont()
        font.PointSize += 2
        font = font.Bold()
        self.queue_title.SetFont(font)
        queue_sizer.Add(self.queue_title, 0, wx.ALL, 5)
        # ----------------------------------------
        self.queue_list = wx.ListCtrl(self.queue_panel, style=wx.LC_REPORT)
        self.queue_list.AppendColumn("Название", width=200)
        self.queue_list.AppendColumn("ID", width=150)
        queue_sizer.Add(self.queue_list, 1, wx.ALL | wx.EXPAND, 5)
        # --- Добавляем кнопки экспорта/импорта и очистки ---
        top_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.export_btn = wx.Button(self.queue_panel, label="Экспорт")
        self.export_btn.Bind(wx.EVT_BUTTON, self._on_export)
        top_row_sizer.Add(self.export_btn, 0, wx.ALL, 5)
        self.import_btn = wx.Button(self.queue_panel, label="Импорт")
        self.import_btn.Bind(wx.EVT_BUTTON, self._on_import)
        top_row_sizer.Add(self.import_btn, 0, wx.ALL, 5)
        self.clear_queue_btn = wx.Button(self.queue_panel, label="Очистить") # <-- Новая кнопка
        self.clear_queue_btn.Bind(wx.EVT_BUTTON, self._on_clear_queue) # <-- Привязка
        self.clear_queue_btn.Enable(False) # Отключена, если очередь пуста
        top_row_sizer.Add(self.clear_queue_btn, 0, wx.ALL, 5)
        queue_sizer.Add(top_row_sizer, 0, wx.ALIGN_CENTER)
        # ----------------------------------------
        queue_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.remove_from_queue_btn = wx.Button(self.queue_panel, label="Убрать из очереди")
        self.remove_from_queue_btn.Bind(wx.EVT_BUTTON, self._on_remove_from_queue)
        self.remove_from_queue_btn.Enable(False)
        queue_buttons_sizer.Add(self.remove_from_queue_btn, 0, wx.ALL, 5)
        self.download_btn = wx.Button(self.queue_panel, label="Скачать")
        self.download_btn.Bind(wx.EVT_BUTTON, self._on_download_queue)
        self.download_btn.Enable(False)
        queue_buttons_sizer.Add(self.download_btn, 0, wx.ALL, 5)
        queue_sizer.Add(queue_buttons_sizer, 0, wx.ALIGN_CENTER)
        self.queue_panel.SetSizer(queue_sizer)
        # Убираем parent_sizer.Add, так как панель добавляется через SplitterWindow

    # --- ОБНОВЛЕННЫЙ _update_queue_list с отображением количества и состоянием кнопки очистки ---
    def _update_queue_list(self):
        """Обновляет список очереди и связанный UI."""
        self.queue_list.DeleteAllItems()
        queue = self.download_manager.download_queue
        for mod in queue:
            index = self.queue_list.InsertItem(
                self.queue_list.GetItemCount(), mod.name
            )
            self.queue_list.SetItem(index, 1, mod.mod_id)
        has_items = len(queue) > 0
        self.remove_from_queue_btn.Enable(has_items)
        self.download_btn.Enable(has_items)
        # --- Обновляем заголовок с количеством ---
        self.queue_title.SetLabel(f"Очередь загрузки ({len(queue)} модов)")
        # --- Обновляем состояние кнопки очистки ---
        self.clear_queue_btn.Enable(has_items)
        # ----------------------------------------

    # --- КОНЕЦ ОБНОВЛЕННОГО _update_queue_list ---

    def _create_browser_panel(self, parent):
        # Теперь parent - это splitter
        self.browser_panel = wx.Panel(parent) # <-- Сохраняем ссылку на панель
        browser_sizer = wx.BoxSizer(wx.VERTICAL)
        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.back_btn = wx.Button(self.browser_panel, label="Назад", size=(60, -1))
        self.back_btn.Bind(wx.EVT_BUTTON, self._on_back)
        nav_sizer.Add(self.back_btn, 0, wx.ALL, 5)
        self.forward_btn = wx.Button(self.browser_panel, label="Вперед", size=(60, -1))
        self.forward_btn.Bind(wx.EVT_BUTTON, self._on_forward)
        nav_sizer.Add(self.forward_btn, 0, wx.ALL, 5)
        self.refresh_btn = wx.Button(self.browser_panel, label="Обновить")
        self.refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        nav_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        self.url_text = wx.TextCtrl(self.browser_panel, style=wx.TE_PROCESS_ENTER)
        self.url_text.Bind(wx.EVT_TEXT_ENTER, self._on_url_enter)
        nav_sizer.Add(self.url_text, 1, wx.ALL | wx.EXPAND, 5)
        browser_sizer.Add(nav_sizer, 0, wx.EXPAND)
        self.webview = wx.html2.WebView.New(self.browser_panel)
        # --- Исправление навигации: перехватываем все переходы ---
        self.webview.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self._on_navigating)
        # ---------------------------------------------------------
        self.webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self._on_loaded)
        browser_sizer.Add(self.webview, 1, wx.ALL | wx.EXPAND, 5)
        self.progress = wx.Gauge(self.browser_panel)
        self.progress.Hide()
        browser_sizer.Add(self.progress, 0, wx.ALL | wx.EXPAND, 5)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.add_to_queue_btn = wx.Button(self.browser_panel, label="Добавить в очередь")
        self.add_to_queue_btn.Bind(wx.EVT_BUTTON, self._on_add_to_queue)
        self.add_to_queue_btn.Enable(False)
        buttons_sizer.Add(self.add_to_queue_btn, 0, wx.ALL, 5)
        self.add_collection_btn = wx.Button(self.browser_panel, label="Добавить коллекцию")
        self.add_collection_btn.Bind(wx.EVT_BUTTON, self._on_add_collection_clicked) # <-- Исправлено имя метода
        self.add_collection_btn.Enable(True)
        buttons_sizer.Add(self.add_collection_btn, 0, wx.ALL, 5)
        browser_sizer.Add(buttons_sizer, 0, wx.ALIGN_CENTER)
        self.browser_panel.SetSizer(browser_sizer)
        # Убираем parent_sizer.Add, так как панель добавляется через SplitterWindow

    def set_game(self, game):
        self.current_game = game
        # --- Обновляем кэш установленных модов ---
        self._update_installed_mods_cache()
        # ----------------------------------------
        if game:
            url = f"https://steamcommunity.com/app/{game.steam_id}/workshop/"
            self.webview.LoadURL(url)
            self.url_text.SetValue(url)
        else:
            # Если игра не выбрана, загружаем домашнюю страницу Steam Workshop
            self.webview.LoadURL(STEAM_WORKSHOP_HOMEPAGE)
            self.url_text.SetValue(STEAM_WORKSHOP_HOMEPAGE)

    # --- НОВЫЙ МЕТОД: Обновление кэша установленных модов ---
    def _update_installed_mods_cache(self):
        """Обновляет внутренний кэш установленных mod_id."""
        self.installed_mod_ids.clear()
        if self.current_game and self.mod_manager:
            try:
                # Получаем все моды (включая отключенные)
                # installed_mods = self.mod_manager.get_installed_mods() # Только включенные
                all_mods = self.mod_manager._mods # Предполагаем доступ к внутреннему списку
                # Или лучше: добавить метод get_all_mods в ModManager
                self.installed_mod_ids = {mod.mod_id for mod in all_mods}
                logger.debug(f"[Browser] Кэш установленных модов обновлен: {len(self.installed_mod_ids)} модов")
            except Exception as e:
                logger.error(f"[Browser] Ошибка обновления кэша установленных модов: {e}")

    # --- КОНЕЦ НОВОГО МЕТОДА ---

    # --- НОВЫЙ МЕТОД: Обработчик события обновления модов ---
    def _on_mods_updated(self, game):
        """Вызывается, когда список модов обновляется."""
        if self.current_game and game and self.current_game.steam_id == game.steam_id:
            logger.debug("[Browser] Получено событие mods_updated, обновляем кэш.")
            self._update_installed_mods_cache()
            # Если страница мода/списка открыта, можно перезагрузить индикацию
            # Но это может быть избыточно. Лучше делать при каждой загрузке страницы.

    # --- КОНЕЦ НОВОГО МЕТОДА ---

    def _on_back(self, event):
        if self.webview.CanGoBack():
            self.webview.GoBack()

    def _on_forward(self, event):
        if self.webview.CanGoForward():
            self.webview.GoForward()

    def _on_refresh(self, event):
        self.webview.Reload()

    def _on_url_enter(self, event):
        url = self.url_text.GetValue()
        if url:
            self.webview.LoadURL(url)

    # --- ИСПРАВЛЕННЫЙ _on_navigating ---
    def _on_navigating(self, event):
        """
        Перехватываем переходы. Пытаемся удержать навигацию внутри нашего WebView
        для страниц модов и коллекций.
        """
        url = event.GetURL()
        logger.debug(f"[Browser] Navigating to: {url}")
        self.url_text.SetValue(url)
        # Определяем, является ли URL страницей мода или коллекции
        is_mod_page = "steamcommunity.com/sharedfiles/filedetails/" in url and "id=" in url
        # is_collection_page = ... (можно добавить логику, если нужно)
        # Включаем кнопки, если это страница мода
        self.add_to_queue_btn.Enable(is_mod_page)
        self.back_btn.Enable(self.webview.CanGoBack())
        self.forward_btn.Enable(self.webview.CanGoForward())
        # --- Логика удержания навигации ---
        # event.Veto() # Останавливаем стандартный переход
        # self.webview.LoadURL(url) # Загружаем внутри
        # return
        # ----------------------------------
        # Пока оставляем стандартное поведение, но логируем
        # event.Skip() вызывается автоматически, если не вызван event.Veto()

    # --- КОНЕЦ ИСПРАВЛЕННОГО _on_navigating ---

    # --- ИСПРАВЛЕННЫЙ _on_loaded с индикацией ---
    def _on_loaded(self, event):
        """Вызывается, когда страница загружена."""
        url = self.webview.GetCurrentURL()
        logger.debug(f"[Browser] Loaded URL: {url}")
        self.url_text.SetValue(url)
        is_mod_page = "steamcommunity.com/sharedfiles/filedetails/" in url and "id=" in url
        self.add_to_queue_btn.Enable(is_mod_page)
        self.back_btn.Enable(self.webview.CanGoBack())
        self.forward_btn.Enable(self.webview.CanGoForward())
        self.progress.Hide()
        self.Layout()
        # --- Добавляем визуальную индикацию установленных модов ---
        if self.installed_mod_ids:
            # --- УЛУЧШЕННЫЙ JAVASCRIPT СКРИПТ ---
            # Пытаемся выделить не только ссылки, но и сами блоки модов и зависимости
            script = f"""
            (function() {{
                console.log("Starting improved mod indication script...");
                var installedIds = new Set({json.dumps(list(self.installed_mod_ids))});
                console.log("Installed IDs:", Array.from(installedIds));
                // 1. Индикация на странице самого мода (если это страница мода)
                var modIdMatch = window.location.href.match(/id=(\\d+)/);
                if (modIdMatch) {{
                    var currentPageModId = modIdMatch[1];
                    console.log("Current page mod ID:", currentPageModId);
                    var titleElem = document.querySelector('.workshopItemTitle'); // Проверить селектор
                    if (titleElem && installedIds.has(currentPageModId)) {{
                        if (!titleElem.innerHTML.startsWith('&#x2714;')) {{
                            titleElem.innerHTML = '&#x2714; ' + titleElem.innerHTML; // HTML entity for checkmark
                            console.log("Marked current mod as installed.");
                        }}
                    }}
                }}
                // 2. Индикация для модов на страницах списков/коллекций
                // Ищем контейнеры модов. Это может быть .workshopBrowseItems, .workshopItem, div с data-publishedfileid и т.д.
                // Пример для страницы коллекции или списка:
                var potentialModContainers = document.querySelectorAll('.workshopItem, [data-publishedfileid]'); 
                console.log("Found", potentialModContainers.length, "potential mod containers.");
                potentialModContainers.forEach(function(container) {{
                    var modId = null;
                    // Попытка 1: Получить ID из data-атрибута
                    if (container.dataset && container.dataset.publishedfileid) {{
                        modId = container.dataset.publishedfileid;
                    }}
                    // Попытка 2: Получить ID из ссылки внутри контейнера
                    if (!modId) {{
                        var linkInside = container.querySelector('a[href*="sharedfiles/filedetails"][href*="id="]');
                        if (linkInside) {{
                            var idMatch = linkInside.href.match(/id=(\\d+)/);
                            modId = idMatch ? idMatch[1] : null;
                        }}
                    }}
                    // Попытка 3: Получить ID из любого data-id внутри
                    if (!modId) {{
                         var dataIdElem = container.querySelector('[data-id]');
                         if (dataIdElem && dataIdElem.dataset.id) {{
                              modId = dataIdElem.dataset.id;
                         }}
                    }}
                    if (modId && installedIds.has(modId)) {{
                        console.log("Marking container for mod ID:", modId);
                        // Выделяем весь контейнер
                        container.style.border = '2px solid green';
                        container.style.borderRadius = '5px';
                        container.style.boxShadow = 'inset 0 0 5px rgba(0, 128, 0, 0.3)';
                        container.style.backgroundColor = 'rgba(0, 255, 0, 0.05)'; // Легкий зеленый фон
                        // Добавляем галочку в заголовок, если её ещё нет
                        var titleElemInContainer = container.querySelector('.workshopItemTitle');
                        if (titleElemInContainer && !titleElemInContainer.innerHTML.includes('&#x2714;')) {{
                             titleElemInContainer.innerHTML = '&#x2714; ' + titleElemInContainer.innerHTML;
                        }}
                    }}
                }});
                // 3. Индикация для зависимостей
                var requiredItemsContainer = document.querySelector('.requiredItemsContainer'); // Исправленный селектор
                if (requiredItemsContainer) {{
                    console.log("Found required items container.");
                    var requiredItemLinks = requiredItemsContainer.querySelectorAll('a[href*="sharedfiles/filedetails"][href*="id="]');
                    requiredItemLinks.forEach(function(link) {{
                        console.log("Processing dependency link:", link.href);
                        var idMatch = link.href.match(/id=(\\d+)/);
                        if (idMatch) {{
                            var depModId = idMatch[1];
                            console.log("Dependency mod ID:", depModId);
                            if (installedIds.has(depModId)) {{
                                console.log("Dependency is installed:", depModId);
                                // Добавляем галочку или меняем стиль
                                var requiredItemDiv = link.querySelector('.requiredItem'); // Или сам link
                                if (requiredItemDiv) {{
                                    requiredItemDiv.style.border = '2px solid green';
                                    requiredItemDiv.style.borderRadius = '3px';
                                    requiredItemDiv.style.backgroundColor = 'rgba(0, 255, 0, 0.1)';
                                    if (!requiredItemDiv.innerHTML.includes('&#x2714;')) {{
                                        // Вставляем галочку в начало
                                        requiredItemDiv.insertAdjacentHTML('afterbegin', '<span style="color:green;margin-right:5px;">&#x2714;</span>');
                                    }}
                                }} else {{
                                     // Если .requiredItem не найден, меняем стиль самой ссылки
                                     link.style.border = '2px solid green';
                                     link.style.borderRadius = '3px';
                                     link.style.backgroundColor = 'rgba(0, 255, 0, 0.1)';
                                     // Проверяем, есть ли уже галочка в тексте ссылки
                                     if (!link.textContent.includes('✓') && !link.innerHTML.includes('&#x2714;')) {{
                                         // Добавляем галочку в текст ссылки
                                         link.textContent = '✓ ' + link.textContent;
                                     }}
                                }}
                            }}
                        }}
                    }});
                }} else {{
                    console.log("Required items container not found.");
                }}
                console.log("Finished improved mod indication script.");
            }})();
            """
            # --- КОНЕЦ УЛУЧШЕННОГО JAVASCRIPT СКРИПТА ---
            try:
                # Сначала логируем сам скрипт для отладки
                # logger.debug(f"[Browser/JS] Executing script: {{script}}")
                self.webview.RunScript(script)
                logger.debug(f"[Browser] Improved JS indication script executed for URL: {url}")
            except Exception as e:
                logger.warning(f"[Browser] Не удалось выполнить улучшенный скрипт индикации: {e}")
        # --- КОНЕЦ ИНДИКАЦИИ ---

    # --- КОНЕЦ ИСПРАВЛЕННОГО _on_loaded ---

    # --- ОБНОВЛЕННЫЙ _on_add_to_queue с диалогом зависимостей ---
    def _on_add_to_queue(self, event):
        """Добавляет мод в очередь загрузки."""
        if not self.current_game:
            wx.MessageBox("Сначала выберите игру", "Ошибка", wx.OK | wx.ICON_WARNING)
            return
        url = self.webview.GetCurrentURL()
        if "steamcommunity.com/sharedfiles/filedetails/" in url:
            match = re.search(r'id=(\d+)', url)
            if match:
                mod_id = match.group(1)
                queue = self.download_manager.download_queue
                if any(mod.mod_id == mod_id for mod in queue):
                    wx.MessageBox("Мод уже находится в очереди загрузки", "Информация", wx.OK | wx.ICON_INFORMATION)
                    return
                # - Получаем данные мода -
                mod_name = "Новый мод"
                dependencies = [] # Список зависимостей
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    logger.debug(f"[Browser/Add] Запрос данных мода {mod_id}")
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        title_elem = soup.find('div', class_='workshopItemTitle')
                        if title_elem:
                            mod_name = title_elem.text.strip()
                        # - ИСПРАВЛЕННЫЙ Поиск зависимостей -
                        # Ищем контейнер зависимостей
                        required_items_container = soup.find('div', id='RequiredItems') # Попробуем ID
                        if not required_items_container:
                            required_items_container = soup.find('div', class_='requiredItemsContainer') # Или класс
                        if required_items_container:
                            logger.debug("[Browser/Add] Найден контейнер зависимостей.")
                            # Ищем все ссылки внутри контейнера, ведущие на страницы модов
                            required_links = required_items_container.find_all('a', href=re.compile(r'https://steamcommunity\.com/workshop/filedetails/\?id=\d+'))
                            for link in required_links:
                                href = link.get('href', '')
                                logger.debug(f"[Browser/Add] Обработка ссылки зависимости: {href}")
                                # Извлекаем ID из href
                                dep_match = re.search(r'id=(\d+)', href)
                                if dep_match:
                                    dep_id = dep_match.group(1)
                                    # Убедимся, что ID уникален и не является ID самого модуля
                                    if dep_id and dep_id != mod_id and dep_id not in dependencies:
                                        dependencies.append(dep_id)
                                        logger.debug(f"[Browser/Add] Найдена зависимость ID: {dep_id}")
                                else:
                                    logger.warning(f"[Browser/Add] Не удалось извлечь ID из href зависимости: {href}")
                            logger.debug(f"[Browser/Add] Всего найдено уникальных зависимостей: {len(dependencies)}")
                        else:
                            logger.debug("[Browser/Add] Контейнер зависимостей не найден.")
                        # - КОНЕЦ ИСПРАВЛЕННОГО Поиска зависимостей -
                        logger.info(f"[Browser/Add] Мод '{mod_name}' ({mod_id}) найден. Зависимости: {dependencies}")
                    else:
                        logger.error(f"[Browser/Add] Ошибка запроса страницы мода: {response.status_code}")
                        wx.MessageBox("Не удалось получить информацию о моде", "Ошибка", wx.OK | wx.ICON_ERROR)
                        return
                except Exception as e:
                    logger.error(f"[Browser/Add] Ошибка при парсинге страницы мода: {e}")
                    wx.MessageBox("Ошибка при получении данных мода", "Ошибка", wx.OK | wx.ICON_ERROR)
                    return

                # --- ИМПОРТЫ ---
                from src.models.mod import Mod, ModDependency
                # ---------------

                # - ИСПРАВЛЕНИЕ: Передаем зависимости правильно -
                # Создаем полноценные объекты ModDependency для зависимостей
                mod_dependencies_raw = []
                for dep_id in dependencies:
                    # Проверяем, установлен ли этот мод (используя кэш)
                    is_installed = dep_id in self.installed_mod_ids
                    # Создаем объект зависимости как ModDependency
                    dep_mod = ModDependency(
                        mod_id=dep_id,
                        name=f"Зависимость {dep_id}", # Имя по умолчанию, можно попробовать получить настоящее имя позже
                        is_installed=is_installed # <-- is_installed относится к ModDependency
                    )
                    mod_dependencies_raw.append(dep_mod) # Добавляем объект ModDependency

                # Создаем основной мод с зависимостями (пустыми, заполним позже)
                mod = Mod(
                    mod_id=mod_id,
                    name=mod_name,
                    author="Неизвестен",
                    workshop_url=url,
                    dependencies=[] # Пока пусто, заполним позже
                )
                # - КОНЕЦ ИСПРАВЛЕНИЯ -

                # --- ЛОГИКА С ДИАЛОГОМ ---
                if mod_dependencies_raw: # Если есть зависимости
                    # Создаем и показываем диалог
                    dlg = DependencyConfirmationDialog(self, mod, mod_dependencies_raw, self.installed_mod_ids)
                    if dlg.ShowModal() == wx.ID_OK:
                        # Пользователь подтвердил, получаем выбранные зависимости
                        selected_dep_items = dlg.get_selected_dependencies()
                        logger.info(f"[Browser/Add] Пользователь выбрал {len(selected_dep_items)} зависимостей для установки.")

                        # Добавляем выбранные зависимости в очередь
                        added_deps_count = 0
                        for dep_item in selected_dep_items:
                            # dep_item - это объект ModDependency
                            # Проверяем еще раз, нет ли её уже в очереди
                            if not self.download_manager.is_in_queue(dep_item.mod_id):
                                # Создаем полноценный Mod объект для зависимости, чтобы добавить его в очередь
                                dep_mod_for_queue = Mod(
                                    mod_id=dep_item.mod_id,
                                    name=dep_item.name,
                                    author="Неизвестен",
                                    workshop_url=f"https://steamcommunity.com/workshop/filedetails/?id={dep_item.mod_id}",
                                    is_enabled=False # Зависимости по умолчанию не включены отдельно
                                )
                                self.download_manager.add_to_queue(dep_mod_for_queue)
                                added_deps_count += 1
                            else:
                                logger.info(f"[Browser/Add] Зависимость {dep_item.mod_id} уже в очереди (после выбора).")

                        if added_deps_count > 0:
                            self._update_queue_list() # Обновляем список, если добавлены зависимости

                        # Добавляем основной мод в очередь
                        # Перед добавлением обновляем его список зависимостей (уже выбранными)
                        mod.dependencies = [dep_item for dep_item in selected_dep_items]

                        self.download_manager.add_to_queue(mod)
                        self._update_queue_list()

                        logger.info(f"[Browser/Add] Мод '{mod_name}' ({mod_id}) и {added_deps_count} его зависимостей добавлены в очередь загрузки.")

                    else: # wx.ID_CANCEL
                        # Пользователь отменил добавление
                        logger.info(f"[Browser/Add] Пользователь отменил добавление мода '{mod_name}' и его зависимостей.")

                    dlg.Destroy()
                else:
                    # Нет зависимостей, просто добавляем основной мод
                    self.download_manager.add_to_queue(mod)
                    self._update_queue_list()
                    logger.info(f"[Browser/Add] Мод '{mod_name}' ({mod_id}) добавлен в очередь загрузки (без зависимостей).")

                # --- КОНЕЦ ЛОГИКИ С ДИАЛОГОМ ---

    # --- КОНЕЦ ОБНОВЛЕННОГО _on_add_to_queue ---

    # --- Добавлен недостающий метод _on_add_collection_clicked ---
    def _on_add_collection_clicked(self, event):
        """Обработчик нажатия кнопки 'Добавить коллекцию'."""
        if self.current_game:
            url = self.webview.GetCurrentURL()
            if "steamcommunity.com/sharedfiles/filedetails/" in url and "id=" in url:
                match = re.search(r'id=(\d+)', url)
                if match:
                    collection_id = match.group(1)
                    self.progress.Show()
                    self.progress.Pulse()
                    self.Layout()
                    threading.Thread(target=self._parse_and_add_collection, args=(collection_id,), daemon=True).start()

    # --- Конец добавленного метода ---

    # --- ОБНОВЛЕННЫЙ _parse_and_add_collection с диалогом ---
    def _parse_and_add_collection(self, collection_id):
        """Парсит коллекцию и добавляет моды в очередь."""
        try:
            logger.info(f"[Browser/Collection] Начало парсинга коллекции {collection_id}")
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                content = response.text
                # Метод 1: Поиск в JavaScript
                mod_ids = re.findall(r'MakeVoteableItem\(\s*["\'](\d+)["\']', content)
                logger.debug(f"[Browser/Collection] Метод 1 (MakeVoteableItem) нашел {len(mod_ids)} ID")
                # Метод 2: Поиск по data-id
                if not mod_ids:
                    mod_ids = re.findall(r'data-id=["\'](\d+)["\']', content)
                    logger.debug(f"[Browser/Collection] Метод 2 (data-id) нашел {len(mod_ids)} ID")
                # Метод 3: BeautifulSoup (более надежный)
                if not mod_ids:
                    soup = BeautifulSoup(content, 'html.parser')
                    # Ищем ссылки на моды внутри коллекции
                    # Обычно они в виде <a href="...filedetails/?id=12345">
                    links = soup.find_all('a', href=re.compile(r'sharedfiles/filedetails/\?id=\d+'))
                    mod_ids = []
                    for link in links:
                        match = re.search(r'id=(\d+)', link['href'])
                        if match:
                            mod_ids.append(match.group(1))
                    mod_ids = list(set(mod_ids)) # Убираем дубликаты
                    logger.debug(f"[Browser/Collection] Метод 3 (BeautifulSoup) нашел {len(mod_ids)} ID")
                if mod_ids:
                    # Убираем дубликаты
                    unique_mod_ids = list(set(mod_ids))
                    logger.info(f"[Browser/Collection] Коллекция {collection_id} распарсена. Найдено {len(unique_mod_ids)} уникальных модов.")

                    # --- ЛОГИКА С ДИАЛОГОМ КОЛЛЕКЦИЙ ---
                    # Подготовка данных для диалога
                    mods_for_dialog = []
                    for mod_id in unique_mod_ids:
                        if mod_id == collection_id:
                            continue # Пропускаем ID самой коллекции
                        mod_name = f"Мод из коллекции {collection_id}"
                        try:
                            mod_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
                            mod_response = requests.get(mod_url, headers=headers, timeout=10)
                            if mod_response.status_code == 200:
                                mod_soup = BeautifulSoup(mod_response.text, 'html.parser')
                                title_elem = mod_soup.find('div', class_='workshopItemTitle')
                                if title_elem:
                                    mod_name = title_elem.text.strip()
                        except Exception as e:
                            logger.warning(f"[Browser/Collection] Ошибка получения названия для мода {mod_id}: {e}")

                        from src.models.mod import Mod
                        mod_obj = Mod(
                            mod_id=mod_id,
                            name=mod_name,
                            author="Неизвестен",
                            workshop_url=mod_url
                        )
                        is_installed = mod_id in self.installed_mod_ids
                        mods_for_dialog.append({'mod': mod_obj, 'is_installed': is_installed})

                    # Показываем диалог (в основном потоке)
                    def show_dialog():
                        if not mods_for_dialog:
                            self.progress.Hide()
                            self.Layout()
                            wx.MessageBox("Коллекция пуста или не содержит новых модов.", "Коллекция", wx.OK | wx.ICON_INFORMATION)
                            return

                        dlg = CollectionConfirmationDialog(self, collection_id, mods_for_dialog)
                        if dlg.ShowModal() == wx.ID_OK:
                            selected_mods = dlg.get_selected_mods()
                            logger.info(f"[Browser/Collection] Пользователь выбрал {len(selected_mods)} модов для установки.")
                            added_count = 0
                            skipped_count = 0
                            for mod in selected_mods:
                                # Проверяем, нет ли уже в очереди
                                if not self.download_manager.is_in_queue(mod.mod_id):
                                    self.download_manager.add_to_queue(mod)
                                    added_count += 1
                                else:
                                    logger.debug(f"[Browser/Collection] Мод {mod.mod_id} уже в очереди (после выбора).")
                                    skipped_count += 1

                            self.progress.Hide()
                            self.Layout()
                            if added_count > 0 or skipped_count > 0: # Обновляем только если были изменения
                                self._update_queue_list()
                            message = f"Добавлено модов из коллекции в очередь: {added_count}"
                            if skipped_count > 0:
                                message += f"\nПропущено (уже в очереди): {skipped_count}"
                            wx.MessageBox(message, "Коллекция", wx.OK | wx.ICON_INFORMATION)
                            logger.info(f"[Browser/Collection] Коллекция {collection_id}: добавлено {added_count}, пропущено {skipped_count} (после подтверждения).")
                        else: # wx.ID_CANCEL
                            self.progress.Hide()
                            self.Layout()
                            logger.info(f"[Browser/Collection] Пользователь отменил добавление коллекции {collection_id}.")
                        dlg.Destroy()

                    wx.CallAfter(show_dialog)
                    # --- КОНЕЦ ЛОГИКИ С ДИАЛОГОМ ---

                else:
                    logger.error(f"[Browser/Collection] Не удалось извлечь mod_id из коллекции {collection_id}")
                    wx.CallAfter(self._collection_error, "Не удалось получить список модов из коллекции (пустой список)")
            else:
                logger.error(f"[Browser/Collection] Ошибка загрузки коллекции {collection_id}, статус: {response.status_code}")
                wx.CallAfter(self._collection_error, f"Ошибка загрузки коллекции (HTTP {response.status_code})")
        except requests.exceptions.RequestException as e:
            logger.error(f"[Browser/Collection] Сетевая ошибка при парсинге коллекции {collection_id}: {e}")
            wx.CallAfter(self._collection_error, f"Сетевая ошибка: {e}")
        except Exception as e:
            logger.error(f"[Browser/Collection] Ошибка парсинга коллекции {collection_id}: {e}")
            wx.CallAfter(self._collection_error, f"Ошибка парсинга: {e}")

    def _finish_collection_add(self, added_count, skipped_count):
        # Этот метод теперь может быть упрощен или удален, так как логика перенесена в диалог
        self.progress.Hide()
        self.Layout()
        self._update_queue_list()
        message = f"Добавлено модов: {added_count}"
        if skipped_count > 0:
            message += f"\nПропущено: {skipped_count}"
        wx.MessageBox(message, "Коллекция", wx.OK | wx.ICON_INFORMATION)

    def _collection_error(self, message):
        self.progress.Hide()
        self.Layout()
        wx.MessageBox(message, "Ошибка", wx.OK | wx.ICON_ERROR)

    # --- НОВЫЕ МЕТОДЫ для экспорта/импорта ---
    def _on_export(self, event):
        """Экспортирует список установленных модов."""
        if not self.current_game:
            wx.MessageBox("Сначала выберите игру", "Ошибка", wx.OK | wx.ICON_WARNING)
            return
        if not self.installed_mod_ids:
            wx.MessageBox("Нет установленных модов для экспорта", "Информация", wx.OK | wx.ICON_INFORMATION)
            return
        with wx.FileDialog(self, "Сохранить список модов",
                           wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            try:
                # Получаем полные объекты модов для экспорта названий
                mod_list = []
                if self.mod_manager:
                    for mod in self.mod_manager._mods: # Или get_all_mods
                        if mod.mod_id in self.installed_mod_ids:
                            mod_list.append({
                                'mod_id': mod.mod_id,
                                'name': mod.name,
                                'author': mod.author
                            })
                data_to_export = {
                    'game_steam_id': self.current_game.steam_id,
                    'game_name': self.current_game.name,
                    'exported_at': wx.DateTime.Now().FormatISOCombined(),
                    'mods': mod_list
                }
                with open(pathname, 'w', encoding='utf-8') as f:
                    json.dump(data_to_export, f, indent=4, ensure_ascii=False)
                wx.MessageBox(f"Список модов экспортирован в:\n{pathname}", "Экспорт", wx.OK | wx.ICON_INFORMATION)
                logger.info(f"[Browser/Export] Список модов экспортирован в {pathname}")
            except Exception as e:
                logger.error(f"[Browser/Export] Ошибка экспорта: {e}")
                wx.MessageBox(f"Ошибка при экспорте: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)

    def _on_import(self, event):
        """Импортирует список модов из файла."""
        if not self.current_game:
            wx.MessageBox("Сначала выберите игру", "Ошибка", wx.OK | wx.ICON_WARNING)
            return
        with wx.FileDialog(self, "Открыть список модов",
                           wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # --- ИСПРАВЛЕНИЕ ОШИБКИ СИНТАКСИСА ---
                if not isinstance(data, dict) or 'mods' not in data:
                    raise ValueError("Неверный формат файла")
                # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
                imported_mods = data['mods']
                if not isinstance(imported_mods, list):
                    raise ValueError("Неверный формат списка модов в файле")
                game_name = data.get('game_name', 'Неизвестная игра')
                num_mods = len(imported_mods)
                message = f"Импортировано из файла '{os.path.basename(pathname)}' ({game_name}):\nНайдено модов: {num_mods}\nДобавить их в очередь загрузки?"
                res = wx.MessageBox(message, "Импорт", wx.YES_NO | wx.ICON_QUESTION)
                if res == wx.YES:
                    added_count = 0
                    skipped_count = 0
                    for mod_data in imported_mods:
                        mod_id = str(mod_data.get('mod_id', ''))
                        if not mod_id.isdigit():
                            logger.warning(f"[Browser/Import] Пропущен мод с некорректным ID: {mod_data}")
                            continue
                        # Проверка на наличие в очереди
                        if any(m.mod_id == mod_id for m in self.download_manager.download_queue):
                            logger.debug(f"[Browser/Import] Мод {mod_id} уже в очереди, пропущен.")
                            skipped_count += 1
                            continue
                        mod_name = mod_data.get('name', f'Импортированный мод {mod_id}')
                        mod_author = mod_data.get('author', 'Неизвестен')

                        from src.models.mod import Mod
                        mod = Mod(
                            mod_id=mod_id,
                            name=mod_name,
                            author=mod_author,
                            workshop_url=f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
                        )
                        self.download_manager.add_to_queue(mod)
                        added_count += 1
                    self._update_queue_list()
                    result_msg = f"Добавлено в очередь: {added_count}"
                    if skipped_count > 0:
                        result_msg += f"\nПропущено (уже в очереди): {skipped_count}"
                    wx.MessageBox(result_msg, "Импорт", wx.OK | wx.ICON_INFORMATION)
                    logger.info(f"[Browser/Import] Импортировано: {added_count}, пропущено: {skipped_count}")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"[Browser/Import] Ошибка формата файла {pathname}: {e}")
                wx.MessageBox(f"Ошибка чтения файла (неверный формат): {e}", "Ошибка", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                logger.error(f"[Browser/Import] Ошибка импорта из {pathname}: {e}")
                wx.MessageBox(f"Ошибка при импорте: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)

    # --- КОНЕЦ НОВЫХ МЕТОДОВ ---

    # --- НОВЫЙ МЕТОД: Очистка очереди ---
    def _on_clear_queue(self, event):
        """Обработчик нажатия кнопки 'Очистить очередь'."""
        if self.download_manager.download_queue: # Проверяем, не пустая ли очередь
            res = wx.MessageBox("Вы уверены, что хотите очистить всю очередь загрузки?", "Подтверждение", wx.YES_NO | wx.ICON_QUESTION)
            if res == wx.YES:
                self.download_manager.clear_queue()
                self._update_queue_list()
                logger.info("[Browser] Очередь загрузки очищена пользователем.")
        else:
            logger.debug("[Browser] Попытка очистки пустой очереди.")

    # --- КОНЕЦ НОВОГО МЕТОДА ---

    def _on_remove_from_queue(self, event):
        selection = self.queue_list.GetFirstSelected()
        if selection >= 0:
            queue = self.download_manager.download_queue
            if 0 <= selection < len(queue):
                mod = queue[selection]
                self.download_manager.remove_from_queue(mod.mod_id)
                self._update_queue_list()
                logger.info(f"Мод {mod.name} удален из очереди загрузки")

    # --- ИЗМЕНЕННЫЙ _on_download_queue ---
    def _on_download_queue(self, event):
        """Обработчик нажатия кнопки 'Скачать' - открывает диалог прогресса."""
        if not self.current_game:
            wx.MessageBox("Сначала выберите игру", "Ошибка", wx.OK | wx.ICON_WARNING)
            return
        # --- ИСПРАВЛЕНИЕ ОШИБКИ: Правильный вызов свойства ---
        if not self.download_manager.download_queue:
            wx.MessageBox("Очередь загрузки пуста", "Информация", wx.OK | wx.ICON_INFORMATION)
            return
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ОШИБКИ ---
        # Создаем и показываем модальный диалог
        # Передаем download_manager и current_game
        dlg = DownloadProgressDialog(self, self.download_manager, self.current_game)
        dlg.ShowModal() # Блокирует MainWindow до закрытия диалога
        # После закрытия диалога
        if dlg.is_download_successful():
            # Обновляем UI главного окна
            self._update_queue_list() # Очередь должна стать пустой
            # Сообщаем, что моды обновились
            if HAS_EVENT_BUS:
                event_bus.emit("mods_updated", self.current_game)
            wx.MessageBox("Моды успешно загружены и установлены!", "Успех", wx.OK | wx.ICON_INFORMATION)
            logger.info("[Browser] Моды успешно загружены через диалог.")
        else:
            # Ошибки или отмена уже залогированы в диалоге
            logger.info("[Browser] Загрузка через диалог завершена (возможно, с ошибками или отменой).")
            # Queue list обновлять не нужно, если не успешно
        dlg.Destroy()

    # --- КОНЕЦ ИЗМЕНЕННОГО _on_download_queue ---

    def Destroy(self):
        # Отписываемся от событий при уничтожении панели
        if HAS_EVENT_BUS:
            event_bus.unsubscribe("mods_updated", self._on_mods_updated)
        super().Destroy()
