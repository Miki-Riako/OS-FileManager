import os
import sys

from PySide6.QtCore import QObject, Signal, QProcess, Qt

class API(QObject):
    standardOutputReady = Signal(str, str)
    standardErrorReady = Signal(str, str)
    processFinished = Signal(str, int, QProcess.ExitStatus)
    processErrorOccurred = Signal(str, str)

    def __init__(self, terminal_object_name: str, executable_filename: str, parent=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.terminal_object_name = terminal_object_name
        self.executable_filename = executable_filename # 存储要启动的 app 的文件名
        self.process = QProcess(self) # QProcess 的父对象是 API 自身，方便管理

        if sys.platform == 'win32':
            self.process_output_encoding = 'gbk'
        else:
            self.process_output_encoding = 'utf-8'

        self.process.readyReadStandardOutput.connect(self._on_ready_read_standard_output)
        self.process.readyReadStandardError.connect(self._on_ready_read_standard_error)
        self.process.finished.connect(self._on_process_finished)
        self.process.errorOccurred.connect(self._on_qprocess_error_occurred)

    def _get_executable_path(self, executable_name):
        """在目录下查找可执行文件的完整路径。"""
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        executable_dir = os.path.join(root_dir, "build")
        # executable_dir = os.path.join(root_dir, "bin")

        if sys.platform == 'win32' and not executable_name.lower().endswith(('.py', '.bat', '.cmd', '.exe')):
            executable_name += ".exe"

        full_path = os.path.join(executable_dir, executable_name)

        if not os.path.exists(full_path): # 不在这里直接显示 warning，而是返回 None，让调用者处理
            self.parent_gui.warning("Executable not found", f"[API._get_executable_path] Error: Executable not found at '{full_path}'")
            return None
        return full_path

    def _on_ready_read_standard_output(self):
        """读取 QProcess 的标准输出并发出自定义信号。"""
        output = self.process.readAllStandardOutput().data().decode(self.process_output_encoding, errors='replace')
        self.standardOutputReady.emit(self.terminal_object_name, output)

    def _on_ready_read_standard_error(self):
        """读取 QProcess 的标准错误输出并发出自定义信号。"""
        error_output = self.process.readAllStandardError().data().decode(self.process_output_encoding, errors='replace')
        self.standardErrorReady.emit(self.terminal_object_name, error_output)

    def _on_process_finished(self, exitCode: int, exitStatus: QProcess.ExitStatus):
        """处理 QProcess 进程结束事件并发出自定义信号。"""
        self.processFinished.emit(self.terminal_object_name, exitCode, exitStatus)

    def _on_qprocess_error_occurred(self, error: QProcess.ProcessError):
        """处理 QProcess 自身发生的错误并发出自定义信号。"""
        error_messages = {
            QProcess.FailedToStart: "Failed to start process (program not found or permissions issue).",
            QProcess.Crashed: "Process crashed.",
            QProcess.Timedout: "Process timed out.",
            QProcess.ReadError: "Read error occurred.",
            QProcess.WriteError: "Write error occurred.",
            QProcess.UnknownError: "An unknown error occurred."
        }
        error_msg = error_messages.get(error, "An unknown process error occurred.")
        self.processErrorOccurred.emit(self.terminal_object_name, error_msg)

    def start_app_process(self):
        """启动关联的外部应用程序进程。"""
        if self.process.state() != QProcess.NotRunning: # 如果进程已经在运行，先尝试终止它，避免重复启动
            self.terminate_app_process()

        executable_path = self._get_executable_path(self.executable_filename)
        if not executable_path: # 如果路径无效，发出错误信号并返回 False
            self.processErrorOccurred.emit(self.terminal_object_name, f"Error: Executable '{self.executable_filename}' not found.")
            return False

        self.process.start(executable_path)
        if not self.process.waitForStarted(1500): # 等待1.5秒
            error_msg = f"Failed to start process '{executable_path}': {self.process.errorString()}"
            self.processErrorOccurred.emit(self.terminal_object_name, error_msg)
            return False
        return True

    def send_input_to_app(self, data: str):
        """向关联的应用程序进程的标准输入发送数据。"""
        if self.process.state() == QProcess.Running: # 将数据写入 QProcess 的标准输入 必须添加换行符，因为你的 app 预期通过换行符来结束一行输入
            self.process.write((data + '\n').encode('utf-8'))
        else:
            self.processErrorOccurred.emit(self.terminal_object_name, "Error: Application process is not running. Cannot send input.")

    def terminate_app_process(self):
        """终止关联的应用程序进程并清理资源。"""
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate() # 尝试正常终止进程
            if not self.process.waitForFinished(1000): # 等待1秒让进程退出
                self.process.kill() # 如果未退出，则强制杀死