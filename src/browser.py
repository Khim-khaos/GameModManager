from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, pyqtSignal

class Browser(QWidget):
    url_changed = pyqtSignal(QUrl)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWebEngineView()
        self.page = CustomWebEnginePage(self.view)
        self.view.setPage(self.page)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

        self.page.urlChanged.connect(self.on_url_changed)

    def load_url(self, url):
        self.view.load(QUrl(url))

    def on_url_changed(self, url):
        self.url_changed.emit(url)

class CustomWebEnginePage(QWebEnginePage):
    urlChanged = pyqtSignal(QUrl)

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok:
            self.urlChanged.emit(self.url())
