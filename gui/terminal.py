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

class TerminalInputMode:
    NORMAL = "NORMAL" # 普通命令输入模式
    LOGIN_USERNAME = "LOGIN_USERNAME" # 登录：等待用户名
    LOGIN_PASSWORD = "LOGIN_PASSWORD" # 登录：等待密码
    SUDO_PASSWORD = "SUDO_PASSWORD" # Sudo：等待密码

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
        self.terminal_modes = {}
        self.password_buffers = {}

        self.login_username_prompt_regex = re.compile(r"host@login:Username\$ ")
        self.login_password_prompt_regex = re.compile(r"host@login:Password\$ ")
        self.sudo_password_prompt_regex = re.compile(r"\[sudo\] password for .*?:\s")
        self.main_shell_prompt_regex = re.compile(r"FileSystem@[\w\.-]+:.*?\$\s")

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

    def _determine_terminal_state(self, full_text: str) -> tuple[TerminalInputMode, int]:
        """根据终端的完整文本内容，确定当前的输入模式和用户输入的起始索引。"""
        potential_prompts = []
        prompt_patterns = [ # 定义所有可能的提示符正则表达式和它们对应的模式
            (self.login_username_prompt_regex, TerminalInputMode.LOGIN_USERNAME),
            (self.login_password_prompt_regex, TerminalInputMode.LOGIN_PASSWORD),
            (self.sudo_password_prompt_regex, TerminalInputMode.SUDO_PASSWORD),
            (self.main_shell_prompt_regex, TerminalInputMode.NORMAL)
        ]
        for regex, mode in prompt_patterns: # 遍历所有提示符类型，找到它们在 full_text 中最后一次出现的位置
            match = None
            for m in regex.finditer(full_text): # 使用 finditer 找到所有匹配，并取最后一个（最靠后的）
                match = m
            if match:
                potential_prompts.append((match.end(), mode))

        potential_prompts.sort(key=lambda x: x[0]) # 根据匹配的结束位置进行排序，最新的提示符在列表末尾
        new_mode = TerminalInputMode.NORMAL # 默认模式和输入位置：如果没有识别到特定提示符，则默认为普通模式，输入位置在文本末尾
        new_input_start_index = len(full_text)

        if potential_prompts:
            latest_match_end_pos, latest_mode = potential_prompts[-1] # 取列表中最后一个（即位置最靠后，最新的）提示符来决定当前模式和输入起始位置
            new_mode = latest_mode
            new_input_start_index = latest_match_end_pos

        return new_mode, new_input_start_index

    def _handle_api_output(self, terminal_object_name: str, output: str, is_error: bool = False):
        """处理来自 API 的标准输出信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if not text_edit:
            return
        if '\x0c' in output:
            # text_edit.clear()
            output = output.replace('\x0c', '') # 移除换页符，防止它干扰后续文本显示和高亮

        self._append_to_terminal(text_edit, output, is_error)
        full_text = text_edit.document().toPlainText()

        self.terminal_modes[terminal_object_name],\
        self.input_start_indices[terminal_object_name]\
            = self._determine_terminal_state(full_text)

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
        current_mode = self.terminal_modes.get(object_name, TerminalInputMode.NORMAL)
        if input_start_index is None:
            self._append_to_terminal(text_edit, "\n错误：未初始化输入位置，无法发送命令。\n", is_error=True)
            return

        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        full_text = text_edit.toPlainText()

        input_data = ""
        if current_mode in [TerminalInputMode.LOGIN_PASSWORD, TerminalInputMode.SUDO_PASSWORD]:
            input_data = self.password_buffers.get(object_name, "") # 在密码模式下，从内部缓冲区获取数据
            self.password_buffers[object_name] = "" # 清空内部缓冲区，因为密码已发送
        else:
            input_data = full_text[input_start_index:].strip() # 普通命令模式下，从 PlainTextEdit 获取数据

        terminal_api = self.terminal_apis.get(object_name)
        if not terminal_api:
            self._append_to_terminal(text_edit, "错误：未找到终端 API 实例。\n", is_error=True)
            self.input_start_indices[object_name] = len(text_edit.document().toPlainText())
            cursor.movePosition(QTextCursor.End); text_edit.setTextCursor(cursor)
            return

        if input_data.strip().lower() == "clear" and current_mode == TerminalInputMode.NORMAL:
            text_edit.clear()
            self.input_start_indices[object_name] = 0
            terminal_api.send_input_to_app(input_data)
            return

        cursor.setPosition(input_start_index)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        text_edit.setTextCursor(cursor)

        if current_mode == TerminalInputMode.NORMAL:
            text_edit.insertPlainText(input_data + '\n') # 重新插入用户输入的命令，后面跟一个换行符，模拟用户按Enter
        else:
            text_edit.insertPlainText('\n')
        terminal_api.send_input_to_app(input_data)

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
            text_edit = watched_object
            object_name = text_edit.objectName()
            input_start_index = self.input_start_indices.get(object_name, 0)
            current_cursor = text_edit.textCursor()
            current_mode = self.terminal_modes.get(object_name, TerminalInputMode.NORMAL)
            is_password_or_sudo_mode = (current_mode in [TerminalInputMode.LOGIN_PASSWORD, TerminalInputMode.SUDO_PASSWORD])

            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                key_text = event.text() # 获取按下的字符
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter: # 处理 Enter 键 (优先级最高)
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                        return super().eventFilter(watched_object, event) # Shift+Enter 依然是换行，即使在密码模式下，不过通常密码不需要多行输入
                    else:
                        self._send_command_to_current_terminal(watched_object)
                        return True # 消费事件
                if key == Qt.Key.Key_Backspace: # 处理 Backspace 和 Delete 键阻止删除提示符之前的内容，无论是否在密码模式
                    if current_cursor.hasSelection():
                        if current_cursor.selectionStart() < input_start_index:
                            return True # 阻止删除
                    elif current_cursor.position() <= input_start_index: # 如果光标在提示符边界或之前
                        return True # 阻止删除
                    if is_password_or_sudo_mode: # 密码模式下，处理内部缓冲区
                        password_buffer = self.password_buffers.get(object_name, "")
                        if password_buffer: # 如果缓冲区不为空，则删除最后一个字符
                            self.password_buffers[object_name] = password_buffer[:-1]
                        return True # 消费事件，阻止 PlainTextEdit 默认处理
                elif key == Qt.Key.Key_Delete:
                    if current_cursor.hasSelection():
                        if current_cursor.selectionStart() < input_start_index:
                            return True # 阻止删除
                    elif current_cursor.position() < input_start_index:
                        return True # 阻止删除
                    if is_password_or_sudo_mode:
                        pass # 为了简单且符合常见终端行为，对于密码输入，通常忽略 Delete 键。
                if is_password_or_sudo_mode: # 处理密码输入模式下的字符显示 (什么都不显示)
                    if current_cursor.position() < input_start_index: # 如果光标不在用户输入区域，先强制移到正确位置
                        current_cursor.setPosition(input_start_index)
                        text_edit.setTextCursor(current_cursor)
                    if key_text and key_text.isprintable(): # 对于所有可打印字符，添加到内部缓冲区，但不显示在 PlainTextEdit 上
                        password_buffer = self.password_buffers.get(object_name, "") # 获取当前密码缓冲区，如果不存在则初始化
                        self.password_buffers[object_name] = password_buffer + key_text
                        text_edit.textCursor().movePosition(QTextCursor.EndOfLine) # 确保光标仍然在正确位置，但不要插入任何字符
                        return True # 消费事件，阻止 PlainTextEdit 默认处理 (即显示字符)
                return super().eventFilter(watched_object, event) # 如果不是密码模式，或不是特殊处理的键，则允许 PlainTextEdit 正常处理
            elif event.type() == QEvent.Type.MouseButtonPress: #  阻止鼠标点击/拖动光标到提示符之前
                text_edit = watched_object
                object_name = text_edit.objectName()
                input_start_index = self.input_start_indices.get(object_name, 0)
                cursor_at_click = text_edit.cursorForPosition(event.position().toPoint())
                if cursor_at_click.position() < input_start_index:
                    QTimer.singleShot(0, lambda: text_edit.textCursor().setPosition(input_start_index))
        return super().eventFilter(watched_object, event)

    def addTerminalTab(self, widget: PlainTextEdit, objectName, text, icon):
        widget.setObjectName(objectName)
        widget.setFont(QFont(self.font_family, self.font_size))
        widget.setPlaceholderText("Command prompt...")

        self.terminal_modes[objectName] = TerminalInputMode.NORMAL
        self.password_buffers[objectName] = "" # 初始化密码缓冲区为空字符串

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
        # self.tabBar.setCurrentTab(objectName) # !!!不知道为什么有未知的bug会导致切换时文本不变但进程改变，暂时不切换，让用户手动切换

        terminal_api = API(objectName, "app", self)
        self.terminal_apis[objectName] = terminal_api # 存储起来
        terminal_api.standardOutputReady.connect(self._handle_api_output)
        terminal_api.standardErrorReady.connect(lambda obj_name, error_output: self._handle_api_output(obj_name, error_output, True))
        terminal_api.processFinished.connect(self._handle_api_finished)
        terminal_api.processErrorOccurred.connect(self._handle_api_error_occurred)
        if not terminal_api.start_app_process():
            pass

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