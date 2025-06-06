import json
import re

from pathlib import Path

from PySide6.QtCore import Qt, QSize, QProcess, QEvent, QTimer, Signal
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
    INITIALIZING = "INITIALIZING" # 表示 Shell 刚刚启动，等待登录

class Terminal(QWidget):
    explorerCommandOutputReady = Signal(str, str, bool, str, str) # 用于 Explorer
    requestExplorerRefresh = Signal()
    editorContentReady = Signal(str, str, bool, str)
    editorSaveComplete = Signal(str, bool, str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setConfig()

        self.vBoxLayout = QVBoxLayout(self)
        self.tabBoxLayout = QHBoxLayout()
        self.tabBar = TabBar(self)
        self.runButton = TransparentToolButton(FIF.PLAY.icon(color=QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)), self)
        self.runShortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.stackedWidget = QStackedWidget(self)

        self.next_unique_tab_id = 0
        self.terminal_apis = {}
        self.input_start_indices = {}
        self.terminal_modes = {}
        self.password_buffers = {}
        self.current_paths_by_terminal = {}

        # 状态追踪：用于Explorer的命令执行
        self._explorer_pending_requests = {} # {terminal_object_name: {"output_buffer": []}}
        self._explorer_current_api_obj_name = None # 当前Explorer正在使用的API实例的object_name
        self._explorer_command_sent_at_index = -1 # 标记命令发送时PlaintextEdit的文本长度

        self.login_username_prompt_regex = re.compile(r"host@login:Username\$ ")
        self.login_password_prompt_regex = re.compile(r"host@login:Password\$ ")
        self.sudo_password_prompt_regex = re.compile(r"\[sudo\] password for .*?:\s")
        self.main_shell_prompt_regex = re.compile(r"OSFileSystem@[\w\.-]+:.*?\$\s")

        self.__initWidget()
        self.setObjectName(text.replace(' ', '-'))

    def __initWidget(self):
        self.__initLayout()
        self.__initButton()
        self.__initShortcut()
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

    def __initButton(self):
        self.runButton.clicked.connect(self.run)

    def __initShortcut(self):
        self.runShortcut.activated.connect(self.run)

    def _get_terminal_widget_by_object_name(self, object_name: str) -> PlainTextEdit:
        """根据 objectName 获取对应的 PlainTextEdit 实例。"""
        return self.stackedWidget.findChild(PlainTextEdit, object_name)

    def _append_to_terminal(self, text_edit: PlainTextEdit, text: str, is_error: bool = False, is_prompt: bool = False):
        """辅助方法：向指定 PlainTextEdit 追加文本，并处理光标和可能的颜色。"""
        if '\x0c' in text: # 移除换页符，防止它干扰后续文本显示和高亮
            text = text.replace('\x0c', '')

        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.insertPlainText(text)

        # 确保光标在文本末尾并可见
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
        search_text = full_text[-2000:] # 检查最后个字符，避免对超长文本进行全匹配

        for regex, mode in prompt_patterns: # 遍历所有提示符类型，找到它们在 full_text 中最后一次出现的位置
            match = None
            for m in regex.finditer(search_text): # 使用 finditer 找到所有匹配，并取最后一个（最靠后的）
                match = m
            if match: # 转换回 full_text 的绝对位置
                potential_prompts.append((len(full_text) - len(search_text) + match.end(), mode))

        potential_prompts.sort(key=lambda x: x[0]) # 根据匹配的结束位置进行排序，最新的提示符在列表末尾
        new_mode = TerminalInputMode.NORMAL # 默认模式和输入位置：如果没有识别到特定提示符，则默认为普通模式，输入位置在文本末尾
        new_input_start_index = len(full_text)

        if potential_prompts:
            latest_match_end_pos, latest_mode = potential_prompts[-1] # 取列表中最后一个（即位置最靠后，最新的）提示符来决定当前模式和输入起始位置
            new_mode = latest_mode
            new_input_start_index = latest_match_end_pos
        else:
            if not full_text.strip() and self.terminal_apis.get(self.stackedWidget.currentWidget().objectName()).state() == QProcess.Running:
                new_mode = TerminalInputMode.INITIALIZING
            else: # 否则，默认为正常模式，等待用户输入
                new_mode = TerminalInputMode.NORMAL
        return new_mode, new_input_start_index

    def _process_special_command_output_output(self, terminal_object_name: str, output: str, is_error: bool = False):
        """处理来自 API 的标准输出信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if not text_edit:
            return
        self._append_to_terminal(text_edit, output, is_error)
        full_text = text_edit.document().toPlainText()

        self.terminal_modes[terminal_object_name],\
        self.input_start_indices[terminal_object_name]\
            = self._determine_terminal_state(full_text)

        extracted_path = "~"
        prompt_matches = list(self.main_shell_prompt_regex.finditer(full_text)) # 重新从 full_text 中匹配最新的主 shell 提示符，提取路径
        if prompt_matches:
            last_prompt_match = prompt_matches[-1] # 取最后一个匹配，确保是最新提示符
            prompt_full_text = last_prompt_match.group(0).strip()
            path_start_index = prompt_full_text.find(":") + 1
            path_end_index = prompt_full_text.rfind("$") # 使用 rfind 确保找到最后一个 $
            if path_start_index != -1 and path_end_index != -1 and path_start_index < path_end_index:
                extracted_path_from_prompt = prompt_full_text[path_start_index:path_end_index].strip()
                if extracted_path_from_prompt == "":
                    extracted_path = "~"
                else:
                    extracted_path = extracted_path_from_prompt.replace('//', '/')
        self.current_paths_by_terminal[terminal_object_name] = extracted_path

        if terminal_object_name == self._explorer_current_api_obj_name and self._explorer_command_sent_at_index != -1:
            self._process_special_command_output(terminal_object_name, output, is_error, full_text)

    def _process_special_command_output(self, terminal_obj_name: str, output: str, is_error, full_text: str):
        """处理来自 API 的标准输出信号，专门用于 Explorer 和 Editor 的后台命令。"""
        if terminal_obj_name not in self._explorer_pending_requests:
            return

        request_info = self._explorer_pending_requests[terminal_obj_name]
        request_info["output_buffer"].append(output) # 累积所有输出
        full_buffered_output = "".join(request_info["output_buffer"])
        current_mode = self.terminal_modes.get(terminal_obj_name)

        command_is_complete = False
        if current_mode == TerminalInputMode.NORMAL:
            prompt_matches = list(self.main_shell_prompt_regex.finditer(full_buffered_output))
            if prompt_matches:
                last_prompt_match = prompt_matches[-1] # 确保最后一个提示符在缓冲输出的末尾附近，才认为是命令完成
                if full_buffered_output.strip().endswith(last_prompt_match.group(0).strip()):
                    command_is_complete = True

        if is_error and command_is_complete: # 如果收到了错误输出且命令似乎已完成
            self._handle_special_command_completion(terminal_obj_name, full_buffered_output, True) # 标记为失败并完成
            return

        if command_is_complete:
            self._handle_special_command_completion(terminal_obj_name, full_buffered_output, False)

    def _handle_special_command_completion(self, terminal_obj_name: str, full_buffered_output: str, force_error: bool = False):
        """
        处理特殊命令（Explorer 或 Editor）完成后的逻辑。
        force_error: 标记为真表示即使没有明显的错误提示符，也应将此操作视为失败。
        """
        request_info = self._explorer_pending_requests.get(terminal_obj_name)
        if not request_info:
            return

        issued_command_type = request_info.get("command_type", "unknown")
        file_path_for_editor = request_info.get("file_path", "")
        command_queue = request_info.get("command_queue", [])
        
        # 查找最后一个提示符以截断输出
        prompt_match = self.main_shell_prompt_regex.search(full_buffered_output)
        output_to_process = full_buffered_output
        if prompt_match:
            prompt_text = prompt_match.group(0)
            prompt_start_index = full_buffered_output.rfind(prompt_text)
            if prompt_start_index != -1:
                output_to_process = full_buffered_output[:prompt_start_index].strip()
            
        request_info["output_buffer"].clear() # 清空缓冲区

        if issued_command_type == "save_file_content":
            # 如果是保存命令，检查命令队列
            if command_queue: # 还有命令在队列中
                next_command = command_queue.pop(0) # 取出下一条命令
                api = self.terminal_apis.get(terminal_obj_name)
                if api:
                    # 避免在错误状态下继续发送命令
                    if force_error:
                        self._reset_special_command_state(terminal_obj_name)
                        self.editorSaveComplete.emit(file_path_for_editor, False, "保存操作中途发生错误。")
                        return

                    self._append_to_terminal(self._get_terminal_widget_by_object_name(terminal_obj_name), next_command + '\n')
                    api.send_input_to_app(next_command)
                else:
                    self._reset_special_command_state(terminal_obj_name)
                    self.editorSaveComplete.emit(file_path_for_editor, False, "API实例丢失，无法继续保存操作。")
            else: # 命令队列为空，所有保存命令已发送完毕
                self._reset_special_command_state(terminal_obj_name)
                self.editorSaveComplete.emit(file_path_for_editor, not force_error, "" if not force_error else "保存操作失败。")
        else: # 处理 Explorer 命令完成
            self._reset_special_command_state(terminal_obj_name) # Reset Explorer state (important!)
            if issued_command_type == "cat_file_content":
                self.editorContentReady.emit(
                    file_path_for_editor,
                    output_to_process,
                    not force_error,
                    "" if not force_error else "Failed to retrieve file content."
                )
            elif issued_command_type.startswith("cd"):
                self.explorerCommandOutputReady.emit(
                    terminal_obj_name,
                    output_to_process,
                    not force_error,
                    "" if not force_error else "CD command failed.",
                    issued_command_type
                )
                if not force_error:
                    self.requestExplorerRefresh.emit()
            elif issued_command_type.startswith("ls"):
                self.explorerCommandOutputReady.emit(
                    terminal_obj_name,
                    output_to_process,
                    not force_error,
                    "" if not force_error else "LS command failed.",
                    issued_command_type
                )
            else: # For "other" or unknown commands
                self.explorerCommandOutputReady.emit(
                    terminal_obj_name,
                    output_to_process,
                    not force_error,
                    "",
                    issued_command_type
                )

    def _reset_special_command_state(self, terminal_object_name: str):
        """重置特殊命令处理状态。"""
        self._explorer_command_sent_at_index = -1
        self._explorer_current_api_obj_name = None
        self._explorer_pending_requests.pop(terminal_object_name, None)

    def _send_special_command_error(self, terminal_object_name: str, error_message: str, original_command_type: str, file_path: str = ""):
        if original_command_type == "cat_file_content" or original_command_type == "save_file_content":
            self.editorContentReady.emit(file_path, "", False, error_message) if original_command_type == "cat_file_content" else self.editorSaveComplete.emit(file_path, False, error_message)
        else: # Explorer commands
            self.explorerCommandOutputReady.emit(
                terminal_object_name,
                "", # 无输出
                False, # 失败
                error_message,
                original_command_type
            )
        self._reset_special_command_state(terminal_object_name)

    def _process_special_command_output_finished(self, terminal_object_name: str, exitCode: int, exitStatus: QProcess.ExitStatus):
        """处理来自 API 的进程结束信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            status_str = "正常退出" if exitStatus == QProcess.NormalExit else "崩溃"
            self._append_to_terminal(text_edit, f"\n进程已结束，退出码: {exitCode} ({status_str})\n", is_error=True)
            terminal_api = self.terminal_apis.get(terminal_object_name) # 进程结束后重新启动Shell。新的提示符会在 API 重新启动成功后打印
            if terminal_api:
                self._append_to_terminal(text_edit, "尝试重新启动 Shell...\n")
                if not terminal_api.start_app_process(): # 重新启动应用程序
                    self._append_to_terminal(text_edit, "重新启动 Shell 失败。\n", is_error=True)
                    if terminal_object_name == self._explorer_current_api_obj_name:
                        self._send_special_command_error(terminal_object_name, f"Shell process crashed or failed to restart: {status_str}")

    def _process_special_command_output_error_occurred(self, terminal_object_name: str, error_message: str):
        """处理来自 API 的 QProcess 错误信号。"""
        text_edit = self._get_terminal_widget_by_object_name(terminal_object_name)
        if text_edit:
            self._append_to_terminal(text_edit, f"\nAPI 错误: {error_message}\n", is_error=True)
            self.input_start_indices[terminal_object_name] = len(text_edit.document().toPlainText())
            cursor = text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            text_edit.setTextCursor(cursor)
            text_edit.ensureCursorVisible()
            if terminal_object_name == self._explorer_current_api_obj_name:
                self._send_special_command_error(terminal_object_name, f"API process error: {error_message}")

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
        # 特殊处理 'clear' 命令
        if input_data.strip().lower() == "clear" and current_mode == TerminalInputMode.NORMAL:
            text_edit.clear()
            self.input_start_indices[object_name] = 0 # 重置输入起始位置
            terminal_api.send_input_to_app(input_data) # 仍然将命令发送给后端
            return
        # 删除用户在PlaintextEdit中输入的部分（如果是密码模式则无实际可见删除）
        cursor.setPosition(input_start_index)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        text_edit.setTextCursor(cursor)
        # 模拟用户在UI上看到输入
        if current_mode == TerminalInputMode.NORMAL:
            text_edit.insertPlainText(input_data + '\n') # 重新插入用户输入的命令，后面跟一个换行符，模拟用户按Enter
        else: # 密码模式只插入换行符，不显示密码
            text_edit.insertPlainText('\n')

        terminal_api.send_input_to_app(input_data)
        self.input_start_indices[object_name] = len(text_edit.document().toPlainText()) # 更新输入起始位置到当前文本末尾
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def get_current_api(self) -> API | None:
        """返回当前激活的终端标签页对应的 API 实例。"""
        current_tab_item = self.tabBar.currentTab()
        if not current_tab_item:
            return None
        current_object_name = current_tab_item.routeKey()
        return self.terminal_apis.get(current_object_name)

    def get_terminal_mode(self, terminal_object_name: str) -> TerminalInputMode:
        return self.terminal_modes.get(terminal_object_name, TerminalInputMode.INITIALIZING)

    def execute_command_for_explorer(self, command: str) -> bool:
        """为 Explorer 执行命令。命令的输出会通过 explorerCommandOutputReady 信号发出。返回 True 表示命令已发送，False 表示无法发送（如无活跃终端）。 """
        api = self.get_current_api()
        if not api:
            self.warning("警告", "没有激活的终端API实例可供Explorer使用。")
            self.explorerCommandOutputReady.emit("", "", False, "No active terminal API for Explorer.", "")
            return False
        terminal_obj_name = api.terminal_object_name
        text_edit = self._get_terminal_widget_by_object_name(terminal_obj_name)
        if not text_edit:
            self.warning("警告", f"未找到终端UI组件 '{terminal_obj_name}'。")
            self.explorerCommandOutputReady.emit(terminal_obj_name, "", False, f"No UI widget for '{terminal_obj_name}'.", "")
            return False
        if self._explorer_current_api_obj_name is not None:
            self.warning("警告", "Explorer命令正在进行中，请稍后。")
            self.explorerCommandOutputReady.emit(terminal_obj_name, "", False, "Another Explorer command is already in progress.", "")
            return False
        current_terminal_mode = self.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._send_special_command_error(terminal_obj_name, f"终端未就绪（当前模式：{current_terminal_mode}）。请先在 '终端管理器' 标签页登录。", command)
            return False
        self._explorer_current_api_obj_name = terminal_obj_name
        self._explorer_command_sent_at_index = len(text_edit.document().toPlainText()) # 记录当前文本长度。

        command_lower = command.lower().strip()
        cmd_type = "cd" if command_lower.startswith("cd") else "ls" if command_lower.startswith("ls") else "other"
        self._explorer_pending_requests[terminal_obj_name] = {
            "output_buffer": [],
            "command_type": cmd_type
        }

        self._append_to_terminal(text_edit, command + '\n') # 注意：这行内容是 GUI 自己的显示，不是来自 Shell 的回显
        api.send_input_to_app(command)
        return True

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
                        return True # 阻止 Delete 键的默认行为
                if is_password_or_sudo_mode: # 处理密码输入模式下的字符显示 (什么都不显示)
                    # 如果光标不在用户输入区域（提示符后面），强制移到正确位置
                    if current_cursor.position() < input_start_index:
                        current_cursor.setPosition(input_start_index)
                        text_edit.setTextCursor(current_cursor)
                    if key_text and key_text.isprintable(): # 对于所有可打印字符，添加到内部缓冲区，但不显示在 PlainTextEdit 上
                        password_buffer = self.password_buffers.get(object_name, "")
                        self.password_buffers[object_name] = password_buffer + key_text
                        current_cursor = text_edit.textCursor() # 确保光标在文本末尾，但不要插入任何字符到 PlainTextEdit
                        current_cursor.movePosition(QTextCursor.End)
                        text_edit.setTextCursor(current_cursor)
                        return True # 消费事件，阻止 PlainTextEdit 默认处理 (即显示字符)
                return super().eventFilter(watched_object, event) # 如果不是密码模式，或不是特殊处理的键，则允许 PlainTextEdit 正常处理
            elif event.type() == QEvent.Type.MouseButtonPress: # 阻止鼠标点击/拖动光标到提示符之前
                text_edit = watched_object
                object_name = text_edit.objectName()
                input_start_index = self.input_start_indices.get(object_name, 0)
                cursor_at_click = text_edit.cursorForPosition(event.position().toPoint())
                if cursor_at_click.position() < input_start_index:
                    QTimer.singleShot(0, lambda: text_edit.textCursor().setPosition(input_start_index))
                    return True # 消费事件，阻止默认行为
            elif event.type() == QEvent.Type.ContextMenu: # 阻止右键菜单，如果需要
                return True # 阻止右键菜单
        return super().eventFilter(watched_object, event)

    def addTerminalTab(self, widget: PlainTextEdit, objectName, text, icon):
        widget.setObjectName(objectName)
        widget.setFont(QFont(self.font_family, self.font_size))
        widget.setPlaceholderText("Command prompt...")
        self.terminal_modes[objectName] = TerminalInputMode.INITIALIZING # 初始化模式为 INITIALIZING，等待 Shell 启动和登录
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
        # self.tabBar.setCurrentTab(objectName) # 有bug暂时别用
        terminal_api = API(objectName, "app", self)
        self.terminal_apis[objectName] = terminal_api # 存储起来
        terminal_api.standardOutputReady.connect(self._process_special_command_output_output)
        terminal_api.standardErrorReady.connect(lambda obj_name, error_output: self._process_special_command_output_output(obj_name, error_output, True))
        terminal_api.processFinished.connect(self._process_special_command_output_finished)
        terminal_api.processErrorOccurred.connect(self._process_special_command_output_error_occurred)
        if not terminal_api.start_app_process():
            self.warning("启动失败", f"无法启动终端进程 {objectName}。")

    def onTabCloseRequested(self, index: int):
        tab_item = self.tabBar.tabItem(index)
        route_key = tab_item.routeKey()
        if route_key == self._explorer_current_api_obj_name: # 如果关闭的是 Explorer 正在使用的终端，重置 Explorer 的状态
            self._explorer_current_api_obj_name = None
            self._explorer_command_sent_at_index = -1
            self._explorer_pending_requests.pop(route_key, None)

        terminal_api = self.terminal_apis.get(route_key)
        if terminal_api:
            terminal_api.terminate_app_process() # 告诉 API 终止其管理的 Shell 进程
            del self.terminal_apis[route_key] # 从字典中移除引用
            terminal_api.deleteLater() # 销毁 API 对象

        self.terminal_modes.pop(route_key, None) # 移除模式和密码缓冲区状态
        self.input_start_indices.pop(route_key, None)
        self.password_buffers.pop(route_key, None)
        self.current_paths_by_terminal.pop(route_key, None)

        widget_to_remove = self.stackedWidget.findChild(PlainTextEdit, route_key)
        if widget_to_remove:
            self.stackedWidget.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None) # 解除父子关系
            widget_to_remove.deleteLater()   # 将 widget 标记为待删除，在事件循环空闲时销毁

        self.tabBar.removeTab(index)
        if self.tabBar.count() == 0:
            self.onTabAddRequested()

    def onTabChanged(self, index: int):
        route_key = self.tabBar.tabItem(index).routeKey()
        target_widget = self.stackedWidget.findChild(PlainTextEdit, route_key)
        if target_widget:
            self.stackedWidget.setCurrentWidget(target_widget)
            cursor = target_widget.textCursor() # 确保切换后光标在正确位置
            cursor.movePosition(QTextCursor.End)
            target_widget.setTextCursor(cursor)
            target_widget.ensureCursorVisible()

    def onTabAddRequested(self):
        current_id = self.next_unique_tab_id
        new_tab_name = f"Bash-{current_id + 1}"
        new_tab_text = f"Bash {current_id + 1}"
        new_terminal_edit = PlainTextEdit(self)
        self.addTerminalTab(new_terminal_edit, new_tab_name, new_tab_text, FIF.COMMAND_PROMPT)
        self.next_unique_tab_id += 1
        # self.tabBar.setCurrentTab(new_tab_name) # 有bug，先不用

    def run(self):
        current_widget = self.stackedWidget.currentWidget()
        if not isinstance(current_widget, PlainTextEdit):
            self.warning('警告', '当前没有激活的终端。')
            return
        api = self.get_current_api()
        if not api or api.state() != QProcess.Running:
            self.warning("警告", "终端进程未运行。请稍后或尝试重新启动。")
            return
        terminal_obj_name = api.terminal_object_name
        current_mode = self.get_terminal_mode(terminal_obj_name)
        if current_mode != TerminalInputMode.NORMAL:
            self.warning("警告", "终端未就绪（请先登录）。")
            return
        self.requestExplorerRefresh.emit() # 如果终端就绪，发出信号请求 Explorer 刷新
        self.inform("提示", "已请求资源管理器刷新目录。")

    def inform(self, title, content):
        InfoBar.info(
            title=title,
            content=content,
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

    def request_file_content_for_editor(self, file_path: str) -> bool:
        api = self.get_current_api()
        if not api:
            self._send_special_command_error("", "没有激活的终端API实例可供编辑器使用。", "cat_file_content", file_path)
            return False

        terminal_obj_name = api.terminal_object_name
        text_edit = self._get_terminal_widget_by_object_name(terminal_obj_name)
        if not text_edit:
            self._send_special_command_error(terminal_obj_name, f"未找到终端UI组件 '{terminal_obj_name}'。", "cat_file_content", file_path)
            return False

        if self._explorer_current_api_obj_name is not None:
            self._send_special_command_error(terminal_obj_name, "已有命令正在进行中，请稍后。", "cat_file_content", file_path)
            return False

        current_terminal_mode = self.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._send_special_command_error(terminal_obj_name, f"终端未就绪（当前模式：{current_terminal_mode}）。请先在 '终端管理器' 标签页登录。", "cat_file_content", file_path)
            return False

        self._explorer_current_api_obj_name = terminal_obj_name
        self._explorer_command_sent_at_index = len(text_edit.document().toPlainText()) # Record current text length.

        # Store file path and command type
        self._explorer_pending_requests[terminal_obj_name] = {
            "output_buffer": [],
            "command_type": "cat_file_content",
            "file_path": file_path, # Store the file path for the signal
            "command_queue": [] # For cat, no queue needed, just one command
        }

        command_to_send = f"cat \"{file_path}\"" # 确保文件路径包含空格时也能正确处理
        self._append_to_terminal(text_edit, command_to_send + '\n') # Show the command in the terminal
        api.send_input_to_app(command_to_send)
        return True

    def save_file_content_from_editor(self, file_path: str, content: str) -> bool:
        api = self.get_current_api()
        if not api:
            self._send_special_command_error("", "没有激活的终端API实例可供编辑器使用。", "save_file_content", file_path)
            return False

        terminal_obj_name = api.terminal_object_name
        text_edit = self._get_terminal_widget_by_object_name(terminal_obj_name)
        if not text_edit:
            self._send_special_command_error(terminal_obj_name, f"未找到终端UI组件 '{terminal_obj_name}'。", "save_file_content", file_path)
            return False

        if self._explorer_current_api_obj_name is not None:
            self._send_special_command_error(terminal_obj_name, "已有命令正在进行中，请稍后。", "save_file_content", file_path)
            return False

        current_terminal_mode = self.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._send_special_command_error(terminal_obj_name, f"终端未就绪（当前模式：{current_terminal_mode}）。请先在 '终端管理器' 标签页登录。", "save_file_content", file_path)
            return False

        lines = content.splitlines()
        commands = []
        if lines:
            # 第一行使用 > 覆盖
            escaped_first_line_content = lines[0].replace('"', '\\"')
            commands.append(f'echo "{escaped_first_line_content}" > {file_path}')
            # 后续行使用 >> 追加
            for line in lines[1:]:
                escaped_line_content = line.replace('"', '\\"')
                commands.append(f'echo "{escaped_line_content}" >> {file_path}')
        else: # 如果内容为空，则清空文件
            commands.append(f'echo "" > {file_path}')

        self._explorer_current_api_obj_name = terminal_obj_name
        self._explorer_command_sent_at_index = len(text_edit.document().toPlainText())

        self._explorer_pending_requests[terminal_obj_name] = {
            "output_buffer": [],
            "command_type": "save_file_content",
            "file_path": file_path,
            "command_queue": commands # Store all commands to be executed sequentially
        }
        if commands: # Send the first command immediately
            first_command = commands.pop(0)
            self._append_to_terminal(text_edit, first_command + '\n')
            api.send_input_to_app(first_command)
            return True
        else: # Should not happen if lines processing is correct
            self._send_special_command_error(terminal_obj_name, "没有生成保存命令。", "save_file_content", file_path)
            return False

    def get_current_terminal_path(self, terminal_object_name: str) -> str:
        return self.current_paths_by_terminal.get(terminal_object_name, "~")