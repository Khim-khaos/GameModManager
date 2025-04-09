from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from loguru import logger

class ConsoleTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output)

        self.clear_button = QPushButton("Очистить консоль")
        self.clear_button.clicked.connect(self.clear_console)
        layout.addWidget(self.clear_button)

        self.setLayout(layout)

        # Подписка на логи
        logger.add(self.log_handler, format="{time} {level} {message}")

    def update_ui_texts(self):
        self.clear_button.setText("Очистить консоль")  # Можно добавить перевод

    def log_handler(self, message):
        self.console_output.append(message)

    def clear_console(self):
        self.console_output.clear()
        logger.info("Консоль очищена")

