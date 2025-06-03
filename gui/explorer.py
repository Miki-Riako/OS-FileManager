from typing import List
import re
import os

from PySide6.QtCore import Qt, Signal, QUrl, QEvent, QProcess
from PySide6.QtGui import QDesktopServices, QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame

from qfluentwidgets import (ScrollArea, PushButton, FlowLayout, ToolButton, FluentIcon,
                            isDarkTheme, IconWidget, Theme, ToolTipFilter, TitleLabel, CaptionLabel,
                            SmoothScrollArea, SearchLineEdit, StrongBodyLabel, BodyLabel, toggleTheme,
                            InfoBar, InfoBarPosition)

from .trie import Trie
from .terminal import Terminal, TerminalInputMode

class FileData:
    """ Represents a file or directory in the simulated file system """
    def __init__(self, name: str, logical_path: str, is_directory: bool, uid: str, owner: str, access_string: str, creation_time_str: str, modified_time_str: str):
        self.name = name
        self.logical_path = logical_path
        self.is_directory = is_directory
        self.uid = uid
        self.owner = owner
        self.access_string = access_string
        self.creation_time_str = creation_time_str
        self.modified_time_str = modified_time_str
        self.size = 0 
        self.fluent_icon = self._determine_fluent_icon()

    def _determine_fluent_icon(self):
        if self.name == "..":
            return FluentIcon.RETURN # 更换为返回图标
        if self.is_directory:
            return FluentIcon.FOLDER
        else:
            return FluentIcon.DOCUMENT


class FileIcon(QFrame):
    clicked = Signal(FileData)
    doubleClicked = Signal(FileData)

    def __init__(self, file_data: FileData, parent=None):
        super().__init__(parent=parent)
        self.file_data = file_data
        self.isSelected = False
        try: # 确保图标是有效的 FluentIcon 枚举值
            self.iconWidget = IconWidget(file_data.fluent_icon, self)
        except Exception as e:
            print(f"Error creating IconWidget for {file_data.name} (icon: {file_data.fluent_icon}): {e}. Using default error icon.")
            self.iconWidget = IconWidget(FluentIcon.CANCEL, self) # 使用默认错误图标
        self.nameLabel = QLabel(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.setFixedSize(96, 96)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(8, 28, 8, 0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.iconWidget.setFixedSize(28, 28)
        self.vBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignHCenter)
        self.vBoxLayout.addSpacing(14)
        self.vBoxLayout.addWidget(self.nameLabel, 0, Qt.AlignHCenter)
        text = self.nameLabel.fontMetrics().elidedText(file_data.name, Qt.ElideRight, 90)
        self.nameLabel.setText(text)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.pos()): # 只有在鼠标点击位置在文件图标的有效区域内才处理
            self.clicked.emit(self.file_data) # 即使已经选中，也可以重新点击以确认选择
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.rect().contains(e.pos()):
            self.doubleClicked.emit(self.file_data)
        super().mouseDoubleClickEvent(e)

    def setSelected(self, isSelected: bool, force=False):
        if isSelected == self.isSelected and not force:
            return
        self.isSelected = isSelected
        if not isSelected:
            self.iconWidget.setIcon(self.file_data.fluent_icon)
        else: # 在选中状态下，使用强调色图标
            # FluentIcon.icon() 方法需要 Theme 参数来获取带颜色的图标
            accent_color = QColor(255, 140, 0) if isDarkTheme() else QColor(0, 120, 212) # 示例强调色
            self.iconWidget.setIcon(self.file_data.fluent_icon.icon(color=accent_color)) # 确保这里使用 QColor
        self.setProperty('isSelected', isSelected)
        self.setStyle(QApplication.style())


