from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel, QSplitter, QDialog, QTableWidget, QTableWidgetItem, QLineEdit
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QUrl, Slot, Qt, QThread, Signal
from PySide6.QtWebChannel import QWebChannel
from ui.dialogs.dependency_dialog import DependencyDialog, parse_dependencies
from loguru import logger
import requests
from bs4 import BeautifulSoup


# Класс для работы скачивания в отдельном потоке
class DownloadWorker(QThread):
    update_status = Signal(str, str, str)  # mod_id, mod_name, status
    finished = Signal()

    def __init__(self, download_manager):
        super().__init__()
        self.download_manager = download_manager

    def run(self):
        logger.debug("DownloadWorker: Начало работы потока")
        self.download_manager.start(self.update_status.emit)
        self.finished.emit()
        logger.debug("DownloadWorker: Работа потока завершена")


# Диалог для отображения статуса загрузки
class DownloadStatusDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("DownloadStatusDialog: Инициализация")
        self.setWindow needy to apply settings immediatelyTitle("Статус загрузки")
        self.setGeometry(100, 100, 600, 400)
        layout = QVBoxLayout()

        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["ID мода", "Название мода", "Статус"])
        self.status_table.setRowCount(0)
        self.status_table.horizontalHeader().setStretchLastSection(True)
        # Делаем таблицу прозрачной
        self.status_table.setAttribute(Qt.WA_TranslucentBackground, True)
        self.status_table.setStyleSheet("background: transparent; color: white;")
        layout.addWidget(self.status_table)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        # Делаем диалог прозрачным
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        logger.debug("DownloadStatusDialog: Инициализация завершена")

    def add_mod(self, mod_id, mod_name):
        row = self.status_table.rowCount()
        self.status_table.insertRow(row)
        self.status_table.setItem(row, 0, QTableWidgetItem(mod_id))
        self.status_table.setItem(row, 1, QTableWidgetItem(mod_name))
        self.status_table.setItem(row, 2, QTableWidgetItem("Скачивание..."))

    def update_status(self, mod_id, mod_name, status):
        logger.debug(f"DownloadStatusDialog: Обновление статуса для мода {mod_id}: {status}")
        for row in range(self.status_table.rowCount()):
            if self.status_table.item(row, 0).text() == mod_id:
                status_text = "Успешно" if status == "success" else "Ошибка" if status == "failed" else "Скачивание..."
                self.status_table.setItem(row, 2, QTableWidgetItem(status_text))
                break

    def enable_close(self):
        self.close_button.setEnabled(True)
        logger.debug("DownloadStatusDialog: Кнопка закрытия активирована")

    def closeEvent(self, event):
        logger.debug("DownloadStatusDialog: Закрытие диалога")
        event.accept()


# Кастомный QWebEnginePage для обработки ссылок
class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_url = "https://steamcommunity.com"

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        url_str = url.toString()
        logger.debug(f"Перехват навигации: {url_str}, тип: {navigation_type}, main_frame: {is_main_frame}")

        if navigation_type == QWebEnginePage.NavigationTypeLinkClicked:
            if url_str.startswith("/"):
                full_url = self.base_url + url_str
                logger.debug(f"Преобразован относительный URL: {url_str} -> {full_url}")
                self.setUrl(QUrl(full_url))
                return False

            if not url_str.startswith("https://steamcommunity.com"):
                logger.debug(f"Открываем внешнюю ссылку в системном браузере: {url_str}")
                QDesktopServices.openUrl(url)
                return False

            logger.debug(f"Разрешена навигация по ссылке: {url_str}")
            return True

        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)

    def certificateError(self, error):
        logger.warning(f"Ошибка сертификата: {error.errorDescription()}")
        return True


