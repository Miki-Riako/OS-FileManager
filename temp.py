from typing import List
import os
from datetime import datetime
import stat # 导入stat模块用于文件属性判断

from PySide6.QtCore import Qt, Signal, QUrl, QEvent
from PySide6.QtGui import QDesktopServices, QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame

from qfluentwidgets import (ScrollArea, PushButton, FlowLayout, ToolButton, FluentIcon,
                            isDarkTheme, IconWidget, Theme, ToolTipFilter, TitleLabel, CaptionLabel,
                            SmoothScrollArea, SearchLineEdit, StrongBodyLabel, BodyLabel, toggleTheme)

from .trie import Trie # 假设trie模块存在，并且支持字符串搜索

# --- 文件数据模型 ---
class FileData:
    """ Represents a file or directory """
    def __init__(self, path: str):
        self.path = os.path.abspath(path) # 确保路径是绝对路径
        self.name = os.path.basename(path)
        
        # 默认值
        self.is_directory = False
        self.size = 0
        self.last_modified = None
        self.fluent_icon = FluentIcon.DOCUMENT # 默认图标：通用文档图标

        # 尝试获取文件信息
        # 检查os.path.islink，如果是符号链接，尝试解析真实路径
        if os.path.islink(self.path):
            try:
                real_path = os.path.realpath(self.path)
                if os.path.exists(real_path):
                    self.path = real_path 
                    self.name = os.path.basename(real_path) # 更新名称，通常不变
                else:
                    self.fluent_icon = FluentIcon.CANCEL # 链接目标不存在
                    return 
            except (OSError, PermissionError) as e:
                self.fluent_icon = FluentIcon.CANCEL # 链接解析失败或无权限
                return 
        
        # 检查文件是否存在，如果不存在，则无法获取信息
        if not os.path.exists(self.path):
            self.fluent_icon = FluentIcon.DOCUMENT # 文件不存在，用默认文档图标
            return 

        try:
            file_stat = os.stat(self.path)
            self.is_directory = stat.S_ISDIR(file_stat.st_mode)
            if not self.is_directory:
                self.size = file_stat.st_size
            self.last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        except (OSError, PermissionError) as e:
            self.fluent_icon = FluentIcon.CANCEL # 文件存在但无法获取属性
            return 

        # 根据文件类型或是否为目录选择FluentIcon
        if self.is_directory:
            self.fluent_icon = FluentIcon.FOLDER
        elif self.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg')):
            self.fluent_icon = FluentIcon.PHOTO
        elif self.name.lower().endswith(('.txt', '.log', '.md', '.json', '.xml', '.yaml', '.yml', '.csv')):
            self.fluent_icon = FluentIcon.DOCUMENT
        elif self.name.lower().endswith(('.py', '.js', '.html', '.css', '.cpp', '.h', '.c', '.java', '.cs', '.go', '.rs', '.sh', '.bat', '.ps1')):
            self.fluent_icon = FluentIcon.CODE
        elif self.name.lower().endswith(('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz')):
            self.fluent_icon = FluentIcon.ZIP_FOLDER
        elif self.name.lower().endswith(('.pdf')):
            self.fluent_icon = FluentIcon.PDF
        elif self.name.lower().endswith(('.doc', '.docx')):
            self.fluent_icon = FluentIcon.WORD 
        elif self.name.lower().endswith(('.xls', '.xlsx')):
            self.fluent_icon = FluentIcon.EXCEL 
        elif self.name.lower().endswith(('.ppt', '.pptx')):
            self.fluent_icon = FluentIcon.POWER_POINT 
        elif self.name.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.aac')):
            self.fluent_icon = FluentIcon.MUSIC
        elif self.name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')):
            self.fluent_icon = FluentIcon.VIDEO
        elif self.name.lower().endswith(('.exe', '.dll', '.msi')):
            self.fluent_icon = FluentIcon.APPLICATION 
        elif self.name.lower().endswith(('.lnk')): # Windows快捷方式
            self.fluent_icon = FluentIcon.LINK 
        else:
            self.fluent_icon = FluentIcon.DOCUMENT # 默认文件图标


