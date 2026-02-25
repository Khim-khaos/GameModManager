# src/ui/dialogs/dependency_confirmation_dialog.py
import wx
# Импорт логгера для отладки, если нужно
# from loguru import logger

class DependencyItem:
    """Вспомогательный класс для хранения данных об элементе списка зависимостей."""
    def __init__(self, mod_dependency):
        # Предполагается, что mod_dependency имеет атрибуты mod_id, name, is_installed
        # Это может быть объект ModDependency или временный объект с этими атрибутами
        self.mod_id = getattr(mod_dependency, 'mod_id', 'Unknown ID')
        self.name = getattr(mod_dependency, 'name', 'Unknown Name')
        self.is_installed = getattr(mod_dependency, 'is_installed', False)
        # По умолчанию включаем неустановленные зависимости
        self.include = not self.is_installed

class DependencyConfirmationDialog(wx.Dialog):
    """Диалог для подтверждения установки зависимостей мода."""
    def __init__(self, parent, main_mod, dependencies: list, installed_mod_ids: set):
        super().__init__(parent, title=f"Зависимости для '{getattr(main_mod, 'name', 'Unknown Mod')}'", size=(600, 400))
        self.main_mod = main_mod
        self.installed_mod_ids = installed_mod_ids

        # Подготавливаем список зависимостей с их статусом
        # Убедимся, что переданные зависимости имеют нужные атрибуты
        self.dependency_items = [DependencyItem(dep) for dep in dependencies]

        self._create_ui()
        self._populate_list()

    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Пояснительный текст
        mod_name = getattr(self.main_mod, 'name', 'Unknown Mod')
        info_text = wx.StaticText(self, label=f"Мод '{mod_name}' требует следующие зависимости:")
        main_sizer.Add(info_text, 0, wx.ALL, 10)

        # Список зависимостей с чекбоксами (используем CheckListBox)
        self.check_list = wx.CheckListBox(self, choices=[], style=wx.LB_EXTENDED) # LB_EXTENDED для множественного выбора
        main_sizer.Add(self.check_list, 1, wx.ALL | wx.EXPAND, 10)

        # Кнопки для массового управления
        button_row_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.select_all_btn = wx.Button(self, label="Выбрать все")
        self.select_all_btn.Bind(wx.EVT_BUTTON, self._on_select_all)
        button_row_sizer.Add(self.select_all_btn, 0, wx.RIGHT, 5)

        self.deselect_all_btn = wx.Button(self, label="Снять все")
        self.deselect_all_btn.Bind(wx.EVT_BUTTON, self._on_deselect_all)
        button_row_sizer.Add(self.deselect_all_btn, 0, wx.RIGHT, 5)

        # --- Добавляем кнопки для специфических действий ---
        self.select_not_installed_btn = wx.Button(self, label="Выбрать неустановленные")
        self.select_not_installed_btn.Bind(wx.EVT_BUTTON, self._on_select_not_installed)
        button_row_sizer.Add(self.select_not_installed_btn, 0, wx.RIGHT, 5)

        self.select_installed_btn = wx.Button(self, label="Выбрать установленные")
        self.select_installed_btn.Bind(wx.EVT_BUTTON, self._on_select_installed)
        button_row_sizer.Add(self.select_installed_btn, 0, wx.RIGHT, 5)
        # ---------------------------------------------------

        main_sizer.Add(button_row_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 10)

        # Кнопки OK/Cancel
        ok_cancel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_cancel_sizer.AddStretchSpacer(1) # Отступ справа

        self.ok_btn = wx.Button(self, wx.ID_OK, label="Добавить")
        self.ok_btn.SetDefault()
        ok_cancel_sizer.Add(self.ok_btn, 0, wx.LEFT, 5)

        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, label="Отмена")
        ok_cancel_sizer.Add(self.cancel_btn, 0, wx.LEFT, 5)

        main_sizer.Add(ok_cancel_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(main_sizer)

    def _populate_list(self):
        """Заполняет список зависимостями и устанавливает состояние чекбоксов."""
        choices = []
        # Сначала формируем список строк для отображения
        for item in self.dependency_items:
            status = " (Установлен)" if item.is_installed else " (Не установлен)"
            # Формат: "Название мода (ID: 123456789) (Статус)"
            choices.append(f"{item.name} (ID: {item.mod_id}){status}")

        # ЗАПОЛНЯЕМ СПИСОК ЭЛЕМЕНТАМИ
        self.check_list.Set(choices)

        # ТЕПЕРЬ, КОГДА ЭЛЕМЕНТЫ ДОБАВЛЕНЫ, УСТАНАВЛИВАЕМ СОСТОЯНИЕ ЧЕКБОКСОВ
        for i, item in enumerate(self.dependency_items):
            # Проверяем, что индекс действителен (на всякий случай)
            if i < self.check_list.GetCount():
                if item.include:
                    self.check_list.Check(i, True)
            # else:
            # logger.error если нужно отладить

    def _on_select_all(self, event):
        """Выбирает все зависимости."""
        for i in range(self.check_list.GetCount()):
            self.check_list.Check(i, True)

    def _on_deselect_all(self, event):
        """Снимает выбор со всех зависимостей."""
        for i in range(self.check_list.GetCount()):
            self.check_list.Check(i, False)

    def _on_select_not_installed(self, event):
        """Выбирает только неустановленные зависимости."""
        self._on_deselect_all(None) # Сначала снимаем все
        for i, item in enumerate(self.dependency_items):
            if not item.is_installed:
                # Проверяем, что индекс действителен
                if i < self.check_list.GetCount():
                    self.check_list.Check(i, True)
                # else:
                # logger.error если нужно отладить

    def _on_select_installed(self, event):
        """Выбирает только установленные зависимости."""
        self._on_deselect_all(None) # Сначала снимаем все
        for i, item in enumerate(self.dependency_items):
            if item.is_installed:
                # Проверяем, что индекс действителен
                if i < self.check_list.GetCount():
                    self.check_list.Check(i, True)
                # else:
                # logger.error если нужно отладить

    def get_selected_dependencies(self) -> list:
        """
        Возвращает список DependencyItem, которые пользователь выбрал для добавления.
        :return: Список DependencyItem.
        """
        selected_indices = self.check_list.GetCheckedItems()
        # Возвращаем оригинальные DependencyItem
        return [self.dependency_items[i] for i in selected_indices]
