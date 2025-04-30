from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QComboBox, QLabel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger
import os


class LogFileHandler(FileSystemEventHandler):
    """Обработчик изменений файла логов."""

    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith("app.log"):
            self.callback()


class LogsTab(QWidget):
    """Вкладка для отображения и фильтрации логов программы."""

    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.layout = QVBoxLayout(self)

        # Фильтр логов
        self.filter_label = QLabel(self.main_window.language_manager.get("log_filter", "Фильтр логов:"))
        self.layout.addWidget(self.filter_label)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "INFO", "ERROR", "DEBUG"])
        self.filter_combo.currentTextChanged.connect(self.update_logs)
        self.layout.addWidget(self.filter_combo)

        # Вывод логов
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)

        # Настройка наблюдателя за логами
        self.observer = Observer()
        self.event_handler = LogFileHandler(self.update_logs)
        self.observer.schedule(self.event_handler, path="Logs", recursive=False)
        self.observer.start()
        self.update_logs()

    def update_logs(self):
        """Обновляет отображаемые логи с учетом выбранного фильтра."""
        log_file = "Logs/app.log"
        filter_level = self.filter_combo.currentText()
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.readlines()
                filtered_logs = []
                for log in logs:
                    if filter_level == "Все" or filter_level in log:
                        filtered_logs.append(log)
                self.log_output.setText("".join(filtered_logs))
            logger.debug(f"Логи обновлены с фильтром: {filter_level}")

    def __del__(self):
        """Останавливает наблюдатель при уничтожении объекта."""
        self.observer.stop()
        self.observer.join()
