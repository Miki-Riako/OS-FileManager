from PySide6.QtCore import Qt, QSize, QUrl, QPoint, QProcess
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QDesktopServices, QColor, QFont, QSyntaxHighlighter, QTextCharFormat
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

        self.api = API()

        # self.controller = controller
        # self.helper = helper

        self.cpp_process = QProcess(self)
        self.cpp_executable_path = self.api.get_executable_path("app")
        self.cpp_process.readyReadStandardOutput.connect(self._handle_cpp_stdout)
        self.cpp_process.readyReadStandardError.connect(self._handle_cpp_stderr)
        self.cpp_process.errorOccurred.connect(self._handle_cpp_process_error)
        self.cpp_process.finished.connect(self._handle_cpp_process_finished)

        self.vBoxLayout = QVBoxLayout(self)
        self.tabBoxLayout = QHBoxLayout(self)
        self.tabBar = TabBar(self)
        self.runButton = TransparentToolButton(FIF.PLAY.icon(color=QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)), self)
        self.stackedWidget = QStackedWidget(self)
        self.new_edit = PlainTextEdit(self)
        self.new_edit.setPlaceholderText("Input your string here, then press Run (Ctrl+R)")

        # terminal = 'input your string'
        # self.new_edit.setPlainText(terminal)
        self.__initWidget()
        self.saveShortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.saveShortcut.activated.connect(self.save)
        self.runShortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.runShortcut.activated.connect(self.run)
        self.runButton.clicked.connect(self.run)
        self.setObjectName(text.replace(' ', '-'))

        self._start_cpp_process_if_not_running()

    def __initWidget(self):
        self.initLayout()
        self.addSubInterface(self.new_edit, 'InputTab', self.tr('new'), FIF.COMMAND_PROMPT)
        qrouter.setDefaultRouteKey(self.stackedWidget, self.new_edit.objectName())

    def initLayout(self):
        self.tabBar.setTabMaximumWidth(200)

        self.tabBoxLayout.addWidget(self.tabBar)
        self.tabBoxLayout.addWidget(self.runButton)
        self.vBoxLayout.addLayout(self.tabBoxLayout)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(5, 5, 5, 5)

    def addSubInterface(self, widget: PlainTextEdit, objectName, text, icon):
        widget.setObjectName(objectName)
        widget.setFont(QFont("Consolas", 20))
        self.highlighter = Highlighter(widget.document())
        self.stackedWidget.addWidget(widget)
        self.tabBar.addTab(
            routeKey=objectName,
            text=text,
            icon=icon,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

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

    def _start_cpp_process_if_not_running(self):
        if self.cpp_process.state() == QProcess.ProcessState.NotRunning:
            InfoBar.success(
                title='C++ Process',
                content=f"Starting: {self.cpp_executable_path}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            self.cpp_process.start(self.cpp_executable_path, [])
            if not self.cpp_process.waitForStarted(3000):
                error_msg = f"Failed to start C++: {self.cpp_process.errorString()}"
                InfoBar.error("C++ Error", error_msg, parent=self, duration=5000)
                self.runButton.setEnabled(False)
                return False
            else:
                InfoBar.success("C++ Process", "C++ backend started.", parent=self, duration=2000)
                self.runButton.setEnabled(True)
                return True
        return True # Already running or successfully started

    def run(self):
        if not self._start_cpp_process_if_not_running():
            InfoBar.error("Run Error", "C++ backend is not running and could not be started.", parent=self, duration=3000)
            return

        # Get the text from the PlainTextEdit (which you referred to as 'terminal')
        input_string = self.new_edit.toPlainText()

        if not input_string.strip():
            InfoBar.info("Input", "Input is empty.", parent=self, duration=2000)
            return

        # For this simple test, we'll send the entire content as one block,
        # assuming C++ handles it or expects a single line.
        # C++ app must read a line, process, print a line, then loop to read next.
        # Ensure your C++ app's loop is correct (e.g., `while(std::getline(std::cin, line))`).

        self.new_edit.appendPlainText(f"\n>>> Sending to C++: {input_string.splitlines()[0]}...") # Show what's sent
        self.cpp_process.write(f"{input_string}\n".encode('utf-8')) # Send with newline
        # self.cpp_process.waitForBytesWritten(100) # Optional: if you want to be sure it's written

        # Output from C++ will be handled by `_handle_cpp_stdout` and appended to `self.new_edit`

    def _handle_cpp_stdout(self):
        if self.cpp_process:
            output_bytes = self.cpp_process.readAllStandardOutput()
            output_string = output_bytes.data().decode('utf-8', errors='ignore').strip()
            if output_string:
                # Append C++ output directly to the same PlainTextEdit for simplicity
                self.new_edit.appendPlainText(f"<<< From C++: {output_string}")
                # Auto-scroll to the end
                cursor = self.new_edit.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.new_edit.setTextCursor(cursor)

    def _handle_cpp_stderr(self):
        if self.cpp_process:
            error_bytes = self.cpp_process.readAllStandardError()
            error_string = error_bytes.data().decode('utf-8', errors='ignore').strip()
            if error_string:
                self.new_edit.appendPlainText(f"<font color='red'>C++ STDERR: {error_string}</font>")
                InfoBar.error("C++ STDERR", error_string, parent=self, duration=5000)

    def _handle_cpp_process_error(self, error: QProcess.ProcessError):
        if self.cpp_process:
            error_msg = f"C++ Process Error: {self.cpp_process.errorString()} (Code: {error})"
            self.new_edit.appendPlainText(f"<font color='red'>{error_msg}</font>")
            InfoBar.critical("C++ Critical Error", error_msg, parent=self, duration=0)
            self.runButton.setEnabled(False)

    def _handle_cpp_process_finished(self, exitCode: int, exitStatus: QProcess.ExitStatus):
        status_str = "C++ Process Finished. "
        if exitStatus == QProcess.ExitStatus.NormalExit:
            status_str += f"Exited normally (code: {exitCode})."
        else:
            status_str += f"Crashed (code: {exitCode})."
        self.new_edit.appendPlainText(f"<font color='orange'>{status_str} Please restart app or C++ process if needed.</font>")
        InfoBar.warning("C++ Process", status_str, parent=self, duration=5000)
        self.runButton.setEnabled(False) # Process ended

    def closeEvent(self, event):
        if self.cpp_process and self.cpp_process.state() == QProcess.ProcessState.Running:
            InfoBarManager.info("Exiting", "Terminating C++ process...", parent=self)
            self.cpp_process.terminate()
            if not self.cpp_process.waitForFinished(1000): # Shorter wait for simple test
                self.cpp_process.kill()
        super().closeEvent(event)