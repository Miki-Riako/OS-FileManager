from typing import List
import re
import os

from PySide6.QtCore import Qt, Signal, QUrl, QEvent, QProcess, QTimer
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
    def __init__(
        self,
        name: str,
        uid: str,
        owner: str,
        access: str,
        creation_time: str,
        modified_time: str
    ):
        self.name = name
        self.uid = uid
        self.owner = owner
        self.access = access # This is the full access string, e.g., 'drwxrwxrwx' or 'frwxrw-r--'
        self.creation_time = creation_time
        self.modified_time = modified_time

class FileIcon(QFrame):
    clicked = Signal(FileData)
    doubleClicked = Signal(FileData)

    def __init__(self, file_data: FileData, parent=None):
        super().__init__(parent=parent)
        self.file_data = file_data
        self.isSelected = False

        # Determine icon and if it's a directory based on access string
        self.fluent_icon, self.is_directory_ui = FileIcon._determine_icon_and_type(file_data.name, file_data.access)

        try:
            self.iconWidget = IconWidget(self.fluent_icon, self)
        except Exception as e:
            print(f"Error creating IconWidget for {file_data.name} (icon: {self.fluent_icon}): {e}. Using default error icon.")
            self.iconWidget = IconWidget(FluentIcon.CANCEL, self)

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
        self.setObjectName('FileIconCard') # Set object name for styling if needed

    @staticmethod
    def _determine_icon_and_type(name: str, access_string: str):
        """ Determines the FluentIcon and if it's a directory based on name and access string. """
        if name == "..":
            return FluentIcon.RETURN, True # ".." is always treated as a directory for navigation
        if name == ".":
            return FluentIcon.FOLDER, True # . is also a directory for navigation

        is_directory = access_string.startswith('d')
        is_file = access_string.startswith('-') or access_string.startswith('f') # 'f' is treated as file for now based on output

        if is_directory:
            return FluentIcon.FOLDER, True
        elif is_file:
            return FluentIcon.DOCUMENT, False
        else: # Default for unknown types (e.g., links, block devices etc. not covered here)
            return FluentIcon.DOCUMENT, False # Treat as a generic file for now


    def mouseReleaseEvent(self, e):
        self.clicked.emit(self.file_data)
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
            self.iconWidget.setIcon(self.fluent_icon) # Use the base icon
        else:
            accent_color = QColor(0, 120, 212) # Fluent blue accent
            if isDarkTheme(): # For dark theme, use a lighter accent if needed
                accent_color = QColor(100, 180, 255) # Example: lighter blue for dark theme
            self.iconWidget.setIcon(self.fluent_icon.icon(color=accent_color))
        self.setProperty('isSelected', isSelected)
        self.setStyle(QApplication.style()) # Apply stylesheet to update visual state


