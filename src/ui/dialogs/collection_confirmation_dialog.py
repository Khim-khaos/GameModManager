# src/ui/dialogs/collection_confirmation_dialog.py
import wx
from loguru import logger

class CollectionItem:
    """
    Вспомогательный класс для хранения данных об элементе списка модов из коллекции.
    """
    def __init__(self, mod, is_installed: bool):
        """
        :param mod: Объект Mod, представляющий мод из коллекции.
        :param is_installed: Булево значение, указывающее, установлен ли мод.
        """
        self.mod = mod
        self.is_installed = is_installed
        # По умолчанию включаем в очередь неустановленные моды.
        # Установленные моды пользователь может выбрать для переустановки.
        self.include = not is_installed

class CollectionConfirmationDialog(wx.Dialog):
    """
    Диалог для подтверждения установки модов из коллекции.
    Позволяет выбрать, какие моды добавить в очередь загрузки,
    с опциями пропустить установленные или переустановить их.
    """
    def __init__(self, parent, collection_id: str, mods_data: list): # Исправлено имя параметра
        """
        :param parent: Родительское окно.
        :param collection_id: ID коллекции.
        :param mods_data: Список словарей, каждый из которых содержит
                          ключи 'mod' (объект Mod) и 'is_installed' (bool).
        """
        # Убедимся, что список не пустой, чтобы избежать проблем с wx.Dialog
        if not mods_data:
            logger.warning(f"[CollectionDialog] Создание диалога с пустым списком модов для коллекции {collection_id}")
            # Можно показать сообщение и сразу закрыть, или обработать иначе
            # Для начала просто создадим пустой диалог

        super().__init__(parent, title=f"Моды из коллекции {collection_id}", size=(700, 500))
        self.collection_id = collection_id

        # Подготавливаем список модов с их статусом
        self.collection_items = [CollectionItem(data['mod'], data['is_installed']) for data in mods_data]

        self._create_ui()
        self._populate_list()

    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Пояснительный текст
        info_text = wx.StaticText(self, label=f"Выберите моды из коллекции {self.collection_id} для добавления в очередь загрузки:")
        main_sizer.Add(info_text, 0, wx.ALL, 10)

        # Список модов с чекбоксами (используем CheckListBox)
        self.check_list = wx.CheckListBox(self, choices=[], style=wx.LB_EXTENDED) # LB_EXTENDED для множественного выбора мышью
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
        """Заполняет список модами из коллекции и устанавливает состояние чекбоксов."""
        choices = []
        # Сначала формируем список строк для отображения
        for item in self.collection_items:
            status = " (Установлен)" if item.is_installed else " (Не установлен)"
            # Формат: "Название мода (ID: 123456789) (Статус)"
            choices.append(f"{item.mod.name} (ID: {item.mod.mod_id}){status}")

        # ЗАПОЛНЯЕМ СПИСОК ЭЛЕМЕНТАМИ
        self.check_list.Set(choices)

        # ТЕПЕРЬ, КОГДА ЭЛЕМЕНТЫ ДОБАВЛЕНЫ, УСТАНАВЛИВАЕМ СОСТОЯНИЕ ЧЕКБОКСОВ
        for i, item in enumerate(self.collection_items):
            if item.include:
                # Проверяем, что индекс действителен (на всякий случай)
                if i < self.check_list.GetCount():
                    self.check_list.Check(i, True)
                else:
                    logger.error(f"[CollectionDialog] Попытка установить чекбокс для недействительного индекса {i} при количестве элементов {self.check_list.GetCount()}")

    def _on_select_all(self, event):
        """Выбирает все моды."""
        for i in range(self.check_list.GetCount()):
            self.check_list.Check(i, True)

    def _on_deselect_all(self, event):
        """Снимает выбор со всех модов."""
        for i in range(self.check_list.GetCount()):
            self.check_list.Check(i, False)

    def _on_select_not_installed(self, event):
        """Выбирает только неустановленные моды."""
        self._on_deselect_all(None) # Сначала снимаем все
        for i, item in enumerate(self.collection_items):
            if not item.is_installed:
                # Проверяем, что индекс действителен
                if i < self.check_list.GetCount():
                    self.check_list.Check(i, True)
                else:
                    logger.error(f"[CollectionDialog/_on_select_not_installed] Попытка установить чекбокс для недействительного индекса {i}")

    def _on_select_installed(self, event):
        """Выбирает только установленные моды."""
        self._on_deselect_all(None) # Сначала снимаем все
        for i, item in enumerate(self.collection_items):
            if item.is_installed:
                # Проверяем, что индекс действителен
                if i < self.check_list.GetCount():
                    self.check_list.Check(i, True)
                else:
                    logger.error(f"[CollectionDialog/_on_select_installed] Попытка установить чекбокс для недействительного индекса {i}")

    def get_selected_mods(self) -> list:
        """
        Возвращает список объектов Mod, которые пользователь выбрал для добавления.
        :return: Список объектов src.models.mod.Mod.
        """
        selected_indices = self.check_list.GetCheckedItems()
        # Возвращаем оригинальные объекты Mod
        return [self.collection_items[i].mod for i in selected_indices]