class FileInfoPanel(QFrame):
    def __init__(self, file_data: FileData = None, parent=None):
        super().__init__(parent=parent)
        self.nameLabel = StrongBodyLabel(self) # 名字标签更显眼
        self.iconWidget = IconWidget(self)
        self.pathTitleLabel = CaptionLabel('Path', self)
        self.pathLabel = BodyLabel(self)
        self.typeTitleLabel = CaptionLabel('Type', self)
        self.typeLabel = BodyLabel(self)
        self.sizeTitleLabel = CaptionLabel('Size', self)
        self.sizeLabel = BodyLabel(self)
        self.modifiedTitleLabel = CaptionLabel('Last Modified', self)
        self.modifiedLabel = BodyLabel(self)
        self.ownerTitleLabel = CaptionLabel('Owner', self)
        self.ownerLabel = BodyLabel(self)
        self.accessTitleLabel = CaptionLabel('Access', self)
        self.accessLabel = BodyLabel(self)
        self.creationTimeTitleLabel = CaptionLabel('Creation Time', self)
        self.creationTimeLabel = BodyLabel(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 20, 16, 20)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.addWidget(self.nameLabel)
        self.vBoxLayout.addSpacing(16)
        self.vBoxLayout.addWidget(self.iconWidget)
        self.vBoxLayout.addSpacing(25)
        self.vBoxLayout.addWidget(self.pathTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.pathLabel)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.typeTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.typeLabel)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.sizeTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.sizeLabel)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.ownerTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.ownerLabel)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.accessTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.accessLabel)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.creationTimeTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.creationTimeLabel)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.modifiedTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.modifiedLabel)
        self.vBoxLayout.addStretch(1)
        self.iconWidget.setFixedSize(48, 48)
        self.setFixedWidth(216)
        self.nameLabel.setObjectName('nameLabel')
        self.pathTitleLabel.setObjectName('subTitleLabel')
        self.typeTitleLabel.setObjectName('subTitleLabel')
        self.sizeTitleLabel.setObjectName('subTitleLabel')
        self.modifiedTitleLabel.setObjectName('subTitleLabel')
        self.ownerTitleLabel.setObjectName('subTitleLabel')
        self.accessTitleLabel.setObjectName('subTitleLabel')
        self.creationTimeTitleLabel.setObjectName('subTitleLabel')
        # 统一设置标签的字体和颜色
        for label in [self.pathLabel, self.typeLabel, self.sizeLabel, self.modifiedLabel, self.ownerLabel, self.accessLabel, self.creationTimeLabel]:
            label.setWordWrap(True) # 允许文本换行
            label.setStyleSheet("color: grey;") # 示例：设置字体颜色为灰色

        if file_data:
            self.setFileInfo(file_data)
        else:
            self.clearFileInfo()

    def setFileInfo(self, file_data: FileData):
        self.iconWidget.setIcon(file_data.fluent_icon)
        self.nameLabel.setText(file_data.name)
        self.pathLabel.setText(file_data.logical_path)
        if file_data.is_directory:
            self.typeLabel.setText("Folder")
        else:
            self.typeLabel.setText("File")
        self.sizeLabel.setText(self._format_size(file_data.size)) # size is always 0 for now, as per problem.
        self.modifiedLabel.setText(file_data.modified_time_str)
        self.ownerLabel.setText(file_data.owner)
        self.accessLabel.setText(file_data.access_string)
        self.creationTimeLabel.setText(file_data.creation_time_str)

    def clearFileInfo(self):
        self.iconWidget.setIcon(FluentIcon.INFO)
        self.nameLabel.setText("No item selected")
        self.pathLabel.setText("")
        self.typeLabel.setText("")
        self.sizeLabel.setText("")
        self.modifiedLabel.setText("")
        self.ownerLabel.setText("")
        self.accessLabel.setText("")
        self.creationTimeLabel.setText("")

    def _format_size(self, size_bytes: int):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileView(QWidget):
    def __init__(self, terminal_instance: Terminal, parent=None):
        super().__init__(parent=parent)
        self.terminal_instance = terminal_instance
        self.trie = Trie()
        self.current_path = "~" # Initial path in Explorer view, matches Shell's initial login path

        self._ls_output_regex = re.compile(
            r"^\s*(?P<fileName>.*?)\s*\|\s*(?P<uid>\d+)\s*\|\s*(?P<owner>.*?)\s*\|\s*(?P<access>[fdrwx\-]+)\s*\|\s*(?P<creation_time>[\d\-\s:]+)\s*\|\s*(?P<modified_time>[\d\-\s:]+)$"
        )
        self._prompt_regex = re.compile(r"FileSystem@[\w\.-]+:.*?\$\s")

        self.backButton = ToolButton(FluentIcon.RETURN, self)
        self.backButton.setToolTip("Go to parent folder")
        self.backButton.setFixedSize(32, 32)
        self.backButton.clicked.connect(self.go_up_directory)

        self.pathLabel = BodyLabel(f"Current Path: {self.current_path}", self)
        self.pathLabel.setContentsMargins(5,0,0,0)

        self.navLayout = QHBoxLayout()
        self.navLayout.setContentsMargins(0, 0, 0, 0)
        self.navLayout.setSpacing(5)
        self.navLayout.addWidget(self.backButton)
        self.navLayout.addWidget(self.pathLabel)
        self.navLayout.addStretch(1)

        self.searchLineEdit = SearchLineEdit(self)
        self.searchLineEdit.setPlaceholderText('Search files')
        self.searchLineEdit.setFixedWidth(500)

        self.view = QFrame(self)
        self.scrollArea = SmoothScrollArea(self.view)
        self.scrollWidget = QWidget(self.scrollArea)
        self.infoPanel = FileInfoPanel(parent=self)

        self.vBoxLayout = QVBoxLayout(self)
        self.hBoxLayout = QHBoxLayout(self.view)
        self.flowLayout = FlowLayout(self.scrollWidget, isTight=True)

        self.cards = []
        self.files_data = []
        self.currentIndex = -1

        # Connect the signal from Terminal to refresh Explorer
        self.terminal_instance.explorerCommandOutputReady.connect(self._handle_explorer_command_response)
        self.__initWidget() # Explorer 启动时为空，等待 Terminal 的 run 按钮触发

    def __initWidget(self):
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setViewportMargins(0, 5, 0, 5)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(12)
        self.vBoxLayout.addLayout(self.navLayout)
        self.vBoxLayout.addWidget(self.searchLineEdit)
        self.vBoxLayout.addWidget(self.view)

        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.scrollArea)
        self.hBoxLayout.addWidget(self.infoPanel, 0, Qt.AlignRight)

        self.flowLayout.setVerticalSpacing(8)
        self.flowLayout.setHorizontalSpacing(8)
        self.flowLayout.setContentsMargins(8, 3, 8, 8)

        self.searchLineEdit.clearSignal.connect(self.showAllFiles)
        self.searchLineEdit.searchSignal.connect(self.search)

        self.clear_file_display() # 初始化时清空显示，确保它最初是空的

    def _show_infobar(self, title, content, type_info: InfoBarPosition):
        InfoBar.info(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=type_info,
            duration=3000,
            parent=self
        )

    def clear_file_display(self):
        """ 清空文件显示区，包括卡片、数据和信息面板 """
        while self.flowLayout.count(): # 移除 FlowLayout 中的所有 widget
            item = self.flowLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater() # 延迟删除 widget

        self.cards.clear()
        self.files_data.clear()
        self.currentIndex = -1
        self.infoPanel.clearFileInfo()
        self.trie = Trie() # 重置 Trie
        self.pathLabel.setText("Current Path: (Empty)") # 显示为空状态

    def load_current_terminal_directory(self):
        """Public slot: 由 Terminal 的 Run 按钮触发，加载当前 Terminal 的目录。"""
        current_api = self.terminal_instance.get_current_api()
        if not current_api or current_api.state() != QProcess.Running:
            self._show_infobar("错误", "当前没有激活或运行中的终端实例。", InfoBarPosition.TOP)
            self.pathLabel.setText("Error: No active terminal.")
            self.clear_file_display() # 清空显示
            return

        terminal_obj_name = current_api.terminal_object_name
        current_terminal_mode = self.terminal_instance.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._show_infobar("请先登录", "请先在 '终端管理器' 标签页登录系统。", InfoBarPosition.TOP)
            self.pathLabel.setText("Please login in Terminal Manager first.")
            self.clear_file_display() # 清空显示
            return
        # 如果没有未完成的 Explorer 命令，并且终端处于 NORMAL 模式，则发送 ls -a
        if self.terminal_instance._explorer_current_api_obj_name is None:
            self.pathLabel.setText(f"Loading: {self.current_path}...") # 显示加载中
            self.terminal_instance.execute_command_for_explorer("ls -a") # 直接发送 ls -a，因为我们假设 Shell 的当前目录就是我们要显示的
        else:
            self._show_infobar("请稍候", "正在加载目录，请等待当前操作完成。", InfoBarPosition.TOP)


    def _handle_explorer_command_response(self, terminal_obj_name: str, raw_output: str, success: bool, error_msg: str):
        if self.terminal_instance._explorer_current_api_obj_name != terminal_obj_name: # 确认这是当前 Explorer 正在使用的终端实例的响应
            print(f"[Explorer] Ignoring output from {terminal_obj_name} as it's not the active Explorer API.")
            return

        if not success:
            self._show_infobar("命令失败", f"执行命令失败：{error_msg}", InfoBarPosition.TOP)
            self.pathLabel.setText(f"Error: {error_msg}")
            self.clear_file_display() # 出错时清空显示
            return

        match = self._prompt_regex.search(raw_output) # 获取命令执行后的真实当前路径
        if match: # 提取路径部分
            prompt_full = match.group(0).strip()
            path_start_index = prompt_full.find(":") + 1
            path_end_index = prompt_full.find("$")
            if path_start_index != -1 and path_end_index != -1 and path_start_index < path_end_index:
                extracted_path = prompt_full[path_start_index:path_end_index].strip()
                # 规范化路径，例如 "~/path" 或 "/path"
                if extracted_path == "": # 如果是根目录，可能解析为""
                    self.current_path = "~"
                else:
                    self.current_path = extracted_path.replace('//', '/') # 消除双斜杠
        # ls -a 的输出包含了表头，可以通过这个来判断
        # 即使是 cd 命令的响应，最终也会触发 ls -a 的输出，所以这里统一处理 ls -a 的解析
        # 只有 ls -a 命令的原始输出才包含表头和文件列表
        # 如果 raw_output 仅包含 cd 命令的提示符，_parse_ls_output_and_populate_cards 会自行判断并清空显示
        self._parse_ls_output_and_populate_cards(raw_output)
        self._show_infobar("目录加载成功", f"当前路径：{self.current_path}", InfoBarPosition.TOP)


    def _parse_ls_output_and_populate_cards(self, raw_output: str):
        """解析 ls -a 的原始输出，创建 FileData 对象，并填充 UI。"""
        self.clear_file_display() # 清空旧数据
        lines = raw_output.strip().split('\n')
        data_lines = []
        is_data_section = False

        for line_num, line in enumerate(lines):
            stripped_line = line.strip()
            # 改进 Header 检测：使用正则表达式来更精确地匹配表头行
            # 表头行通常以 "  fileName   | uid |" 这样的形式开始
            # 我们可以用一个正则表达式来匹配表头模式，而不是简单的 startsWith
            if re.search(r"^\s*fileName\s*\|\s*uid\s*\|", stripped_line) and not is_data_section:
                print(f"[DEBUG_EXPLORER] Detected header line at line {line_num}: '{stripped_line}'")
                is_data_section = True
                continue # 跳过表头行
            # 检测到提示符且在数据段内，表示数据段结束
            if is_data_section and self._prompt_regex.search(stripped_line):
                print(f"[DEBUG_EXPLORER] Detected prompt at line {line_num}, ending data section: '{stripped_line}'")
                is_data_section = False
                break # 退出循环，不再处理后续行
            # 如果在数据段内且行不为空，则添加到 data_lines
            if is_data_section and stripped_line:
                data_lines.append(stripped_line)
                # print(f"[DEBUG_EXPLORER] Added data line: '{stripped_line}'") # 可以打开此行进行详细调试

        parsed_data = []
        for line_num, line in enumerate(data_lines):
            match = self._ls_output_regex.match(line)
            if match:
                data = match.groupdict()
                # Apply .strip() to all captured groups to remove whitespace
                name = data['fileName'].strip()
                uid = data['uid'].strip()
                owner = data['owner'].strip()
                access_string = data['access'].strip()
                creation_time_str = data['creation_time'].strip()
                modified_time_str = data['modified_time'].strip()

                is_dir = access_string.startswith('d')
                # 为每个条目构建逻辑路径 (当前路径 + 文件名)
                item_logical_path = ""
                if name == ".":
                    item_logical_path = self.current_path
                elif name == "..":
                    # Calculate parent path
                    parts = self.current_path.split('/')
                    if parts and parts[-1] == '': # Handle trailing slash for root or empty path parts
                        parts = parts[:-1]
                    if not parts or (len(parts) == 1 and (parts[0] == '~' or parts[0] == '/')):
                        item_logical_path = '~' # Already at root, parent is still root (represented by ~)
                    else:
                        temp_path = '/'.join(parts[:-1])
                        if temp_path == '': # e.g., from "/dir" to "/", new_path becomes empty. Set to "/"
                            item_logical_path = '/'
                        else:
                            item_logical_path = temp_path
                    # Standardize '/' and '~' representations for root paths
                    if item_logical_path == '/':
                        # Preserve original root indicator if it was '~'
                        if self.current_path.startswith('~'):
                            item_logical_path = '~'
                    elif item_logical_path == '': # Should not happen if above logic is good, but as a fallback
                        item_logical_path = '~'
                else: # Regular file/folder
                    if self.current_path == "~":
                        item_logical_path = f"~/{name}"
                    elif self.current_path == "/":
                        item_logical_path = f"/{name}"
                    else:
                        item_logical_path = f"{self.current_path}/{name}"
                item_logical_path = item_logical_path.replace('//', '/') # Normalize path again (e.g. `//` to `/`)

                try:
                    file_data = FileData(
                        name=name,
                        logical_path=item_logical_path,
                        is_directory=is_dir,
                        uid=uid,
                        owner=owner,
                        access_string=access_string,
                        creation_time_str=creation_time_str,
                        modified_time_str=modified_time_str
                    )
                    if file_data.name != ".": # Exclude the current directory entry
                        parsed_data.append(file_data)
                except Exception as e:
                    print(f"[Explorer] Error creating FileData from line '{line}' (line_num {line_num}): {e}")
        parsed_data.sort(key=lambda x: (not x.is_directory, x.name.lower()))

        for file_data in parsed_data:
            self.addFile(file_data)
        if self.files_data:
            self.setSelectedFile(self.files_data[0])
        else:
            self.infoPanel.clearFileInfo()

        self.pathLabel.setText(f"Current Path: {self.current_path}")

    def load_files(self, logical_path: str):
        """
        内部方法：用于导航，发送 cd 命令到目标路径，然后触发 ls -a。
        这个方法不应直接检查 Terminal 登录状态，而是假定调用者（例如 load_current_terminal_directory 或 handleDoubleClick）已经检查过。
        """
        if self.terminal_instance._explorer_current_api_obj_name is not None:
             self._show_infobar("请稍候", "正在加载目录，请等待当前操作完成。", InfoBarPosition.TOP)
             return
        self.pathLabel.setText(f"Loading: {logical_path}...")

        normalized_logical_path = logical_path.replace('//', '/')
        if normalized_logical_path == "": # Empty path usually means user home
            normalized_logical_path = "~"
        if normalized_logical_path != self.current_path:
            cd_command = f"cd {normalized_logical_path}"
            self.terminal_instance.execute_command_for_explorer(cd_command)
        else:
            self.terminal_instance.execute_command_for_explorer("ls -a")

    def addFile(self, file_data: FileData):
        try:
            card = FileIcon(file_data, self)
            card.clicked.connect(self.setSelectedFile)
            card.doubleClicked.connect(self.handleDoubleClick)

            self.trie.insert(file_data.name.lower(), len(self.cards)) # Store name in lowercase for case-insensitive search
            self.cards.append(card)
            self.files_data.append(file_data)
            self.flowLayout.addWidget(card)
        except Exception as e:
            print(f"Error adding file card for {file_data.logical_path}: {e}")

    def setSelectedFile(self, file_data: FileData):
        try:
            index = -1
            for i, fd in enumerate(self.files_data):
                if fd is file_data: # Use identity for comparison as FileData objects are unique instances here
                    index = i
                    break
            if index == -1:
                if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
                    self.cards[self.currentIndex].setSelected(False)
                self.currentIndex = -1
                self.infoPanel.clearFileInfo()
                return

            if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
                # Deselect previous card if it exists and is different from current
                if self.currentIndex != index:
                    self.cards[self.currentIndex].setSelected(False)

            self.currentIndex = index
            self.cards[index].setSelected(True)
            self.infoPanel.setFileInfo(file_data)
        except Exception as e:
            print(f"Error in setSelectedFile for {file_data.logical_path}: {e}")
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()


    def handleDoubleClick(self, file_data: FileData):
        current_api = self.terminal_instance.get_current_api()
        if not current_api or current_api.state() != QProcess.Running:
            self._show_infobar("错误", "当前没有激活或运行中的终端实例。", InfoBarPosition.TOP)
            return

        terminal_obj_name = current_api.terminal_object_name
        current_terminal_mode = self.terminal_instance.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._show_infobar("请先登录", "请先在 '终端管理器' 标签页登录系统。", InfoBarPosition.TOP)
            return

        if file_data.is_directory:
            self.searchLineEdit.clear()
            self.load_files(file_data.logical_path) # 调用内部的 load_files
        else:
            self._show_infobar("提示", f"双击文件 '{file_data.name}' 功能暂未实现。", InfoBarPosition.TOP)


    def openFile(self, file_path: str):
        pass

    def search(self, keyWord: str):
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
            self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()

        self.flowLayout.removeAllWidgets()

        if not keyWord:
            self.showAllFiles()
            return

        items_indices = self.trie.items(keyWord.lower())
        indexes = {i[1] for i in items_indices}

        for i in range(len(self.cards)):
            card = self.cards[i]
            isVisible = (i in indexes)
            card.setVisible(isVisible)
            if isVisible:
                self.flowLayout.addWidget(card)

    def showAllFiles(self):
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
            self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()

        self.flowLayout.removeAllWidgets()
        for card in self.cards:
            card.show()
            self.flowLayout.addWidget(card)

    def go_up_directory(self):
        current_api = self.terminal_instance.get_current_api()
        if not current_api or current_api.state() != QProcess.Running:
            self._show_infobar("错误", "当前没有激活或运行中的终端实例。", InfoBarPosition.TOP)
            return

        terminal_obj_name = current_api.terminal_object_name
        current_terminal_mode = self.terminal_instance.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._show_infobar("请先登录", "请先在 '终端管理器' 标签页登录系统。", InfoBarPosition.TOP)
            return
        # Check if already at root based on common shell representations
        if self.current_path == "~" or self.current_path == "/":
            self._show_infobar("提示", "已在根目录。", InfoBarPosition.TOP)
            return
        parts = self.current_path.split('/')
        # Remove empty string if path ends with / (e.g., "/dir/")
        if parts and parts[-1] == '':
            parts = parts[:-1]

        new_path = ""
        if len(parts) > 1: # If more than one part (e.g., "~/dir" or "/dir/subdir")
            new_path = '/'.join(parts[:-1])
            if new_path == '': # If moving from "/dir" to "/", new_path becomes empty. Set to "/"
                new_path = '/'
        else: # Current path is "~" or "/" or a single segment like "dir"
            new_path = "~" # Default to user home root if no parent or single segment.
            # If current_path was "/", then new_path becomes "~", which is a valid transition in this system.
        self.load_files(new_path)


class Explorer(QWidget):
    def __init__(self, text: str, terminal_instance: Terminal, parent=None):
        super().__init__(parent=parent)
        self.setupUi()
        self.setObjectName(text.replace(' ', '-'))
        self.fileView = FileView(terminal_instance, self)
        self.layout.addWidget(self.fileView)
        terminal_instance.requestExplorerRefresh.connect(self.fileView.load_current_terminal_directory)

    def setupUi(self):
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)