class FileInfoPanel(QFrame):
    def __init__(self, file_data: FileData = None, parent=None):
        super().__init__(parent=parent)
        self.nameLabel = StrongBodyLabel(self)
        self.iconWidget = IconWidget(self)
        self.pathTitleLabel = CaptionLabel('Path', self)
        self.pathLabel = BodyLabel(self)
        self.typeTitleLabel = CaptionLabel('Type', self)
        self.typeLabel = BodyLabel(self)
        self.modifiedTitleLabel = CaptionLabel('Last Modified', self)
        self.modifiedLabel = BodyLabel(self)
        self.ownerTitleLabel = CaptionLabel('Owner', self)
        self.ownerLabel = BodyLabel(self)
        self.accessTitleLabel = CaptionLabel('Access', self)
        self.accessLabel = BodyLabel(self)
        self.creationTimeTitleLabel = CaptionLabel('Creation Time', self)
        self.creationTimeLabel = BodyLabel(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.__initWidget()
        self.nameLabel.setObjectName('nameLabel')
        self.pathTitleLabel.setObjectName('subTitleLabel')
        self.typeTitleLabel.setObjectName('subTitleLabel')
        self.modifiedTitleLabel.setObjectName('subTitleLabel')
        self.ownerTitleLabel.setObjectName('subTitleLabel')
        self.accessTitleLabel.setObjectName('subTitleLabel')
        self.creationTimeTitleLabel.setObjectName('subTitleLabel')
        for label in [self.pathLabel, self.typeLabel, self.modifiedLabel, self.ownerLabel, self.accessLabel, self.creationTimeLabel]:
            label.setWordWrap(True)
            label.setStyleSheet("color: grey;")

        if file_data:
            self.setFileInfo(file_data, "") # Initial call, path will be set later
        else:
            self.clearFileInfo()

    def __initWidget(self):
        self.__initLayout()
        self.vBoxLayout.setContentsMargins(16, 20, 16, 20)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.iconWidget.setFixedSize(48, 48)
        self.setFixedWidth(216)

    def __initLayout(self):
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

    def setFileInfo(self, file_data: FileData, current_explorer_path: str):
        # Determine icon and type for display
        fluent_icon, is_directory = FileIcon._determine_icon_and_type(file_data.name, file_data.access)
        self.iconWidget.setIcon(fluent_icon)
        self.nameLabel.setText(file_data.name)
        
        # Construct and set the logical path for display
        logical_path_to_display = Explorer._get_item_logical_path(current_explorer_path, file_data.name)
        self.pathLabel.setText(logical_path_to_display)
        
        self.typeLabel.setText("Folder" if is_directory else "File")
        self.modifiedLabel.setText(file_data.modified_time)
        self.ownerLabel.setText(file_data.owner)
        self.accessLabel.setText(file_data.access)
        self.creationTimeLabel.setText(file_data.creation_time)

    def clearFileInfo(self):
        self.iconWidget.setIcon(FluentIcon.INFO)
        self.nameLabel.setText("No item selected")
        self.pathLabel.setText("")
        self.typeLabel.setText("")
        self.modifiedLabel.setText("")
        self.ownerLabel.setText("")
        self.accessLabel.setText("")
        self.creationTimeLabel.setText("")

class Explorer(QWidget):
    def __init__(self, text: str, terminal_manager: Terminal, parent=None):
        super().__init__(parent=parent)
        self.setupUi()
        self.terminal_manager = terminal_manager
        self.terminal_manager.requestExplorerRefresh.connect(self.load_current_terminal_directory)
        self.terminal_manager.explorerCommandOutputReady.connect(self._handle_explorer_command_response)

        self.trie = Trie()
        self.current_path = "~" # Initial path in Explorer view, matches Shell's initial login path

        self._ls_output_regex = re.compile(
            r"^\s*(?P<fileName>.*?)\s*\|\s*(?P<uid>\d+)\s*\|\s*(?P<owner>.*?)\s*\|\s*(?P<access>[fdrwx\-]+)\s*\|\s*(?P<creation_time>[\d\-\s:]+)\s*\|\s*(?P<modified_time>[\d\-\s:]+)$"
        )
        self._prompt_regex = re.compile(r"OSFileSystem@[\w\.-]+:.*?\$\s")

        self.backButton = ToolButton(FluentIcon.RETURN, self)
        self.pathLabel = StrongBodyLabel(f"Current Path: {self.current_path}", self)
        self.navLayout = QHBoxLayout()
        self.searchLineEdit = SearchLineEdit(self)
        self.view = QFrame(self)
        self.scrollArea = SmoothScrollArea(self.view)
        self.scrollWidget = QWidget(self.scrollArea) # This widget will contain the FlowLayout
        self.infoPanel = FileInfoPanel(parent=self)
        self.hBoxLayout = QHBoxLayout(self.view)
        # FlowLayout's parent is scrollWidget
        self.flowLayout = FlowLayout(self.scrollWidget, isTight=True) 
        self.cards = [] # Store FileIcon instances here
        self.files_data = [] # Store FileData instances here
        self.currentIndex = -1

        self.__initWidget()
        self.clear_file_display() # 初始化时清空显示，确保它最初是空的
        self.setObjectName(text.replace(' ', '-'))

    def setupUi(self):
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

    def __initWidget(self):
        self.__initLayout()
        self.__initButton()
        self.pathLabel.setContentsMargins(5,0,0,0)

        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setViewportMargins(0, 5, 0, 5)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)

        self.flowLayout.setVerticalSpacing(8)
        self.flowLayout.setHorizontalSpacing(8)
        self.flowLayout.setContentsMargins(8, 3, 8, 8)

        self.searchLineEdit.clearSignal.connect(self.showAllFiles)
        self.searchLineEdit.searchSignal.connect(self.search)

        self.navLayout.setContentsMargins(0, 0, 0, 0)
        self.navLayout.setSpacing(5)
        self.navLayout.addStretch(1)

        self.searchLineEdit.setPlaceholderText('Search files')
        self.searchLineEdit.setFixedWidth(1096)

    def __initLayout(self):
        self.layout.addLayout(self.navLayout)
        self.layout.addWidget(self.searchLineEdit)
        self.layout.addWidget(self.view)
        self.hBoxLayout.addWidget(self.scrollArea)
        self.hBoxLayout.addWidget(self.infoPanel, 0, Qt.AlignRight)
        self.navLayout.addWidget(self.backButton)
        self.navLayout.addWidget(self.pathLabel)

    def __initButton(self):
        self.backButton.setToolTip("Go to parent folder")
        self.backButton.setFixedSize(32, 32)
        self.backButton.clicked.connect(self.go_up_directory)

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
        """ Clears the file display area, including cards, data, and info panel """
        # Deselect any currently selected item and clear info panel
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
            self.cards[self.currentIndex].setSelected(False)
        self.currentIndex = -1
        self.infoPanel.clearFileInfo()
        # 隐藏所有卡片，但并不立即删除它们，以便后续的搜索和显示操作可以重用
        for card in self.cards:
            card.setVisible(False)
        self.flowLayout.removeAllWidgets() # 从布局中移除所有
        self.cards.clear()
        self.files_data.clear()
        self.trie = Trie() # Reinitialize trie as all file data is gone
        self.pathLabel.setText("Current Path: (Empty)")
        self.flowLayout.update()
        self.scrollWidget.update()
        self.view.update()
        self.update()

    def load_current_terminal_directory(self):
        """此方法现在只负责发起 'ls -l' 命令，不负责改变当前路径。"""
        current_api = self.terminal_manager.get_current_api()
        if not current_api or current_api.state() != QProcess.Running:
            self._show_infobar("错误", "当前没有激活或运行中的终端实例。", InfoBarPosition.TOP)
            self.pathLabel.setText("Error: No active terminal.")
            self.clear_file_display() # Clear display if no terminal
            return

        terminal_obj_name = current_api.terminal_object_name
        current_terminal_mode = self.terminal_manager.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._show_infobar("请先登录", "请先在 '终端管理器' 标签页登录系统。", InfoBarPosition.TOP)
            self.pathLabel.setText("Please login in Terminal Manager first.")
            self.clear_file_display() # Clear display if not logged in
            return
        # 避免重复发送命令：如果Explorer正忙于处理其他Explorer命令，则等待
        if self.terminal_manager._explorer_current_api_obj_name is not None:
            #  self._show_infobar("请稍候", "正在加载目录，请等待当前操作完成。", InfoBarPosition.TOP)
             return
        self.pathLabel.setText(f"Loading: {self.current_path}...")
        self.terminal_manager.execute_command_for_explorer("ls -l")

    def _handle_explorer_command_response(self, terminal_obj_name: str, raw_output: str, success: bool, error_msg: str, command_type: str):
        """处理来自 Terminal 的命令执行结果。"""
        if not success:
            self._show_infobar("命令失败", f"执行命令失败：{error_msg}", InfoBarPosition.TOP)
            self.pathLabel.setText(f"Error: {error_msg}")
            self.clear_file_display()
            return

        extracted_path = "~" # 默认值
        match = self._prompt_regex.search(raw_output)
        if match:
            prompt_full = match.group(0).strip()
            path_start_index = prompt_full.find(":") + 1
            path_end_index = prompt_full.find("$")
            if path_start_index != -1 and path_end_index != -1 and path_start_index < path_end_index:
                extracted_path = prompt_full[path_start_index:path_end_index].strip()
                if extracted_path == "":
                    extracted_path = "~"
                else:
                    extracted_path = extracted_path.replace('//', '/')
        self.current_path = extracted_path # 始终更新当前路径，使其与终端同步

        if command_type.startswith("cd"): # 'cd' 命令成功完成
            self._show_infobar("目录切换成功", f"当前路径：{self.current_path}", InfoBarPosition.TOP)
            self.terminal_manager.execute_command_for_explorer("ls -l")
        elif command_type.startswith("ls"): # 'ls' 命令成功完成，现在解析输出并填充 UI
            self._parse_ls_output_and_populate_cards(raw_output)
            # self._show_infobar("目录加载成功", f"当前路径：{self.current_path}", InfoBarPosition.TOP)
        else: # 处理其他命令的完成，如果需要的话
            pass # 对于 "other" 类型命令，我们目前不进行特殊处理

    @staticmethod
    def _get_item_logical_path(current_path: str, item_name: str) -> str:
        """ Helper to construct the full logical path for a given item. """
        if item_name == ".":
            return current_path
        elif item_name == "..":
            parts = current_path.split('/')
            if parts and parts[-1] == '': # Handle trailing slash if present
                parts = parts[:-1]
            if not parts or (len(parts) == 1 and (parts[0] == '~' or parts[0] == '')):
                return '~' # Already at root (represented by ~), parent is still root
            elif current_path == '/': # If current is /, parent is still /
                return '/'
            else:
                temp_path = '/'.join(parts[:-1])
                if temp_path == '': # If parts[:-1] results in empty, it means we went from /some_dir to /
                    return '/'
                elif temp_path == '~': # If we go up from ~/something to ~, keep it as ~
                    return '~'
                else:
                    return temp_path
        else:
            if current_path == "~":
                return f"~/{item_name}"
            elif current_path == "/":
                return f"/{item_name}"
            else:
                # Ensure no double slashes, especially when current_path might end with '/'
                return f"{current_path.rstrip('/')}/{item_name}"

    def _parse_ls_output_and_populate_cards(self, raw_output: str):
        """Parses raw ls -l output, creates FileData objects, and populates the UI."""
        self.clear_file_display() # 确保完全清空现有显示，包括重新初始化 Trie
        lines = raw_output.strip().split('\n')
        data_lines = []
        is_data_section = False

        for line_num, line in enumerate(lines):
            stripped_line = line.strip()
            if re.search(r"^\s*fileName\s*\|\s*uid\s*\|", stripped_line) and not is_data_section:
                is_data_section = True
                continue
            if is_data_section and self._prompt_regex.search(stripped_line):
                is_data_section = False
                break
            if is_data_section and stripped_line:
                data_lines.append(stripped_line)
        parsed_data = []
        for line_num, line in enumerate(data_lines):
            match = self._ls_output_regex.match(line)
            if match:
                data = match.groupdict()
                file_data = FileData(
                    name=data['fileName'].strip(),
                    uid=data['uid'].strip(),
                    owner=data['owner'].strip(),
                    access=data['access'].strip(),
                    creation_time=data['creation_time'].strip(),
                    modified_time=data['modified_time'].strip()
                )
                parsed_data.append(file_data)

        # Sort directories before files, then alphabetically
        def sort_key(file_data: FileData):
            _, is_dir = FileIcon._determine_icon_and_type(file_data.name, file_data.access)
            if file_data.name == "..":
                return (0, file_data.name.lower())
            elif file_data.name == ".":
                return (1, file_data.name.lower())
            else:
                return (2 if is_dir else 3, file_data.name.lower()) # Directories first, then alphabetical

        parsed_data.sort(key=sort_key)

        for file_data in parsed_data:
            self.addFile(file_data)
        self.showAllFiles() # 初始加载时，只添加所有文件到布局，然后 setSelectedFile 来更新信息面板
        if self.files_data:
            initial_selection_index = 0 # Try to select the first non-special file/folder
            if len(self.files_data) > 2 and self.files_data[0].name == ".." and self.files_data[1].name == ".":
                 initial_selection_index = 2
            elif len(self.files_data) > 1 and (self.files_data[0].name == ".." or self.files_data[0].name == "."):
                 initial_selection_index = 1 # Select the second item if only one special exists
            if len(self.files_data) > initial_selection_index:
                self.setSelectedFile(self.files_data[initial_selection_index])
            else: # Fallback if there are only '.' or '..'
                 if len(self.files_data) > 0:
                     self.setSelectedFile(self.files_data[0])
                 else:
                    self.infoPanel.clearFileInfo()
        else:
            self.infoPanel.clearFileInfo()

        self.pathLabel.setText(f"Current Path: {self.current_path}")

    def load_files(self, logical_path: str):
        """发起文件加载（可能包括目录切换）。"""
        if self.terminal_manager._explorer_current_api_obj_name is not None: # 检查 Explorer 是否正在执行另一个命令
             self._show_infobar("请稍候", "正在加载目录，请等待当前操作完成。", InfoBarPosition.TOP)
             return

        current_api = self.terminal_manager.get_current_api() # 检查终端状态
        if not current_api or current_api.state() != QProcess.Running:
            self._show_infobar("错误", "当前没有激活或运行中的终端实例。", InfoBarPosition.TOP)
            return

        terminal_obj_name = current_api.terminal_object_name
        current_terminal_mode = self.terminal_manager.get_terminal_mode(terminal_obj_name)
        if current_terminal_mode != TerminalInputMode.NORMAL:
            self._show_infobar("请先登录", "请先在 '终端管理器' 标签页登录系统。", InfoBarPosition.TOP)
            return

        normalized_logical_path = logical_path.replace('//', '/')
        if normalized_logical_path == "":
            normalized_logical_path = "~"

        if normalized_logical_path != self.current_path: # 如果路径不同，则执行 cd 命令
            self.pathLabel.setText(f"Loading: {normalized_logical_path}...")
            self.terminal_manager.execute_command_for_explorer(f"cd {normalized_logical_path}")
        else: # 如果路径相同，则直接执行 'ls -l' 命令来刷新
            self.terminal_manager.execute_command_for_explorer("ls -l")

    def addFile(self, file_data: FileData):
        """ Adds a FileData object to the display. """
        try:
            card = FileIcon(file_data, self.scrollWidget) 
            card.clicked.connect(self.setSelectedFile)
            card.doubleClicked.connect(self.handleDoubleClick)

            self.trie.insert(file_data.name, len(self.cards)) 
            self.cards.append(card)
            self.files_data.append(file_data) # Store original FileData object
            # 初始时不立即添加到布局，由 _parse_ls_output_and_populate_cards 统一调用 showAllFiles 处理
            # card.show() # Ensure the newly added card is visible
        except Exception as e:
            print(f"Error adding file card for {file_data.name}: {e}")

    def setSelectedFile(self, file_data: FileData):
        """ Selects a file card and updates the info panel. """
        try:
            index = -1
            for i, fd in enumerate(self.files_data):
                if fd is file_data:
                    index = i
                    break
            if index == -1:
                if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
                    self.cards[self.currentIndex].setSelected(False)
                self.currentIndex = -1
                self.infoPanel.clearFileInfo()
                return

            if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
                if self.currentIndex != index:
                    self.cards[self.currentIndex].setSelected(False)

            self.currentIndex = index
            self.cards[index].setSelected(True)
            # Pass current_path to infoPanel for dynamic path display
            self.infoPanel.setFileInfo(file_data, self.current_path)
        except Exception as e:
            print(f"Error in setSelectedFile for {file_data.name}: {e}")
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()

    def handleDoubleClick(self, file_data: FileData):
        """ Handles double-click event on a file/directory icon. """
        _, is_directory_for_action = FileIcon._determine_icon_and_type(file_data.name, file_data.access)

        if is_directory_for_action:
            self.searchLineEdit.clear() # 清空搜索框
            target_path = Explorer._get_item_logical_path(self.current_path, file_data.name)
            self.load_files(target_path)
        else:
            self._show_infobar("提示", f"双击文件 '{file_data.name}' 功能暂未实现。", InfoBarPosition.TOP)

    def openFile(self, file_path: str):
        pass # To be implemented later

    def search(self, keyWord: str):
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards): # 清除当前选中项和信息面板
            self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()
        # 清空布局中的所有小部件
        self.flowLayout.removeAllWidgets()

        if not keyWord: # 如果搜索关键词为空，则显示所有文件
            self.showAllFiles()
            return
        # 使用修改后的 Trie 进行搜索，关键词转小写由 Trie 内部处理
        items_indices = self.trie.items(keyWord)
        indexes_to_show = {i[1] for i in items_indices}
        # 遍历所有卡片，只添加匹配的卡片到布局中
        for i, card in enumerate(self.cards):
            if i in indexes_to_show:
                card.setVisible(True)
                self.flowLayout.addWidget(card)
            else:
                card.setVisible(False) # 确保不匹配的卡片被隐藏
        # 强制更新布局
        self.flowLayout.update()
        self.scrollWidget.update()
        self.view.update()
        self.update()

    def showAllFiles(self):
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards): # 清除当前选中项和信息面板
            self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()

        self.flowLayout.removeAllWidgets() # 清空布局中的所有小部件
        for card in self.cards: # 重新添加所有卡片到布局中，并确保它们可见
            card.setVisible(True)
            self.flowLayout.addWidget(card)

        self.flowLayout.update() # 强制更新布局
        self.scrollWidget.update()
        self.view.update()
        self.update()

    def go_up_directory(self):
        if self.current_path == "~" or self.current_path == "/":
            self._show_infobar("提示", "已在根目录。", InfoBarPosition.TOP)
            return

        new_path = Explorer._get_item_logical_path(self.current_path, "..")
        self.load_files(new_path)