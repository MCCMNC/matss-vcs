import difflib
import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit

from DBFunctions import databaseStoragePath


class DiffPanel(QWidget):
    def __init__(self, versions):
        super().__init__()
        self.setFixedWidth(350)
        self.versions = sorted(versions, key=lambda x: x.version_number)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)

        # Dropdown Header Row
        header_layout = QHBoxLayout()
        self.combo_left = QComboBox()
        self.combo_right = QComboBox()
        self.combo_right.setEnabled(False)

        self.combo_left.addItem("Select First", None)
        for v in self.versions:
            self.combo_left.addItem(f"Ver {v.version_number}", v)

        header_layout.addWidget(self.combo_left)
        header_layout.addWidget(self.combo_right)
        layout.addLayout(header_layout)

        # Diff Display Area
        self.diff_display = QTextEdit()
        self.diff_display.setReadOnly(True)
        self.diff_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.diff_display.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #30363d;
            }
        """)
        layout.addWidget(self.diff_display)

        # Connections
        self.combo_left.currentIndexChanged.connect(self.update_right_options)
        self.combo_right.currentIndexChanged.connect(self.run_diff)

    def update_right_options(self):
        self.combo_right.clear()
        self.combo_right.addItem("Select Second", None)

        v1 = self.combo_left.currentData()
        if v1:
            self.combo_right.setEnabled(True)
            # Filter: Only allow versions HIGHER than V1
            for v in self.versions:
                if v.version_number > v1.version_number:
                    self.combo_right.addItem(f"Ver {v.version_number}", v)
        else:
            self.combo_right.setEnabled(False)

    def run_diff(self):
        v1 = self.combo_left.currentData()
        v2 = self.combo_right.currentData()
        if not v1 or not v2: return

        try:
            # 1. Get the Repo folder name from the DB
            # Example: "Demo Code Repository_24"
            repo_folder = v1.project.repository.path

            # 2. Build the Absolute Path to the Repository Root
            base_storage = os.path.normpath(databaseStoragePath)

            # Safety check to prevent doubling the base storage if repo_folder is already absolute
            if os.path.isabs(repo_folder) or repo_folder.startswith(base_storage):
                repo_root_disk = repo_folder
            else:
                repo_root_disk = os.path.join(base_storage, repo_folder)

            # 3. Join with the Versioned path (e.g., "RepoFolder 1/Document 4_1.txt")
            # os.path.join + os.path.normpath fixes the mixed \ and / slashes
            path1 = os.path.normpath(os.path.join(repo_root_disk, v1.path))
            path2 = os.path.normpath(os.path.join(repo_root_disk, v2.path))

            print(f"Final Disk Path 1: {path1}")
            print(f"Final Disk Path 2: {path2}")

            # 4. Read and Diff
            with open(path1, 'r', encoding='utf-8', errors='ignore') as f:
                text1 = f.readlines()
            with open(path2, 'r', encoding='utf-8', errors='ignore') as f:
                text2 = f.readlines()

            diff = difflib.unified_diff(
                text1, text2,
                fromfile=f'V{v1.version_number}',
                tofile=f'V{v2.version_number}'
            )

            # 5. Format for the UI
            html_output = "<pre style='margin:0; font-family: Consolas, monospace;'>"
            for line in diff:
                # Escape HTML characters so code like <html> doesn't vanish
                clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                if line.startswith('+'):
                    html_output += f"<span style='color:#3fb950;'>{clean_line}</span>"  # Green
                elif line.startswith('-'):
                    html_output += f"<span style='color:#f85149;'>{clean_line}</span>"  # Red
                elif line.startswith('@@'):
                    html_output += f"<span style='color:#8b949e;'>{clean_line}</span>"  # Gray header
                else:
                    html_output += clean_line
            html_output += "</pre>"

            self.diff_display.setHtml(html_output)

        except Exception as e:
            self.diff_display.setText(f"Error loading diff: {e}")