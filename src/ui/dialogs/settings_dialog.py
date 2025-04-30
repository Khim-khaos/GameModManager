from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QSlider, \
    QMessageBox
from PySide6.QtCore import Qt
from qtawesome import icon
from loguru import logger


class SettingsDialog(QDialog):
    """Диалог для редактирования настроек приложения."""

    def __init__(self, settings_manager, language_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.language_manager = language_manager
        self.setWindowTitle(self.language_manager.get("settings", "Настройки"))
        self.layout = QVBoxLayout(self)

        # Путь до SteamCMD
        self.steamcmd_label = QLabel(self.language_manager.get("steamcmd_path", "Путь до steamcmd.exe:"))
        self.layout.addWidget(self.steamcmd_label)
        self.steamcmd_path = QLineEdit(self.settings_manager.settings.get("steamcmd_path", ""))
        self.steamcmd_browse = QPushButton(
            icon("fa5.folder-open"), self.language_manager.get("browse", "Обзор")
        )
        self.steamcmd_browse.clicked.connect(self.browse_steamcmd)
        self.layout.addWidget(self.steamcmd_path)
        self.layout.addWidget(self.steamcmd_browse)

        # Язык
        self.language_label = QLabel(self.language_manager.get("language", "Язык:"))
        self.layout.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["rus", "en"])
        self.language_combo.setCurrentText(self.settings_manager.settings.get("language", "rus"))
        self.layout.addWidget(self.language_combo)

        # Тема
        self.theme_label = QLabel(self.language_manager.get("theme", "Тема интерфейса:"))
        self.layout.addWidget(self.theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.settings_manager.settings.get("theme", "light"))
        self.layout.addWidget(self.theme_combo)

        # Фон
        self.background_label = QLabel(self.language_manager.get("background", "Фоновое изображение:"))
        self.layout.addWidget(self.background_label)
        self.background_path = QLineEdit(self.settings_manager.settings.get("background", ""))
        self.background_browse = QPushButton(
            icon("fa5.image"), self.language_manager.get("browse", "Обзор")
        )
        self.background_browse.clicked.connect(self.browse_background)
        self.layout.addWidget(self.background_path)
        self.layout.addWidget(self.background_browse)

        # Прозрачность
        self.opacity_label = QLabel(self.language_manager.get("opacity", "Прозрачность интерфейса:"))
        self.layout.addWidget(self.opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(self.settings_manager.settings.get("opacity", 1.0) * 100))
        self.layout.addWidget(self.opacity_slider)

        # Размер шрифта
        self.font_size_label = QLabel(self.language_manager.get("font_size", "Размер шрифта:"))
        self.layout.addWidget(self.font_size_label)
        self.font_size_input = QLineEdit(str(self.settings_manager.settings.get("font_size", 12)))
        self.layout.addWidget(self.font_size_input)

        # Кнопки
        self.save_button = QPushButton(
            icon("fa5.save"), self.language_manager.get("save", "Сохранить")
        )
        self.save_button.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_button)

    def browse_steamcmd(self):
        """Открывает диалог для выбора steamcmd.exe."""
        path, _ = QFileDialog.getOpenFileName(
            self, self.language_manager.get("select_steamcmd", "Выберите steamcmd.exe"), "", "Executables (*.exe)"
        )
        if path:
            self.steamcmd_path.setText(path)

    def browse_background(self):
        """Открывает диалог для выбора фонового изображения."""
        path, _ = QFileDialog.getOpenFileName(
            self, self.language_manager.get("select_background", "Выберите фоновое изображение"), "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.background_path.setText(path)

    def save_settings(self):
        """Сохраняет настройки."""
        try:
            self.settings_manager.settings.update({
                "steamcmd_path": self.steamcmd_path.text(),
                "language": self.language_combo.currentText(),
                "theme": self.theme_combo.currentText(),
                "background": self.background_path.text(),
                "opacity": self.opacity_slider.value() / 100.0,
                "font_size": int(self.font_size_input.text())
            })
            self.settings_manager.save_settings()
            self.accept()
        except ValueError as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            QMessageBox.warning(self, self.language_manager.get("error", "Ошибка"),
                                self.language_manager.get("invalid_font_size", "Введите корректный размер шрифта"))
