# from PySide6.QtCore import Qt, QSize, QUrl, QPoint, QProcess
# from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QDesktopServices, QColor, QFont, QSyntaxHighlighter, QTextCharFormat
# from PySide6.QtWidgets import (
#     QApplication, QLabel, QFrame, QMessageBox,
#     QWidget, QVBoxLayout,  QHBoxLayout, QVBoxLayout,
#     QStackedWidget
#     )
# from qfluentwidgets import (
#     CaptionLabel, PlainTextEdit, PushButton, CheckBox, BodyLabel, SpinBox, ComboBox, qrouter,
#     NavigationItemPosition, MessageBox, TabBar, SubtitleLabel, setFont, TabCloseButtonDisplayMode, IconWidget,
#     TransparentDropDownToolButton, TransparentToolButton, setTheme, Theme, isDarkTheme,
#     InfoBar, InfoBarPosition, InfoBarManager
#     )
# from qfluentwidgets import FluentIcon as FIF

# from api.api import API

# from .highlighter import Highlighter

# class Workspace(QWidget):
#     def __init__(self, text: str, parent=None):
#         super().__init__(parent=parent)
#         self.api = API(self, "app")

#         self.vBoxLayout = QVBoxLayout(self)
#         self.tabBoxLayout = QHBoxLayout(self)
#         self.tabBar = TabBar(self)
#         self.runButton = TransparentToolButton(FIF.PLAY.icon(color=QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)), self)
#         self.stackedWidget = QStackedWidget(self)
#         self.terminal_text = PlainTextEdit(self)
#         self.terminal_text.setPlaceholderText("Input your string here, then press Run (Ctrl+R)")

#         self.__initWidget()
#         self.runShortcut = QShortcut(QKeySequence("Ctrl+R"), self)
#         self.runShortcut.activated.connect(self.run)
#         self.runButton.clicked.connect(self.run)
#         self.setObjectName(text.replace(' ', '-'))

#     def __initWidget(self):
#         self.initLayout()
#         self.addSubInterface(self.terminal_text, 'InputTab', self.tr('new'), FIF.COMMAND_PROMPT)
#         qrouter.setDefaultRouteKey(self.stackedWidget, self.terminal_text.objectName())

#     def initLayout(self):
#         self.tabBar.setTabMaximumWidth(200)

#         self.tabBoxLayout.addWidget(self.tabBar)
#         self.tabBoxLayout.addWidget(self.runButton)
#         self.vBoxLayout.addLayout(self.tabBoxLayout)
#         self.vBoxLayout.addWidget(self.stackedWidget)
#         self.vBoxLayout.setContentsMargins(5, 5, 5, 5)

#     def addSubInterface(self, widget: PlainTextEdit, objectName, text, icon):
#         widget.setObjectName(objectName)
#         widget.setFont(QFont("Consolas", 20))
#         self.highlighter = Highlighter(widget.document())
#         self.stackedWidget.addWidget(widget)
#         self.tabBar.addTab(
#             routeKey=objectName,
#             text=text,
#             icon=icon,
#             onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
#         )

#     def warning(self, title, content):
#         InfoBar.warning(
#             title=title,
#             content=content,
#             orient=Qt.Horizontal,
#             isClosable=True,
#             position=InfoBarPosition.TOP,
#             duration=2000,
#             parent=self
#         )

#     def run(self):
#         self.terminal_text.appendPlainText(self.api.api_io(self.terminal_text.toPlainText()))

from PySide6.QtCore import Qt, QSize, QProcess # Removed unused QUrl, QPoint
from PySide6.QtGui import QFont, QTextCursor, QColor, QKeySequence, QShortcut, QTextCharFormat # Added QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QApplication # Added QLineEdit, QApplication
)
from qfluentwidgets import (
    PlainTextEdit, PushButton, InfoBar, InfoBarPosition, FluentIcon as FIF, isDarkTheme
) # Removed TabBar, StackedWidget etc.

from api.api import API # from api.api import API

from .highlighter import Highlighter