class BrowserTab(QWidget):
    def __init__(self, parent, mod_manager):
        super().__init__(parent)
        self.parent = parent
        self.mod_manager = mod_manager
        self.selected_game = None
        self.mod_names_cache = {}
        self.skip_installed = False  # Флаг для пропуска всех установленных модов
        self.init_ui()

    def init_ui(self):
        # Делаем основной виджет прозрачным
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout()

        self.game_label = QLabel("Текущая игра: не выбрана")
        self.game_label.setFixedHeight(30)
        self.game_label.setStyleSheet("color: white;")
        layout.addWidget(self.game_label)

        # Панель навигации
        nav_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL и нажмите Enter...")
        self.url_input.returnPressed.connect(self.load_url)
        self.url_input.setStyleSheet("background: rgba(255, 255, 255, 50); color: white; border: 1px solid gray;")
        nav_layout.addWidget(self.url_input)

        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        nav_layout.addWidget(self.back_button)

        self.forward_button = QPushButton("Вперёд")
        self.forward_button.clicked.connect(self.go_forward)
        self.forward_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        nav_layout.addWidget(self.forward_button)

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.refresh_page)
        self.refresh_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        nav_layout.addWidget(self.refresh_button)

        layout.addLayout(nav_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setAttribute(Qt.WA_TranslucentBackground, True)
        splitter.setStyleSheet("background: transparent;")

        left_widget = QWidget()
        left_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout()
        self.queue_label = QLabel("Очередь загрузки:")
        self.queue_label.setStyleSheet("color: white;")
        left_layout.addWidget(self.queue_label)

        self.queue_list = QListWidget()
        self.queue_list.setMinimumWidth(200)
        self.queue_list.setMaximumWidth(400)
        self.queue_list.setWordWrap(True)
        self.queue_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.queue_list.itemDoubleClicked.connect(self.open_mod_page)
        self.queue_list.setAttribute(Qt.WA_TranslucentBackground, True)
        self.queue_list.setStyleSheet("background: rgba(255, 255, 255, 50); color: white; border: 1px solid gray;")
        left_layout.addWidget(self.queue_list)

        queue_buttons = QHBoxLayout()
        self.add_button = QPushButton("Добавить мод")
        self.add_button.clicked.connect(self.add_mod_to_queue)
        self.add_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        queue_buttons.addWidget(self.add_button)

        self.download_button = QPushButton("Скачать")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        queue_buttons.addWidget(self.download_button)

        self.remove_button = QPushButton("Удалить выбранные моды")
        self.remove_button.clicked.connect(self.remove_selected_from_queue)
        self.remove_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        queue_buttons.addWidget(self.remove_button)

        self.clear_button = QPushButton("Очистить очередь")
        self.clear_button.clicked.connect(self.clear_queue)
        self.clear_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        queue_buttons.addWidget(self.clear_button)

        # Кнопка для пропуска всех установленных модов
        self.skip_all_button = QPushButton("Пропускать установленные моды")
        self.skip_all_button.clicked.connect(self.toggle_skip_installed)
        self.skip_all_button.setStyleSheet("background: rgba(255, 255, 255, 50); color: white;")
        queue_buttons.addWidget(self.skip_all_button)

        left_layout.addLayout(queue_buttons)
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        self.browser = QWebEngineView()
        self.custom_page = CustomWebEnginePage(self.browser)
        self.browser.setPage(self.custom_page)
        self.browser.setAttribute(Qt.WA_TranslucentBackground, True)
        self.browser.setStyleSheet("background: transparent;")
        self.custom_page.setBackgroundColor(Qt.transparent)

        self.channel = QWebChannel(self.custom_page)
        self.custom_page.setWebChannel(self.channel)
        self.channel.registerObject("backend", self)
        self.browser.setUrl(QUrl("https://steamcommunity.com/workshop/"))
        self.browser.urlChanged.connect(self.update_url_input)
        splitter.addWidget(self.browser)

        splitter.setSizes([250, 800])
        layout.addWidget(splitter)

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
        logger.debug("BrowserTab: Инициализация завершена")

    def toggle_skip_installed(self):
        """Переключает режим пропуска всех установленных модов."""
        self.skip_installed = not self.skip_installed
        if self.skip_installed:
            self.skip_all_button.setText("Устанавливать все моды")
            logger.info("Включён режим пропуска установленных модов")
        else:
            self.skip_all_button.setText("Пропускать установленные моды")
            logger.info("Отключён режим пропуска установленных модов")

    def update_url_input(self, url):
        self.url_input.setText(url.toString())

    def load_url(self):
        url = self.url_input.text()
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            self.browser.setUrl(QUrl(url))
            logger.info(f"BrowserTab: Загрузка URL: {url}")
        else:
            logger.warning("BrowserTab: URL не указан")

    def go_back(self):
        self.browser.back()
        logger.debug("BrowserTab: Назад")

    def go_forward(self):
        self.browser.forward()
        logger.debug("BrowserTab: Вперёд")

    def refresh_page(self):
        self.browser.reload()
        logger.debug("BrowserTab: Обновить страницу")

    def update_ui_texts(self):
        self.add_button.setText("Добавить мод")
        self.download_button.setText("Скачать")
        self.remove_button.setText("Удалить выбранные моды")
        self.clear_button.setText("Очистить очередь")
        self.skip_all_button.setText(
            "Пропускать установленные моды" if not self.skip_installed else "Устанавливать все моды")
        self.queue_label.setText("Очередь загрузки:")
        if self.selected_game:
            game = self.parent.game_manager.get_game(self.selected_game)
            self.game_label.setText(
                f"Текущая игра: {game['name']} ({self.selected_game})" if game else "Текущая игра: не выбрана")
        else:
            self.game_label.setText("Текущая игра: не выбрана")

        # Принудительно обновляем виджеты
        self.update()
        self.repaint()
        self.game_label.update()
        self.game_label.repaint()
        self.url_input.update()
        self.url_input.repaint()
        self.back_button.update()
        self.back_button.repaint()
        self.forward_button.update()
        self.forward_button.repaint()
        self.refresh_button.update()
        self.refresh_button.repaint()
        self.queue_label.update()
        self.queue_label.repaint()
        self.queue_list.update()
        self.queue_list.repaint()
        self.add_button.update()
        self.add_button.repaint()
        self.download_button.update()
        self.download_button.repaint()
        self.remove_button.update()
        self.remove_button.repaint()
        self.clear_button.update()
        self.clear_button.repaint()
        self.skip_all_button.update()
        self.skip_all_button.repaint()
        self.browser.update()
        self.browser.repaint()

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
        if mod_id in self.mod_names_cache:
            return self.mod_names_cache[mod_id]
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
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
        mod_name = self.get_mod_name(mod_id)

        # Проверяем, установлен ли мод
        installed_mods = self.mod_manager.get_installed_mods(self.selected_game)
        if mod_id in installed_mods:
            if self.skip_installed:
                logger.info(
                    f"Мод {mod_name}-{mod_id} уже установлен, пропущен из-за настройки 'Пропускать установленные моды'")
                return  # Пропускаем мод, если включён режим пропуска установленных

            # Показываем диалог с выбором
            reply = QMessageBox.question(
                self, "Мод уже установлен",
                f"Мод '{mod_name}-{mod_id}' уже установлен.\n"
                "Вы хотите обновить его (перезаписать текущую версию)?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                logger.info(f"Мод {mod_name}-{mod_id} уже установлен, пользователь выбрал пропустить")
                return  # Пропускаем мод
            elif reply == QMessageBox.Cancel:
                logger.info(f"Мод {mod_name}-{mod_id} уже установлен, пользователь отменил добавление")
                return  # Отменяем добавление
            else:
                logger.info(f"Мод {mod_name}-{mod_id} уже установлен, пользователь выбрал обновить")

        # Добавляем мод в очередь, если он ещё не добавлен
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

        # Проверяем зависимости
        dependencies = parse_dependencies(mod_id)
        if dependencies:
            dialog = DependencyDialog(self, mod_id, dependencies)
            if dialog.exec():
                selected_deps = dialog.get_selected_dependencies()
                for dep_id in selected_deps:
                    dep_name = self.get_mod_name(dep_id)
                    # Проверяем, установлена ли зависимость
                    if dep_id in installed_mods and self.skip_installed:
                        logger.info(
                            f"Зависимость {dep_name}-{dep_id} уже установлена, пропущена из-за настройки 'Пропускать установленные моды'")
                        continue

                    if dep_id in installed_mods:
                        reply = QMessageBox.question(
                            self, "Зависимость уже установлена",
                            f"Зависимость '{dep_name}-{dep_id}' уже установлена.\n"
                            "Вы хотите обновить её (перезаписать текущую версию)?",
                            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                            QMessageBox.No
                        )
                        if reply == QMessageBox.No:
                            logger.info(
                                f"Зависимость {dep_name}-{dep_id} уже установлена, пользователь выбрал пропустить")
                            continue
                        elif reply == QMessageBox.Cancel:
                            logger.info(
                                f"Зависимость {dep_name}-{dep_id} уже установлена, пользователь отменил добавление")
                            continue
                        else:
                            logger.info(
                                f"Зависимость {dep_name}-{dep_id} уже установлена, пользователь выбрал обновить")

                    if (self.selected_game, dep_id) not in self.mod_manager.download_queue:
                        self.mod_manager.add_to_queue(self.selected_game, dep_id)
                        logger.info(
                            f"Зависимость {dep_name}-{dep_id} добавлена в очередь для игры {self.selected_game}")
                    else:
                        reply = QMessageBox.question(self, "Дубликат зависимости",
                                                     f"Зависимость '{dep_name}-{dep_id}' уже в очереди. Уверены, что хотите её добавить снова?",
                                                     QMessageBox.Yes | QMessageBox.No)
                        if reply == QMessageBox.Yes:
                            self.mod_manager.add_to_queue(self.selected_game, dep_id)
                            logger.info(
                                f"Зависимость {dep_name}-{dep_id} добавлена повторно в очередь для игры {self.selected_game}")
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

        self.status_dialog = DownloadStatusDialog(self)
        for app_id, mod_id in self.mod_manager.download_queue:
            mod_name = self.get_mod_name(mod_id)
            self.status_dialog.add_mod(mod_id, mod_name)
        self.status_dialog.show()

        self.download_worker = DownloadWorker(self.parent.download_manager)
        self.download_worker.update_status.connect(self.status_dialog.update_status)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()
        logger.debug("BrowserTab: Запущен DownloadWorker")

    def on_download_finished(self):
        self.status_dialog.enable_close()
        self.update_queue()
        logger.info("Все загрузки завершены")

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
            item_to_remove = (app_id, mod_id)
            if item_to_remove in self.mod_manager.download_queue:
                self.mod_manager.download_queue.remove(item_to_remove)
                logger.info(f"Мод {mod_name}-{mod_id} удалён из очереди для игры {app_id}")
            else:
                logger.warning(f"Мод {mod_name}-{mod_id} для игры {app_id} не найден в очереди")
        self.update_queue()

    def open_mod_page(self, item):
        text = item.text()
        mod_id = text.split("-")[1].split(" для игры")[0]
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        self.browser.setUrl(QUrl(url))
        logger.info(f"Открыта страница мода {mod_id}: {url}")

    def clear_queue(self):
        self.mod_manager.download_queue.clear()
        self.update_queue()
        logger.info("Очередь загрузки очищена")
