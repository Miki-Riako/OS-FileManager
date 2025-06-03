import json
import re

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
        self.input_start_indices = {}

        self.__initWidget()
        self.runButton.clicked.connect(self.run)
        self.setObjectName(text.replace(' ', '-'))

    def _get_terminal_widget_by_object_name(self, object_name: str) -> PlainTextEdit:
        """根据 objectName 获取对应的 PlainTextEdit 实例。"""
        return self.stackedWidget.findChild(PlainTextEdit, object_name)

    def _append_to_terminal(self, text_edit: PlainTextEdit, text: str, is_error: bool = False, is_prompt: bool = False):
        """辅助方法：向指定 PlainTextEdit 追加文本，并处理光标和可能的颜色。"""
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.insertPlainText(text)

        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def _handle_api_output(self, terminal_object_name: str, output: str, is_error: bool = False):
        """处理来自 API 的标准输出信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if not text_edit:
            return
        if '\x0c' in output:
            text_edit.clear()
            output = output.replace('\x0c', '') # 移除换页符，防止它干扰后续文本显示和高亮
            self.input_start_indices[terminal_object_name] = 0 # 由于清空了，光标起始位置可以暂时设为0，后续的提示符会更新它

        self._append_to_terminal(text_edit, output, is_error)
        full_text = text_edit.document().toPlainText() # 在追加内容后，尝试识别并设置新的输入起始位置
        general_prompt_regex = r"([\w\.-]+@[\w\.-]+:.*?\$\s)" 
        last_prompt_match = None
        for match in re.finditer(general_prompt_regex, full_text):
            last_prompt_match = match # 使用 finditer 遍历所有匹配，以确保找到最后一个提示符
        if last_prompt_match: # 提示符的结束位置就是用户可以开始输入的位置
            self.input_start_indices[terminal_object_name] = last_prompt_match.end()
        else:
            self.input_start_indices[terminal_object_name] = len(full_text)

        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def _handle_api_finished(self, terminal_object_name: str, exitCode: int, exitStatus: QProcess.ExitStatus):
        """处理来自 API 的进程结束信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            status_str = "正常退出" if exitStatus == QProcess.NormalExit else "崩溃"
            self._append_to_terminal(text_edit, f"\n进程已结束，退出码: {exitCode} ({status_str})\n", is_error=True)
            terminal_api = self.terminal_apis.get(terminal_object_name) # 进程结束后重新启动Shell。新的提示符会在 API 重新启动成功后打印
            if terminal_api:
                self._append_to_terminal(text_edit, "\n尝试重新启动 Shell...\n")
                if not terminal_api.start_app_process(): # 重新启动应用程序
                    self._append_to_terminal(text_edit, "重新启动 Shell 失败。\n", is_error=True)

    def _handle_api_error_occurred(self, terminal_object_name: str, error_message: str):
        """处理来自 API 的 QProcess 错误信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            self._append_to_terminal(text_edit, f"\nAPI 错误: {error_message}\n", is_error=True)
            self.input_start_indices[terminal_object_name] = len(text_edit.document().toPlainText())
            cursor = text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            text_edit.setTextCursor(cursor)
            text_edit.ensureCursorVisible()

    def _send_command_to_current_terminal(self, text_edit: PlainTextEdit):
        """从 PlainTextEdit 中获取用户输入的命令，并通过 API 发送给对应的 Shell。"""
        object_name = text_edit.objectName() # 获取当前终端的输入起始位置
        input_start_index = self.input_start_indices.get(object_name)
        if input_start_index is None:
            self._append_to_terminal(text_edit, "\n错误：未初始化输入位置，无法发送命令。\n", is_error=True)
            return
        full_text = text_edit.toPlainText()
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        input_data = full_text[input_start_index:].strip()

        if input_data.strip().lower() == "clear":
            text_edit.clear() # 清空 PlainTextEdit
            self.input_start_indices[object_name] = 0 # 清空后，输入起始位置回到 0，API 会重新发送提示符
            terminal_api = self.terminal_apis.get(object_name)
            if terminal_api:
                terminal_api.send_input_to_app(input_data)
            return # 阻止后续的 input_data + '\n' 追加，因为它已经被清空了

        cursor.setPosition(input_start_index) # 将用户输入的命令显示为历史记录的一部分，然后删除用户输入和旧的提示符 从 input_start_index 到文本末尾
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        text_edit.setTextCursor(cursor)
        text_edit.insertPlainText(input_data + '\n') # 重新插入用户输入的命令，后面跟一个换行符，模拟用户按Enter
        terminal_api = self.terminal_apis.get(object_name)
        if terminal_api:
            terminal_api.send_input_to_app(input_data)
        else:
            self._append_to_terminal(text_edit, "错误：未找到终端 API 实例。\n", is_error=True)
            self.input_start_indices[object_name] = len(text_edit.document().toPlainText()) # 如果没有 API 实例，保持提示符可见，光标在末尾

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
        if isinstance(watched_object, PlainTextEdit) and watched_object is self.stackedWidget.currentWidget():
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                text_edit = watched_object
                current_cursor = text_edit.textCursor()
                object_name = text_edit.objectName()
                input_start_index = self.input_start_indices.get(object_name, 0) # 获取当前终端的输入起始位置，如果不存在，默认是0（允许从头开始输入）
                if key == Qt.Key.Key_Backspace: # 阻止 Backspace 键删除提示符
                    if current_cursor.hasSelection(): # 如果有选中文字，且选中范围的开始位置在提示符之前，则阻止
                        if current_cursor.selectionStart() < input_start_index:
                            return True # 消费事件，阻止删除
                    elif current_cursor.position() <= input_start_index: # 如果没有选中文字，且光标在提示符或提示符之前，则阻止
                        return True # 消费事件，阻止删除
                elif key == Qt.Key.Key_Delete: # 阻止 Delete 键删除提示符 (Delete是向前删除)
                    if current_cursor.hasSelection(): # 如果有选中文字，且选中范围的开始位置在提示符之前，则阻止
                        if current_cursor.selectionStart() < input_start_index:
                            return True # 消费事件，阻止删除
                    elif current_cursor.position() < input_start_index: # 如果没有选中文字，且光标在提示符之前，则阻止 (在提示符处按Delete删除用户输入是允许的)
                        return True # 消费事件，阻止删除
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter: # 处理 Enter 键 (保持不变)
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: # 同时按下了 Shift 键默认换行
                        return super().eventFilter(watched_object, event)
                    else: # 普通 Enter 键，触发命令发送
                        self._send_command_to_current_terminal(watched_object)
                        return True # 消费这个事件，阻止 PlainTextEdit 默认的换行
            elif event.type() == QEvent.Type.MouseButtonPress: # 阻止鼠标点击/拖动光标到提示符之前
                text_edit = watched_object
                object_name = text_edit.objectName()
                input_start_index = self.input_start_indices.get(object_name, 0)
                cursor_at_click = text_edit.cursorForPosition(event.position().toPoint()) # 获取鼠标点击位置对应的文本光标位置
                if cursor_at_click.position() < input_start_index: # 如果点击位置在提示符之前，则强制将光标设置到提示符开始处
                    QTimer.singleShot(0, lambda: text_edit.textCursor().setPosition(input_start_index))
                    # 延时设置光标，以确保在 QPlainTextEdit 自己的事件处理之后发生
                    # 不阻止事件，让QPlainTextEdit处理鼠标点击，然后我们再调整光标
                    # return True # 如果返回True，则完全阻止QPlainTextEdit的鼠标点击处理

        return super().eventFilter(watched_object, event)

    def addTerminalTab(self, widget: PlainTextEdit, objectName, text, icon):
        widget.setObjectName(objectName)
        widget.setFont(QFont(self.font_family, self.font_size))
        widget.setPlaceholderText("Command prompt...")
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        widget.setTextCursor(cursor)

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