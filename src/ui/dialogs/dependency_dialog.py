from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout
from loguru import logger
import requests
from bs4 import BeautifulSoup


class DependencyDialog(QDialog):
    def __init__(self, parent, mod_id, dependencies):
        super().__init__(parent)
        self.mod_id = mod_id
        self.dependencies = dependencies
        self.selected_dependencies = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Зависимости для мода {self.mod_id}")
        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"Для мода {self.mod_id} найдены следующие зависимости:"))
        self.dep_list = QListWidget()
        for dep_id, dep_name in self.dependencies:
            self.dep_list.addItem(f"{dep_name}-{dep_id}")
        self.dep_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.dep_list)

        # Кнопка "Выбрать все"
        select_all_button = QPushButton("Выбрать все")
        select_all_button.clicked.connect(self.select_all)
        layout.addWidget(select_all_button)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("Установить выбранные")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Пропустить")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_all(self):
        """Выбирает все элементы в списке зависимостей."""
        for i in range(self.dep_list.count()):
            self.dep_list.item(i).setSelected(True)

    def get_selected_dependencies(self):
        return [item.text().split("-")[1] for item in self.dep_list.selectedItems()]


def parse_dependencies(mod_id):
    """Парсит зависимости мода из секции 'Required Items' на Steam Workshop."""
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, timeout=5, headers=headers)
        if response.status_code != 200:
            logger.error(f"Ошибка HTTP {response.status_code} при запросе мода {mod_id}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        logger.debug(f"HTML страницы мода {mod_id} успешно загружен, длина: {len(response.text)} символов")

        required_items = soup.find("div", class_="requiredItemsContainer")
        if not required_items:
            logger.debug(f"Секция 'Required Items' для мода {mod_id} не найдена в HTML")
            return []

        dependencies = []
        for link in required_items.find_all("a", href=True):
            href = link["href"]
            logger.debug(f"Найдена ссылка в 'Required Items': {href}")
            if "steamcommunity.com/workshop/filedetails/?id=" in href or "steamcommunity.com/sharedfiles/filedetails/?id=" in href:
                try:
                    dep_id_part = href.split("id=")[1].split("&")[0]
                    dep_id = "".join(filter(str.isdigit, dep_id_part))
                    if dep_id and dep_id != mod_id:
                        dep_name = link.text.strip() or f"Мод {dep_id}"
                        dependencies.append((dep_id, dep_name))
                        logger.debug(f"Добавлена зависимость: {dep_name}-{dep_id}")
                except IndexError:
                    logger.debug(f"Неверный формат ссылки на зависимость: {href}")
                    continue

        if dependencies:
            logger.debug(f"Найдены зависимости для мода {mod_id} из 'Required Items': {dependencies}")
        else:
            logger.debug(f"Зависимости для мода {mod_id} в 'Required Items' не найдены, хотя ссылки присутствуют")
        return dependencies
    except Exception as e:
        logger.error(f"Ошибка при парсинге зависимостей мода {mod_id}: {e}")
        return []

