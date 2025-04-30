from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
from qtawesome import icon


class ModInfoDialog(QDialog):
    """Диалог для отображения информации о моде."""

    def __init__(self, mod_info, language_manager, parent=None):
        super().__init__(parent)
        self.language_manager = language_manager
        self.setWindowTitle(language_manager.get("mod_info", "Информация о моде"))
        self.layout = QVBoxLayout(self)

        # Название мода
        self.name_label = QLabel(f"{language_manager.get('mod_name', 'Название мода:')} {mod_info['name']}")
        self.layout.addWidget(self.name_label)

        # Описание мода
        self.description_label = QLabel(language_manager.get("mod_description", "Описание:"))
        self.layout.addWidget(self.description_label)
        self.description_text = QTextEdit(mod_info["description"])
        self.description_text.setReadOnly(True)
        self.layout.addWidget(self.description_text)

        # Зависимости
        self.dependencies_label = QLabel(language_manager.get("dependencies", "Зависимости:"))
        self.layout.addWidget(self.dependencies_label)
        dependencies = mod_info.get("dependencies", [])
        self.dependencies_text = QTextEdit(
            ", ".join(dependencies) if dependencies else language_manager.get("no_dependencies", "Нет зависимостей"))
        self.dependencies_text.setReadOnly(True)
        self.layout.addWidget(self.dependencies_text)

        # Кнопка закрытия
        self.close_button = QPushButton(icon("fa5.window-close"),
                                        language_manager.get("close", "Закрыть"))  # Исправлено
        self.close_button.clicked.connect(self.accept)
        self.layout.addWidget(self.close_button)