class FileIcon(QFrame):
    """ File or Folder card """

    clicked = Signal(FileData)
    doubleClicked = Signal(FileData)

    def __init__(self, file_data: FileData, parent=None):
        super().__init__(parent=parent)
        self.file_data = file_data
        self.isSelected = False

        try:
            self.iconWidget = IconWidget(file_data.fluent_icon, self)
        except Exception as e:
            print(f"Error creating IconWidget for {file_data.name} (icon: {file_data.fluent_icon}): {e}. Using default error icon.")
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

    def mouseReleaseEvent(self, e):
        """ Handles single click """
        if not self.isSelected:
            self.clicked.emit(self.file_data)
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        """ Handles double click """
        self.doubleClicked.emit(self.file_data)
        super().mouseDoubleClickEvent(e)

    def setSelected(self, isSelected: bool, force=False):
        """ Sets the selection state of the card """
        if isSelected == self.isSelected and not force:
            return

        self.isSelected = isSelected

        if not isSelected:
            self.iconWidget.setIcon(self.file_data.fluent_icon)
        else:
            accent_icon = self.file_data.fluent_icon.icon(Theme.LIGHT if isDarkTheme() else Theme.DARK)
            self.iconWidget.setIcon(accent_icon)

        self.setProperty('isSelected', isSelected)
        self.setStyle(QApplication.style())


