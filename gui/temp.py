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
    def __init__(
        self,
        path: str,
        fileName: str,
        uid: str,
        owner: str,
        access: str,
        creation_time: str,
        modified_time: str
    ):
        self.path = path
        self.fileName = fileName
        self.uid      = uid
        self.owner    = owner
        self.access   = access
        self.creation_time = creation_time
        self.modified_time = modified_time

class FileIcon(QFrame):
    clicked = Signal(open)

    def __init__(self, icon: FluentIcon, parent=None):
        super().__init__(parent=parent)
        self.icon = icon
        self.isSelected = False
        self.iconWidget = IconWidget(icon, self)
        self.nameLabel = QLabel(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.__initWidget()

    def __initWidget(self):
        self.setFixedSize(96, 96)
        self.vBoxLayout.setContentsMargins(8, 28, 8, 0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.iconWidget.setFixedSize(28, 28)
        self.vBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignHCenter)
        self.vBoxLayout.addSpacing(14)
        self.vBoxLayout.addWidget(self.nameLabel, 0, Qt.AlignHCenter)

        text = self.nameLabel.fontMetrics().elidedText(icon.value, Qt.ElideRight, 90)
        self.nameLabel.setText(text)

    def mouseReleaseEvent(self, e):
        if self.isSelected:
            return

        self.clicked.emit(self.icon)

    def setSelected(self, isSelected: bool, force=False):
        if isSelected == self.isSelected and not force:
            return

        self.isSelected = isSelected

        if not isSelected:
            self.iconWidget.setIcon(self.icon)
        else:
            icon = self.icon.icon(Theme.LIGHT if isDarkTheme() else Theme.DARK)
            self.iconWidget.setIcon(icon)

        self.setProperty('isSelected', isSelected)
        self.setStyle(QApplication.style())

    def open():
        ...


class IconInfoPanel(QFrame):
    """ Icon info panel """

    def __init__(self, icon: FluentIcon, parent=None):
        super().__init__(parent=parent)
        self.nameLabel = QLabel(icon.value, self)
        self.iconWidget = IconWidget(icon, self)
        self.iconNameTitleLabel = QLabel(self.tr('Icon name'), self)
        self.iconNameLabel = QLabel(icon.value, self)
        self.enumNameTitleLabel = QLabel(self.tr('Enum member'), self)
        self.enumNameLabel = QLabel("FluentIcon." + icon.name, self)
        self.vBoxLayout = QVBoxLayout(self)
        self.__initWidget()

    def __initWidget(self):
        self.__initLayout()
        self.vBoxLayout.setContentsMargins(16, 20, 16, 20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.iconWidget.setFixedSize(48, 48)
        self.setFixedWidth(216)
        self.nameLabel.setObjectName('nameLabel')
        self.iconNameTitleLabel.setObjectName('subTitleLabel')
        self.enumNameTitleLabel.setObjectName('subTitleLabel')

    def __initLayout(self):
        self.vBoxLayout.addWidget(self.nameLabel)
        self.vBoxLayout.addSpacing(16)
        self.vBoxLayout.addWidget(self.iconWidget)
        self.vBoxLayout.addSpacing(45)
        self.vBoxLayout.addWidget(self.iconNameTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.iconNameLabel)
        self.vBoxLayout.addSpacing(34)
        self.vBoxLayout.addWidget(self.enumNameTitleLabel)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.enumNameLabel)

    def setIcon(self, icon: FluentIcon):
        self.iconWidget.setIcon(icon)
        self.nameLabel.setText(icon.value)
        self.iconNameLabel.setText(icon.value)
        self.enumNameLabel.setText("FluentIcon."+icon.name)

class Explorer(QWidget):
    def __init__(self, text: str, terminal_manager: Terminal, parent=None):
        super().__init__(parent=parent)
        self.setupUi()
        self.explorerLabel = TitleLabel('File Explorer', self)
        self.searchLineEdit = SearchLineEdit(self)
        self.view = QFrame(self)
        self.scrollArea = SmoothScrollArea(self.view)
        self.scrollWidget = QWidget(self.scrollArea)
        self.infoPanel = IconInfoPanel(FluentIcon.MENU, self)
        self.hBoxLayout = QHBoxLayout(self.view)
        self.flowLayout = FlowLayout(self.scrollWidget, isTight=True)

        # terminal_manager.requestExplorerRefresh.connect(self.load_current_terminal_directory)
        self.trie = Trie() # 用于File Explorer的快速搜索
        self.cards = []
        self.currentIndex = -1

        self.__initWidget()
        self.setObjectName(text.replace(' ', '-'))

    def __initWidget(self):
        self.__initLayout()
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(12)

        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setViewportMargins(0, 5, 0, 5)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)

        self.flowLayout.setVerticalSpacing(8)
        self.flowLayout.setHorizontalSpacing(8)
        self.flowLayout.setContentsMargins(8, 3, 8, 8)

        self.searchLineEdit.setPlaceholderText('Search files')
        self.searchLineEdit.setFixedWidth(1096)
        self.searchLineEdit.textChanged.connect(self.search)
        self.searchLineEdit.clearSignal.connect(self.showAllIcons)
        self.searchLineEdit.searchSignal.connect(self.search)

    def __initLayout(self):
        self.layout.addWidget(self.explorerLabel)
        self.layout.addWidget(self.searchLineEdit)
        self.layout.addWidget(self.view)
        self.hBoxLayout.addWidget(self.scrollArea)
        self.hBoxLayout.addWidget(self.infoPanel, 0, Qt.AlignRight)

    def setupUi(self):
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

    def addFile(self, file : FileData):
        card = FileIcon(file.access, self)
        card.clicked.connect(self.open)

        self.trie.insert(file.fileName, len(self.cards))
        self.cards.append(card)
        self.flowLayout.addWidget(card)

    def search(self, keyWord: str):
        items = self.trie.items(keyWord.lower())
        indexes = {i[1] for i in items}
        self.flowLayout.removeAllWidgets()

        for i, card in enumerate(self.cards):
            isVisible = i in indexes
            card.setVisible(isVisible)
            if isVisible:
                self.flowLayout.addWidget(card)

    def showAllIcons(self):
        '''显示所有 ICON 仅当搜索框为空时'''
        self.flowLayout.removeAllWidgets()
        for card in self.cards:
            card.show()
            self.flowLayout.addWidget(card)

    def setSelectedIcon(self, icon: FluentIcon):
        ...

    def open(self):
        ...

