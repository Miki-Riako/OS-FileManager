import json

from pathlib import Path

from PySide6.QtCore import QSize, QEventLoop, QTimer, Qt
from PySide6.QtGui import QIcon, QFont, QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, SplashScreen, Theme,
    PlainTextEdit, TransparentToolButton, isDarkTheme, InfoBar, InfoBarPosition
)
from qfluentwidgets import FluentIcon as FIF

class Editor(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setupUi()
        self.editor_space = PlainTextEdit(self)
        self.saveShortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.current_file_path = None
        self.__initWidget()
        self.setObjectName(text.replace(' ', '-'))

    def __initWidget(self):
        self.__initLayout()
        self.__initShortcut()
        config_file_path = Path(__file__).resolve().parent.parent / "config" / "config.json"
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        self.editor_space.setFont(QFont(config_data.get("fontFamily", "Monospace"), config_data.get("fontSize", 20)))
        self.editor_space.setPlaceholderText("Editor Space...")

    def __initLayout(self):
        self.layout.addWidget(self.editor_space)

    def __initShortcut(self):
        self.saveShortcut.activated.connect(self.save)

    def setupUi(self):
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

    def save(self):
        InfoBar.success(
            title='Save',
            content="You pressed Ctrl+S. Waiting for save to be implemented...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def load_content(self, file_path: str, content: str):
        self.current_file_path = file_path
        self.editor_space.setPlainText(content)
        self.editor_space.setPlaceholderText(f"Editing: {file_path}")
        InfoBar.success(
            title='File Loaded',
            content=f"Successfully loaded '{Path(file_path).name}'",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
