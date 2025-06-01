import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt # Qt.UserRole + N for custom roles if needed

SHELL_COMMANDS = [
    'ls', 'cd', 'pwd', 'mkdir', 'rm', 'cp', 'mv', 'cat', 'echo', 'grep',
    'find', 'man', 'sudo', 'apt', 'yum', 'dnf', 'pacman', 'git', 'docker',
    'python', 'pip', 'node', 'npm', 'gcc', 'make', 'ssh', 'scp', 'ping',
    'ifconfig', 'ip', 'netstat', 'ps', 'kill', 'bg', 'fg', 'jobs', 'exit',
    'clear', 'history', 'export', 'unset', 'alias', 'unalias', 'source',
    'chmod', 'chown', 'tar', 'zip', 'unzip', 'wget', 'curl', 'htop', 'top'
]

class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlighting_rules = []

        # 提示符 (Prompt)
        prompt_format = QTextCharFormat()
        prompt_format.setForeground(QColor("#50fa7b")) # 明亮的绿色 (Dracula theme-like)
        prompt_format.setFontWeight(QFont.Bold)
        prompt_pattern = r"^[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+:[^$]*\$\s"
        self.highlighting_rules.append((re.compile(prompt_pattern), prompt_format))

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
        variable_format.setForeground(QColor("#50fa7b")) # Same as prompt, or choose another green
        variable_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"\$[a-zA-Z_]\w*|\$\{[^}]+\}"), variable_format))

    def highlightBlock(self, text: str):
        # 提示符规则通常是第一个
        prompt_rule = self.highlighting_rules[0]
        prompt_pattern_compiled, prompt_fmt = prompt_rule
 
        prompt_end_offset = 0
        # 尝试匹配行首的提示符 使用 re.match 因为提示符必须在行首
        prompt_match = prompt_pattern_compiled.match(text)
        if prompt_match:
            start, end = prompt_match.span()
            self.setFormat(start, end - start, prompt_fmt)
            prompt_end_offset = end # 记录提示符的结束位置

        # 处理其他规则，但只在提示符之后的部分
        for pattern, char_format in self.highlighting_rules:
            # 跳过提示符规则，因为它已经处理过了
            if pattern == prompt_pattern_compiled:
                continue

            for match in pattern.finditer(text):
                start, end = match.span()
                # 确保匹配项不在提示符内部 (如果提示符本身可能包含关键词) 并且确保匹配项在提示符之后开始，或者根本没有提示符
                if start >= prompt_end_offset:
                    self.setFormat(start, end - start, char_format)