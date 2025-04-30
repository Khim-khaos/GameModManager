from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QPushButton
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt
from qtawesome import icon
from core.mod_manager import ModManager
from loguru import logger


class DraggableListWidget(QListWidget):
    """Список с поддержкой drag-and-drop для очереди модов."""

    def __init__(self, mod_manager):
        super().__init__()
        self.mod_manager = mod_manager
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setAcceptDrops(True)
        self.model().rowsMoved.connect(self.update_queue)

    def update_queue(self):
        """Обновляет очередь модов после перетаскивания."""
        new_queue = []
        for i in range(self.count()):
            mod_id = self.item(i).text().split("ID: ")[1]
            for item in self.mod_manager.queue:
                if item["mod_id"] == mod_id:
                    new_queue.append(item)
        self.mod_manager.queue = new_queue
        logger.info("Очередь модов переупорядочена")


class BrowserTab(QWidget):
    """Вкладка браузера Steam Workshop и управления очередью модов."""

    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.mod_manager = ModManager()
        self.current_game = None
        self.layout = QHBoxLayout(self)

        # Очередь загрузки (слева)
        self.queue_layout = QVBoxLayout()
        self.queue_list = DraggableListWidget(self.mod_manager)
        self.add_to_queue_button = QPushButton(
            icon("fa5.plus"), self.main_window.language_manager.get("add_to_queue", "Добавить в очередь")
        )
        self.add_to_queue_button.clicked.connect(self.add_to_queue)
        self.clear_queue_button = QPushButton(
            icon("fa5.trash"), self.main_window.language_manager.get("clear_queue", "Очистить очередь")
        )
        self.clear_queue_button.clicked.connect(self.clear_queue)
        self.queue_layout.addWidget(self.queue_list)
        self.queue_layout.addWidget(self.add_to_queue_button)
        self.queue_layout.addWidget(self.clear_queue_button)
        self.layout.addLayout(self.queue_layout, 1)

        # Браузер (справа)
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("https://steamcommunity.com/workshop/"))
        self.layout.addWidget(self.web_view, 4)

    def update_game(self, game):
        """Обновляет браузер для выбранной игры."""
        self.current_game = game
        if game:
            workshop_url = f"https://steamcommunity.com/app/{game.app_id}/workshop/"
            self.web_view.setUrl(QUrl(workshop_url))
            self.queue_list.clear()
            logger.info(f"Обновлен браузер для игры: {game.name}")
        else:
            self.web_view.setUrl(QUrl("https://steamcommunity.com/workshop/"))
            self.queue_list.clear()

    def add_to_queue(self):
        """Добавляет мод в очередь загрузки."""
        if not self.current_game:
            logger.warning("Игра не выбрана")
            return
        current_url = self.web_view.url().toString()
        if "workshop" in current_url and "filedetails" in current_url:
            mod_id = current_url.split("id=")[-1]
            self.queue_list.addItem(f"Мод ID: {mod_id}")
            self.mod_manager.add_to_queue(self.current_game, mod_id)
            logger.info(f"Мод {mod_id} добавлен в очередь для игры {self.current_game.name}")

    def clear_queue(self):
        """Очищает очередь загрузки."""
        self.queue_list.clear()
        self.mod_manager.clear_queue()
        logger.info("Очередь очищена")
