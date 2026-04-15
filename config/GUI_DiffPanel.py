import os
import django
import difflib
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit
from PyQt6.QtGui import QFont

# --- DJANGO SETUP ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    django.setup()
except Exception:
    pass

# Опитваме импорт на Pygments
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, TextLexer
    from pygments.formatters import HtmlFormatter

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

from DBFunctions import databaseStoragePath


class DiffPanel(QWidget):
    def __init__(self, versions):
        super().__init__()
        self.setFixedWidth(400)
        # Сортираме версиите по номер
        self.versions = sorted(versions, key=lambda x: x.version_number)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)

        # Контейнер за избор на версии
        header_layout = QHBoxLayout()
        self.combo_left = QComboBox()
        self.combo_right = QComboBox()
        self.combo_right.setEnabled(False)

        self.combo_left.addItem("Избери Версия 1", None)
        for v in self.versions:
            self.combo_left.addItem(f"Ver {v.version_number}", v)

        self.combo_left.currentIndexChanged.connect(self.on_left_changed)
        self.combo_right.currentIndexChanged.connect(self.update_diff)

        header_layout.addWidget(self.combo_left)
        header_layout.addWidget(self.combo_right)
        layout.addLayout(header_layout)

        # Прозорец за показване на Diff
        self.diff_display = QTextEdit()
        self.diff_display.setReadOnly(True)
        self.diff_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # Стилизация в стила на GitHub Dark
        self.diff_display.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.diff_display)

    def on_left_changed(self, index):
        v1 = self.combo_left.currentData()
        self.combo_right.clear()
        self.combo_right.addItem("Избери Версия 2", None)

        if v1:
            self.combo_right.setEnabled(True)
            for v in self.versions:
                # Показваме само по-нови версии в десния комбобокс
                if v.version_number > v1.version_number:
                    self.combo_right.addItem(f"Ver {v.version_number}", v)
        else:
            self.combo_right.setEnabled(False)

    def update_diff(self):
        v1 = self.combo_left.currentData()
        v2 = self.combo_right.currentData()

        if not v1 or not v2:
            self.diff_display.clear()
            return

        # ВАЖНО: Тук Django обектите трябва да имат поле 'path'
        path1 = os.path.join(databaseStoragePath, v1.path)
        path2 = os.path.join(databaseStoragePath, v2.path)

        try:
            # Четем файловете с 'ignore' на грешките за бинарни файлове
            with open(path1, 'r', encoding='utf-8', errors='ignore') as f:
                text1 = f.readlines()
            with open(path2, 'r', encoding='utf-8', errors='ignore') as f:
                text2 = f.readlines()

            diff = list(difflib.unified_diff(
                text1, text2,
                fromfile=f'V{v1.version_number}',
                tofile=f'V{v2.version_number}'
            ))

            if not diff:
                self.diff_display.setHtml("<b style='color:gray; padding:10px;'>Няма открити разлики.</b>")
                return

            # Настройваме синтактичния анализатор
            lexer = TextLexer()
            formatter = HtmlFormatter(nowrap=True)
            if PYGMENTS_AVAILABLE:
                try:
                    # Използваме името на файла за определяне на езика
                    lexer = get_lexer_for_filename(v1.path)
                except:
                    lexer = TextLexer()

            html_output = "<pre style='margin:0; font-family: Consolas, monospace; font-size: 9pt;'>"

            for line in diff:
                # Ескейпваме символи за HTML безопасност
                clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                # Обработка на съдържанието за подчертаване
                content = line[1:] if len(line) > 1 else ""
                highlighted_content = highlight(content, lexer, formatter) if PYGMENTS_AVAILABLE else clean_line[1:]

                if line.startswith('+'):
                    html_output += f"<div style='background-color: #1a361e; color:#3fb950;'>+ {highlighted_content}</div>"
                elif line.startswith('-'):
                    html_output += f"<div style='background-color: #3b1a1a; color:#f85149;'>- {highlighted_content}</div>"
                elif line.startswith('@@'):
                    html_output += f"<div style='color:#8b949e; background-color: #161b22;'>{clean_line}</div>"
                else:
                    # За нормалните редове подчертаваме целия ред
                    highlighted_full = highlight(line, lexer, formatter) if PYGMENTS_AVAILABLE else clean_line
                    html_output += f"<div>{highlighted_full}</div>"

            html_output += "</pre>"

            style_defs = formatter.get_style_defs('.highlight') if PYGMENTS_AVAILABLE else ""
            full_html = f"<style>{style_defs}</style>{html_output}"

            self.diff_display.setHtml(full_html)

        except Exception as e:
            self.diff_display.setPlainText(f"Грешка при четене на файловете: {e}\nПът: {path1}")