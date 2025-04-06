from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QHBoxLayout

class AddGameDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Добавить игру")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        layout.addWidget(QLabel("Название игры:"))
        layout.addWidget(self.name_input)

        # Путь к исполняемому файлу
        exe_layout = QHBoxLayout()
        self.exe_input = QLineEdit()
        exe_browse = QPushButton("Обзор")
        exe_browse.clicked.connect(self.browse_exe)
        exe_layout.addWidget(self.exe_input)
        exe_layout.addWidget(exe_browse)
        layout.addWidget(QLabel("Путь к исполняемому файлу:"))
        layout.addLayout(exe_layout)

        # Путь к папке модов
        mods_layout = QHBoxLayout()
        self.mods_input = QLineEdit()
        mods_browse = QPushButton("Обзор")
        mods_browse.clicked.connect(self.browse_mods)
        mods_layout.addWidget(self.mods_input)
        mods_layout.addWidget(mods_browse)
        layout.addWidget(QLabel("Путь к папке модов:"))
        layout.addLayout(mods_layout)

        self.app_id_input = QLineEdit()
        layout.addWidget(QLabel("ID приложения Steam:"))
        layout.addWidget(self.app_id_input)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)

    def browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать исполняемый файл", "", "Исполняемые файлы (*.exe)")
        if path:
            self.exe_input.setText(path)

    def browse_mods(self):
        path = QFileDialog.getExistingDirectory(self, "Выбрать папку модов")
        if path:
            self.mods_input.setText(path)

    def get_data(self):
        return (
            self.name_input.text(),
            self.exe_input.text(),
            self.mods_input.text(),
            self.app_id_input.text()
        )
