# src/browser.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import pyqtSignal, QUrl
from bs4 import BeautifulSoup
import requests


class Browser(QWidget):
    add_mod_to_queue_requested = pyqtSignal(str)
    add_collection_to_queue_requested = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        # Панель управления браузером
        self.toolbar_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.go_button = QPushButton("Перейти")
        self.back_button = QPushButton("Назад")
        self.forward_button = QPushButton("Вперед")
        self.reload_button = QPushButton("Обновить")

        self.go_button.clicked.connect(self.load_url)
        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)
        self.reload_button.clicked.connect(self.reload_page)

        self.toolbar_layout.addWidget(self.back_button)
        self.toolbar_layout.addWidget(self.forward_button)
        self.toolbar_layout.addWidget(self.reload_button)
        self.toolbar_layout.addWidget(self.url_input)
        self.toolbar_layout.addWidget(self.go_button)

        self.layout.addLayout(self.toolbar_layout)

        # Веб-браузер
        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.update_url_input)
        self.web_view.page().profile().downloadRequested.connect(self.handle_download)
        self.web_view.page().urlChanged.connect(self.update_url_input)
        self.layout.addWidget(self.web_view)

        self.web_view.page().profile().setDownloadPath("./downloads")

        self.web_view.page().load(QUrl("https://steamcommunity.com/workshop/"))

    def load_url(self, url=None):
        if url is None:
            url = self.url_input.text()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        self.web_view.load(QUrl(url))

    def go_back(self):
        self.web_view.back()

    def go_forward(self):
        self.web_view.forward()

    def reload_page(self):
        self.web_view.reload()

    def update_url_input(self, url=None):
        if url is None:
            url = self.web_view.url()
        if isinstance(url, QUrl):
            self.url_input.setText(url.toString())

    def handle_download(self, download):
        download.accept()
        download.finished.connect(self.download_finished)

    def download_finished(self):
        print("Download finished")
        # Здесь можно добавить логику обработки завершения загрузки

    def contextMenuEvent(self, event):
        menu = self.web_view.page().createStandardContextMenu()

        hit_test_result = self.web_view.page().hitTest(event.pos())
        if hit_test_result and hit_test_result.linkUrl().isValid():
            url = hit_test_result.linkUrl().toString()
            if "/workshop/filedetails/?id=" in url:
                mod_id = url.split("?id=")[1]
                add_mod_action = menu.addAction("Добавить мод в очередь")
                add_mod_action.triggered.connect(lambda: self.add_mod_to_queue_requested.emit(mod_id))
            elif "/sharedfiles/filedetails/?id=" in url:
                collection_id = url.split("?id=")[1]
                add_collection_action = menu.addAction("Добавить коллекцию в очередь")
                add_collection_action.triggered.connect(lambda: self.add_collection_to_queue(collection_id))

        menu.exec_(event.globalPos())

    def add_collection_to_queue(self, collection_id):
        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            mod_links = soup.find_all('a', class_='ugc')
            mod_ids = []
            for link in mod_links:
                mod_url = link.get('href')
                if mod_url and "/workshop/filedetails/?id=" in mod_url:
                    mod_id = mod_url.split("?id=")[1]
                    mod_ids.append(mod_id)

            if mod_ids:
                self.add_collection_to_queue_requested.emit(mod_ids)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось найти моды в коллекции.")
        except requests.exceptions.RequestException as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при загрузке коллекции: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Неизвестная ошибка: {e}")
