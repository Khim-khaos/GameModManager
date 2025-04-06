from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel, QDialog, QCheckBox, QDialogButtonBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, QSize, Slot
from PySide6.QtWebEngineCore import QWebEngineScript
from loguru import logger

class DependencyDialog(QDialog):
    def __init__(self, dependencies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Установка зависимостей")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Для этого мода требуются следующие зависимости. Установить их?"))
        self.checkboxes = {}
        for dep_id, dep_name in dependencies.items():
            cb = QCheckBox(f"{dep_name} (ID: {dep_id})")
            self.checkboxes[dep_id] = cb
            layout.addWidget(cb)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_selected(self):
        return [dep_id for dep_id, cb in self.checkboxes.items() if cb.isChecked()]

class BrowserTab(QWidget):
    def __init__(self, parent, mod_manager):
        super().__init__(parent)
        self.parent = parent
        self.mod_manager = mod_manager
        self.selected_game = None
        self.dependencies = {}  # Храним зависимости для текущего мода
        self.mod_names = {}    # Кэш имен модов
        self.init_ui()
        setup_webchannel(self)  # Настраиваем WebChannel при инициализации

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
        self.browser.loadFinished.connect(self.inject_add_button)
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

    def inject_add_button(self, ok):
        if not ok:
            logger.error("Ошибка загрузки страницы")
            return
        if "steamcommunity.com/sharedfiles/filedetails" in self.browser.url().toString():
            script = """
                var button = document.createElement('button');
                button.innerHTML = 'Добавить в список';
                button.style.position = 'fixed';
                button.style.top = '10px';
                button.style.right = '10px';
                button.style.zIndex = '1000';
                button.style.padding = '10px';
                button.style.backgroundColor = '#4CAF50';
                button.style.color = 'white';
                button.style.border = 'none';
                button.style.borderRadius = '5px';
                button.style.cursor = 'pointer';
                button.onclick = function() {
                    if (window.pywebchannel) {
                        window.pywebchannel.addToQueue();
                    } else {
                        console.log('pywebchannel не инициализирован');
                    }
                };
                document.body.appendChild(button);
            """
            self.browser.page().runJavaScript(script)
            logger.debug("Скрипт для кнопки внедрен")
            self.browser.page().toHtml(self.parse_dependencies)

    @Slot()
    def add_mod_to_queue(self):
        if not self.selected_game:
            logger.warning("Игра не выбрана для добавления мода")
            QMessageBox.warning(self, "Ошибка", "Сначала выберите игру во вкладке 'Игры' или сверху!")
            return
        mod_id = self.get_mod_id_from_url(self.browser.url().toString())
        if mod_id:
            # Сохраняем название мода, если оно известно
            mod_name = self.get_mod_name(mod_id)
            self.mod_names[mod_id] = mod_name
            self.add_mod_with_dependencies(mod_id)
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

    def get_mod_name(self, mod_id):
        # Если название уже есть в зависимостях или кэше
        if mod_id in self.dependencies:
            return self.dependencies[mod_id]
        if mod_id in self.mod_names:
            return self.mod_names[mod_id]
        # Если нет, пытаемся извлечь из текущей страницы
        def callback(html):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('div', class_='workshopItemTitle')
            if title:
                self.mod_names[mod_id] = title.text.strip()
                logger.debug(f"Извлечено название мода {mod_id}: {self.mod_names[mod_id]}")
            else:
                self.mod_names[mod_id] = f"Мод {mod_id}"
                logger.debug(f"Название мода {mod_id} не найдено, используется по умолчанию")
        self.browser.page().toHtml(callback)
        return self.mod_names.get(mod_id, f"Мод {mod_id}")

    def parse_dependencies(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        dependencies = {}
        description = soup.find('div', {'id': 'highlightContent'})
        if description:
            for link in description.find_all('a', href=True):
                if "steamcommunity.com/sharedfiles/filedetails/?id=" in link['href']:
                    dep_id = self.get_mod_id_from_url(link['href'])
                    if dep_id and dep_id not in dependencies:
                        dep_name = link.text.strip() or f"Мод {dep_id}"
                        dependencies[dep_id] = dep_name
        self.dependencies = dependencies
        logger.debug(f"Найденные зависимости: {dependencies}")

    def add_mod_with_dependencies(self, mod_id):
        self.mod_manager.add_to_queue(self.selected_game, mod_id)
        if self.dependencies:
            dialog = DependencyDialog(self.dependencies, self)
            if dialog.exec() == QDialog.Accepted:
                selected_deps = dialog.get_selected()
                for dep_id in selected_deps:
                    self.mod_names[dep_id] = self.dependencies[dep_id]  # Сохраняем название зависимости
                    self.mod_manager.add_to_queue(self.selected_game, dep_id)
                    logger.info(f"Зависимость {dep_id} добавлена в очередь для игры {self.selected_game}")

    def update_queue(self):
        self.queue_list.clear()
        for app_id, mod_id in self.mod_manager.download_queue:
            mod_name = self.get_mod_name(mod_id)
            display_text = f"{mod_name} ({app_id}) - {mod_id}"
            self.queue_list.addItem(display_text)
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

def setup_webchannel(widget):
    script = QWebEngineScript()
    script.setName("pywebchannel")
    script.setSourceCode("""
        new QWebChannel(qt.webChannelTransport, function(channel) {
            window.pywebchannel = channel.objects.pywebchannel;
        });
    """)
    script.setWorldId(QWebEngineScript.MainWorld)
    script.setInjectionPoint(QWebEngineScript.DocumentReady)
    widget.browser.page().scripts().insert(script)

    from PySide6.QtWebChannel import QWebChannel
    channel = QWebChannel(widget.browser.page())
    widget.browser.page().setWebChannel(channel)
    channel.registerObject("pywebchannel", widget)
