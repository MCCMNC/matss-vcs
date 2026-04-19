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
        """
        Initializes the version comparison panel.
        Sorts the provided versions chronologically and sets up a dual-combobox header for selection,
        along with a dark-themed QTextEdit to render the highlighted code differences.
        """
        super().__init__()
        self.setFixedWidth(400)
        # Sorting versions by version_number to ensure the dropdown sequence makes logical sense
        self.versions = sorted(versions, key=lambda x: x.version_number)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)

        # Version choice container: Left for base version, Right for comparison version
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

        # Diff window setup: Read-only display using HTML for color-coded line differences
        self.diff_display = QTextEdit()
        self.diff_display.setReadOnly(True)
        self.diff_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Applying a GitHub-style dark aesthetic to the text area
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
        """
        Triggered when the base version (left combobox) is changed.
        It filters the comparison combobox (right) to only show versions newer than the selected base,
        preventing illogical "backwards" comparisons.
        """
        v1 = self.combo_left.currentData()
        self.combo_right.clear()
        self.combo_right.addItem("Choose Second (Compare)", None)

        if v1:
            self.combo_right.setEnabled(True)
            for v in self.versions:
                # Only allow comparing against versions that came AFTER the first selection
                if v.version_number > v1.version_number:
                    self.combo_right.addItem(f"Ver {v.version_number}", v)
        else:
            self.combo_right.setEnabled(False)

        # Update the display: if only one is chosen, it shows the source code normally
        self.update_diff()

    def update_diff(self):
        """
        The core rendering engine for the panel.
        Resolves local file paths for the selected versions, reads the source text,
        and either displays a single version or calculates a unified diff using 'difflib'.
        The output is formatted as an HTML table with custom CSS for 'git-style' green/red highlighting.
        """
        v1 = self.combo_left.currentData()
        v2 = self.combo_right.currentData()

        if not v1:
            self.diff_display.clear()
            return

        self.diff_display.document().setDocumentMargin(0)

        def resolve_path(version_obj):
            """Internal helper to convert stored database paths into absolute local system paths."""
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_file_dir)
            repo_path = os.path.normpath(version_obj.project.repository.path)
            if repo_path.startswith("config"):
                return os.path.normpath(os.path.join(project_root, repo_path, version_obj.path))
            return os.path.normpath(os.path.join(repo_path, version_obj.path))

        try:
            # Load the primary version text
            path1 = resolve_path(v1)
            with open(path1, 'r', encoding='utf-8', errors='ignore') as f:
                text1 = f.readlines()

            # Initialize syntax highlighting if Pygments is available
            formatter = HtmlFormatter(nowrap=True, style='monokai', noclasses=True)
            lexer = TextLexer()
            if PYGMENTS_AVAILABLE:
                try:
                    lexer = get_lexer_for_filename(v1.path)
                except:
                    lexer = TextLexer()

            html_rows = []

            # Determine whether to show a raw file or a comparison
            if not v2:
                # --- SINGLE VIEW MODE ---
                # Simply display the code of the first version with standard formatting
                for line in text1:
                    h_line = highlight(line, lexer, formatter) if PYGMENTS_AVAILABLE else line.replace('<', '&lt;')
                    html_rows.append(
                        f"<tr><td style='width:25px;'> </td><td style='white-space:pre; color:#c9d1d9; padding:0 5px;'>{h_line}</td></tr>")
            else:
                # --- DIFF VIEW MODE ---
                # Generate a unified diff and map indicator characters to HTML colors
                path2 = resolve_path(v2)
                with open(path2, 'r', encoding='utf-8', errors='ignore') as f:
                    text2 = f.readlines()

                diff = list(difflib.unified_diff(text1, text2, n=3))

                for line in diff:
                    if not line: continue
                    indicator = line[0]
                    content = line[1:]

                    # Set up standard cell styling
                    base_td = "padding: 0px 5px; font-family: Consolas, monospace; font-size: 9.5pt; vertical-align: middle; border: none;"
                    sign_td = f"{base_td} width: 20px; text-align: center; font-weight: bold;"
                    code_td_style = f"{base_td} white-space: pre;"

                    # Assign colors based on the diff indicators (+, -, @)
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
                        # Chunk headers
                        sign_html = f"<td style='{sign_td} color: #8b949e;'> </td>"
                        code_html = f"<td style='{code_td_style} color: #8b949e; background-color: #161b22;'>{line.replace('<', '&lt;')}</td>"
                    else:
                        # Context lines (no change)
                        sign_html = f"<td style='{sign_td} color: #484f58;'> </td>"
                        h_line = highlight(line, lexer, formatter) if PYGMENTS_AVAILABLE else line.replace('<', '&lt;')
                        code_html = f"<td style='{code_td_style} color: #c9d1d9;'>{h_line}</td>"

                    html_rows.append(f"<tr>{sign_html}{code_html}</tr>")

            # Final Assembly: Wrap the table in body tags with the correct background to prevent flashing
            table_content = "".join(html_rows)
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
            # Fallback error reporting in case file paths fail to resolve or files are locked
            self.diff_display.setPlainText(f"Error: {e}")