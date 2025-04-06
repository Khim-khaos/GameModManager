from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, QSize
from loguru import logger

class BrowserTab(QWidget):
    def __init__(self, parent, mod_manager):  # Добавлен параметр mod_manager
        super().__init__(parent)
        self.parent = parent
        self.mod_manager = mod_manager  # Используем переданный ModManager
        self.selected_game = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.game_label = QLabel("Текущая игра: не выбрана")
        layout.addWidget(self.game_label)

        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        self.queue_label = QLabel("Очередь загрузки:")
        left_layout.addWidget(self.queue_label)
        self.queue_list = QListWidget()
        self.queue_list.setMinimumWidth(200)
        self.queue_list.setMaximumWidth(300)
        self.queue_list.setMinimumHeight(100)
        left_layout.addWidget(self.queue_list)

        queue_buttons = QHBoxLayout()
        self.add_button = QPushButton("Добавить мод")
        self.add_button.clicked.connect(self.add_mod_to_queue)
        queue_buttons.addWidget(self.add_button)

        self.download_button = QPushButton("Скачать")
        self.download_button.clicked.connect(self.start_download)
        queue_buttons.addWidget(self.download_button)

        self.clear_button = QPushButton("Очистить очередь")
        self.clear_button.clicked.connect(self.clear_queue)
        queue_buttons.addWidget(self.clear_button)

        left_layout.addLayout(queue_buttons)
        content_layout.addLayout(left_layout)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://steamcommunity.com/workshop/"))
        content_layout.addWidget(self.browser)

        layout.addLayout(content_layout)
        self.setLayout(layout)

    def update_ui_texts(self):
        self.add_button.setText("Добавить мод")
        self.download_button.setText("Скачать")
        self.clear_button.setText("Очистить очередь")
        self.queue_label.setText("Очередь загрузки:")
        if self.selected_game:
            game = self.parent.game_manager.get_game(self.selected_game)
            self.game_label.setText(f"Текущая игра: {game['name']} (ID: {self.selected_game})" if game else "Текущая игра: не выбрана")
        else:
            self.game_label.setText("Текущая игра: не выбрана")

    def set_game(self, app_id):
        self.selected_game = app_id
        game = self.parent.game_manager.get_game(app_id)
        if game:
            self.game_label.setText(f"Текущая игра: {game['name']} (ID: {app_id})")
            workshop_url = f"https://steamcommunity.com/app/{app_id}/workshop/"
            self.browser.setUrl(QUrl(workshop_url))
            logger.info(f"Выбрана игра с ID {app_id}, открыт URL: {workshop_url}")
        else:
            self.game_label.setText("Текущая игра: не выбрана")
            logger.warning(f"Игра с ID {app_id} не найдена")

    def add_mod_to_queue(self):
        if not self.selected_game:
            logger.warning("Игра не выбрана для добавления мода")
            QMessageBox.warning(self, "Ошибка", "Сначала выберите игру во вкладке 'Игры' или сверху!")
            return
        mod_id = self.get_mod_id_from_url(self.browser.url().toString())
        if mod_id:
            self.mod_manager.add_to_queue(self.selected_game, mod_id)
            self.update_queue()
            logger.info(f"Мод {mod_id} добавлен в очередь для игры {self.selected_game}")
        else:
            logger.warning("Не удалось извлечь ID мода из URL")
            QMessageBox.warning(self, "Ошибка", "Перейдите на страницу мода в Steam Workshop с параметром id!")

    def get_mod_id_from_url(self, url):
        if "id=" in url:
            try:
                mod_id_part = url.split("id=")[1]
                mod_id = "".join(filter(str.isdigit, mod_id_part.split("&")[0]))
                if mod_id:
                    return mod_id
                else:
                    logger.error(f"ID мода не найден в URL: {url}")
                    return None
            except IndexError:
                logger.error(f"Неверный формат URL: {url}")
                return None
        logger.error(f"URL не содержит id: {url}")
        return None

    def update_queue(self):
        self.queue_list.clear()
        for app_id, mod_id in self.mod_manager.download_queue:
            self.queue_list.addItem(f"Мод {mod_id} для игры {app_id}")
        logger.debug(f"Очередь обновлена: {self.mod_manager.download_queue}")

    def start_download(self):
        if not self.mod_manager.download_queue:
            QMessageBox.warning(self, "Ошибка", "Очередь загрузки пуста!")
            return
        logger.info("Начата загрузка модов из очереди")
        self.parent.download_manager.start()

    def clear_queue(self):
        self.mod_manager.download_queue.clear()
        self.update_queue()
        logger.info("Очередь загрузки очищена")
