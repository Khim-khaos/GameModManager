from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton

class DependencyDialog(QDialog):
    def __init__(self, dependencies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор зависимостей")
        self.layout = QVBoxLayout(self)
        self.dependencies = dependencies
        self.selected_dependencies = []

        self.label = QLabel("Этот мод имеет следующие зависимости. Выберите, какие установить:")
        self.layout.addWidget(self.label)

        self.dep_list = QListWidget()
        for dep in dependencies:
            self.dep_list.addItem(f"Мод ID: {dep}")
        self.dep_list.setSelectionMode(QListWidget.MultiSelection)
        self.layout.addWidget(self.dep_list)

        self.ok_button = QPushButton("ОК")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)

    def accept(self):
        self.selected_dependencies = [item.text().split("ID: ")[1] for item in self.dep_list.selectedItems()]
        super().accept()
