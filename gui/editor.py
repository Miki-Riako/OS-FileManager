import json

from pathlib import Path

from PySide6.QtCore import QSize, QEventLoop, QTimer, Qt, Signal
from PySide6.QtGui import QIcon, QFont, QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, SplashScreen, Theme,
    PlainTextEdit, TransparentToolButton, isDarkTheme, InfoBar, InfoBarPosition
)
from qfluentwidgets import FluentIcon as FIF

class Editor(QFrame):
    saveFileRequested = Signal(str, str)

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
        if not self.current_file_path:
            InfoBar.warning(
                title='保存失败',
                content="请先加载文件才能保存。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        file_content = self.editor_space.toPlainText()
        self.saveFileRequested.emit(self.current_file_path, file_content) # 发出信号，请求 Terminal 执行保存操作
        InfoBar.info( # 立即显示正在保存的提示
            title='保存中',
            content=f"正在保存 '{Path(self.current_file_path).name}'...",
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

    def _handle_save_complete(self, file_path: str, success: bool, error_message: str):
        if success:
            InfoBar.success(
                title='保存成功',
                content=f"文件 '{Path(file_path).name}' 已成功保存。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.error(
                title='保存失败',
                content=f"文件 '{Path(file_path).name}' 保存失败: {error_message}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
