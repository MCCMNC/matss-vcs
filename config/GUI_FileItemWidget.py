import os
from PyQt6.QtCore import Qt, QFileInfo, QSize
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QFont, QPixmap, QIcon


class FileItemWidget(QWidget):
    # Added 'current_version' parameter to the constructor
    def __init__(self, file_obj, icon, parent_page, context_type, current_version=None):
        super().__init__()
        self.file_obj = file_obj
        self.parent_page = parent_page
        self.context_type = context_type
        self.current_version = current_version # Store the version context
        self.active_buttons = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(20, 20))

        # Use .title for Projects/Repos, .path for VersionFiles
        display_text = getattr(file_obj, 'title', getattr(file_obj, 'path', "Unknown"))
        self.name_label = QLabel(display_text)
        self.name_label.setStyleSheet("color: #dce1e6;")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label, 1)

        # --- Context Switcher ---
        if self.context_type == "ProjectVersionFile":
            # SWAPPED: Delete now comes before Open in the layout
            self._add_delete_button(layout)
            self._add_open_button(layout)

        elif self.context_type in ["Project", "Repository"]:
            self._add_follow_button(layout)

    def _add_follow_button(self, layout):
        btn = QPushButton("Follow")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #20528a;
                color: white;
                border: 1px solid #388bfd;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388bfd;
            }
        """)
        btn.clicked.connect(lambda: self.parent_page.handle_follow(self.file_obj))
        layout.addWidget(btn)
        self.active_buttons.append(btn)

    def _add_open_button(self, layout):
        btn = QPushButton("Open")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: white;
                border: 1px solid #2ea043; border-radius: 3px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        # CRITICAL: If opening an audio file, it might need the version path
        btn.clicked.connect(lambda: self.parent_page.handle_file_open(self.file_obj))
        layout.addWidget(btn)
        self.active_buttons.append(btn)

    def _add_delete_button(self, layout):
        btn = QPushButton("Delete")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3e1414; color: #f85149;
                border: 1px solid #484f58; border-radius: 3px;
            }
            QPushButton:hover { background-color: #b11226; color: white; }
        """)
        # CRITICAL: We pass self.file_obj so the handler knows WHICH file to unlink
        btn.clicked.connect(lambda: self.parent_page.handle_file_delete(self.file_obj))
        layout.addWidget(btn)
        self.active_buttons.append(btn)