import os
from PyQt6.QtCore import Qt, QFileInfo, QSize
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QFont, QPixmap, QIcon

from GUIFunctions import guiLocalDeviceHasDefaultProgram
from vcs_core.models import RepositoryMembership

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QFileIconProvider
from PyQt6.QtGui import QPixmap, QIcon

from GUIFunctions import guiLocalDeviceHasDefaultProgram
from vcs_core.models import RepositoryMembership

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QFileIconProvider
from PyQt6.QtGui import QPixmap, QIcon

from GUIFunctions import guiLocalDeviceHasDefaultProgram
from vcs_core.models import RepositoryMembership


class FileItemWidget(QWidget):
    def __init__(self, file_obj, icon, parent_page, context_type, current_version=None, explicitNoFollow=False):
        super().__init__()
        self.file_obj = file_obj
        self.parent_page = parent_page
        self.context_type = context_type
        self.current_version = current_version
        self.active_buttons = []
        self.explicitNoFollow = explicitNoFollow

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(5)  # Small spacing between icons and text
        self.setFixedHeight(50)

        textSize = 12
        folder_icon = QFileIconProvider().icon(QFileIconProvider.IconType.Folder)

        # 1. Handle Version Label (ProjectVersion context only)
        if self.context_type == "ProjectVersion" and hasattr(file_obj, 'version_number'):
            self.ver_label = QLabel(f"Ver {file_obj.version_number}")
            self.ver_label.setStyleSheet("color: #8b949e; font-weight: bold; margin-right: 5px;")
            self.ver_label.setFixedWidth(50)
            layout.addWidget(self.ver_label)

        # 2. Universal Path/Icon Logic
        if self.context_type == "ProjectVersion":
            raw_path = getattr(self.file_obj, 'path', "")
        else:
            raw_path = getattr(file_obj, 'title', getattr(file_obj, 'path', "Unknown"))

        normalized_path = os.path.normpath(raw_path)
        parts = normalized_path.split(os.sep) if raw_path != "Unknown" else ["Unknown"]

        # 3. Build the path incrementally (Icon -> Folder Name -> Slash)
        if len(parts) > 1:
            for folder_name in parts[:-1]:
                # Add Folder Icon
                f_icon_label = QLabel()
                f_icon_label.setPixmap(folder_icon.pixmap(18, 18))
                layout.addWidget(f_icon_label)

                # Add Folder Name + separator
                f_text_label = QLabel(f"{folder_name}\\")
                f_text_label.setStyleSheet(f"color: #dce1e6; font-size: {textSize}pt;")
                layout.addWidget(f_text_label)

        # 4. Add the Final File Icon
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(20, 20))
        layout.addWidget(self.icon_label)

        # 5. Add the Final Filename Label
        filename = parts[-1]
        if self.context_type == "ProjectVersion":
            display_text = f"{filename} | {getattr(file_obj, 'message', '')}"
        else:
            display_text = filename

        self.name_label = QLabel(display_text)
        self.name_label.setStyleSheet(f"color: #dce1e6; font-size: {textSize}pt;")
        layout.addWidget(self.name_label, 1)  # Give the final label the stretch factor

        # --- Context Switcher (Button Logic) ---
        if self.context_type == "ProjectVersionFile":
            self._add_delete_button(layout, action_type="file")
            self._add_open_button(layout, is_version_context=False)

        elif self.context_type == "ProjectVersion":
            parent_repo = getattr(self.file_obj.project, 'repository', None)
            can_approve = False
            can_edit = False

            if parent_repo:
                can_edit = RepositoryMembership.objects.filter(
                    user=parent_page.user,
                    repository=parent_page.currentRepository,
                    repo_role__in=["Admin", "Author"]
                ).exists()
                can_approve = RepositoryMembership.objects.filter(
                    user=parent_page.user,
                    repository=parent_page.currentRepository,
                    repo_role__in=["Admin", "Reviewer"]
                ).exists()

            if can_edit:
                if not (parent_repo.repoType == "Code" and file_obj.version_number == 1):
                    self._add_delete_button(layout, action_type="version")

            if file_obj.status == "Draft" and can_approve:
                self.name_label.setStyleSheet(f"color: #f06081; font-size: {textSize}pt;")
                self._add_approve_button(layout)

            file_path = getattr(self.file_obj, 'path', "")
            if file_path:
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                project_extensions = ['.rpp', '.wav', '.mp3', '.txt', '.pdf']
                if guiLocalDeviceHasDefaultProgram(ext) or ext in project_extensions:
                    self._add_open_button(layout, is_version_context=True)

            if not self.explicitNoFollow:
                self._add_follow_button(layout)

        elif self.context_type == "Project":
            parent_repo = getattr(self.file_obj, 'repository', None)
            can_edit = False
            if parent_repo:
                can_edit = RepositoryMembership.objects.filter(
                    user=parent_page.user,
                    repository=parent_repo,
                    repo_role__in=["Admin", "Author"]
                ).exists()

            if can_edit:
                self._add_delete_button(layout)
            self._add_open_button(layout)
            if not self.explicitNoFollow:
                self._add_follow_button(layout)

        elif self.context_type == "Repository":
            is_admin = RepositoryMembership.objects.filter(
                user=parent_page.user,
                repository=file_obj,
                repo_role="Admin"
            ).exists()
            if is_admin:
                self._add_delete_button(layout, action_type="repository")
            if not self.explicitNoFollow:
                self._add_follow_button(layout)
    def _add_follow_button(self, layout):
        if self.explicitNoFollow : return
        btn = QPushButton("Follow")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #20528a; color: white;
                border: 1px solid #388bfd; border-radius: 3px; font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        btn.clicked.connect(lambda: self.parent_page.handle_follow(self.file_obj))
        layout.addWidget(btn)
        self.active_buttons.append(btn)

    def _add_approve_button(self, layout):
        btn = QPushButton("Approve")
        btn.setFixedSize(75, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2bab13; color: black;
                border: 1px solid #388bfd; border-radius: 3px; font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        btn.clicked.connect(lambda: self.parent_page.handle_approve(self.file_obj))
        layout.addWidget(btn)
        self.active_buttons.append(btn)

    def _add_open_button(self, layout, is_version_context=False):
        btn = QPushButton("Open")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: white;
                border: 1px solid #2ea043; border-radius: 3px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)

        if is_version_context:
            btn.clicked.connect(lambda: self.parent_page.handle_version_open(self.file_obj))
        else:
            btn.clicked.connect(lambda: self.parent_page.handle_file_open(self.file_obj))

        layout.addWidget(btn)
        self.active_buttons.append(btn)

    def _add_delete_button(self, layout, action_type="file"):
        btn = QPushButton("Delete")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3e1414; color: #f85149;
                border: 1px solid #484f58; border-radius: 3px;
            }
            QPushButton:hover { background-color: #b11226; color: white; }
        """)

        # Route to the correct callback based on what we are deleting
        if action_type == "repository":
            btn.clicked.connect(lambda: self.parent_page.handle_delete(self.file_obj))
        elif action_type == "version":
            btn.clicked.connect(lambda: self.parent_page.handle_version_delete(self.file_obj))
        else: # default to file
            btn.clicked.connect(lambda: self.parent_page.handle_file_delete(self.file_obj))

        layout.addWidget(btn)
        self.active_buttons.append(btn)