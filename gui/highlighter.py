import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

SHELL_COMMANDS = [
    'ls', 'cd', 'pwd', 'mkdir', 'rm', 'cp', 'mv', 'cat', 'echo', 'grep',
    'find', 'man', 'sudo', 'apt', 'yum', 'dnf', 'pacman', 'git', 'docker',
    'python', 'pip', 'node', 'npm', 'gcc', 'make', 'ssh', 'scp', 'ping',
    'ifconfig', 'ip', 'netstat', 'ps', 'kill', 'bg', 'fg', 'jobs', 'exit',
    'clear', 'history', 'export', 'unset', 'alias', 'unalias', 'source',
    'chmod', 'chown', 'tar', 'zip', 'unzip', 'wget', 'curl', 'htop', 'top',

    'logout', 'format', 'mkuser', 'rmuser', 'lsuser', 'passwd', 'trust', 'distrust', 'vim',
    'help', 'rmdir', 'touch'
]

class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlighting_rules = []

        # 提示符 (Prompt)
        self.prompt_user_host_color = QColor("#50fa7b")  # 亮绿色 (Dracula theme-like)
        self.prompt_path_color = QColor("#8be9fd")       # 青蓝色 (Dracula theme-like)
        self.prompt_user_host_format = QTextCharFormat()
        self.prompt_user_host_format.setForeground(self.prompt_user_host_color)
        self.prompt_user_host_format.setFontWeight(QFont.Bold)

        self.prompt_path_format = QTextCharFormat()
        self.prompt_path_format.setForeground(self.prompt_path_color)
        # self.prompt_path_format.setFontWeight(QFont.Bold) # 路径通常不加粗，可根据喜好决定

        self.prompt_regex = re.compile(
            r"^(?P<user_host>[\w\.-]+@[\w\.-]+)"  # user@host
            r"(?P<colon>:)"                      # :
            r"(?P<path>.*?)"                     # path part (non-greedy)
            r"(?P<dollar_space>\$\s)"            # $
        )

        # 注释 (Comments)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272a4")) # 紫灰色 (Dracula theme-like)
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"#.*$"), comment_format))

        # 字符串 (Strings)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c")) # 黄色 (Dracula theme-like)
        self.highlighting_rules.append((re.compile(r"'[^']*'"), string_format))
        self.highlighting_rules.append((re.compile(r'"[^"]*"'), string_format))

        # 命令 (Keywords)
        command_format = QTextCharFormat()
        command_format.setForeground(QColor("#8be9fd")) # 青色 (Dracula theme-like)
        command_format.setFontWeight(QFont.Bold)
        command_pattern = r"\b(" + "|".join(SHELL_COMMANDS) + r")\b"
        self.highlighting_rules.append((re.compile(command_pattern), command_format))

        # 选项/标志 (Options/Flags)
        option_format = QTextCharFormat()
        option_format.setForeground(QColor("#ff79c6")) # 粉色 (Dracula theme-like)
        self.highlighting_rules.append((re.compile(r"(?<!\w)(-{1,2}[\w-]+)"), option_format))

        # 数字 (Numbers)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#bd93f9")) # 紫色 (Dracula theme-like)
        self.highlighting_rules.append((re.compile(r"\b\d+(\.\d+)?\b"), number_format))

        # 操作符 (Operators)
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("#ffb86c")) # 橙色 (Dracula theme-like)
        operator_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r"(\|\||&&|\||&|;|>|<)"), operator_format))

        # Shell Variables (e.g., $VAR, ${VAR_NAME})
        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor("#50fa7b"))
        variable_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"\$[a-zA-Z_]\w*|\$\{[^}]+\}"), variable_format))

    def highlightBlock(self, text: str):
        prompt_match = self.prompt_regex.match(text)
        prompt_end_offset = 0 # 默认没有提示符
        if prompt_match:
            start = prompt_match.start('user_host') # 应用绿色到 user@host 部分
            end = prompt_match.end('user_host')
            self.setFormat(start, end - start, self.prompt_user_host_format)
            start = prompt_match.start('path') # 应用蓝色到路径部分
            end = prompt_match.end('path')
            self.setFormat(start, end - start, self.prompt_path_format)
            prompt_end_offset = prompt_match.end() # 整个提示符的结束位置，用于后续规则的起始点
        for pattern, char_format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                # 确保匹配项在提示符的结束位置之后才应用高亮
                if start >= prompt_end_offset:
                    self.setFormat(start, end - start, char_format)