class Workspace(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))

        self.vBoxLayout = QVBoxLayout(self)

        # 输出区域
        self.output_area = PlainTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 11))
        self.output_area.setPlaceholderText("Process output will appear here...")
        self.highlighter = Highlighter(self.output_area.document()) # 你的语法高亮器

        # 输入区域
        self.input_layout = QHBoxLayout()
        self.input_prompt_label = QLabel(">", self) # 模拟一个提示符
        self.input_line = QLineEdit(self)
        self.input_line.setFont(QFont("Consolas", 11))
        self.input_line.setPlaceholderText("Enter command and press Enter")
        
        # (可选) 发送按钮，如果不想只依赖回车
        # self.send_button = PushButton(FIF.SEND, "Send", self)
        # self.input_layout.addWidget(self.send_button)

        self.input_layout.addWidget(self.input_prompt_label)
        self.input_layout.addWidget(self.input_line, 1) # 输入行占据主要空间

        self.vBoxLayout.addWidget(self.output_area, 1) # 输出区域占据主要垂直空间
        self.vBoxLayout.addLayout(self.input_layout)
        self.vBoxLayout.setContentsMargins(5, 5, 5, 5)

        # --- API 实例化和信号连接 ---
        # 重要: 将 "app" 替换为你的 C++ 编译出的可执行文件名 (不含.exe后缀)
        self.cpp_executable_name = "app"
        self.api = API(self, self.cpp_executable_name)

        if not self.api.executable_path: # API未能找到可执行文件
            self._append_to_output(f"Error: Executable '{self.cpp_executable_name}' not found. Terminal cannot start.\n", is_error=True)
            self.input_line.setEnabled(False)
        else:
            # 连接API的信号到Workspace的槽
            self.api.standardOutputReady.connect(self._append_to_output)
            self.api.standardErrorReady.connect(lambda text: self._append_to_output(text, is_error=True))
            self.api.processFinished.connect(self._on_process_terminated)
            self.api.processErrorOccurred.connect(self._on_api_process_error)

            # 连接用户输入
            self.input_line.returnPressed.connect(self._send_input_from_user)
            # if hasattr(self, 'send_button'):
            #     self.send_button.clicked.connect(self._send_input_from_user)

            # 初始化时，如果进程未能立即启动 (例如API中waitForStarted超时)，输入可能仍是禁用的
            # 我们会在第一次收到输出或错误时启用它，或者在API错误时保持禁用
            if not self.api.is_running() and self.api.process.error() == QProcess.ProcessError.Timedout:
                self._append_to_output("Waiting for process to start...\n", is_error=True) # 提示用户
                self.input_line.setEnabled(False)
            elif self.api.is_running():
                 self.input_line.setEnabled(True)
                 self.input_line.setFocus()
            else: # 其他启动失败的情况
                self.input_line.setEnabled(False)
        
        self.setFocusProxy(self.input_line) # 当Workspace获得焦点时，实际给输入行

    def _append_to_output(self, text: str, is_error: bool = False):
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 为错误文本设置不同颜色
        original_format = cursor.charFormat()
        if is_error:
            error_format = QTextCharFormat(original_format)
            error_color = QColor(255, 80, 80) if isDarkTheme() else QColor(200, 0, 0)
            error_format.setForeground(error_color)
            cursor.setCharFormat(error_format)
        
        cursor.insertText(text)
        
        if is_error: # 恢复原始格式
            cursor.setCharFormat(original_format)
            
        self.output_area.ensureCursorVisible()

        # 如果之前输入被禁用且进程现在是运行的 (例如，延迟启动后收到第一个输出)
        if not self.input_line.isEnabled() and self.api and self.api.is_running():
            self.input_line.setEnabled(True)
            self.input_line.setFocus()


    def _on_process_terminated(self, exit_code: int, exit_status: QProcess.ExitStatus):
        status_text = "normally" if exit_status == QProcess.ExitStatus.NormalExit else "unexpectedly (crashed?)"
        self._append_to_output(
            f"\n--- Process '{self.cpp_executable_name}' terminated {status_text} (Exit Code: {exit_code}) ---\n",
            is_error=(exit_status != QProcess.ExitStatus.NormalExit)
        )
        self.input_line.setEnabled(False) # 进程结束后禁用输入
        # self.input_line.clear()

    def _on_api_process_error(self, error_message: str):
        self._append_to_output(f"Process Error: {error_message}\n", is_error=True)
        self.input_line.setEnabled(False) # 发生错误，禁用输入

    def _send_input_from_user(self):
        if not self.api or not self.api.is_running():
            self._append_to_output("Cannot send input: Process is not running.\n", is_error=True)
            return

        command = self.input_line.text()
        if command: # 只发送非空命令
            # (可选) 在输出区域回显用户输入的命令，模仿终端行为
            # self._append_to_output(f"{self.input_prompt_label.text()} {command}\n")
            
            self.api.send_input_to_process(command)
            self.input_line.clear() # 清空输入行

    def warning(self, title, content):
        InfoBar.warning(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self.window() or self # 确保InfoBar有合适的父对象
        )

    def closeEvent(self, event):
        if hasattr(self, 'api') and self.api:
            self.api.stop_process()
        super().closeEvent(event)