import os
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QFileIconProvider
from GUIFunctions import guiLocalDeviceHasDefaultProgram


class FileItemWidget(QWidget):
    def __init__(self, file_obj, icon, parent_page, context_type, current_version=None, explicitNoFollow=False,
                 can_edit=False, is_admin=False, can_approve=False):
        super().__init__()
        self.file_obj = file_obj
        self.parent_page = parent_page
        self.context_type = context_type
        self.current_version = current_version
        self.active_buttons = []
        self.explicitNoFollow = explicitNoFollow

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(5)
        self.setFixedHeight(50)

        textSize = 12
        folder_icon = QFileIconProvider().icon(QFileIconProvider.IconType.Folder)

        # Helper to extract data whether file_obj is a dict (API) or an object (Local)
        def get_val(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # 1. Handle Version Label (ProjectVersion context only)
        v_num = get_val(self.file_obj, 'version_number')
        if self.context_type == "ProjectVersion" and v_num is not None:
            self.ver_label = QLabel(f"Ver {v_num}")
            self.ver_label.setStyleSheet("color: #8b949e; font-weight: bold; margin-right: 5px;")
            self.ver_label.setFixedWidth(50)
            layout.addWidget(self.ver_label)

        # 2. Universal Path/Icon Logic - This is where the "Map" crash was happening
        if self.context_type == "ProjectVersion":
            raw_path = get_val(self.file_obj, 'path', "")
        else:
            # Try title, then path
            raw_path = get_val(self.file_obj, 'title') or get_val(self.file_obj, 'path') or "Unknown"

        # Force raw_path to be a string. If it's a dict, extract the 'path' key from it.
        if isinstance(raw_path, dict):
            raw_path = raw_path.get('path', str(raw_path))

        # Final safety check for the "Double Drive" issue seen in logs
        path_str = str(raw_path)
        if path_str.count(':') > 1:
            path_str = path_str.split(':')[-1][1:]

        normalized_path = os.path.normpath(path_str)
        print("normalized_path : ", normalized_path)
        parts = normalized_path.split(os.sep) if path_str != "Unknown" else ["Unknown"]

        # 3. Build the path incrementally (Code projects)
        if hasattr(parent_page, 'programType') and parent_page.programType == "Code":
            if len(parts) > 1:
                for folder_name in parts[:-1]:
                    f_icon_label = QLabel()
                    f_icon_label.setPixmap(folder_icon.pixmap(18, 18))
                    layout.addWidget(f_icon_label)

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
            msg = get_val(self.file_obj, 'message', '')
            display_text = f"{filename} | {msg}"
        else:
            display_text = filename

        self.name_label = QLabel(display_text)
        self.name_label.setStyleSheet(f"color: #dce1e6; font-size: {textSize}pt;")
        layout.addWidget(self.name_label, 1)

        # 6. Author label
        if self.context_type == "ProjectVersion":
            author_obj = get_val(self.file_obj, 'author')
            author_name = get_val(author_obj, 'username', 'Unknown') if author_obj else "Unknown"

            self.author_label = QLabel(f"by {author_name}")
            self.author_label.setStyleSheet("color: #8b949e; font-size: 10pt; margin-left: -4px; padding-right: 10px;")
            layout.addWidget(self.author_label)

        # --- Context Switcher (Button Logic) ---
        status = get_val(self.file_obj, 'status')

        if self.context_type == "ProjectVersionFile":
            self._add_delete_button(layout, action_type="file")
            self._add_open_button(layout, is_version_context=False)

        elif self.context_type == "ProjectVersion":
            project_obj = get_val(self.file_obj, 'project')
            parent_repo = get_val(project_obj, 'repository') if project_obj else None
            repo_type = get_val(parent_repo, 'repoType') if parent_repo else None

            if can_edit:
                if not (repo_type == "Code" and v_num == 1):
                    self._add_delete_button(layout, action_type="version")

            if status != "Approved":
                self.name_label.setStyleSheet(f"color: #f06081; font-size: {textSize}pt;")
                if can_approve:
                    self._add_approve_button(layout)

            file_path = get_val(self.file_obj, 'path', "")
            if file_path:
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                project_extensions = ['.rpp', '.wav', '.mp3', '.txt', '.pdf']
                if guiLocalDeviceHasDefaultProgram(ext) or ext in project_extensions:
                    self._add_open_button(layout, is_version_context=True)

            if not self.explicitNoFollow:
                self._add_follow_button(layout)

        elif self.context_type == "Project":
            if can_edit:
                self._add_delete_button(layout, "project")

            file_path = get_val(self.file_obj, 'path', "")
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            project_extensions = ['.rpp', '.wav', '.mp3', '.txt', '.pdf']
            if guiLocalDeviceHasDefaultProgram(ext) or ext in project_extensions:
                self._add_open_button(layout)
            if not self.explicitNoFollow:
                self._add_follow_button(layout)

        elif self.context_type == "Repository":
            self._add_pull_button(layout)
            if is_admin:
                self._add_delete_button(layout, action_type="repository")
            if not self.explicitNoFollow:
                self._add_follow_button(layout)
    def _add_pull_button(self,layout):
        btn = QPushButton("Pull")
        btn.setFixedSize(60, 25)
        btn.setStyleSheet("""
                    QPushButton {
                        background-color: #82ceea color: black;
                        border: 1px solid #388bfd; border-radius: 3px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #82ceea; }
                """)
        btn.clicked.connect(lambda: self.parent_page.handle_pull(self.file_obj))
        layout.addWidget(btn)
        self.active_buttons.append(btn)
        return 0
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
        elif action_type == "project":
            btn.clicked.connect(lambda: self.parent_page.handle_project_delete(self.file_obj))
        else: # default to file
            btn.clicked.connect(lambda: self.parent_page.handle_file_delete(self.file_obj))

        layout.addWidget(btn)
        self.active_buttons.append(btn)