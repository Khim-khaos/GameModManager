from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import QProcess
from loguru import logger

class ConsoleTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.layout = QVBoxLayout(self)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.layout.addWidget(self.console_output)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)

    def update_game(self, game):
        self.console_output.clear()
        logger.info("Консоль очищена для новой игры")

    def handle_output(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8")
        self.console_output.append(data)
        logger.debug(f"SteamCMD вывод: {data}")

    def handle_error(self):
        data = self.process.readAllStandardError().data().decode("utf-8")
        self.console_output.append(f"<font color='red'>{data}</font>")
        logger.error(f"SteamCMD ошибка: {data}")
