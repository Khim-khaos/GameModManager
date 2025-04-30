from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QMessageBox, QLabel, \
    QFileDialog, QSplitter, QScrollArea
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from core.game_manager import GameManager
from loguru import logger
import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
from io import BytesIO


class GamesTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.game_manager = GameManager()
        self.mod_info_cache = {}
        self.mod_images_cache = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Главный сплиттер: слева информация о моде, справа список модов
        splitter = QSplitter(Qt.Horizontal)

        # Левая часть: информация о моде
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # Изображение мода
        self.mod_image_label = QLabel()
        self.mod_image_label.setAlignment(Qt.AlignCenter)
        self.mod_image_label.setMinimumSize(300, 200)
        self.mod_image_label.setMaximumSize(600, 400)
        left_layout.addWidget(self.mod_image_label)

        # Информация о моде
        self.mod_info_label = QLabel("Информация о моде: выберите мод")
        left_layout.addWidget(self.mod_info_label)

        self.mod_author_label = QLabel("Автор: -")
        left_layout.addWidget(self.mod_author_label)

        self.mod_update_date_label = QLabel("Последнее обновление: -")
        left_layout.addWidget(self.mod_update_date_label)

        self.mod_dependencies_label = QLabel("Зависимости:")
        left_layout.addWidget(self.mod_dependencies_label)

        self.dependencies_list = QListWidget()
        self.dependencies_list.setMaximumHeight(150)
        left_layout.addWidget(self.dependencies_list)

        self.mod_installed_deps_label = QLabel("Установленные зависимости:")
        left_layout.addWidget(self.mod_installed_deps_label)

        self.installed_deps_list = QListWidget()
        self.installed_deps_list.setMaximumHeight(150)
        left_layout.addWidget(self.installed_deps_list)

        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # Правая часть: список модов
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        self.mods_label = QLabel("Установленные моды:")
        right_layout.addWidget(self.mods_label)

        self.mods_list = QListWidget()
        self.mods_list.setMinimumWidth(200)
        self.mods_list.setMaximumWidth(400)
        self.mods_list.setWordWrap(True)
        self.mods_list.itemClicked.connect(self.on_mod_selected)
        right_layout.addWidget(self.mods_list)

        # Кнопки управления модами
        button_layout = QHBoxLayout()

        self.refresh_mods_button = QPushButton("Обновить список модов")
        self.refresh_mods_button.clicked.connect(self.refresh_mods_list)
        button_layout.addWidget(self.refresh_mods_button)

        self.check_updates_button = QPushButton("Проверить обновления")
        self.check_updates_button.clicked.connect(self.check_updates)
        button_layout.addWidget(self.check_updates_button)

        self.export_button = QPushButton("Экспорт модов")
        self.export_button.clicked.connect(self.export_mods)
        button_layout.addWidget(self.export_button)

        self.import_button = QPushButton("Импорт модов")
        self.import_button.clicked.connect(self.import_mods)
        button_layout.addWidget(self.import_button)

        right_layout.addLayout(button_layout)
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        self.setLayout(layout)

        # Обновляем список модов при инициализации
        self.refresh_mods_list()

    def refresh_mods_list(self):
        """Обновляет список установленных модов."""
        if not self.parent.selected_game:
            self.mods_list.clear()
            self.clear_mod_info()
            return

        # Загружаем список модов только если это необходимо
        if self.parent.mod_manager.needs_refresh:
            self.parent.mod_manager._load_installed_mods()

        installed_mods = self.parent.mod_manager.get_installed_mods(self.parent.selected_game)
        logger.debug(f"Обновление списка модов для игры {self.parent.selected_game}: {installed_mods}")

        self.mods_list.clear()
        for mod_id in installed_mods:
            mod_name = self.get_mod_name(mod_id)
            self.mods_list.addItem(f"{mod_name}-{mod_id}")

    def update_ui_texts(self):
        """Обновляет текст интерфейса."""
        self.mods_label.setText("Установленные моды:")
        self.mod_info_label.setText("Информация о моде: выберите мод")
        self.mod_author_label.setText("Автор: -")
        self.mod_update_date_label.setText("Последнее обновление: -")
        self.mod_dependencies_label.setText("Зависимости:")
        self.mod_installed_deps_label.setText("Установленные зависимости:")
        self.refresh_mods_button.setText("Обновить список модов")
        self.check_updates_button.setText("Проверить обновления")
        self.export_button.setText("Экспорт модов")
        self.import_button.setText("Импорт модов")
        self.clear_mod_info()

    def get_mod_name(self, mod_id):
        """Получает название мода из Steam Workshop или возвращает ID."""
        mod_info = self.get_mod_info(mod_id)
        return mod_info.get("name", f"Мод {mod_id}")

    def get_mod_info(self, mod_id):
        """Получает информацию о моде (название, автор, дата обновления, зависимости, изображение)."""
        if mod_id in self.mod_info_cache:
            return self.mod_info_cache[mod_id]

        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, timeout=5, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            # Название мода
            title = soup.find("div", class_="workshopItemTitle")
            name = title.text.strip() if title else f"Мод {mod_id}"

            # Автор
            author = soup.find("div", class_="friendBlockContent")
            author_name = author.text.strip().split("\n")[0] if author else "Неизвестно"

            # Дата обновления
            date_div = soup.find("div", class_="detailsStatRight",
                                 string=lambda text: "Updated" in text if text else False)
            update_date = None
            if date_div:
                date_str = date_div.next_sibling.strip()
                try:
                    update_date = datetime.datetime.strptime(date_str, "%d %b, %Y @ %I:%M%p")
                except ValueError as e:
                    logger.error(f"Ошибка парсинга даты обновления для мода {mod_id}: {e}")

            # Зависимости
            dependencies = []
            dep_section = soup.find("div", class_="requiredItemsContainer")
            if dep_section:
                for link in dep_section.find_all("a"):
                    href = link.get("href", "")
                    if "id=" in href:
                        dep_id = href.split("id=")[1].split("&")[0]
                        dep_name = link.text.strip()
                        dependencies.append({"id": dep_id, "name": dep_name})

            # Изображение
            image_url = None
            image_div = soup.find("div", class_="workshopItemPreviewImageMain")
            if image_div:
                image_url = image_div.find("img").get("src")
                if image_url and image_url not in self.mod_images_cache:
                    image_response = requests.get(image_url, headers=headers)
                    image = QImage.fromData(image_response.content)
                    self.mod_images_cache[image_url] = QPixmap.fromImage(image)

            mod_info = {
                "name": name,
                "author": author_name,
                "update_date": update_date,
                "dependencies": dependencies,
                "image_url": image_url
            }
            self.mod_info_cache[mod_id] = mod_info
            return mod_info
        except Exception as e:
            logger.error(f"Ошибка при получении информации о моде {mod_id}: {e}")
            return {"name": f"Мод {mod_id}", "author": "Неизвестно", "update_date": None, "dependencies": [],
                    "image_url": None}

    def on_mod_selected(self, item):
        """Обновляет информацию о выбранном моде."""
        mod_id = item.text().split("-")[1].strip()
        mod_info = self.get_mod_info(mod_id)
        installed_mods = self.parent.mod_manager.get_installed_mods(self.parent.selected_game)

        # Обновляем информацию
        self.mod_info_label.setText(f"Информация о моде: {mod_info['name']} (ID: {mod_id})")
        self.mod_author_label.setText(f"Автор: {mod_info['author']}")
        self.mod_update_date_label.setText(
            f"Последнее обновление: {mod_info['update_date'].strftime('%d %b, %Y @ %I:%M%p') if mod_info['update_date'] else 'Неизвестно'}"
        )

        # Зависимости
        self.dependencies_list.clear()
        for dep in mod_info["dependencies"]:
            self.dependencies_list.addItem(f"{dep['name']} (ID: {dep['id']})")

        # Установленные зависимости
        self.installed_deps_list.clear()
        for dep in mod_info["dependencies"]:
            if dep["id"] in installed_mods:
                self.installed_deps_list.addItem(f"{dep['name']} (ID: {dep['id']})")

        # Изображение
        if mod_info["image_url"] and mod_info["image_url"] in self.mod_images_cache:
            pixmap = self.mod_images_cache[mod_info["image_url"]]
            scaled_pixmap = pixmap.scaled(self.mod_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.mod_image_label.setPixmap(scaled_pixmap)
        else:
            self.mod_image_label.clear()

    def clear_mod_info(self):
        """Очищает информацию о моде."""
        self.mod_info_label.setText("Информация о моде: выберите мод")
        self.mod_author_label.setText("Автор: -")
        self.mod_update_date_label.setText("Последнее обновление: -")
        self.dependencies_list.clear()
        self.installed_deps_list.clear()
        self.mod_image_label.clear()

    def check_updates(self):
        """Проверяет обновления для всех установленных модов."""
        if not self.parent.selected_game:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите игру!")
            return

        installed_mods = self.parent.mod_manager.get_installed_mods(self.parent.selected_game)
        if not installed_mods:
            QMessageBox.information(self, "Информация", "Нет установленных модов для проверки обновлений.")
            return

        mods_to_update = []
        for mod_id in installed_mods:
            mod_info = self.parent.mod_manager.get_installed_mod_info(self.parent.selected_game, mod_id)
            if not mod_info:
                continue

            installed_date = mod_info["installed_date"]
            mod_name = self.get_mod_name(mod_id)
            update_date = self.get_mod_update_date(mod_id)

            if update_date and update_date > installed_date:
                logger.info(
                    f"Для мода {mod_name}-{mod_id} найдено обновление: {datetime.datetime.fromtimestamp(update_date)}")
                mods_to_update.append((mod_id, mod_name))
            else:
                logger.debug(
                    f"Мод {mod_name}-{mod_id} актуален, дата обновления: {datetime.datetime.fromtimestamp(update_date) if update_date else 'неизвестно'}")

        if not mods_to_update:
            QMessageBox.information(self, "Результат проверки", "Все моды актуальны!")
            return

        # Показываем диалог с модами, которые можно обновить
        reply = QMessageBox.question(
            self, "Обновления найдены",
            f"Найдены обновления для следующих модов:\n" +
            "\n".join([f"{name}-{mod_id}" for mod_id, name in mods_to_update]) +
            "\n\nДобавить их в очередь для обновления?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for mod_id, mod_name in mods_to_update:
                if (self.parent.selected_game, mod_id) not in self.parent.mod_manager.download_queue:
                    self.parent.mod_manager.add_to_queue(self.parent.selected_game, mod_id)
                    logger.info(f"Мод {mod_name}-{mod_id} добавлен в очередь для обновления")
            self.parent.browser_tab.update_queue()
            QMessageBox.information(self, "Успех", "Моды добавлены в очередь для обновления!")
        else:
            logger.info("Пользователь отказался от обновления модов")

    def get_mod_update_date(self, mod_id):
        """Получает дату последнего обновления мода через парсинг страницы."""
        mod_info = self.get_mod_info(mod_id)
        update_date = mod_info.get("update_date")
        return update_date.timestamp() if update_date else None

    def export_mods(self):
        if not self.parent.selected_game:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для экспорта модов!")
            return

        installed_mods = []
        mods = self.parent.mod_manager.get_installed_mods(self.parent.selected_game)
        if not mods:
            QMessageBox.warning(self, "Предупреждение", "Для этой игры нет установленных модов!")
            return

        for mod_id in mods:
            mod_name = self.get_mod_name(mod_id)
            installed_mods.append({"app_id": self.parent.selected_game, "mod_id": mod_id, "mod_name": mod_name})

        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Выберите файл для экспорта модов",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not export_path:
            logger.info("Пользователь отменил выбор файла для экспорта")
            return

        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(installed_mods, f, indent=4, ensure_ascii=False)
            logger.info(f"Список модов для игры {self.parent.selected_game} экспортирован в {export_path}")
            QMessageBox.information(self, "Успех", f"Список модов экспортирован в {export_path}")
        except Exception as e:
            logger.error(f"Ошибка при экспорте модов: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать моды: {e}")

    def import_mods(self):
        if not self.parent.selected_game:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для импорта модов!")
            return

        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл для импорта модов",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not import_path:
            logger.info("Пользователь отменил выбор файла для импорта")
            return

        try:
            with open(import_path, "r", encoding="utf-8") as f:
                mods = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении файла импорта {import_path}: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл: {e}")
            return

        if not mods:
            QMessageBox.warning(self, "Ошибка", "Список модов пуст!")
            return

        mods_for_game = [mod for mod in mods if mod["app_id"] == self.parent.selected_game]
        if not mods_for_game:
            QMessageBox.warning(self, "Ошибка", "В файле нет модов для выбранной игры!")
            return

        mod_list = "\n".join([f"{mod['mod_name']} (ID: {mod['mod_id']})" for mod in mods_for_game])
        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите добавить следующие моды в очередь для игры {self.parent.selected_game}?\n\n{mod_list}",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            logger.info("Пользователь отменил импорт модов")
            return

        for mod in mods_for_game:
            app_id = mod["app_id"]
            mod_id = mod["mod_id"]
            if (app_id, mod_id) not in self.parent.mod_manager.download_queue:
                self.parent.mod_manager.add_to_queue(app_id, mod_id)
                logger.info(f"Мод {mod['mod_name']}-{mod_id} добавлен в очередь для игры {app_id}")
            else:
                logger.warning(f"Мод {mod['mod_name']}-{mod_id} уже в очереди для игры {app_id}")
        self.parent.browser_tab.update_queue()
        self.parent.mod_manager.needs_refresh = True  # Устанавливаем флаг, так как список модов изменится
        QMessageBox.information(self, "Успех", "Моды добавлены в очередь!")
