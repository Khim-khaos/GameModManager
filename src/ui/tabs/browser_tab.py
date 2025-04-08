from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel, QSplitter
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, QSize, Slot, Qt
from PySide6.QtWebChannel import QWebChannel
from ui.dialogs.dependency_dialog import DependencyDialog, parse_dependencies
from loguru import logger
import requests
from bs4 import BeautifulSoup

class BrowserTab(QWidget):
    def __init__(self, parent, mod_manager):
        super().__init__(parent)
        self.parent = parent
        self.mod_manager = mod_manager
        self.selected_game = None
        self.mod_names_cache = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Настраиваем game_label с минимальной высотой
        self.game_label = QLabel("Текущая игра: не выбрана")
        self.game_label.setFixedHeight(30)  # Ограничиваем высоту
        layout.addWidget(self.game_label)

        # Используем QSplitter для разделения очереди и браузера
        splitter = QSplitter(Qt.Horizontal)

        # Левый виджет для очереди
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        self.queue_label = QLabel("Очередь загрузки:")
        left_layout.addWidget(self.queue_label)
        self.queue_list = QListWidget()
        self.queue_list.setMinimumWidth(200)
        self.queue_list.setMaximumWidth(400)
        self.queue_list.setWordWrap(True)  # Включаем перенос текста
        self.queue_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.queue_list.itemDoubleClicked.connect(self.open_mod_page)
        left_layout.addWidget(self.queue_list)

        queue_buttons = QHBoxLayout()
        self.add_button = QPushButton("Добавить мод")
        self.add_button.clicked.connect(self.add_mod_to_queue)
        queue_buttons.addWidget(self.add_button)

        self.download_button = QPushButton("Скачать")
        self.download_button.clicked.connect(self.start_download)
        queue_buttons.addWidget(self.download_button)

        self.remove_button = QPushButton("Удалить выбранные моды")
        self.remove_button.clicked.connect(self.remove_selected_from_queue)
        queue_buttons.addWidget(self.remove_button)

        self.clear_button = QPushButton("Очистить очередь")
        self.clear_button.clicked.connect(self.clear_queue)
        queue_buttons.addWidget(self.clear_button)

        left_layout.addLayout(queue_buttons)
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # Браузер
        self.browser = QWebEngineView()
        self.channel = QWebChannel(self.browser.page())
        self.browser.page().setWebChannel(self.channel)
        self.channel.registerObject("backend", self)
        self.browser.setUrl(QUrl("https://steamcommunity.com/workshop/"))
        splitter.addWidget(self.browser)

        # Устанавливаем начальные размеры (больше места для браузера)
        splitter.setSizes([250, 800])  # 250 для очереди, 800 для браузера
        layout.addWidget(splitter)

        # JavaScript для кнопки добавления мода
        script = """
        var button = document.createElement("button");
        button.innerText = "Добавить мод в GameModManager";
        button.onclick = function() {
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    channel.objects.backend.addModToQueue();
                });
            }
        };
        document.body.appendChild(button);
        """
        self.browser.page().runJavaScript(script)

        self.setLayout(layout)

    def update_ui_texts(self):
        self.add_button.setText("Добавить мод")
        self.download_button.setText("Скачать")
        self.remove_button.setText("Удалить выбранные моды")
        self.clear_button.setText("Очистить очередь")
        self.queue_label.setText("Очередь загрузки:")
        if self.selected_game:
            game = self.parent.game_manager.get_game(self.selected_game)
            self.game_label.setText(f"Текущая игра: {game['name']} ({self.selected_game})" if game else "Текущая игра: не выбрана")
        else:
            self.game_label.setText("Текущая игра: не выбрана")

    def set_game(self, app_id):
        self.selected_game = app_id
        game = self.parent.game_manager.get_game(app_id)
        if game:
            self.game_label.setText(f"Текущая игра: {game['name']} ({app_id})")
            workshop_url = f"https://steamcommunity.com/app/{app_id}/workshop/"
            self.browser.setUrl(QUrl(workshop_url))
            logger.info(f"Выбрана игра с ID {app_id}, открыт URL: {workshop_url}")
        else:
            self.game_label.setText("Текущая игра: не выбрана")
            logger.warning(f"Игра с ID {app_id} не найдена")

    @Slot()
    def add_mod_to_queue(self):
        if not self.selected_game:
            logger.warning("Игра не выбрана для добавления мода")
            QMessageBox.warning(self, "Ошибка", "Сначала выберите игру во вкладке 'Игры' или сверху!")
            return
        mod_id = self.get_mod_id_from_url(self.browser.url().toString())
        if mod_id:
            self.add_mod_with_dependencies(mod_id)
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

    def get_mod_name(self, mod_id):
        """Получаем название мода из Steam Workshop с кэшированием."""
        if mod_id in self.mod_names_cache:
            return self.mod_names_cache[mod_id]
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(url, timeout=5, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("div", class_="workshopItemTitle")
            name = title.text.strip() if title else f"Мод {mod_id}"
            self.mod_names_cache[mod_id] = name
            return name
        except Exception as e:
            logger.error(f"Ошибка при получении названия мода {mod_id}: {e}")
            return f"Мод {mod_id}"

    def add_mod_with_dependencies(self, mod_id):
        """Добавляет мод и предлагает установить зависимости с проверкой дубликатов."""
        mod_name = self.get_mod_name(mod_id)
        if (self.selected_game, mod_id) not in self.mod_manager.download_queue:
            self.mod_manager.add_to_queue(self.selected_game, mod_id)
            self.update_queue()
            logger.info(f"Мод {mod_name}-{mod_id} добавлен в очередь для игры {self.selected_game}")
        else:
            reply = QMessageBox.question(self, "Дубликат мода",
                                         f"Мод '{mod_name}-{mod_id}' уже в очереди. Уверены, что хотите его добавить снова?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.mod_manager.add_to_queue(self.selected_game, mod_id)
                self.update_queue()
                logger.info(f"Мод {mod_name}-{mod_id} добавлен повторно в очередь для игры {self.selected_game}")
            elif reply == QMessageBox.No:
                logger.info(f"Мод {mod_name}-{mod_id} не добавлен повторно в очередь")

        dependencies = parse_dependencies(mod_id)
        if dependencies:
            dialog = DependencyDialog(self, mod_id, dependencies)
            if dialog.exec():
                selected_deps = dialog.get_selected_dependencies()
                for dep_id in selected_deps:
                    dep_name = self.get_mod_name(dep_id)
                    if (self.selected_game, dep_id) not in self.mod_manager.download_queue:
                        self.mod_manager.add_to_queue(self.selected_game, dep_id)
                        logger.info(f"Зависимость {dep_name}-{dep_id} добавлена в очередь для игры {self.selected_game}")
                    else:
                        reply = QMessageBox.question(self, "Дубликат зависимости",
                                                     f"Зависимость '{dep_name}-{dep_id}' уже в очереди. Уверены, что хотите её добавить снова?",
                                                     QMessageBox.Yes | QMessageBox.No)
                        if reply == QMessageBox.Yes:
                            self.mod_manager.add_to_queue(self.selected_game, dep_id)
                            logger.info(f"Зависимость {dep_name}-{dep_id} добавлена повторно в очередь для игры {self.selected_game}")
                        else:
                            logger.info(f"Зависимость {dep_name}-{dep_id} не добавлена повторно в очередь")
                self.update_queue()

    def update_queue(self):
        self.queue_list.clear()
        for app_id, mod_id in self.mod_manager.download_queue:
            mod_name = self.get_mod_name(mod_id)
            self.queue_list.addItem(f"{mod_name}-{mod_id} для игры {app_id}")
        logger.debug(f"Очередь обновлена: {self.mod_manager.download_queue}")

    def start_download(self):
        if not self.mod_manager.download_queue:
            QMessageBox.warning(self, "Ошибка", "Очередь загрузки пуста!")
            return
        logger.info("Начата загрузка модов из очереди")
        failed_mods = []
        for app_id, mod_id in self.mod_manager.download_queue[:]:  # Копируем очередь
            mod_name = self.get_mod_name(mod_id)
            success = self.parent.download_manager.steam_handler.download_mod(app_id, mod_id)
            if success:
                self.mod_manager.download_queue.remove((app_id, mod_id))
                self.update_queue()
                QMessageBox.information(self, "Успех", f"Мод {mod_name}-{mod_id} успешно скачан!")
            else:
                failed_mods.append(f"{mod_name}-{mod_id}")
        if failed_mods:
            QMessageBox.warning(self, "Ошибка", f"Не удалось скачать следующие моды:\n{', '.join(failed_mods)}\nПодробности в failed_downloads.txt")
        else:
            QMessageBox.information(self, "Успех", "Все моды успешно скачаны!")

    def remove_selected_from_queue(self):
        selected_items = self.queue_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите моды для удаления из очереди!")
            return
        for item in selected_items:
            text = item.text()
            mod_id = text.split("-")[1].split(" для игры")[0]
            app_id = text.split("для игры ")[1]
            mod_name = text.split("-")[0]
            self.mod_manager.download_queue.remove((app_id, mod_id))
            logger.info(f"Мод {mod_name}-{mod_id} удалён из очереди для игры {app_id}")
        self.update_queue()

    def open_mod_page(self, item):
        """Открывает страницу мода при двойном клике."""
        text = item.text()
        mod_id = text.split("-")[1].split(" для игры")[0]
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        self.browser.setUrl(QUrl(url))
        logger.info(f"Открыта страница мода {mod_id}: {url}")

    def clear_queue(self):
        self.mod_manager.download_queue.clear()
        self.update_queue()
        logger.info("Очередь загрузки очищена")
