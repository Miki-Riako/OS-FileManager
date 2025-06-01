import os
import sys # 主要用于 sys.executable 如果你的 "app" 是 .py 脚本

from PySide6.QtCore import QObject, Signal, QProcess, QIODeviceBase, Qt

class API(QObject):
    # 自定义信号
    standardOutputReady = Signal(str) # 当有标准输出时发出
    standardErrorReady = Signal(str)  # 当有标准错误时发出
    processFinished = Signal(int, QProcess.ExitStatus) # 当进程结束时发出 (exitCode, exitStatus)
    processErrorOccurred = Signal(str) # 当进程启动或运行时发生一般性错误

    def __init__(self, parent_workspace, executable_filename):
        super().__init__(parent_workspace) # parent_workspace 是 Workspace 实例
        self.terminal_widget = parent_workspace
        self.process = QProcess(self)
        self.executable_path = self._get_executable_path(executable_filename)

        if not self.executable_path:
            # 如果路径无效，立即发出错误信号
            # QTimer.singleShot(0, lambda: self.processErrorOccurred.emit(f"Error: Executable '{executable_filename}' not found."))
            # ^ 使用 QTimer.singleShot 确保信号在事件循环中发出，如果 parent_workspace 尚未完全初始化
            # 更简单的方式是在 Workspace 中检查 self.api.executable_path 是否为 None
            return # 阻止进一步初始化如果路径无效

        # 连接QProcess的信号到内部槽函数
        self.process.readyReadStandardOutput.connect(self._on_ready_read_standard_output)
        self.process.readyReadStandardError.connect(self._on_ready_read_standard_error)
        self.process.finished.connect(self._on_process_finished)
        self.process.errorOccurred.connect(self._on_qprocess_error_occurred) # QProcess内部错误

        # 准备启动
        # 假设 'executable_filename' 是一个直接的可执行文件 (如 C++ 编译的)
        # 如果是 .py 脚本，则应为: self.process.start(sys.executable, [self.executable_path])
        self.process.start(self.executable_path, [])

        # waitForStarted 可以用于检查是否立即启动成功，但对于长期运行的进程，
        # 主要的交互是通过信号。
        if not self.process.waitForStarted(1500): # 等待1.5秒
            # 如果不是因为超时 (即进程仍在启动中)，而是其他错误
            if self.process.error() != QProcess.ProcessError.Timedout:
                 self.processErrorOccurred.emit(f"Failed to start process '{self.executable_path}': {self.process.errorString()}")
            # 如果是超时，我们假设它可能仍在后台启动，输出将通过信号到达
            # 或者可以认为启动失败
            # else:
            #    self.processErrorOccurred.emit(f"Process '{self.executable_path}' timed out on start.")


    def _get_executable_path(self, executable_name):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bin_dir = os.path.join(root_dir, "bin")

        # if os.name == 'nt':  # Windows
        #     # 避免给.py文件错误地添加.exe
        #     if not executable_name.lower().endswith(('.py', '.bat', '.cmd')) and \
        #        not executable_name.lower().endswith('.exe'):
        #         executable_name += ".exe"
        
        full_path = os.path.join(bin_dir, executable_name)

        if not os.path.exists(full_path):
            # self.terminal_widget.warning("Path Error", f"Executable '{full_path}' not found.")
            # API 初始化时调用 terminal_widget.warning 可能过早，使用print或后续信号
            print(f"[API._get_executable_path] Error: Executable not found at '{full_path}'")
            return None
        return full_path

    def _on_ready_read_standard_output(self):
        data = self.process.readAllStandardOutput().data().decode('gbk', errors='replace')
        self.standardOutputReady.emit(data)

    def _on_ready_read_standard_error(self):
        data = self.process.readAllStandardError().data().decode('gbk', errors='replace')
        self.standardErrorReady.emit(data)

    def _on_process_finished(self, exit_code, exit_status: QProcess.ExitStatus):
        # 在发出 finished 信号前，确保所有剩余的输出都被读取
        remaining_out = self.process.readAllStandardOutput().data().decode(errors='replace')
        if remaining_out:
            self.standardOutputReady.emit(remaining_out)
        remaining_err = self.process.readAllStandardError().data().decode(errors='replace')
        if remaining_err:
            self.standardErrorReady.emit(remaining_err)
        self.processFinished.emit(exit_code, exit_status)

    def _on_qprocess_error_occurred(self, error: QProcess.ProcessError):
        # 这个信号在 QProcess 遇到问题时发出，如启动失败、崩溃等
        self.processErrorOccurred.emit(f"QProcess Error: {self.process.errorString()} (Code: {error})")

    def send_input_to_process(self, text: str):
        if self.process.state() == QProcess.ProcessState.Running:
            if not text.endswith('\n'): # 很多CLI程序期望输入以换行结束
                text += '\n'
            bytes_written = self.process.write(text.encode())
            if bytes_written == -1:
                self.standardErrorReady.emit("Error: Failed to write to process stdin.\n")
        else:
            self.standardErrorReady.emit("Error: Cannot send input, process is not running.\n")

    def stop_process(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate() # 尝试友好关闭
            if not self.process.waitForFinished(1000): # 等待1秒
                self.process.kill() # 强制关闭
                self.standardErrorReady.emit("Process forcefully killed.\n")
        self.process.close() # 清理资源

    def is_running(self):
        return self.process.state() == QProcess.ProcessState.Running