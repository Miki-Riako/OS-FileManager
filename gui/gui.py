import os

from PySide6.QtCore import QSize, QEventLoop, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from qfluentwidgets import FluentWindow
from qfluentwidgets import NavigationItemPosition
from qfluentwidgets import setTheme, SplashScreen
from qfluentwidgets import Theme
from qfluentwidgets import FluentIcon as FIF

from .home import Home
from .terminal import Terminal
from .explorer import Explorer
from .editor import Editor
from .about import About
from .setting import Setting

class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        ...
        self.setObjectName(text.replace(' ', '-'))

class GUI(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(210, 210))
        self.show()
        self.createSubInterface()

        self.compiler = None

        self.homeInterface     = Home("Home Interface", self)
        self.terminalInterface = Terminal('Terminal Interface', self)
        self.explorerInterface = Explorer('Explorer Interface', self.terminalInterface, self)
        self.editor   = Editor('Editor Interface', self)
        self.aboutInterface    = About('About Interface', self)
        self.settingInterface  = Setting('Setting Interface', self)

        self.initNavigation()
        self.splashScreen.finish()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '主页 Home')
        self.addSubInterface(self.terminalInterface, FIF.CONNECT, '终端管理器 Teriminal Manager')
        self.addSubInterface(self.explorerInterface, FIF.CALENDAR, '资源管理器 File Explorer')
        self.addSubInterface(self.editor, FIF.EDIT, '文本编辑器 Editor')

        self.addSubInterface(self.aboutInterface, FIF.PEOPLE, '关于 About', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置 Settings', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        setTheme(Theme.DARK)
        self.resize(900, 700)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'images', 'SOSlogo.png')))
        self.setWindowTitle('欢迎！Welcome to OS-FileManager')
        self.showMaximized()

    def createSubInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(618, loop.quit)
        loop.exec()

    def setupUI(self):
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
