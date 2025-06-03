import json
import sys

from pathlib import Path

from PySide6.QtCore import Qt, QSize, QProcess, QEvent, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor, QKeySequence, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication, QLabel, QFrame, QMessageBox,
    QWidget, QVBoxLayout,  QHBoxLayout,
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
        # self.api = API(self, "app")

        self.setConfig()

        self.vBoxLayout = QVBoxLayout(self)
        self.tabBoxLayout = QHBoxLayout()
        self.tabBar = TabBar(self)
        self.runButton = TransparentToolButton(FIF.PLAY.icon(color=QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)), self)
        self.stackedWidget = QStackedWidget(self)

        self.next_unique_tab_id = 0
        self.terminal_apis = {}

        self.__initWidget()
        self.runButton.clicked.connect(self.run)
        self.setObjectName(text.replace(' ', '-'))

    def _get_terminal_widget_by_object_name(self, object_name: str) -> PlainTextEdit:
        """根据 objectName 获取对应的 PlainTextEdit 实例。"""
        return self.stackedWidget.findChild(PlainTextEdit, object_name)

    def _append_to_terminal(self, text_edit: PlainTextEdit, text: str, is_error: bool = False):
        """辅助方法：向指定 PlainTextEdit 追加文本，并处理光标和可能的颜色。"""
        # if is_error: # 设置文本颜色
        #     original_format = text_edit.currentCharFormat()
        #     error_format = QTextCharFormat(original_format)
        #     error_format.setForeground(QColor("red"))
        #     text_edit.setCurrentCharFormat(error_format)
        text_edit.insertPlainText(text) # 追加新文本
        # if is_error: # 恢复原始文本颜色
        #     text_edit.setCurrentCharFormat(original_format)
        cursor = text_edit.textCursor() # 确保光标和滚动条在最底部，保持用户体验
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def _handle_api_output(self, terminal_object_name: str, output: str, is_error: bool = False):
        """处理来自 API 的标准输出信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            self._append_to_terminal(text_edit, output, is_error)
            self._append_to_terminal(text_edit, "")

    def _handle_api_finished(self, terminal_object_name: str, exitCode: int, exitStatus: QProcess.ExitStatus):
        """处理来自 API 的进程结束信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            status_str = "正常退出" if exitStatus == QProcess.NormalExit else "崩溃"
            self._append_to_terminal(text_edit, f"\n进程已结束，退出码: {exitCode} ({status_str})\n", is_error=True)
            # 进程结束后，尝试重新启动 Shell 或禁用输入，这里我们简单地重新打印提示符
            self._append_to_terminal(text_edit, "host $login: ")
            # 如果是Shell意外退出，可以考虑尝试重启：
            terminal_api = self.terminal_apis.get(terminal_object_name)
            if terminal_api:
                self._append_to_terminal(text_edit, "\n尝试重新启动 Shell...\n")
                if not terminal_api.start_shell():
                    self._append_to_terminal(text_edit, "重新启动 Shell 失败。\n", is_error=True)

    def _handle_api_error_occurred(self, terminal_object_name: str, error_message: str):
        """处理来自 API 的 QProcess 错误信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            self._append_to_terminal(text_edit, f"\nAPI 错误: {error_message}\n", is_error=True)
            self._append_to_terminal(text_edit, "host $login: ") # 确保提示符在末尾

    def _send_command_to_current_terminal(self, text_edit: PlainTextEdit):
        """从 PlainTextEdit 中获取用户输入的命令，并通过 API 发送给对应的 Shell。"""
        prompt = "$ " # 确保与 addTerminalTab 和 _handle_api_output 中的提示符一致

        full_text = text_edit.toPlainText()
        last_prompt_index = full_text.rfind(prompt)

        if last_prompt_index != -1:
            # 提取用户实际输入的命令/数据
            input_data = full_text[last_prompt_index + len(prompt):].strip()

            # 将用户输入的命令和提示符一起作为历史记录显示在终端
            # 首先，清理当前提示符及用户输入的部分
            cursor = text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            text_edit.setTextCursor(cursor)
            # 然后重新打印出用户输入和提示符，形成一条完整的历史记录
            text_edit.insertPlainText(input_data + '\n')
            # text_edit.insertPlainText(prompt + input_data + '\n')


            # 获取当前终端对应的 API 实例
            current_tab_name = text_edit.objectName()
            terminal_api = self.terminal_apis.get(current_tab_name)

            if terminal_api:
                # 调用 API 的方法发送输入
                terminal_api.send_input_to_app(input_data)
            else:
                self._append_to_terminal(text_edit, "错误：未找到终端 API 实例。\n", is_error=True)
                self._append_to_terminal(text_edit, prompt) # 重新显示提示符
        else:
            self._append_to_terminal(text_edit, "\n错误：无法识别当前输入位置。请确保以 '$ ' 提示符开头。\n", is_error=True)
            self._append_to_terminal(text_edit, prompt) # 重新显示提示符

        # 确保光标在末尾，准备接收新的输入
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

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

    def eventFilter(self, watched_object, event):
        # if event.type() == QEvent.Type.KeyPress:
        #     key = event.key()
        #     if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
        #         if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: # 同时按下了 Shift 键默认换行
        #             return super().eventFilter(watched_object, event)
        #         else:
        #             QTimer.singleShot(0, self.run)
        #             return False
        # return super().eventFilter(watched_object, event)
        if isinstance(watched_object, PlainTextEdit) and watched_object is self.stackedWidget.currentWidget():
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: # 同时按下了 Shift 键默认换行
                        return super().eventFilter(watched_object, event)
                    else: # 普通 Enter 键，触发命令发送
                        self._send_command_to_current_terminal(watched_object)
                        return True # 消费这个事件，阻止 PlainTextEdit 默认的换行
        return super().eventFilter(watched_object, event)

    def addTerminalTab(self, widget: PlainTextEdit, objectName, text, icon):
        widget.setObjectName(objectName)
        widget.setFont(QFont(self.font_family, self.font_size))
        widget.setPlaceholderText("Command prompt...")
        widget.setPlainText("")
        # widget.setPlainText("host $login: ")

        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        widget.setTextCursor(cursor)

        widget.installEventFilter(self)
        Highlighter(widget.document())
        self.stackedWidget.addWidget(widget)
        self.tabBar.addTab(
            routeKey=objectName,
            text=text,
            icon=icon
        )
        self.tabBar.setCurrentTab(objectName)

        terminal_api = API(objectName, "app", self)
        self.terminal_apis[objectName] = terminal_api # 存储起来
        terminal_api.standardOutputReady.connect(self._handle_api_output)
        terminal_api.standardErrorReady.connect(lambda obj_name, error_output: self._handle_api_output(obj_name, error_output, True))
        terminal_api.processFinished.connect(self._handle_api_finished)
        terminal_api.processErrorOccurred.connect(self._handle_api_error_occurred)
        if not terminal_api.start_app_process():
            pass # 如果失败，API 发出 processErrorOccurred 信号，这里可不再重复

    def onTabCloseRequested(self, index: int):
        tab_item = self.tabBar.tabItem(index)
        route_key = tab_item.routeKey()

        terminal_api = self.terminal_apis.get(route_key)
        if terminal_api:
            terminal_api.terminate_app_process() # 告诉 API 终止其管理的 Shell 进程
            del self.terminal_apis[route_key] # 从字典中移除引用
            terminal_api.deleteLater() # 销毁 API 对象


        widget_to_remove = self.stackedWidget.findChild(PlainTextEdit, route_key)
        if widget_to_remove:
            self.stackedWidget.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None) # 解除父子关系
            widget_to_remove.deleteLater()   # 将 widget 标记为待删除，在事件循环空闲时销毁

        self.tabBar.removeTab(index)
        if self.tabBar.count() == 0:
            self.onTabAddRequested()

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
        current_widget = self.stackedWidget.currentWidget()
        if isinstance(current_widget, PlainTextEdit):
            self._send_command_to_current_terminal(current_widget)
        else:
            InfoBar.warning(
                title='警告',
                content="没有激活的终端可以运行命令。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def warning(self, title, content):
        InfoBar.warning(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )