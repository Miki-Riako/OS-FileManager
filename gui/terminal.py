import json

from pathlib import Path

from PySide6.QtCore import Qt, QSize, QProcess, QEvent, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor, QKeySequence, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication, QLabel, QFrame, QMessageBox,
    QWidget, QVBoxLayout,  QHBoxLayout, QVBoxLayout,
    QStackedWidget
    )
from qfluentwidgets import (
    CaptionLabel, PlainTextEdit, PushButton, CheckBox, BodyLabel, SpinBox, ComboBox, qrouter,
    NavigationItemPosition, MessageBox, TabBar, SubtitleLabel, setFont, TabCloseButtonDisplayMode, IconWidget,
    TransparentDropDownToolButton, TransparentToolButton, setTheme, Theme, isDarkTheme,
    InfoBar, InfoBarPosition, InfoBarManager
    )
from qfluentwidgets import FluentIcon as FIF

from api.api import API

from .highlighter import Highlighter

class Workspace(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.api = API(self, "app")

        self.setConfig()

        self.vBoxLayout = QVBoxLayout(self)
        self.tabBoxLayout = QHBoxLayout()
        self.tabBar = TabBar(self)
        self.runButton = TransparentToolButton(FIF.PLAY.icon(color=QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)), self)
        self.stackedWidget = QStackedWidget(self)

        self.next_unique_tab_id = 0
        self.__initWidget()
        self.runButton.clicked.connect(self.run)
        self.setObjectName(text.replace(' ', '-'))

    def eventFilter(self, watched_object, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: # 同时按下了 Shift 键默认换行
                    return super().eventFilter(watched_object, event)
                else:
                    QTimer.singleShot(0, self.run)
                    return False
        # 对于其他对象或事件，调用父类的 eventFilter
        return super().eventFilter(watched_object, event)

    def __initWidget(self):
        self.__initLayout()
        self.tabBar.currentChanged.connect(self.onTabChanged)
        self.tabBar.tabAddRequested.connect(self.onTabAddRequested)
        self.tabBar.tabCloseRequested.connect(self.onTabCloseRequested)
        self.onTabAddRequested()

    def __initLayout(self):
        self.tabBar.setTabMaximumWidth(200)
        self.tabBar.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.ON_HOVER)

        self.tabBoxLayout.addWidget(self.tabBar)
        self.tabBoxLayout.addWidget(self.runButton)
        self.vBoxLayout.addLayout(self.tabBoxLayout)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(5, 5, 5, 5)

    def setConfig(self):
        config_file_path = Path(__file__).resolve().parent.parent / "config" / "config.json"
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        self.font_size = config_data.get("fontSize", 20)
        self.font_family = config_data.get("fontFamily", "Monospace")

    def addTerminalTab(self, widget: PlainTextEdit, objectName, text, icon):
        widget.setObjectName(objectName)
        widget.setFont(QFont(self.font_family, self.font_size))
        widget.setPlaceholderText("> ")
        widget.setPlainText(">_")
        widget.installEventFilter(self)
        Highlighter(widget.document())
        self.stackedWidget.addWidget(widget)
        self.tabBar.addTab(
            routeKey=objectName,
            text=text,
            icon=icon
        )
        self.tabBar.setCurrentTab(objectName)

    def onTabCloseRequested(self, index: int):
        tab_item = self.tabBar.tabItem(index)
        route_key = tab_item.routeKey()
        widget_to_remove = self.stackedWidget.findChild(PlainTextEdit, route_key)
        if widget_to_remove:
            self.stackedWidget.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None) # 解除父子关系
            widget_to_remove.deleteLater()   # 将 widget 标记为待删除，在事件循环空闲时销毁

        self.tabBar.removeTab(index)
        if self.tabBar.count() == 0:
            self.onTabAddRequested() # 重新添加一个默认 Tab

    def onTabChanged(self, index: int):
        route_key = self.tabBar.currentTab().routeKey()
        target_widget = self.stackedWidget.findChild(PlainTextEdit, route_key)
        if target_widget:
            self.stackedWidget.setCurrentWidget(target_widget)

    def onTabAddRequested(self):
        current_id = self.next_unique_tab_id
        new_tab_name = f"Bash-{current_id + 1}"
        new_tab_text = f"Bash {current_id + 1}"
        new_terminal_edit = PlainTextEdit(self)
        self.addTerminalTab(new_terminal_edit, new_tab_name, new_tab_text, FIF.COMMAND_PROMPT)
        self.next_unique_tab_id += 1

    def run(self):
        try:
            InfoBar.success(
                title='Run',
                content="You pressed Enter. Waiting for being implemented...",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='Error',
                # content=f"Compilation failed:\n{str(e)}\n\n迂回路を行けば最短ルート。",
                content=f"Compilation failed:\n{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self
            )
