import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog, QSlider, QMessageBox
from PySide6.QtCore import Qt, Signal  # Добавляем импорт Signal
from data.config import Config

class SettingsDialog(QDialog):
    settings_changed = Signal()  # Создаём сигнал для уведомления о изменении настроек

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.languages = self.config.get_available_languages()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Путь к SteamCMD
        layout.addWidget(QLabel(self.parent.tr("select_steamcmd")))
        self.steamcmd_input = QLineEdit(self.config.get("steamcmd_path"))
        browse_button = QPushButton("Обзор")
        browse_button.clicked.connect(self.browse_steamcmd)
        layout.addWidget(self.steamcmd_input)
        layout.addWidget(browse_button)

        # Выбор языка
        layout.addWidget(QLabel(self.parent.tr("language")))
        self.language_combo = QComboBox()
        self.language_map = {}
        for lang_file, lang_name in self.languages:
            self.language_combo.addItem(lang_name)
            self.language_map[lang_name] = lang_file
        current_language = self.config.get("language")
        for lang_file, lang_name in self.languages:
            if lang_file == current_language:
                self.language_combo.setCurrentText(lang_name)
                break
        layout.addWidget(self.language_combo)

        # Выбор темы
        layout.addWidget(QLabel(self.parent.tr("theme")))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.config.get("theme"))
        layout.addWidget(self.theme_combo)

        # Выбор заднего фона
        layout.addWidget(QLabel("Задний фон:"))
        self.background_input = QLineEdit(self.config.get("background_image") or "")
        background_browse = QPushButton("Обзор")
        background_browse.clicked.connect(self.browse_background)
        layout.addWidget(self.background_input)
        layout.addWidget(background_browse)

        # Прозрачность
        layout.addWidget(QLabel("Прозрачность (0.1 - 1.0):"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(10)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(float(self.config.get("opacity", 1.0)) * 100))
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_value_label = QLabel(f"{self.opacity_slider.value() / 100:.1f}")
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        layout.addWidget(self.opacity_slider)
        layout.addWidget(self.opacity_value_label)

        # Кнопка сохранения
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def browse_steamcmd(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать SteamCMD", "", "Исполняемые файлы (*.exe)")
        if path:
            self.steamcmd_input.setText(path)

    def browse_background(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение фона", "", "Изображения (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.background_input.setText(path)

    def update_opacity_label(self, value):
        self.opacity_value_label.setText(f"{value / 100:.1f}")

    def save_settings(self):
        steamcmd_path = self.steamcmd_input.text()
        if not steamcmd_path or not os.path.exists(steamcmd_path):
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, укажите корректный путь к SteamCMD (steamcmd.exe).")
            return

        selected_language_name = self.language_combo.currentText()
        selected_language_file = self.language_map.get(selected_language_name, "rus")

        self.config.set("steamcmd_path", steamcmd_path)
        self.config.set("language", selected_language_file)
        self.config.set("theme", self.theme_combo.currentText())
        self.config.set("background_image", self.background_input.text())
        self.config.set("opacity", self.opacity_slider.value() / 100)
        self.settings_changed.emit()  # Отправляем сигнал
        self.accept()
