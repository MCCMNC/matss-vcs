import os
import difflib
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, TextLexer
    from pygments.formatters import HtmlFormatter

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

class DiffPanel(QWidget):
    def __init__(self, versions):
        super().__init__()
        self.setFixedWidth(400)
        # Sorting versions by version_number
        self.versions = sorted(versions, key=lambda x: x.version_number)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)

        # Version choice container
        header_layout = QHBoxLayout()
        self.combo_left = QComboBox()
        self.combo_right = QComboBox()
        self.combo_right.setEnabled(False)

        self.combo_left.addItem("Choose First", None)
        for v in self.versions:
            self.combo_left.addItem(f"Ver {v.version_number}", v)

        self.combo_left.currentIndexChanged.connect(self.on_left_changed)
        self.combo_right.currentIndexChanged.connect(self.update_diff)

        header_layout.addWidget(self.combo_left)
        header_layout.addWidget(self.combo_right)
        layout.addLayout(header_layout)

        # Diff window
        self.diff_display = QTextEdit()
        self.diff_display.setReadOnly(True)
        self.diff_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # Style
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
        self.combo_right.addItem("Choose Second (Compare)", None)

        if v1:
            self.combo_right.setEnabled(True)
            for v in self.versions:
                if v.version_number > v1.version_number:
                    self.combo_right.addItem(f"Ver {v.version_number}", v)
        else:
            self.combo_right.setEnabled(False)

        # Trigger the display update even if v2 isn't chosen yet
        self.update_diff()

    def update_diff(self):
        v1 = self.combo_left.currentData()
        v2 = self.combo_right.currentData()

        if not v1:
            self.diff_display.clear()
            return

        self.diff_display.document().setDocumentMargin(0)

        def resolve_path(version_obj):
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_file_dir)
            repo_path = os.path.normpath(version_obj.project.repository.path)
            if repo_path.startswith("config"):
                return os.path.normpath(os.path.join(project_root, repo_path, version_obj.path))
            return os.path.normpath(os.path.join(repo_path, version_obj.path))

        try:
            path1 = resolve_path(v1)
            with open(path1, 'r', encoding='utf-8', errors='ignore') as f:
                text1 = f.readlines()

            formatter = HtmlFormatter(nowrap=True, style='monokai', noclasses=True)

            lexer = TextLexer()
            if PYGMENTS_AVAILABLE:
                try:
                    lexer = get_lexer_for_filename(v1.path)
                except:
                    lexer = TextLexer()

            html_rows = []

            # 2. Process Lines
            if not v2:
                # --- SINGLE VIEW MODE ---
                for line in text1:
                    h_line = highlight(line, lexer, formatter) if PYGMENTS_AVAILABLE else line.replace('<', '&lt;')
                    html_rows.append(
                        f"<tr><td style='width:25px;'> </td><td style='white-space:pre; color:#c9d1d9; padding:0 5px;'>{h_line}</td></tr>")
            else:
                # --- DIFF VIEW MODE ---
                path2 = resolve_path(v2)
                with open(path2, 'r', encoding='utf-8', errors='ignore') as f:
                    text2 = f.readlines()

                diff = list(difflib.unified_diff(text1, text2, n=3))

                for line in diff:
                    if not line: continue
                    indicator = line[0]
                    content = line[1:]

                    # Table cell styles
                    base_td = "padding: 0px 5px; font-family: Consolas, monospace; font-size: 9.5pt; vertical-align: middle; border: none;"
                    sign_td = f"{base_td} width: 20px; text-align: center; font-weight: bold;"
                    code_td_style = f"{base_td} white-space: pre;"

                    if indicator == '+':
                        sign_html = f"<td style='{sign_td} background-color: #238636; color: #ffffff;'>+</td>"
                        h_line = highlight(content, lexer, formatter) if PYGMENTS_AVAILABLE else content.replace('<',
                                                                                                                 '&lt;')
                        code_html = f"<td style='{code_td_style} color: #aff5b4;'>{h_line}</td>"
                    elif indicator == '-':
                        sign_html = f"<td style='{sign_td} background-color: #da3633; color: #ffffff;'>-</td>"
                        h_line = highlight(content, lexer, formatter) if PYGMENTS_AVAILABLE else content.replace('<',
                                                                                                                 '&lt;')
                        code_html = f"<td style='{code_td_style} color: #ffa198;'>{h_line}</td>"
                    elif indicator == '@':
                        sign_html = f"<td style='{sign_td} color: #8b949e;'> </td>"
                        code_html = f"<td style='{code_td_style} color: #8b949e; background-color: #161b22;'>{line.replace('<', '&lt;')}</td>"
                    else:
                        sign_html = f"<td style='{sign_td} color: #484f58;'> </td>"
                        h_line = highlight(line, lexer, formatter) if PYGMENTS_AVAILABLE else line.replace('<', '&lt;')
                        code_html = f"<td style='{code_td_style} color: #c9d1d9;'>{h_line}</td>"

                    html_rows.append(f"<tr>{sign_html}{code_html}</tr>")

            # 3. Final HTML Assembly
            table_content = "".join(html_rows)
            # Clean background-color: #0d1117; on the body is the key to no yellow
            full_html = f"""
            <html>
            <body style="background-color: #0d1117; margin: 0; padding: 0;">
                <table cellspacing="0" cellpadding="0" style="border-collapse: collapse; width: 100%; background-color: #0d1117;">
                    {table_content}
                </table>
            </body>
            </html>
            """
            self.diff_display.setHtml(full_html)

        except Exception as e:
            self.diff_display.setPlainText(f"Error: {e}")