class FileInfoPanel(QFrame):
    """ File or Folder Info panel """

    def __init__(self, file_data: FileData = None, parent=None):
        super().__init__(parent=parent)
        self.nameLabel = QLabel(self)
        self.iconWidget = IconWidget(self)
        self.pathTitleLabel = QLabel(self.tr('Path'), self)
        self.pathLabel = QLabel(self)
        self.typeTitleLabel = QLabel(self.tr('Type'), self)
        self.typeLabel = QLabel(self)
        self.sizeTitleLabel = QLabel(self.tr('Size'), self)
        self.sizeLabel = QLabel(self)
        self.modifiedTitleLabel = QLabel(self.tr('Last Modified'), self)
        self.modifiedLabel = QLabel(self)

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

        self.vBoxLayout.addWidget(self.modifiedTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.modifiedLabel)
        self.vBoxLayout.addStretch(1) # 填充剩余空间，让内容靠上

        self.iconWidget.setFixedSize(48, 48)
        self.setFixedWidth(216)

        self.nameLabel.setObjectName('nameLabel')
        self.pathTitleLabel.setObjectName('subTitleLabel')
        self.typeTitleLabel.setObjectName('subTitleLabel')
        self.sizeTitleLabel.setObjectName('subTitleLabel')
        self.modifiedTitleLabel.setObjectName('subTitleLabel')

        if file_data:
            self.setFileInfo(file_data)
        else:
            self.clearFileInfo()

    def setFileInfo(self, file_data: FileData):
        """ Updates the info panel with new file data """
        self.iconWidget.setIcon(file_data.fluent_icon)
        self.nameLabel.setText(file_data.name)
        self.pathLabel.setText(os.path.normpath(file_data.path))
        
        if file_data.is_directory:
            self.typeLabel.setText(self.tr("Folder"))
        elif file_data.fluent_icon == FluentIcon.CANCEL:
            self.typeLabel.setText(self.tr("Invalid Item"))
        elif file_data.fluent_icon == FluentIcon.DOCUMENT:
            self.typeLabel.setText(self.tr("Unknown File Type"))
        else:
            self.typeLabel.setText(self.tr("File"))

        self.sizeLabel.setText(self._format_size(file_data.size))
        self.modifiedLabel.setText(file_data.last_modified.strftime("%Y/%m/%d %H:%M") if file_data.last_modified else self.tr("N/A"))

    def clearFileInfo(self):
        """ Clears all information in the panel """
        self.iconWidget.setIcon(FluentIcon.INFO)
        self.nameLabel.setText(self.tr("No item selected"))
        self.pathLabel.setText("")
        self.typeLabel.setText("")
        self.sizeLabel.setText("")
        self.modifiedLabel.setText("")

    def _format_size(self, size_bytes: int):
        """ Formats size into human-readable string """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.trie = Trie()
        self.current_path = os.path.expanduser('~')

        # --- 新增：导航按钮和路径标签的布局 ---
        self.backButton = ToolButton(FluentIcon.RETURN, self)
        self.backButton.setToolTip(self.tr("Go to parent folder"))
        self.backButton.setFixedSize(32, 32) # 设置按钮大小
        self.backButton.clicked.connect(self.go_up_directory) # 连接到返回上一级目录的方法
        
        self.pathLabel = BodyLabel(self.tr(f"Current Path: {self.current_path}"), self)
        self.pathLabel.setContentsMargins(5,0,0,0) # 路径标签左边距，与按钮间隔

        self.navLayout = QHBoxLayout()
        self.navLayout.setContentsMargins(0, 0, 0, 0)
        self.navLayout.setSpacing(5)
        self.navLayout.addWidget(self.backButton)
        self.navLayout.addWidget(self.pathLabel)
        self.navLayout.addStretch(1) # 确保按钮和路径靠左

        self.searchLineEdit = SearchLineEdit(self)
        self.searchLineEdit.setPlaceholderText(self.tr('Search files'))
        self.searchLineEdit.setFixedWidth(500)

        self.view = QFrame(self)
        self.scrollArea = SmoothScrollArea(self.view)
        self.scrollWidget = QWidget(self.scrollArea)
        self.infoPanel = FileInfoPanel(parent=self)

        self.vBoxLayout = QVBoxLayout(self)
        self.hBoxLayout = QHBoxLayout(self.view)
        self.flowLayout = FlowLayout(self.scrollWidget, isTight=True)

        self.cards = []     # type:List[FileIcon]
        self.files_data = [] # type:List[FileData]
        self.currentIndex = -1

        self.__initWidget()
        self.load_files(self.current_path)

    def __initWidget(self):
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setViewportMargins(0, 5, 0, 5)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(12)
        self.vBoxLayout.addLayout(self.navLayout) # 将新的导航布局添加到主垂直布局
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

        self.__setQss()

    def __setQss(self):
        self.view.setObjectName('fileView')
        self.scrollWidget.setObjectName('scrollWidget')
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
            self.cards[self.currentIndex].setSelected(True, True)

    def load_files(self, path: str):
        """ Loads files and directories from the given path """
        self.flowLayout.removeAllWidgets()
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        self.files_data.clear()
        self.currentIndex = -1
        self.infoPanel.clearFileInfo()
        self.trie = Trie()

        try:
            if not os.path.exists(path):
                print(f"Error: Path does not exist: {path}")
                self.pathLabel.setText(self.tr(f"Error: Path does not exist - {path}"))
                self.backButton.setVisible(False) # 路径错误时隐藏返回按钮
                return
            if not os.path.isdir(path):
                print(f"Error: Path is not a directory: {path}")
                parent_dir = os.path.dirname(path)
                if parent_dir and parent_dir != path:
                    self.load_files(parent_dir)
                else:
                    self.pathLabel.setText(self.tr(f"Error: Path is not a directory - {path}"))
                    self.backButton.setVisible(False)
                return

            self.current_path = os.path.abspath(path)
            self.pathLabel.setText(self.tr(f"Current Path: {self.current_path}"))

            # 控制返回按钮的可见性
            parent_dir = os.path.dirname(self.current_path)
            if parent_dir and parent_dir != self.current_path:
                self.backButton.setVisible(True)
                # 添加“..”的 FileData，它依然需要出现在列表中作为可点击的返回项
                if os.path.exists(parent_dir):
                    try:
                        parent_file_data = FileData(parent_dir)
                        if parent_file_data.fluent_icon != FluentIcon.CANCEL:
                            parent_file_data.name = ".."
                            parent_file_data.fluent_icon = FluentIcon.FOLDER_OPEN
                            self.addFile(parent_file_data, is_parent_dir=True)
                    except Exception as e_parent:
                        print(f"Warning: Failed to create FileData for parent directory {parent_dir}: {e_parent}")
            else:
                self.backButton.setVisible(False)


            items_in_dir = []
            try:
                for item_name in os.listdir(self.current_path):
                    item_path = os.path.join(self.current_path, item_name)
                    
                    excluded_names = {
                        'application data', 'local settings', 'my documents', 'nethood', 'printhood', 
                        'recent', 'sendto', 'start menu', 'templates', 'cookies', 'tracing', 
                        'localservice', 'networkservice', 'default user', 'all users', 
                        'system volume information', '$recycle.bin', 'programdata', 'documents and settings'
                    }
                    if item_name.lower() in excluded_names:
                        continue
                    if item_name.lower().startswith(tuple(['ntuser.'])) or item_name.startswith('.'): # 组合判断
                        continue

                    if os.path.islink(item_path):
                        if not os.path.exists(os.path.realpath(item_path)):
                            continue
                    
                    items_in_dir.append(item_path)

            except PermissionError:
                print(f"Permission denied to list directory contents: {self.current_path}")
                self.pathLabel.setText(self.tr(f"Error: Permission denied to list contents - {self.current_path}"))
                self.backButton.setVisible(True) # 即使无法列出，也可能需要返回
                return
            except Exception as list_e:
                print(f"Error listing directory contents {self.current_path}: {list_e}")
                self.pathLabel.setText(self.tr(f"Error listing contents: {list_e}"))
                self.backButton.setVisible(True)
                return

            items_in_dir.sort(key=lambda x: (not os.path.isdir(x), os.path.basename(x).lower()))

            for item_path in items_in_dir:
                try:
                    file_data = FileData(item_path)
                    if file_data.fluent_icon != FluentIcon.CANCEL:
                        self.addFile(file_data)
                except Exception as file_e:
                    print(f"Warning: Critical error creating FileData for {item_path}: {file_e}")

            if self.files_data:
                first_selectable_data = None
                for fd in self.files_data:
                    if fd.name != ".." and fd.fluent_icon != FluentIcon.CANCEL:
                        first_selectable_data = fd
                        break
                
                if first_selectable_data:
                    self.setSelectedFile(first_selectable_data)
                else:
                    self.infoPanel.clearFileInfo()
            else:
                self.infoPanel.clearFileInfo()

        except PermissionError:
            print(f"Permission denied to access directory: {path}")
            self.pathLabel.setText(self.tr(f"Error: Permission denied - {path}"))
            self.infoPanel.clearFileInfo()
            self.backButton.setVisible(True)
        except Exception as e:
            print(f"Failed to load directory {path}: {e}")
            self.pathLabel.setText(self.tr(f"Error loading path: {e}"))
            self.infoPanel.clearFileInfo()
            self.backButton.setVisible(True)


    def addFile(self, file_data: FileData, is_parent_dir=False):
        """ Adds a file/folder card to the view """
        if file_data.fluent_icon == FluentIcon.CANCEL:
            return

        try:
            card = FileIcon(file_data, self)
            card.clicked.connect(self.setSelectedFile)
            card.doubleClicked.connect(self.handleDoubleClick)

            if not is_parent_dir:
                self.trie.insert(file_data.name.lower(), len(self.cards))
            self.cards.append(card)
            self.files_data.append(file_data)
            self.flowLayout.addWidget(card)
        except Exception as e:
            print(f"Error adding file card for {file_data.path}: {e}")


    def setSelectedFile(self, file_data: FileData):
        """ Sets the selected file/folder and updates info panel """
        if file_data.fluent_icon == FluentIcon.CANCEL:
            if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
                self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()
            return
            
        try:
            index = -1
            for i, fd in enumerate(self.files_data):
                if fd is file_data:
                    index = i
                    break
            
            if index == -1:
                self.currentIndex = -1
                self.infoPanel.clearFileInfo()
                return

            if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
                self.cards[self.currentIndex].setSelected(False)

            self.currentIndex = index
            self.cards[index].setSelected(True)
            self.infoPanel.setFileInfo(file_data)
        except Exception as e:
            print(f"Error in setSelectedFile for {file_data.path}: {e}")
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()


    def handleDoubleClick(self, file_data: FileData):
        """ Handles double click event on a file/folder card """
        if file_data.fluent_icon == FluentIcon.CANCEL:
            return

        if file_data.is_directory:
            self.searchLineEdit.clear()
            self.load_files(file_data.path)
        else:
            self.openFile(file_data.path)

    def openFile(self, file_path: str):
        """ Placeholder for opening a file """
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            print(f"Failed to open file {file_path}: {e}")

    def search(self, keyWord: str):
        """ Searches for files/folders by name """
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
            self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()

        self.flowLayout.removeAllWidgets()

        # 如果有“..”，先加回来
        if self.files_data and self.files_data[0].name == "..":
            self.flowLayout.addWidget(self.cards[0])

        if not keyWord:
            for i, card in enumerate(self.cards):
                if card.file_data.name == "..":
                    continue
                if card.file_data.fluent_icon != FluentIcon.CANCEL:
                    card.setVisible(True)
                    self.flowLayout.addWidget(card)
            return

        items_indices = self.trie.items(keyWord.lower())
        indexes = {i[1] for i in items_indices}

        for i in range(len(self.cards)):
            card = self.cards[i]
            if card.file_data.name == "..":
                card.setVisible(True)
                self.flowLayout.addWidget(card)
                continue

            isVisible = (i in indexes) and (card.file_data.fluent_icon != FluentIcon.CANCEL)
            card.setVisible(isVisible)
            if isVisible:
                self.flowLayout.addWidget(card)

    def showAllFiles(self):
        """ Shows all files and folders in the current directory """
        if self.currentIndex >= 0 and self.currentIndex < len(self.cards):
            self.cards[self.currentIndex].setSelected(False)
            self.currentIndex = -1
            self.infoPanel.clearFileInfo()

        self.flowLayout.removeAllWidgets()
        for card in self.cards:
            if card.file_data.fluent_icon != FluentIcon.CANCEL:
                card.show()
                self.flowLayout.addWidget(card)

    def go_up_directory(self):
        """ Navigates to the parent directory """
        parent_path = os.path.dirname(self.current_path)
        # 只有当当前目录不是根目录时才允许返回
        if parent_path and parent_path != self.current_path and os.path.exists(parent_path) and os.path.isdir(parent_path):
            self.load_files(parent_path)
        else:
            print(f"Already at root or cannot access parent: {self.current_path}")


class Explorer(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setupUi()
        self.setObjectName(text.replace(' ', '-'))
        self.fileView = FileView(self)
        self.layout.addWidget(self.fileView)

    def setupUi(self):
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
```