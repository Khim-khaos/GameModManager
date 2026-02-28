# src/ui/tabs/mods_tab.py
# -*- coding: utf-8 -*-
"""Вкладка установленных модов"""
import os
import re
import wx
import threading
import json
import time
from datetime import datetime
from pathlib import Path
from loguru import logger
from typing import List, Dict, Optional, Any, Set
import requests
from io import BytesIO
# Импорт функции перевода
from src.core.i18n import _
# Импорт моделей
from src.models.mod import Mod
from src.models.game import Game
# Импорт менеджеров
from src.core.mod_manager import ModManager
# Попытка импорта event_bus
try:
    from src.event_bus import event_bus
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False
    logger.warning(_("system.event_bus_not_found") + ", " + _("system.external_browser_fallback"))
# Импортируем новые сервисы
from src.core.steam_workshop_service import SteamWorkshopService
from src.core.task_manager import TaskManager
# Импортируем HyperLinkCtrl для кликабельных ссылок
import wx.lib.agw.hyperlink as hl

class ModsTab(wx.Panel):
    """Вкладка установленных модов с вертикальным расположением панелей."""
    MOD_IMAGE_SIZE = (200, 150)
    COL_NAME = 0
    COL_ID = 1
    COL_STATUS = 2
    COL_INSTALL = 3
    COL_UPDATE = 4
    COL_SIZE = 5

    def __init__(self, parent, mod_manager: ModManager, language_manager,
                 steam_workshop_service: SteamWorkshopService = None,
                 task_manager: TaskManager = None):
        super().__init__(parent)
        self.mod_manager = mod_manager
        self.language_manager = language_manager
        self.steam_workshop_service = steam_workshop_service or SteamWorkshopService()
        self.task_manager = task_manager or TaskManager()
        self.current_game: Optional[Game] = None
        self.mod_details: Dict[str, Dict[str, Any]] = {}
        self.mod_versions: Dict[str, Dict[str, str]] = {}
        self.mod_images: Dict[str, wx.Bitmap] = {}
        self.selected_mod_id: Optional[str] = None
        self.loading_lock = threading.Lock()
        self.loading_dialog = None
        self.total_mods_to_load = 0
        self.loaded_mods_count = 0
        self.loading_aborted = False
        self.names_dialog = None
        self.names_total = 0
        self.names_loaded = 0
        self.names_aborted = False
        self.names_semaphore = threading.Semaphore(2)  # Уменьшил с 5 до 2 для меньшей нагрузки
        self.highlighted_item = None  # Для временного выделения зависимостей
        self.highlighted_list = None  # Список с выделенным элементом
        self.sort_col_enabled = self.COL_NAME
        self.sort_asc_enabled = True
        self.sort_col_disabled = self.COL_NAME
        self.sort_asc_disabled = True
        self.search_term_enabled = ""
        self.search_term_disabled = ""
        self.info_panel: wx.Panel = None
        self.disabled_panel: wx.Panel = None
        self.enabled_panel: wx.Panel = None
        self.disabled_title: wx.StaticText = None
        self.enabled_title: wx.StaticText = None
        self.mod_info_panel: wx.ScrolledWindow = None
        self.mod_info_sizer: wx.BoxSizer = None
        self.mod_title_label: wx.StaticText = None
        self.mod_author_label: wx.StaticText = None
        self.mod_id_label: wx.StaticText = None
        self.mod_description_label: wx.StaticText = None
        self.mod_install_label: wx.StaticText = None
        self.mod_update_label: wx.StaticText = None
        self.mod_local_update_label: wx.StaticText = None
        self.mod_size_label: wx.StaticText = None
        self.mod_tags_label: wx.StaticText = None
        self.mod_tags_panel: wx.Panel = None
        self.mod_tags_sizer: wx.WrapSizer = None
        self.mod_deps_label: wx.StaticText = None
        self.mod_deps_panel: wx.Panel = None
        self.mod_deps_sizer: wx.BoxSizer = None
        self.check_updates_btn: wx.Button = None
        self.update_all_btn: wx.Button = None
        self.disabled_search_ctrl: wx.SearchCtrl = None
        self.enabled_search_ctrl: wx.SearchCtrl = None
        self.disabled_list: wx.ListCtrl = None
        self.enabled_list: wx.ListCtrl = None
        self.main_splitter: wx.SplitterWindow = None
        self.lists_splitter: wx.SplitterWindow = None
        self._create_ui()
        self._load_mod_versions()
        if HAS_EVENT_BUS and event_bus:
            event_bus.subscribe("mods_updated", self._on_mods_updated_event)
            event_bus.subscribe("language_changed", self._on_language_changed)

    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Добавляем панель с кнопками управления модами наверх
        control_panel = wx.Panel(self)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.check_updates_btn = wx.Button(control_panel, label=self.language_manager.get_text("mod.check_updates"))
        self.update_all_btn = wx.Button(control_panel, label=self.language_manager.get_text("mod.update_all"))
        self.check_updates_btn.Bind(wx.EVT_BUTTON, self._on_check_updates)
        self.update_all_btn.Bind(wx.EVT_BUTTON, self._on_update_all_mods)
        
        control_sizer.Add(self.check_updates_btn, 0, wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        control_sizer.Add(self.update_all_btn, 0, wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        control_sizer.AddStretchSpacer(1)  # Растягиваемый spacer для прижатия к левому краю
        
        control_panel.SetSizer(control_sizer)
        main_sizer.Add(control_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        
        self.main_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_3D)
        self.main_splitter.SetMinimumPaneSize(150)
        self.info_panel = wx.Panel(self.main_splitter)
        info_sizer = wx.BoxSizer(wx.VERTICAL)  # Изменено на VERTICAL для вертикального расположения
        
        # Изображение вверху
        self.mod_image = wx.StaticBitmap(self.info_panel, bitmap=wx.NullBitmap, size=self.MOD_IMAGE_SIZE)
        info_sizer.Add(self.mod_image, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Панель с информацией под изображением
        self.mod_info_panel = wx.ScrolledWindow(self.info_panel, style=wx.VSCROLL)
        self.mod_info_panel.SetScrollRate(5, 5)
        self.mod_info_sizer = wx.BoxSizer(wx.VERTICAL)
        self.mod_title_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.name')}: ")
        self.mod_author_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.author')}: ")
        self.mod_id_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.id')}: ")
        self.mod_description_label = wx.TextCtrl(self.mod_info_panel, value=f"{self.language_manager.get_text('mod.description')}:\n", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.BORDER_NONE)
        self.mod_description_label.SetMinSize((-1, 100))  # Минимальная высота 100 пикселей
        self.mod_install_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.installed')}: ")
        self.mod_update_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.steam_updated')}: ")
        self.mod_local_update_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.local_updated')}: ")
        self.mod_size_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.size')}: ")
        self.mod_tags_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.tags')}: ")
        self.mod_tags_panel = wx.Panel(self.mod_info_panel)
        self.mod_tags_sizer = wx.WrapSizer(wx.HORIZONTAL, wx.WRAPSIZER_DEFAULT_FLAGS)
        self.mod_tags_panel.SetSizer(self.mod_tags_sizer)
        self.mod_deps_label = wx.StaticText(self.mod_info_panel, label=f"{self.language_manager.get_text('mod.dependencies')}: ")
        self.mod_deps_panel = wx.Panel(self.mod_info_panel)
        self.mod_deps_sizer = wx.BoxSizer(wx.VERTICAL)
        self.mod_deps_panel.SetSizer(self.mod_deps_sizer)
        
        # Добавляем все элементы информации в вертикальный sizer
        self.mod_info_sizer.Add(self.mod_title_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_author_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_id_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_description_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_install_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_update_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_local_update_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_size_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_tags_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_tags_panel, 0, wx.EXPAND | wx.LEFT, 10)
        self.mod_info_sizer.Add(self.mod_deps_label, 0, wx.EXPAND | wx.ALL, 2)
        self.mod_info_sizer.Add(self.mod_deps_panel, 0, wx.EXPAND | wx.LEFT, 10)
        
        self.mod_info_panel.SetSizer(self.mod_info_sizer)
        info_sizer.Add(self.mod_info_panel, 1, wx.EXPAND | wx.ALL, 5)  # Информация занимает всё оставшееся пространство
        self.info_panel.SetSizer(info_sizer)
        self.lists_splitter = wx.SplitterWindow(self.main_splitter, style=wx.SP_LIVE_UPDATE | wx.SP_3D)
        self.lists_splitter.SetMinimumPaneSize(100)
        self._create_disabled_mods_panel(self.lists_splitter)
        self._create_enabled_mods_panel(self.lists_splitter)
        self.main_splitter.SplitVertically(self.info_panel, self.lists_splitter, 300)
        self.lists_splitter.SplitVertically(self.disabled_panel, self.enabled_panel, -200)
        main_sizer.Add(self.main_splitter, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        self._clear_mod_info()
        self._clear_lists()
        self._update_panel_titles(0, 0)

    def _create_disabled_mods_panel(self, parent):
        self.disabled_panel = wx.Panel(parent)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.disabled_title = wx.StaticText(self.disabled_panel, label=f"{self.language_manager.get_text('mod.disabled_mods')} (0)")
        font = self.disabled_title.GetFont()
        font.PointSize += 2
        font = font.Bold()
        self.disabled_title.SetFont(font)
        panel_sizer.Add(self.disabled_title, 0, wx.ALL, 5)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.disabled_panel, label=f"{self.language_manager.get_text('mod.search')}:")
        self.disabled_search_ctrl = wx.SearchCtrl(self.disabled_panel, style=wx.TE_PROCESS_ENTER)
        self.disabled_search_ctrl.ShowCancelButton(True)
        self.disabled_search_ctrl.Bind(wx.EVT_TEXT, self._on_disabled_search)
        self.disabled_search_ctrl.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_disabled_search_cancel)
        self.disabled_search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_disabled_search)
        search_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        search_sizer.Add(self.disabled_search_ctrl, 1, wx.EXPAND)
        panel_sizer.Add(search_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.disabled_list = wx.ListCtrl(self.disabled_panel, style=wx.LC_REPORT)
        self.disabled_list.AppendColumn(self.language_manager.get_text("mod.name"), width=200)
        self.disabled_list.AppendColumn(self.language_manager.get_text("mod.author"), width=150)
        self.disabled_list.AppendColumn(self.language_manager.get_text("mod.updated"), width=150)
        self.disabled_list.AppendColumn(self.language_manager.get_text("mod.steam_updated"), width=150)
        self.disabled_list.AppendColumn(self.language_manager.get_text("mod.size"), width=100)
        self.disabled_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_mod_selected)
        self.disabled_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._on_mod_right_click)
        self.disabled_list.Bind(wx.EVT_LIST_COL_CLICK, self._on_column_click_disabled)
        self.disabled_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_mod_double_click)
        panel_sizer.Add(self.disabled_list, 1, wx.EXPAND | wx.ALL, 5)
        self.disabled_panel.SetSizer(panel_sizer)

    def _create_enabled_mods_panel(self, parent):
        self.enabled_panel = wx.Panel(parent)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.enabled_title = wx.StaticText(self.enabled_panel, label=f"{self.language_manager.get_text('mod.enabled_mods')} (0)")
        font = self.enabled_title.GetFont()
        font.PointSize += 2
        font = font.Bold()
        self.enabled_title.SetFont(font)
        panel_sizer.Add(self.enabled_title, 0, wx.ALL, 5)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.enabled_panel, label=f"{self.language_manager.get_text('mod.search')}:")
        self.enabled_search_ctrl = wx.SearchCtrl(self.enabled_panel, style=wx.TE_PROCESS_ENTER)
        self.enabled_search_ctrl.ShowCancelButton(True)
        self.enabled_search_ctrl.Bind(wx.EVT_TEXT, self._on_enabled_search)
        self.enabled_search_ctrl.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_enabled_search_cancel)
        self.enabled_search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enabled_search)
        search_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        search_sizer.Add(self.enabled_search_ctrl, 1, wx.EXPAND)
        panel_sizer.Add(search_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.enabled_list = wx.ListCtrl(self.enabled_panel, style=wx.LC_REPORT)
        self.enabled_list.AppendColumn(self.language_manager.get_text("mod.name"), width=200)
        self.enabled_list.AppendColumn(self.language_manager.get_text("mod.id"), width=120)
        self.enabled_list.AppendColumn("Status", width=80)  # Оставляем как есть, это техническое поле
        self.enabled_list.AppendColumn(self.language_manager.get_text("mod.installed"), width=120)
        self.enabled_list.AppendColumn(self.language_manager.get_text("mod.updated"), width=120)
        self.enabled_list.AppendColumn(self.language_manager.get_text("mod.size"), width=80)
        self.enabled_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_mod_selected)
        self.enabled_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._on_mod_right_click)
        self.enabled_list.Bind(wx.EVT_LIST_COL_CLICK, self._on_column_click_enabled)
        self.enabled_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_mod_double_click)
        panel_sizer.Add(self.enabled_list, 1, wx.EXPAND | wx.ALL, 5)
        self.enabled_panel.SetSizer(panel_sizer)

    def set_game(self, game: Optional[Game]):
        logger.debug("[ModsTab] " + _("system.set_game_called", name=game.name if game else 'None'))
        self.current_game = game
        self.selected_mod_id = None
        self._clear_mod_info()
        self._clear_lists()
        self._update_panel_titles(0, 0)
        
        # Добавляем отладку для проверки пути
        if game:
            logger.debug(f"[ModsTab] Game path: {game.mods_path}")
            logger.debug(f"[ModsTab] Path exists: {Path(game.mods_path).exists()}")
            logger.debug(f"[ModsTab] Path isdir: {Path(game.mods_path).is_dir()}")
        
        if not game or not Path(game.mods_path).exists():
            if game and not Path(game.mods_path).exists():
                logger.warning("[ModsTab] " + _("system.mods_folder_not_exists", path=game.mods_path))
            return
        self.task_manager.submit_task(self._load_mods_async_task, game.steam_id, description=f"{self.language_manager.get_text('mod.loading_mods')} {game.name}")

    def _load_mods_async_task(self, steam_id: str):
        try:
            if not self.current_game:
                logger.error("[ModsTab/LoadAsync] " + _("system.current_game_not_set"))
                wx.CallAfter(wx.MessageBox, f"{self.language_manager.get_text('mod.error')}: {self.language_manager.get_text('mod.game_not_selected')}", self.language_manager.get_text("mod.error"), wx.OK | wx.ICON_ERROR)
                return
            
            logger.debug("[ModsTab/LoadAsync] " + _("system.loading_mods_for_game", name=self.current_game.name, id=self.current_game.steam_id))
            logger.debug(f"[ModsTab/LoadAsync] Game mods path: {self.current_game.mods_path}")
            logger.debug(f"[ModsTab/LoadAsync] Path exists: {Path(self.current_game.mods_path).exists()}")
            logger.debug(f"[ModsTab/LoadAsync] Path isdir: {Path(self.current_game.mods_path).is_dir()}")
            
            self.mod_manager.load_mods_for_game(self.current_game)
            enabled_mods = self.mod_manager.get_enabled_mods(steam_id)
            disabled_mods = self.mod_manager.get_disabled_mods(steam_id)
            wx.CallAfter(self._on_mods_loaded, enabled_mods, disabled_mods)
            wx.CallAfter(self._update_panel_titles, len(enabled_mods), len(disabled_mods))
            logger.info("[ModsTab] " + _("system.mods_loaded_count", enabled=len(enabled_mods), disabled=len(disabled_mods)))
        except Exception as e:
            logger.error("[ModsTab/LoadAsync] " + _("system.mods_load_error", error=e))
            wx.CallAfter(wx.MessageBox, _("system.mods_load_list_error", error=e), _("messages.error"), wx.OK | wx.ICON_ERROR)

    def _on_mods_loaded(self, enabled_mods: List[Mod], disabled_mods: List[Mod]):
        if not self: return
        logger.debug("[ModsTab] _on_mods_loaded: " + _("system.updating_ui_lists"))
        try:
            self._clear_lists()
            for mod in disabled_mods:
                self._add_mod_to_list(self.disabled_list, mod)
            for mod in enabled_mods:
                self._add_mod_to_list(self.enabled_list, mod)
            logger.debug("[ModsTab] _on_mods_loaded: " + _("system.ui_lists_updated"))
            all_mods = enabled_mods + disabled_mods
            if all_mods:
                self.task_manager.submit_task(self._load_mod_list_names_task, all_mods, description=_("system.loading_mod_names"))
        except Exception as e:
            logger.error("[ModsTab/OnLoaded] " + _("system.ui_update_error", error=e))

    def _add_mod_to_list(self, list_ctrl: wx.ListCtrl, mod: Mod):
        if not self: return
        try:
            details = self.mod_details.get(mod.mod_id, {})
            title = details.get('title', mod.mod_id)
            display_name = title if title != mod.mod_id else _("mod.mod_display_name", mod_id=mod.mod_id)
            
            # Используем новые свойства мода для правильного отображения
            install_date = mod.formatted_install_date
            updated_date = mod.formatted_updated_date  
            file_size = mod.formatted_file_size
            
            status = "Включен" if mod.is_enabled else "Отключен"
            index = list_ctrl.InsertItem(list_ctrl.GetItemCount(), display_name)
            list_ctrl.SetItem(index, self.COL_ID, mod.mod_id)
            list_ctrl.SetItem(index, self.COL_STATUS, status)
            list_ctrl.SetItem(index, self.COL_INSTALL, install_date)
            list_ctrl.SetItem(index, self.COL_UPDATE, updated_date)
            list_ctrl.SetItem(index, self.COL_SIZE, file_size)
        except Exception as e:
            logger.error("[ModsTab/AddToList] " + _("mod.mod_add_to_list_error", mod_id=mod.mod_id, error=e))

    def _load_mod_list_names_task(self, mod_list: List[Mod]):
        if not self: return
        self.names_total = len(mod_list)
        self.names_loaded = 0
        self.names_aborted = False
        
        # Проверяем, какие моды уже есть в кэше
        mod_ids = [mod.mod_id for mod in mod_list]
        cached_mods = self.steam_workshop_service.get_cached_mods(mod_ids)
        
        # Сразу обновляем интерфейс для модов из кэша
        for mod in mod_list:
            if mod.mod_id in cached_mods:
                cached_data = cached_mods[mod.mod_id]
                self.mod_details[mod.mod_id] = cached_data
                # Обновляем название в списках
                self._update_mod_name_in_lists(mod.mod_id, cached_data.get('title', mod.mod_id))
                self.names_loaded += 1
        
        # Обновляем счетчик
        current = self.names_loaded
        total = self.names_total
        mods_to_load = [mod for mod in mod_list if mod.mod_id not in cached_mods]
        
        if mods_to_load:
            logger.info("[ModsTab/ListNames] " + _("mod.mods_to_load_count", count=len(mods_to_load), total=total))
            if self.names_total > 0:
                wx.CallAfter(self._show_names_loading_dialog, self.names_total)
            
            for mod in mods_to_load:
                with self.loading_lock:
                    if self.names_aborted:
                        logger.info("[ModsTab/Names] " + _("mod.names_loading_aborted_user"))
                        wx.CallAfter(self._hide_names_loading_dialog)
                        return
                self.task_manager.submit_task(
                    self._load_single_mod_name_task,
                    mod,
                    description=_("mod.loading_mod_name", mod_id=mod.mod_id)
                )
        else:
            logger.info("[ModsTab/ListNames] " + _("mod.all_mods_cached", total=total))
            wx.CallAfter(self._hide_names_loading_dialog)

    def _load_single_mod_name_task(self, mod: Mod):
        with self.names_semaphore:
            with self.loading_lock:
                if self.names_aborted or not self:
                    return
            try:
                if mod.mod_id in self.mod_details:
                    wx.CallAfter(self._refresh_single_mod_in_lists, mod.mod_id)
                    with self.loading_lock:
                        if self.names_aborted:
                            return
                        self.names_loaded += 1
                        current = self.names_loaded
                        total = self.names_total
                    wx.CallAfter(self._update_names_loading_dialog, current, total, mod.mod_id)
                    return
                
                # Небольшая задержка между запросами для снижения нагрузки
                time.sleep(0.5)
                
                details = self.steam_workshop_service.get_mod_details(mod.mod_id)
                if details:
                    details.setdefault('tags', [])
                    details.setdefault('dependencies', [])
                    self.mod_details[mod.mod_id] = details
                    wx.CallAfter(self._refresh_single_mod_in_lists, mod.mod_id)
                else:
                    logger.warning("[ModsTab/ListName/Task] [" + mod.mod_id + "] " + _("mod.mod_data_fetch_failed_log"))
                    details = {'title': mod.mod_id, 'author': _("mod.mod_network_error_log"), 'description': 'Ошибка загрузки', 'tags': [], 'dependencies': []}
            except requests.RequestException as e:
                logger.warning("[ModsTab/ListName/Task] [" + mod.mod_id + "] " + _("mod.mod_network_error_log") + f": {e}")
                details = {'title': mod.mod_id, 'author': _("mod.mod_network_error_log"), 'description': str(e), 'tags': [], 'dependencies': []}
            except Exception as e:
                logger.error("[ModsTab/ListName/Task] [" + mod.mod_id + "] " + _("mod.mod_loading_error_log") + f": {e}")
                details = {'title': mod.mod_id, 'author': _("mod.mod_loading_error_log"), 'description': str(e), 'tags': [], 'dependencies': []}
            finally:
                with self.loading_lock:
                    if self.names_aborted:
                        pass
                    self.names_loaded += 1
                    current = self.names_loaded
                    total = self.names_total
                    aborted = self.names_aborted
                logger.info("[ModsTab/ListName/Task] [" + mod.mod_id + "] " + _("mod.mod_processing_finished_log", current=current, total=total))
                if not aborted:
                    wx.CallAfter(self._update_names_loading_dialog, current, total, mod.mod_id)
                else:
                    wx.CallAfter(self._hide_names_loading_dialog)

    def _refresh_single_mod_in_lists(self, mod_id: str):
        if not self: return
        try:
            details = self.mod_details.get(mod_id, {})
            title = details.get('title', mod_id)
            self._update_mod_name_in_lists(mod_id, title)
        except Exception as e:
            logger.error("[ModsTab/Refresh] " + _("mod.mod_refresh_error_log", mod_id=mod_id, error=e))

    def _update_mod_name_in_lists(self, mod_id: str, title: str):
        """Обновляет название мода в обоих списках"""
        if not self: return
        try:
            # Обновляем в списке включенных модов
            if self.enabled_list:
                item = self._find_mod_in_list(self.enabled_list, mod_id)
                if item != -1:
                    self.enabled_list.SetItem(item, self.COL_NAME, title)
            
            # Обновляем в списке отключенных модов
            if self.disabled_list:
                item = self._find_mod_in_list(self.disabled_list, mod_id)
                if item != -1:
                    self.disabled_list.SetItem(item, self.COL_NAME, title)
                    
        except Exception as e:
            logger.error("[ModsTab/UpdateName] " + _("mod.mod_update_name_error_log", mod_id=mod_id, error=e))

    def _find_mod_in_list(self, list_ctrl: wx.ListCtrl, mod_id: str) -> int:
        """Находит индекс мода в списке по ID"""
        if not list_ctrl: return -1
        try:
            for i in range(list_ctrl.GetItemCount()):
                item_mod_id = list_ctrl.GetItem(i, self.COL_ID).GetText()
                if item_mod_id == mod_id:
                    return i
        except Exception as e:
            logger.error("[ModsTab/FindMod] " + _("mod.mod_find_error_log", mod_id=mod_id, error=e))
        return -1

    def _display_mod_info(self, mod_id: str, details: Dict[str, Any]):
        logger.debug("[ModsTab/DisplayInfo] " + _("mod.mod_displaying_info_log", mod_id=mod_id))
        if not self or mod_id != self.selected_mod_id:
            return
        
        # Сначала убираем подсветку зависимостей от предыдущего мода
        self._clear_all_dependency_highlights()
        
        try:
            # Получаем объект мода для правильного отображения дат
            mod_obj = self.mod_manager.get_mod_by_id(mod_id) if self.mod_manager else None
            
            title = details.get('title', mod_id)
            author = details.get('author', 'Неизвестен')
            description = details.get('description', 'Нет описания')
            tags = details.get('tags', [])
            dependencies = details.get('dependencies', [])
            
            logger.debug("[ModsTab/DisplayInfo] " + _("mod.mod_dependencies_debug", mod_id=mod_id, dependencies=dependencies))
            logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_has_deps_info", mod_id=mod_id, count=len(dependencies)))
            
            # Используем данные из Steam если доступны, иначе из объекта мода
            steam_updated_date = None
            steam_file_size = None
            
            if details:
                steam_updated_date = details.get('updated_date')
                steam_file_size = details.get('file_size')
                if steam_updated_date:
                    logger.debug("[ModsTab/DisplayInfo] " + _("mod.mod_steam_update_debug", mod_id=mod_id, date=steam_updated_date))
                if steam_file_size:
                    logger.debug("[ModsTab/DisplayInfo] " + _("mod.mod_steam_size_debug", mod_id=mod_id, size=steam_file_size))
            
            # Используем данные из объекта мода, если доступны
            if mod_obj:
                install_date = mod_obj.formatted_install_date
                local_update_date = mod_obj.formatted_local_update_date
                
                # Приоритет данным из Steam для даты обновления и размера
                if steam_updated_date:
                    updated_date = steam_updated_date.strftime("%d.%m.%Y %H:%M") if isinstance(steam_updated_date, datetime) else str(steam_updated_date)
                else:
                    updated_date = mod_obj.formatted_updated_date
                
                if steam_file_size:
                    # Конвертируем байты в читаемый формат
                    size = steam_file_size
                    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
                        if size < 1024.0:
                            file_size = f"{size:.1f} {unit}"
                            break
                        size /= 1024.0
                    else:
                        file_size = _("mod.mod_tb_size", size=size)
                else:
                    file_size = mod_obj.formatted_file_size
            else:
                # Fallback на старую логику, если мод не найден
                version_info = self.mod_versions.get(mod_id, {})
                install_date = version_info.get('install_date', 'Неизвестно')
                
                if steam_updated_date:
                    updated_date = steam_updated_date.strftime("%d.%m.%Y %H:%M") if isinstance(steam_updated_date, datetime) else str(steam_updated_date)
                else:
                    updated_date = version_info.get('updated_date', 'Неизвестно')
                
                if steam_file_size:
                    size = steam_file_size
                    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
                        if size < 1024.0:
                            file_size = f"{size:.1f} {unit}"
                            break
                        size /= 1024.0
                    else:
                        file_size = _("mod.mod_tb_size", size=size)
                else:
                    file_size = version_info.get('file_size', _("mod.mod_unknown_size"))
                    
                local_update_date = version_info.get('local_update_date', 'Неизвестно')
            
            if self.mod_title_label:
                self.mod_title_label.SetLabel(f"{self.language_manager.get_text('mod.name')}: {title}")
            if self.mod_author_label:
                self.mod_author_label.SetLabel(f"{self.language_manager.get_text('mod.author')}: {author}")
            if self.mod_id_label:
                self.mod_id_label.SetLabel(f"{self.language_manager.get_text('mod.id')}: {mod_id}")
            if self.mod_description_label:
                self.mod_description_label.SetValue(f"{self.language_manager.get_text('mod.description')}:\n{description}")
            if self.mod_install_label:
                self.mod_install_label.SetLabel(f"{self.language_manager.get_text('mod.installed')}: {install_date}")
            if self.mod_update_label:
                self.mod_update_label.SetLabel(f"{self.language_manager.get_text('mod.steam_updated')}: {updated_date}")
            if self.mod_local_update_label:
                self.mod_local_update_label.SetLabel(f"{self.language_manager.get_text('mod.local_updated')}: {local_update_date}")
            if self.mod_size_label:
                self.mod_size_label.SetLabel(f"{self.language_manager.get_text('mod.size')}: {file_size}")
            if self.mod_tags_label:
                self.mod_tags_label.SetLabel(f"{self.language_manager.get_text('mod.tags')}: ")
            if self.mod_tags_sizer:
                self.mod_tags_sizer.Clear(True)
                if tags:
                    for tag in tags:
                        tag_text = wx.StaticText(self.mod_tags_panel, label=tag)
                        self.mod_tags_sizer.Add(tag_text, 0, wx.ALL, 2)
                else:
                    no_tags_text = wx.StaticText(self.mod_tags_panel, label=self.language_manager.get_text("mod.no_tags"))
                    self.mod_tags_sizer.Add(no_tags_text, 0, wx.ALL, 2)
                self.mod_tags_panel.Layout()
            if self.mod_deps_label:
                self.mod_deps_label.SetLabel(f"{self.language_manager.get_text('mod.dependencies')}: ")
            if self.mod_deps_sizer:
                self.mod_deps_sizer.Clear(True)
                
                # Получаем установленные моды независимо от наличия зависимостей
                installed_mod_ids: Set[str] = set()
                if self.current_game:
                    try:
                        installed_mods: List[Mod] = self.mod_manager.get_installed_mods(self.current_game.steam_id)
                        installed_mod_ids = {m.mod_id for m in installed_mods}
                        logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_installed_list_debug", list=list(installed_mod_ids)[:5], total=len(installed_mod_ids)))
                    except Exception as e:
                        logger.error("[ModsTab/DisplayInfo] " + _("mod.mod_installed_error_debug", error=e))
                        installed_mod_ids = set()
                
                if dependencies:
                    for dep_id in dependencies:
                        dep_sizer = wx.BoxSizer(wx.HORIZONTAL)
                        dep_status_text = wx.StaticText(self.mod_deps_panel, label="[Установлен] " if dep_id in installed_mod_ids else "[Не установлен] ")
                        dep_sizer.Add(dep_status_text, 0, wx.ALIGN_CENTER_VERTICAL)
                        
                        # Получаем название зависимости из кэша
                        dep_name = dep_id  # По умолчанию используем ID
                        dep_details = self.steam_workshop_service.get_mod_details(dep_id)
                        if dep_details and dep_details.get('title'):
                            dep_name = dep_details['title']
                        
                        # Временное логирование для отладки
                        logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_dependency_debug", dep_id=dep_id, name=dep_name, status=_("mod.dependency_installed") if dep_id in installed_mod_ids else _("mod.dependency_not_installed")))
                        
                        if dep_id in installed_mod_ids:
                            dep_link = hl.HyperLinkCtrl(self.mod_deps_panel, id=wx.ID_ANY, label=dep_name, URL="")
                            dep_link.SetToolTip(_("mod.mod_dep_installed_tooltip_text", dep_id=dep_id))
                            logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_dep_link_created_log", dep_id=dep_id, name=dep_name))
                            # Пробуем использовать EVT_LEFT_UP вместо EVT_HYPERLINK_LEFT
                            dep_link.Bind(wx.EVT_LEFT_UP, lambda evt, mid=dep_id: self._on_dependency_click(mid))
                            logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_dep_event_bound", dep_id=dep_id))
                            dep_sizer.Add(dep_link, 0, wx.ALIGN_CENTER_VERTICAL)
                        else:
                            dep_id_text = wx.StaticText(self.mod_deps_panel, label=f"{dep_name} ({dep_id})")
                            dep_id_text.SetToolTip(_("mod.mod_dep_not_installed_tooltip", dep_id=dep_id))
                            logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_dep_text_created", dep_id=dep_id, name=dep_name))
                            # Делаем текст кликабельным для неустановленных зависимостей
                            dep_id_text.Bind(wx.EVT_LEFT_UP, lambda evt, mid=dep_id: self._on_dependency_click(mid))
                            logger.info("[ModsTab/DisplayInfo] " + _("mod.mod_dep_event_bound_not_installed", dep_id=dep_id))
                            dep_sizer.Add(dep_id_text, 0, wx.ALIGN_CENTER_VERTICAL)
                        self.mod_deps_sizer.Add(dep_sizer, 0, wx.EXPAND | wx.ALL, 1)
                else:
                    no_deps_text = wx.StaticText(self.mod_deps_panel, label="Нет зависимостей")
                    self.mod_deps_sizer.Add(no_deps_text, 0, wx.ALL, 2)
                self.mod_deps_panel.Layout()
                
                # Подсвечиваем все установленные зависимости этого мода
                self._highlight_all_dependencies(dependencies, installed_mod_ids)
            cached_bitmap = self.mod_images.get(mod_id)
            if cached_bitmap and self.mod_image:
                logger.debug(f"[ModsTab/DisplayInfo] [{mod_id}] Отображение изображения из кэша.")
                self.mod_image.SetBitmap(cached_bitmap)
            elif self.mod_image:
                version_info_img = self.mod_versions.get(mod_id, {})
                image_url = version_info_img.get('image_url') if isinstance(version_info_img, dict) else None
                if image_url:
                    logger.debug(f"[ModsTab/DisplayInfo] [{mod_id}] Запуск загрузки изображения из version_info.")
                    self.task_manager.submit_task(
                        self._load_single_mod_image_task,
                        mod_id, image_url,
                        description=f"Загрузка изображения для {mod_id} (из кэша версий)"
                    )
                else:
                    logger.debug(f"[ModsTab/DisplayInfo] [{mod_id}] Нет URL изображения в кэше версий.")
                    self.mod_image.SetBitmap(wx.NullBitmap)
            if self.mod_info_panel and self.mod_info_sizer:
                self.mod_info_sizer.Layout()
                self.mod_info_panel.FitInside()
        except Exception as e:
            logger.error(f"[ModsTab/DisplayInfo] Ошибка отображения информации для {mod_id}: {e}")

    def _on_dependency_click(self, mod_id: str):
        logger.info(f"[ModsTab/DepClick] Клик по зависимости {mod_id}")
        
        # Проверяем, установлен ли мод
        installed_mods = self.mod_manager.get_installed_mods(self.current_game.steam_id)
        installed_mod_ids = {m.mod_id for m in installed_mods}
        
        logger.info(f"[ModsTab/DepClick] Установленные моды: {list(installed_mod_ids)[:5]}... (всего {len(installed_mod_ids)})")
        logger.info(f"[ModsTab/DepClick] Проверяем зависимость {mod_id}: {'УСТАНОВЛЕН' if mod_id in installed_mod_ids else 'НЕ УСТАНОВЛЕН'}")
        
        if mod_id in installed_mod_ids:
            # Установленная зависимость - выделяем в списке
            logger.info(f"[ModsTab/DepClick] Зависимость {mod_id} установлена, выделяем в списке")
            self._select_mod_by_id(mod_id)
        else:
            # Неустановленная зависимость - открываем в браузере приложения
            logger.info(f"[ModsTab/DepClick] Зависимость {mod_id} не установлена, открываем в браузере")
            self._on_open_mod_in_browser(mod_id)

    def _select_mod_by_id(self, mod_id: str):
        if not mod_id or not self.current_game:
            return
        logger.info(f"[ModsTab/SelectByID] Попытка выделить мод {mod_id}")
        found = False
        
        # НЕ убираем подсветку зависимостей - она теперь постоянная для выбранного мода
        
        for list_ctrl in [self.disabled_list, self.enabled_list]:
            list_name = "disabled_list" if list_ctrl is self.disabled_list else "enabled_list"
            logger.info(f"[ModsTab/SelectByID] Поиск в {list_name} (всего элементов: {list_ctrl.GetItemCount()})")
            
            item_index = self._find_mod_item_index_by_id(list_ctrl, mod_id)
            if item_index != wx.NOT_FOUND:
                logger.info(f"[ModsTab/SelectByID] Мод {mod_id} найден в {list_name} на позиции {item_index}")
                
                other_list = self.enabled_list if list_ctrl is self.disabled_list else self.disabled_list
                other_list.Select(-1, on=0)
                list_ctrl.Select(item_index, on=True)
                list_ctrl.EnsureVisible(item_index)
                list_ctrl.SetFocus()
                
                # НЕ генерируем событие выбора, чтобы не было двойного выбора
                # event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, list_ctrl.GetId())
                # event.m_itemIndex = item_index
                # event.SetEventObject(list_ctrl)
                # wx.PostEvent(list_ctrl, event)
                found = True
                logger.info(f"[ModsTab/SelectByID] Мод {mod_id} выделен в списке {list_name}")
                break
            else:
                logger.info(f"[ModsTab/SelectByID] Мод {mod_id} не найден в {list_name}")
                
        if not found:
            logger.warning(f"[ModsTab/SelectByID] Мод {mod_id} не найден ни в одном списке.")
            # Показываем первые несколько ID из списков для отладки
            if self.enabled_list and self.enabled_list.GetItemCount() > 0:
                sample_ids = [self.enabled_list.GetItemText(i, self.COL_ID) for i in range(min(3, self.enabled_list.GetItemCount()))]
                logger.info(f"[ModsTab/SelectByID] Примеры ID в enabled_list: {sample_ids}")
            if self.disabled_list and self.disabled_list.GetItemCount() > 0:
                sample_ids = [self.disabled_list.GetItemText(i, self.COL_ID) for i in range(min(3, self.disabled_list.GetItemCount()))]
                logger.info(f"[ModsTab/SelectByID] Примеры ID в disabled_list: {sample_ids}")
            
            wx.MessageBox(_("system.mod_not_found", mod_id=mod_id), _("messages.not_found"), wx.OK | wx.ICON_INFORMATION)

    def _highlight_all_dependencies(self, dependencies: List[str], installed_mod_ids: Set[str]):
        """Подсвечивает все установленные зависимости в списках"""
        if not dependencies or not installed_mod_ids:
            return
            
        logger.info(f"[ModsTab/HighlightDeps] Подсветка {len(dependencies)} зависимостей")
        
        # Сначала убираем предыдущую подсветку
        self._clear_all_dependency_highlights()
        
        # Подсвечиваем каждую установленную зависимость
        highlighted_count = 0
        for dep_id in dependencies:
            if dep_id in installed_mod_ids:
                # Ищем мод в списках
                for list_ctrl in [self.disabled_list, self.enabled_list]:
                    item_index = self._find_mod_item_index_by_id(list_ctrl, dep_id)
                    if item_index != wx.NOT_FOUND:
                        # Подсвечиваем мод
                        item = wx.ListItem()
                        item.SetId(item_index)
                        item.SetBackgroundColour(wx.Colour(144, 238, 144))  # Светло-зеленый
                        list_ctrl.SetItem(item)
                        highlighted_count += 1
                        logger.debug(f"[ModsTab/HighlightDeps] Подсвечена зависимость: {dep_id}")
                        break
        
        logger.info(f"[ModsTab/HighlightDeps] Подсвечено {highlighted_count} зависимостей")

    def _clear_all_dependency_highlights(self):
        """Убирает подсветку всех зависимостей"""
        logger.info(f"[ModsTab/HighlightDeps] Начало очистки подсветки зависимостей")
        for list_ctrl in [self.disabled_list, self.enabled_list]:
            item_count = list_ctrl.GetItemCount()
            logger.debug(f"[ModsTab/HighlightDeps] Очистка списка с {item_count} элементами")
            for i in range(item_count):
                # Восстанавливаем стандартный цвет фона
                item = wx.ListItem()
                item.SetId(i)
                item.SetBackgroundColour(list_ctrl.GetBackgroundColour())
                list_ctrl.SetItem(item)
        logger.debug(f"[ModsTab/HighlightDeps] Убрана подсветка всех зависимостей")

    def _highlight_dependency(self, list_ctrl: wx.ListCtrl, item_index: int):
        """Временно выделяет мод зеленым цветом как зависимость"""
        if not list_ctrl or item_index == wx.NOT_FOUND:
            return
        
        # Сохраняем информацию о выделении
        self.highlighted_list = list_ctrl
        self.highlighted_item = item_index
        
        # Устанавливаем зеленый фон для элемента
        item = wx.ListItem()
        item.SetId(item_index)
        item.SetBackgroundColour(wx.Colour(144, 238, 144))  # Светло-зеленый
        list_ctrl.SetItem(item)
        
        # Убираем выделение через 3 секунды
        wx.CallLater(3000, self._clear_dependency_highlight)
        
        logger.debug(f"[ModsTab/Highlight] Мод на позиции {item_index} выделен как зависимость")

    def _clear_dependency_highlight(self):
        """Убирает временное выделение зависимостей"""
        if self.highlighted_list and self.highlighted_item is not None:
            # Восстанавливаем обычный цвет фона
            item = wx.ListItem()
            item.SetId(self.highlighted_item)
            item.SetBackgroundColour(wx.NullColour)  # Стандартный цвет
            self.highlighted_list.SetItem(item)
            
            logger.debug(f"[ModsTab/Highlight] Выделение зависимости убрано")
            
        # Сбрасываем переменные
        self.highlighted_list = None
        self.highlighted_item = None

    def _load_single_mod_image_task(self, mod_id: str, image_url: str):
        try:
            if not image_url or not isinstance(image_url, str) or not image_url.strip():
                logger.warning(f"[ModsTab/ImageLoad/Task] [{mod_id}] Недопустимый или пустой URL изображения: '{image_url}'")
                return
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            response = requests.get(image_url, headers=headers, timeout=15)
            logger.debug(f"[ModsTab/ImageLoad/Task] [{mod_id}] Получен ответ: {response.status_code}, Content-Type: {response.headers.get('content-type')}")
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"[ModsTab/ImageLoad/Task] [{mod_id}] URL {image_url} не является изображением (Content-Type: {content_type})")
                return
            if response.status_code == 200:
                image_data = response.content
                if not image_data:
                    logger.warning(f"[ModsTab/ImageLoad/Task] [{mod_id}] Получены пустые данные изображения.")
                    return
                try:
                    img_stream = BytesIO(image_data)
                    image = wx.Image(img_stream, wx.BITMAP_TYPE_ANY)
                    if not image.IsOk():
                        logger.error(f"[ModsTab/ImageLoad/Task] [{mod_id}] Созданное изображение (wx.Image) не является валидным.")
                        return
                    image = image.Scale(self.MOD_IMAGE_SIZE[0], self.MOD_IMAGE_SIZE[1], wx.IMAGE_QUALITY_HIGH)
                    scaled_bitmap = wx.Bitmap(image)
                    if not scaled_bitmap.IsOk():
                        logger.error(f"[ModsTab/ImageLoad/Task] [{mod_id}] Созданный bitmap не является валидным.")
                        return
                    self.mod_images[mod_id] = scaled_bitmap
                    logger.info(f"[ModsTab/ImageLoad/Task] [{mod_id}] Изображение загружено и сохранено в кэш.")
                    if self.selected_mod_id == mod_id and self.mod_image:
                        wx.CallAfter(self.mod_image.SetBitmap, scaled_bitmap)
                except Exception as e:
                    logger.error(f"[ModsTab/ImageLoad/Task/CreateBitmap] [{mod_id}] Ошибка создания bitmap: {e}")
            else:
                logger.warning(f"[ModsTab/ImageLoad/Task] [{mod_id}] Ошибка загрузки изображения, статус: {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"[ModsTab/ImageLoad/Task] [{mod_id}] Сетевая ошибка при загрузке {image_url}: {e}")
        except Exception as e:
            logger.error(f"[ModsTab/ImageLoad/Task] [{mod_id}] Неожиданная ошибка при загрузке {image_url}: {e}")

    def _find_mod_item_index_by_id(self, list_ctrl: wx.ListCtrl, mod_id: str) -> int:
        if not self: return wx.NOT_FOUND
        for i in range(list_ctrl.GetItemCount()):
            item_id = list_ctrl.GetItemText(i, self.COL_ID)
            if item_id == mod_id:
                return i
        return wx.NOT_FOUND

    def _update_panel_titles(self, enabled_count: int, disabled_count: int):
        logger.debug(f"[ModsTab] _update_panel_titles: Вкл={enabled_count}, Откл={disabled_count}")
        if not self: return
        try:
            if self.disabled_title:
                self.disabled_title.SetLabel(f"Отключённые моды ({disabled_count})")
                logger.debug(f"[ModsTab] Заголовок отключённых обновлён: {self.disabled_title.GetLabel()}")
            else:
                logger.warning("[ModsTab] disabled_title равен None при попытке обновления.")
            if self.enabled_title:
                self.enabled_title.SetLabel(f"Включённые моды ({enabled_count})")
                logger.debug(f"[ModsTab] Заголовок включённых обновлён: {self.enabled_title.GetLabel()}")
            else:
                logger.warning("[ModsTab] enabled_title равен None при попытке обновления.")
            if self.disabled_panel:
                self.disabled_panel.Layout()
            if self.enabled_panel:
                self.enabled_panel.Layout()
        except RuntimeError as e:
            logger.debug(f"[ModsTab/UpdateTitles] Ошибка обновления заголовков (объект уничтожен): {e}")
        except Exception as e:
            logger.error(f"[ModsTab/UpdateTitles] Неожиданная ошибка обновления заголовков: {e}")

    def _clear_lists(self):
        if not self: return
        try:
            if self.disabled_list:
                self.disabled_list.DeleteAllItems()
            if self.enabled_list:
                self.enabled_list.DeleteAllItems()
            logger.debug("[ModsTab] Списки модов очищены.")
        except Exception as e:
            logger.error(f"[ModsTab] Ошибка очистки списков: {e}")

    def _clear_mod_info(self):
        if not self: return
        try:
            if self.mod_title_label:
                self.mod_title_label.SetLabel(f"{self.language_manager.get_text('mod.name')}: ")
            if self.mod_author_label:
                self.mod_author_label.SetLabel(f"{self.language_manager.get_text('mod.author')}: ")
            if self.mod_id_label:
                self.mod_id_label.SetLabel(f"{self.language_manager.get_text('mod.id')}: ")
            if self.mod_description_label:
                self.mod_description_label.SetValue(f"{self.language_manager.get_text('mod.description')}:\n")
            if self.mod_install_label:
                self.mod_install_label.SetLabel(f"{self.language_manager.get_text('mod.installed')}: ")
            if self.mod_update_label:
                self.mod_update_label.SetLabel(f"{self.language_manager.get_text('mod.steam_updated')}: ")
            if self.mod_local_update_label:
                self.mod_local_update_label.SetLabel(f"{self.language_manager.get_text('mod.local_updated')}: ")
            if self.mod_size_label:
                self.mod_size_label.SetLabel(f"{self.language_manager.get_text('mod.size')}: ")
            if self.mod_tags_label:
                self.mod_tags_label.SetLabel(f"{self.language_manager.get_text('mod.tags')}: ")
            if self.mod_tags_sizer:
                self.mod_tags_sizer.Clear(True)
                self.mod_tags_panel.Layout()
            if self.mod_deps_label:
                self.mod_deps_label.SetLabel(f"{self.language_manager.get_text('mod.dependencies')}: ")
            if self.mod_deps_sizer:
                self.mod_deps_sizer.Clear(True)
                self.mod_deps_panel.Layout()
            if self.mod_image:
                self.mod_image.SetBitmap(wx.NullBitmap)
            self.selected_mod_id = None
            logger.debug("[ModsTab] Информация о моде очищена.")
        except Exception as e:
            logger.error(f"[ModsTab] Ошибка очистки информации о моде: {e}")

    def _filter_list(self, list_ctrl: wx.ListCtrl, search_term: str):
        if not self.current_game:
            return
        if list_ctrl is self.enabled_list:
            all_mods_of_this_type = self.mod_manager.get_enabled_mods(self.current_game.steam_id)
        elif list_ctrl is self.disabled_list:
            all_mods_of_this_type = self.mod_manager.get_disabled_mods(self.current_game.steam_id)
        else:
            logger.warning("[ModsTab/Filter] Неизвестный ListCtrl для фильтрации.")
            return
        list_ctrl.DeleteAllItems()
        search_term_lower = search_term.lower() if search_term else ""
        filtered_mods = []
        if not search_term_lower:
            filtered_mods = all_mods_of_this_type
        else:
            for mod in all_mods_of_this_type:
                match_found = False
                if search_term_lower in mod.mod_id.lower():
                    match_found = True
                if match_found:
                    filtered_mods.append(mod)
                    continue
                mod_details = self.mod_details.get(mod.mod_id, {})
                mod_title = mod_details.get('title', mod.mod_id)
                if search_term_lower in mod_title.lower():
                    match_found = True
                if match_found:
                    filtered_mods.append(mod)
                    continue
                mod_tags = mod_details.get('tags', [])
                for tag in mod_tags:
                    if search_term_lower in tag.lower():
                        match_found = True
                        break
                if match_found:
                    filtered_mods.append(mod)
                    continue
        for mod in filtered_mods:
            self._add_mod_to_list(list_ctrl, mod)
        logger.debug(
            f"[ModsTab/Filter] Применен фильтр '{search_term}' к списку {list_ctrl.GetName()}. "
            f"Отображается {len(filtered_mods)} модов."
        )

    def _on_disabled_search(self, event):
        if self.disabled_search_ctrl:
            self.search_term_disabled = self.disabled_search_ctrl.GetValue()
            self._filter_list(self.disabled_list, self.search_term_disabled)

    def _on_disabled_search_cancel(self, event):
        if not self: return
        self.disabled_search_ctrl.SetValue("")
        self.search_term_disabled = ""
        self._filter_list(self.disabled_list, self.search_term_disabled)

    def _on_enabled_search(self, event):
        if self.enabled_search_ctrl:
            self.search_term_enabled = self.enabled_search_ctrl.GetValue()
            self._filter_list(self.enabled_list, self.search_term_enabled)

    def _on_enabled_search_cancel(self, event):
        if not self: return
        self.enabled_search_ctrl.SetValue("")
        self.search_term_enabled = ""
        self._filter_list(self.enabled_list, self.search_term_enabled)

    def _sort_list(self, list_ctrl: wx.ListCtrl, col: int, ascending: bool):
        items = []
        for i in range(list_ctrl.GetItemCount()):
            item_data = []
            for j in range(list_ctrl.GetColumnCount()):
                item_data.append(list_ctrl.GetItemText(i, j))
            items.append((item_data, i))
        def sort_key(item_tuple):
            item_data, original_index = item_tuple
            if col in [self.COL_ID, self.COL_SIZE]:
                try:
                    return (float(item_data[col]), original_index)
                except ValueError:
                    return (item_data[col], original_index)
            return (item_data[col], original_index)
        items.sort(key=sort_key, reverse=not ascending)
        for i, (item_data, original_index) in enumerate(items):
            for j, text in enumerate(item_data):
                if j == 0:
                    list_ctrl.SetItem(i, j, text)
                else:
                    list_ctrl.SetItem(i, j, text)

    def _on_column_click_disabled(self, event):
        if not self: return
        col = event.GetColumn()
        if col == self.sort_col_disabled:
            self.sort_asc_disabled = not self.sort_asc_disabled
        else:
            self.sort_col_disabled = col
            self.sort_asc_disabled = True
        self._sort_list(self.disabled_list, col, self.sort_asc_disabled)

    def _on_column_click_enabled(self, event):
        if not self: return
        col = event.GetColumn()
        if col == self.sort_col_enabled:
            self.sort_asc_enabled = not self.sort_asc_enabled
        else:
            self.sort_col_enabled = col
            self.sort_asc_enabled = True
        self._sort_list(self.enabled_list, col, self.sort_asc_enabled)

    def _on_mod_selected(self, event):
        list_ctrl = event.GetEventObject()
        index = event.GetIndex()
        if index >= 0 and self:
            mod_id = list_ctrl.GetItemText(index, self.COL_ID)
            self.selected_mod_id = mod_id
            details = self.mod_details.get(mod_id, {'title': mod_id, 'author': 'Загружается...', 'description': 'Загружается...', 'tags': [], 'dependencies': []})
            self._display_mod_info(mod_id, details)
            self.task_manager.submit_task(self._load_selected_mod_details_task, mod_id, description=f"Загрузка деталей мода {mod_id}")
        else:
            self.selected_mod_id = None
            self._clear_mod_info()

    def _on_mod_double_click(self, event):
        list_ctrl = event.GetEventObject()
        index = event.GetIndex()
        if index >= 0 and self:
            mod_id = list_ctrl.GetItemText(index, self.COL_ID)
            mod = self.mod_manager.get_mod_by_id(mod_id)
            if mod:
                if mod.is_enabled:
                    self._disable_mod([mod_id])
                else:
                    self._enable_mod([mod_id])
                self._refresh_single_mod_in_lists_after_action(mod_id, "disable" if mod.is_enabled else "enable")

    def _load_selected_mod_details_task(self, mod_id: str):
        if not self or self.selected_mod_id != mod_id:
            return
        try:
            update_info = self.steam_workshop_service.get_mod_update_info(mod_id)
            if update_info:
                if mod_id not in self.mod_versions:
                    self.mod_versions[mod_id] = {}
                self.mod_versions[mod_id].update(update_info)
                logger.debug(f"[ModsTab/Details/Task] [{mod_id}] Доп. инфо загружена: {update_info}")
                image_url = update_info.get('image_url')
                if image_url:
                    self.task_manager.submit_task(
                        self._load_single_mod_image_task,
                        mod_id, image_url,
                        description=f"Загрузка изображения для {mod_id}"
                    )
                else:
                    logger.debug(f"[ModsTab/Details/Task] [{mod_id}] URL изображения не найден в данных.")
                if self.selected_mod_id == mod_id:
                    wx.CallAfter(self._update_mod_info_panel, mod_id, update_info)
            else:
                logger.warning(f"[ModsTab/Details/Task] [{mod_id}] Не удалось загрузить доп. информацию.")
        except Exception as e:
            logger.error(f"[ModsTab/Details/Task] [{mod_id}] Ошибка: {e}")

    def _update_mod_info_panel(self, mod_id: str, update_info: Dict[str, str]):
        if not self or self.selected_mod_id != mod_id:
            return
        try:
            if self.mod_install_label:
                self.mod_install_label.SetLabel(f"Установлен: {update_info.get('install_date', 'Неизвестно')}")
            if self.mod_update_label:
                self.mod_update_label.SetLabel(f"Обновлён: {update_info.get('updated_date', 'Неизвестно')}")
            if self.mod_size_label:
                self.mod_size_label.SetLabel(f"Размер: {update_info.get('file_size', 'Неизвестно')}")
            logger.debug(f"[ModsTab/Details/UI] [{mod_id}] Панель информации обновлена.")
        except Exception as e:
            logger.error(f"[ModsTab/Details/UI] [{mod_id}] Ошибка обновления панели: {e}")

    def _on_mod_right_click(self, event):
        list_ctrl = event.GetEventObject()
        selected_mods = self._get_selected_mods(list_ctrl)
        if selected_mods:
            self._show_mod_context_menu(selected_mods, list_ctrl)

    def _get_selected_mods(self, list_ctrl: wx.ListCtrl) -> List[str]:
        selected_mods = []
        index = -1
        while True:
            index = list_ctrl.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index == -1:
                break
            mod_id = list_ctrl.GetItemText(index, self.COL_ID)
            selected_mods.append(mod_id)
        return selected_mods

    def _show_mod_context_menu(self, mod_ids: List[str], list_ctrl: wx.ListCtrl):
        if not self: return
        menu = wx.Menu()
        open_item = menu.Append(wx.ID_ANY, self.language_manager.get_text("mod.view_workshop"))
        enable_item = menu.Append(wx.ID_ANY, self.language_manager.get_text("mod.enable"))
        disable_item = menu.Append(wx.ID_ANY, self.language_manager.get_text("mod.disable"))
        remove_item = menu.Append(wx.ID_ANY, self.language_manager.get_text("mod.remove"))
        update_item = menu.Append(wx.ID_ANY, self.language_manager.get_text("mod.update"))
        check_update_item = menu.Append(wx.ID_ANY, self.language_manager.get_text("mod.check_updates"))
        mod_objs = []
        if self.current_game:
            mods = self.mod_manager.get_installed_mods(self.current_game.steam_id)
            mod_objs = [m for m in mods if m.mod_id in mod_ids]
        any_enabled = any(mod.is_enabled for mod in mod_objs)
        any_disabled = any(not mod.is_enabled for mod in mod_objs)
        enable_item.Enable(any_disabled)
        disable_item.Enable(any_enabled)
        def on_menu_open(event):
            for mod_id in mod_ids:
                self._on_open_mod_in_browser(mod_id)
        def on_menu_enable(event):
            success = self._enable_mod(mod_ids)
            if success:
                for mod_id in mod_ids:
                    self._refresh_single_mod_in_lists_after_action(mod_id, "enable")
        def on_menu_disable(event):
            success = self._disable_mod(mod_ids)
            if success:
                for mod_id in mod_ids:
                    self._refresh_single_mod_in_lists_after_action(mod_id, "disable")
        def on_menu_remove(event):
            res = wx.MessageBox(_("system.confirm_remove_multiple", count=len(mod_ids)), _("messages.confirmation"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            if res == wx.YES:
                for mod_id in mod_ids:
                    success = self._remove_mod(mod_id)
                    if success:
                        self._remove_mod_from_lists(mod_id)
        def on_menu_update(event):
            wx.MessageBox(_("system.function_not_implemented", function=_("mod.update")), _("messages.in_development"), wx.OK | wx.ICON_INFORMATION)
        def on_menu_check_update(event):
            wx.MessageBox(_("system.function_not_implemented", function=_("mod.check_update")), _("messages.in_development"), wx.OK | wx.ICON_INFORMATION)
        menu.Bind(wx.EVT_MENU, on_menu_open, open_item)
        menu.Bind(wx.EVT_MENU, on_menu_enable, enable_item)
        menu.Bind(wx.EVT_MENU, on_menu_disable, disable_item)
        menu.Bind(wx.EVT_MENU, on_menu_remove, remove_item)
        menu.Bind(wx.EVT_MENU, on_menu_update, update_item)
        menu.Bind(wx.EVT_MENU, on_menu_check_update, check_update_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def _refresh_single_mod_in_lists_after_action(self, mod_id: str, action: str):
        if not self or not self.current_game: return
        updated_mod = self.mod_manager.get_mod_by_id(mod_id)
        if not updated_mod:
            logger.warning(f"[ModsTab/RefreshAfterAction] Мод {mod_id} не найден после действия {action}.")
            return
        target_list = self.enabled_list if updated_mod.is_enabled else self.disabled_list
        source_list = self.disabled_list if updated_mod.is_enabled else self.enabled_list
        source_index = self._find_mod_item_index_by_id(source_list, mod_id)
        if source_index != wx.NOT_FOUND:
            source_list.DeleteItem(source_index)
            logger.debug(f"[ModsTab/RefreshAfterAction] Мод {mod_id} удален из {'отключенных' if updated_mod.is_enabled else 'включенных'}.")
        self._add_mod_to_list(target_list, updated_mod)
        logger.debug(f"[ModsTab/RefreshAfterAction] Мод {mod_id} добавлен в {'включенные' if updated_mod.is_enabled else 'отключенные'}.")
        enabled_count = self.enabled_list.GetItemCount()
        disabled_count = self.disabled_list.GetItemCount()
        self._update_panel_titles(enabled_count, disabled_count)
        if self.selected_mod_id == mod_id:
            details = self.mod_details.get(mod_id, {'title': mod_id, 'author': '...', 'description': '...', 'tags': [], 'dependencies': []})
            self._display_mod_info(mod_id, details)
        if target_list == self.disabled_list and self.search_term_disabled:
            self._filter_list(self.disabled_list, self.search_term_disabled)
        elif target_list == self.enabled_list and self.search_term_enabled:
            self._filter_list(self.enabled_list, self.search_term_enabled)

    def _remove_mod_from_lists(self, mod_id: str):
        if not self: return
        try:
            for list_ctrl in [self.disabled_list, self.enabled_list]:
                index = self._find_mod_item_index_by_id(list_ctrl, mod_id)
                if index != wx.NOT_FOUND:
                    list_ctrl.DeleteItem(index)
                    logger.debug(f"[ModsTab/RemoveFromLists] Мод {mod_id} удален из списка.")
            enabled_count = self.enabled_list.GetItemCount()
            disabled_count = self.disabled_list.GetItemCount()
            self._update_panel_titles(enabled_count, disabled_count)
            if self.selected_mod_id == mod_id:
                self._clear_mod_info()
                self.selected_mod_id = None
        except Exception as e:
            logger.error(f"[ModsTab/RemoveFromLists] Ошибка удаления мода {mod_id} из списков: {e}")

    def _on_open_mod_in_browser(self, mod_id: str):
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        logger.info(f"[ModsTab/ViewPage] Открытие URL: {url}")
        if HAS_EVENT_BUS and event_bus:
            event_bus.emit("open_mod_in_browser", url)
        else:
            wx.LaunchDefaultBrowser(url)

    def _get_mod_folder_update_time(self, mod: Mod) -> Optional[datetime]:
        """Получает дату последнего изменения папки мода"""
        try:
            if not mod.local_path or not os.path.exists(mod.local_path):
                logger.debug(f"[ModsTab/UpdateTime] Папка мода {mod.mod_id} не найдена: {mod.local_path}")
                return None
            
            # Получаем время последнего изменения папки
            folder_time = os.path.getmtime(mod.local_path)
            return datetime.fromtimestamp(folder_time)
        except Exception as e:
            logger.error(f"[ModsTab/UpdateTime] Ошибка получения времени папки для {mod.mod_id}: {e}")
            return None

    def _check_mod_updates_with_local_data(self) -> Dict[str, Dict[str, Any]]:
        """Проверяет обновления модов сравнивая локальные данные с Steam"""
        if not self.current_game:
            return {}
        
        all_mods = self.mod_manager.get_installed_mods(self.current_game.steam_id)
        update_info = {}
        
        logger.info(f"[ModsTab/CheckUpdates] Проверка {len(all_mods)} модов на обновления")
        
        for mod in all_mods:
            try:
                mod_update_info = {
                    'mod_id': mod.mod_id,
                    'name': mod.name or mod.mod_id,
                    'local_update': mod.local_update_date,
                    'steam_update': mod.updated_date,
                    'folder_update': self._get_mod_folder_update_time(mod),
                    'needs_update': False,
                    'status': 'unknown'
                }
                
                # Детальное логирование для одного мода
                logger.debug(f"[ModsTab/CheckUpdates] Мод {mod.mod_id}:")
                logger.debug(f"  - local_update: {mod.local_update_date}")
                logger.debug(f"  - steam_update: {mod.updated_date}")
                logger.debug(f"  - folder_update: {mod_update_info['folder_update']}")
                
                # Получаем данные из Steam для актуальной информации
                details = self.steam_workshop_service.get_mod_details(mod.mod_id, force_refresh=True)
                
                if details:
                    steam_updated_date = details.get('updated_date')
                    logger.debug(f"[ModsTab/CheckUpdates] Мод {mod.mod_id}: Steam дата обновления = {steam_updated_date}")
                    
                    # Сравниваем даты для определения необходимости обновления
                    if mod_update_info['folder_update'] and steam_updated_date:
                        if steam_updated_date > mod_update_info['folder_update']:
                            mod_update_info['needs_update'] = True
                            mod_update_info['status'] = 'needs_update'
                            logger.info(f"[ModsTab/CheckUpdates] Мод {mod.mod_id} требует обновления (Steam: {steam_updated_date} > Local: {mod_update_info['folder_update']})")
                        else:
                            mod_update_info['status'] = 'up_to_date'
                            logger.debug(f"[ModsTab/CheckUpdates] Мод {mod.mod_id} актуален (Steam: {steam_updated_date} <= Local: {mod_update_info['folder_update']})")
                    else:
                        mod_update_info['status'] = 'missing_data'
                        logger.warning(f"[ModsTab/CheckUpdates] Мод {mod.mod_id}: отсутствуют данные для сравнения (local={mod_update_info['folder_update']}, steam={steam_updated_date})")
                else:
                    mod_update_info['status'] = 'no_steam_data'
                    logger.warning(f"[ModsTab/CheckUpdates] Мод {mod.mod_id}: не удалось получить данные из Steam")
                
                update_info[mod.mod_id] = mod_update_info
                    
            except Exception as e:
                logger.error(f"[ModsTab/CheckUpdates] Ошибка при проверке мода {mod.mod_id}: {e}")
        
        logger.info(f"[ModsTab/CheckUpdates] Проверка завершена. Найдено обновлений: {sum(1 for info in update_info.values() if info.get('needs_update', False))}")
        return update_info

    def _on_check_updates(self, event):
        """Проверка обновлений с использованием локальных данных и Steam"""
        if not self.current_game:
            wx.MessageBox(_("system.select_game_first"), _("messages.error"), wx.OK | wx.ICON_WARNING)
            return
        
        # Показываем диалог прогресса
        progress_dialog = wx.ProgressDialog(
            "Проверка обновлений",
            "Анализ локальных данных и проверка Steam...",
            maximum=100,
            parent=self,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT
        )
        
        def check_updates_task():
            try:
                # Шаг 1: Локальная проверка (быстрая)
                if not progress_dialog.Update(10, "Проверка локальных данных..."):
                    progress_dialog.Destroy()
                    return
                
                update_info = self._check_mod_updates_with_local_data()
                
                # Шаг 2: Обновление данных из Steam для модов с устаревшими данными
                if not progress_dialog.Update(30, "Обновление данных из Steam..."):
                    progress_dialog.Destroy()
                    return
                
                # Получаем моды, которые нужно обновить или у которых нет данных
                mods_to_refresh = []
                for mod_id, info in update_info.items():
                    if info['status'] in ['no_data', 'unknown']:
                        mods_to_refresh.append(mod_id)
                
                if mods_to_refresh:
                    logger.info(f"[ModsTab/CheckUpdates] Обновление {len(mods_to_refresh)} модов из Steam")
                    results = self.steam_workshop_service.preload_missing_mods(mods_to_refresh)
                    
                    # Повторная проверка после обновления данных
                    if not progress_dialog.Update(80, "Повторная проверка..."):
                        progress_dialog.Destroy()
                        return
                    
                    update_info = self._check_mod_updates_with_local_data()
                
                # Шаг 3: Показ результатов
                if not progress_dialog.Update(95, "Подготовка отчета..."):
                    progress_dialog.Destroy()
                    return
                
                # Считаем статистику
                total_mods = len(update_info)
                needs_update = sum(1 for info in update_info.values() if info['needs_update'])
                up_to_date = sum(1 for info in update_info.values() if info['status'] == 'up_to_date')
                no_data = sum(1 for info in update_info.values() if info['status'] == 'no_data')
                
                # Формируем сообщение с результатами
                message_parts = [
                    f"{self.language_manager.get_text('mod.total_mods')}: {total_mods}",
                    f"{self.language_manager.get_text('mod.mods_require_updates')}: {needs_update}",
                    f"{self.language_manager.get_text('mod.mods_up_to_date')}: {up_to_date}",
                    f"{self.language_manager.get_text('mod.mods_no_data')}: {no_data}"
                ]
                
                if needs_update > 0:
                    message_parts.append(f"\n\n{self.language_manager.get_text('mod.mods_requiring_updates')}")
                    for mod_id, info in update_info.items():
                        if info['needs_update']:
                            message_parts.append(f"• {info['name']} ({mod_id})")
                
                wx.CallAfter(progress_dialog.Update, 100, self.language_manager.get_text("mod.ready"))
                wx.CallAfter(progress_dialog.Destroy)
                wx.CallAfter(wx.MessageBox, 
                           "\n".join(message_parts), 
                           self.language_manager.get_text("mod.update_check_results"), 
                           wx.OK | wx.ICON_INFORMATION)
                
                # Обновляем интерфейс
                wx.CallAfter(self._refresh_mods_display)
                
            except Exception as e:
                logger.error(f"[ModsTab/CheckUpdates] Ошибка: {e}")
                wx.CallAfter(progress_dialog.Destroy)
                wx.CallAfter(wx.MessageBox, f"{self.language_manager.get_text('mod.error')} {self.language_manager.get_text('mod.check_updates')}: {e}", self.language_manager.get_text("mod.error"), wx.OK | wx.ICON_ERROR)
        
        # Запускаем в отдельном потоке
        threading.Thread(target=check_updates_task, daemon=True).start()

    def _refresh_mods_display(self):
        """Обновляет отображение модов после проверки обновлений"""
        try:
            # Перезагружаем текущий выбранный мод, если есть
            if self.selected_mod_id:
                details = self.steam_workshop_service.get_mod_details(self.selected_mod_id)
                if details:
                    self.mod_details[self.selected_mod_id] = details
                    self._display_mod_info(self.selected_mod_id, details)
            
            # Обновляем списки если нужно
            logger.info(f"[ModsTab/Refresh] Интерфейс обновлен")
        except Exception as e:
            logger.error(f"[ModsTab/Refresh] Ошибка обновления интерфейса: {e}")

    def _on_update_all_mods(self, event):
        """Обновление всех модов (пока просто проверка)"""
        wx.MessageBox(_("system.update_all_not_implemented"), _("messages.in_development"), wx.OK | wx.ICON_INFORMATION)

    def _refresh_all_mod_data(self, results: Dict[str, bool]):
        """Обновляет данные всех модов после проверки"""
        try:
            # Обновляем детали модов из кэша
            for mod_id, success in results.items():
                if success:
                    details = self.steam_workshop_service.get_mod_details(mod_id)
                    if details:
                        self.mod_details[mod_id] = details
                        self._update_mod_name_in_lists(mod_id, details.get('title', mod_id))
            
            # Обновляем информацию о выбранном моде
            if self.selected_mod_id:
                details = self.mod_details.get(self.selected_mod_id, {})
                self._display_mod_info(self.selected_mod_id, details)
            
            logger.info(f"[ModsTab/Refresh] Обновлены данные для {sum(results.values())} модов")
            
        except Exception as e:
            logger.error(f"[ModsTab/Refresh] Ошибка обновления данных: {e}")

    def _enable_mod(self, mod_ids: List[str]) -> bool:
        if not self or not self.current_game: return False
        success = True
        for mod_id in mod_ids:
            try:
                if not self.mod_manager.enable_mod(self.current_game.steam_id, mod_id):
                    success = False
                    logger.error(f"[ModsTab/Enable] [{mod_id}] Не удалось включить мод.")
                else:
                    logger.info(f"[ModsTab/Enable] Мод {mod_id} включён.")
            except Exception as e:
                success = False
                logger.error(f"[ModsTab/Enable] [{mod_id}] Ошибка: {e}")
                wx.MessageBox(_("system.enable_mod_error", mod_id=mod_id, error=e), _("messages.error"), wx.OK | wx.ICON_ERROR)
        return success

    def _disable_mod(self, mod_ids: List[str]) -> bool:
        if not self or not self.current_game: return False
        success = True
        for mod_id in mod_ids:
            try:
                if not self.mod_manager.disable_mod(self.current_game.steam_id, mod_id):
                    success = False
                    logger.error(f"[ModsTab/Disable] [{mod_id}] Не удалось отключить мод.")
                else:
                    logger.info(f"[ModsTab/Disable] Мод {mod_id} отключён.")
            except Exception as e:
                success = False
                logger.error(f"[ModsTab/Disable] [{mod_id}] Ошибка: {e}")
                wx.MessageBox(_("system.disable_mod_error", mod_id=mod_id, error=e), _("messages.error"), wx.OK | wx.ICON_ERROR)
        return success

    def _remove_mod(self, mod_id: str) -> bool:
        if not self or not self.current_game: return False
        try:
            success = self.mod_manager.remove_mod(self.current_game.steam_id, mod_id)
            if success:
                logger.info(f"[ModsTab/Remove] Мод {mod_id} удалён.")
                self.mod_details.pop(mod_id, None)
                self.mod_versions.pop(mod_id, None)
                self.mod_images.pop(mod_id, None)
                if self.selected_mod_id == mod_id:
                    self._clear_mod_info()
            return success
        except Exception as e:
            logger.error(f"[ModsTab/Remove] [{mod_id}] Ошибка: {e}")
            wx.MessageBox(_("system.remove_mod_error", mod_id=mod_id, error=e), _("messages.error"), wx.OK | wx.ICON_ERROR)
            return False

    def _load_mod_versions(self):
        versions_file = Path("mod_versions.json")
        if versions_file.exists():
            try:
                with open(versions_file, 'r', encoding='utf-8') as f:
                    self.mod_versions = json.load(f)
                logger.info(f"[ModsTab/Versions] Загружено {len(self.mod_versions)} записей.")
            except Exception as e:
                logger.error(f"[ModsTab/Versions] Ошибка загрузки версий: {e}")
                self.mod_versions = {}
        else:
            self.mod_versions = {}

    def _save_mod_versions(self):
        try:
            with open("mod_versions.json", 'w', encoding='utf-8') as f:
                json.dump(self.mod_versions, f, ensure_ascii=False, indent=4)
            logger.debug("[ModsTab/Versions] Версии сохранены.")
        except Exception as e:
            logger.error(f"[ModsTab/Versions] Ошибка сохранения версий: {e}")

    def _show_names_loading_dialog(self, total: int):
        if not self: return
        try:
            if not self.names_dialog:
                # Защита от некорректных значений total
                safe_total = max(1, total)  # Минимум 1
                self.names_dialog = wx.ProgressDialog(
                    "Загрузка названий модов",
                    f"Загружено 0 из {total}...",
                    maximum=safe_total,
                    parent=self,
                    style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT
                )
            else:
                self.names_dialog.Update(0, f"Загружено 0 из {total}...")
        except Exception as e:
            logger.error(f"[ModsTab/NamesDialog] Ошибка создания диалога: {e}")

    def _update_names_loading_dialog(self, current: int, total: int, current_mod_id: str):
        if not self:
            return
        if self.names_aborted:
            self._hide_names_loading_dialog()
            return
        if not self.names_dialog:
            return
        try:
            # Убеждаемся, что current не превышает total
            safe_current = max(0, min(current, total))
            # Если total = 0, устанавливаем safe_current = 0
            if total <= 0:
                safe_current = 0
            
            # Обновляем диалог только если значение валидное
            if safe_current <= total:
                keep_going, skip = self.names_dialog.Update(safe_current, f"Загружено {current} из {total}...")
                if not keep_going:
                    logger.info("[ModsTab/NamesDialog] Загрузка названий прервана пользователем через диалог.")
                    self.names_aborted = True
                    self._hide_names_loading_dialog()
        except RuntimeError:
            pass
        except Exception as e:
            logger.error(f"[ModsTab/NamesDialog/Update] Ошибка обновления диалога: {e}")

    def _hide_names_loading_dialog(self):
        if not self: return
        try:
            if self.names_dialog:
                self.names_dialog.Destroy()
        except RuntimeError:
            pass
        except Exception as e:
            logger.error(f"[ModsTab/NamesDialog/Hide] Ошибка закрытия диалога: {e}")
        finally:
            self.names_dialog = None

    def _on_language_changed(self, lang_code: str):
        """Обработчик изменения языка"""
        logger.info(f"[ModsTab] Язык изменен на: {lang_code}")
        # Обновляем тексты UI
        self._update_ui_texts()
        
    def _update_ui_texts(self):
        """Обновляет все тексты в интерфейсе"""
        try:
            # Обновляем кнопки
            if hasattr(self, 'check_updates_btn'):
                self.check_updates_btn.SetLabel(self.language_manager.get_text("mod.check_updates"))
            if hasattr(self, 'update_all_btn'):
                self.update_all_btn.SetLabel(self.language_manager.get_text("mod.update_all"))
            
            # Обновляем заголовки панелей
            if hasattr(self, 'disabled_title'):
                disabled_count = self.disabled_list.GetItemCount() if self.disabled_list else 0
                self.disabled_title.SetLabel(f"{self.language_manager.get_text('mod.disabled_mods')} ({disabled_count})")
            if hasattr(self, 'enabled_title'):
                enabled_count = self.enabled_list.GetItemCount() if self.enabled_list else 0
                self.enabled_title.SetLabel(f"{self.language_manager.get_text('mod.enabled_mods')} ({enabled_count})")
            
            # Обновляем информацию о текущем моде
            if self.selected_mod_id:
                self._display_mod_info(self.selected_mod_id)
            else:
                self._clear_mod_info()
                
        except Exception as e:
            logger.error(f"[ModsTab] Ошибка обновления текстов UI: {e}")

    def _on_mods_updated_event(self, game_steam_id: str):
        if not self: return
        if self.current_game and self.current_game.steam_id == game_steam_id:
            logger.info("[ModsTab] Получено событие mods_updated, перезагрузка списка.")
            pass
        else:
            logger.debug(f"[ModsTab] mods_updated событие для другой игры или игра не выбрана.")

    def Destroy(self):
        self.names_aborted = True
        self.loading_aborted = True
        # Очищаем подсветку зависимостей при закрытии
        self._clear_all_dependency_highlights()
        if HAS_EVENT_BUS and event_bus:
            event_bus.unsubscribe("mods_updated", self._on_mods_updated_event)
        self._hide_names_loading_dialog()
        return super().Destroy()
