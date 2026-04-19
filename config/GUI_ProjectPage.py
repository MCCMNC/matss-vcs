from PyQt6.QtCore import QSize
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUIHelperWindows import *


class ProjectPage(QWidget):
    def __init__(self, loginUser, project_data, back_to_repo_callback, logout_callback, version_callback,
                 pfp_pixmap=None, programType="Studio"):
        """Initializes the Project page, sets up the user session, anchors the parent repository, and builds the UI layout and action buttons."""
        super().__init__()
        self.programType = programType
        self.user = loginUser
        self.project_data = project_data
        self.currentRepository = project_data.repository
        self.back_callback = back_to_repo_callback
        self.on_logout = logout_callback
        self.version_callback = version_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.projectVersionData = getProjectVersionsByProjectID(self.project_data.id)

        self.setAcceptDrops(True)  # Enable at page level but filter in the drop event
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"ProjectPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")
        self.handleAddUser = "TO BE OVERWRITTEN"
        self.handleManageUsers = "TO BE OVERWRITTEN"

        # Builds the UI Design and containers
        gui_buildDesign(self, "Project", self.programType)
        # We create the button row and add buttons to it
        gui_buildBottomRow(self, "Project")

    # -------------------- Handlers --------------------

    def handle_version_open(self, version_obj):
        """Resolves the absolute disk path for a specific versioned file and opens it using the system's default application."""
        try:
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_file_dir)
            repo_path_str = os.path.normpath(self.project_data.repository.path)

            if repo_path_str.startswith("config"):
                repo_base_disk_path = os.path.normpath(os.path.join(project_root, repo_path_str))
            else:
                base_storage = os.path.normpath(databaseStoragePath)
                repo_base_disk_path = os.path.normpath(os.path.join(base_storage, repo_path_str))

            full_path = os.path.normpath(os.path.join(repo_base_disk_path, version_obj.path))

            if not os.path.exists(full_path):
                QMessageBox.warning(self, "File Not Found", f"No file at:\n{full_path}")
                return

            if sys.platform == "win32":
                os.startfile(full_path)
            else:
                project_dir = os.path.dirname(full_path)
                subprocess.Popen(["xdg-open", full_path], cwd=project_dir)

        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Error: {e}")

    def handle_version_delete(self, version_obj):
        """Calculates which unique files will be orphaned by deleting this version and prompts the user for confirmation before removal."""
        m2m_attr = 'version_files' if hasattr(version_obj, 'version_files') else 'files'
        associated_files = getattr(version_obj, m2m_attr).all()

        orphaned_files_paths = []
        for f in associated_files:
            usage_list = client_api.getVersionsByFileID_Client(f.id)
            if len(usage_list) <= 1:
                orphaned_files_paths.append(f.path)

        file_list_str = "\n".join([f" - {path}" for path in orphaned_files_paths])
        if not orphaned_files_paths:
            file_list_str = " (No unique files will be removed)"

        msg = (
            f"Are you sure you want to delete version {version_obj.version_number}?\n\n"
            f"The following unique files will be removed from the database:\n"
            f"{file_list_str}"
        )

        reply = QMessageBox.question(self, 'Confirm Deletion', msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if client_api.api_removeProjectVersionFromDB(self.user, version_obj):
                self.refresh_version_list()
                guiSetAuditLog(self, "Project")
            else:
                QMessageBox.warning(self, "Delete Error", "Could not delete the project version.")

    def handle_follow(self, version_obj):
        """Navigates into the detailed view of a project version, such as the file list or change history."""
        if version_obj:
            self.version_callback(version_obj)
        else:
            print("Project ran into an error following version")

    def handle_approve(self, version_map):
        """Updates the status of a project version to 'Approved' on the server and refreshes the UI."""
        success = client_api.updateProjectVersionStatus_Client(version_map.id, "Approved")
        if success:
            self.refresh_version_list()
        else:
            QMessageBox.critical(self, "Error", "Failed to update version status on server.")

    # -------------------- Drag & Drop Logic --------------------

    def dragEnterEvent(self, event):
        """Ensures that drag-and-drop events are only accepted when performed over the central list widget area."""
        if event.mimeData().hasUrls():
            pos = event.position().toPoint()
            if self.middleList.geometry().contains(self.center_container.mapFrom(self, pos)):
                event.acceptProposedAction()

    def dropEvent(self, event):
        """Processes dropped files to create new project versions, handling path relativity and administrative auto-approval logic."""
        pos = event.position().toPoint()
        if not self.middleList.geometry().contains(self.center_container.mapFrom(self, pos)):
            return

        urls = event.mimeData().urls()
        if not urls: return

        if isinstance(self.project_data, dict):
            repo_path_raw = self.project_data.get('repository', {}).get('path', "")
            project_id = self.project_data.get('id')
        else:
            repo_path_raw = self.project_data.repository.path
            project_id = self.project_data.id

        repo_root = os.path.normpath(os.path.abspath(repo_path_raw))
        user_id = self.user.get('id') if isinstance(self.user, dict) else self.user.id
        currentUserRoleInRepo = client_api.getUserRole_Client(self.user.id, self.currentRepository.id)
        can_edit = (currentUserRoleInRepo in ["Admin", "Author"])
        if not can_edit:
            QMessageBox.warning(self, "Error", "You cannot upload to this repository.")
            return
        for url in urls:
            abs_path = os.path.normpath(url.toLocalFile())
            if os.path.isfile(abs_path):
                currentUserRoleInRepo = client_api.getUserRole_Client(user_id, self.currentRepository.id)

                if self.programType == "Studio":
                    relative_path = os.path.relpath(abs_path, repo_root)
                    if relative_path.startswith(".."):
                        QMessageBox.warning(self, "Invalid Location", f"File must be inside repository:\n{repo_root}")
                        continue

                    message, ok = QInputDialog.getMultiLineText(self, "New Version", "Enter version message:")
                    if ok and message:
                        status = "Draft"
                        if currentUserRoleInRepo == "Admin":
                            reply = QMessageBox.question(self, "Admin", "Auto-approve this version?",
                                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                            if reply == QMessageBox.StandardButton.Yes:
                                status = "Approved"

                        result = client_api.addNextProjectVersion_Client(project_id, user_id, message, relative_path,
                                                                         status)
                        if result and result.get('success'):
                            self.refresh_version_list()
                            guiSetAuditLog(self, "Project")
                        else:
                            QMessageBox.warning(self, "DB Error", f"Failed: {result.get('error', 'Unknown')}")

                elif self.programType == "Code":
                    if checkAbsPathToCodeFile(self.project_data, abs_path):
                        message, ok = QInputDialog.getMultiLineText(self, "New Version", "Enter version message:")
                        if ok and message:
                            status = "Pending"
                            if currentUserRoleInRepo == "Admin":
                                reply = QMessageBox.question(self, "Admin", "Auto-approve this version?",
                                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                if reply == QMessageBox.StandardButton.Yes:
                                    status = "Approved"

                            new_codeFileVer = addNextCodeFileVersionToDB(self.project_data, self.user, message,
                                                                         abs_path)
                            new_codeFileVer.status = status
                            new_codeFileVer.save()
                            self.refresh_version_list()
                            guiSetAuditLog(self, "Project")

        event.acceptProposedAction()

    # -------------------- UI Helpers --------------------

    def showEvent(self, event):
        """Triggers a list refresh and log update whenever the Project page is shown."""
        super().showEvent(event)
        self.refresh_version_list()
        guiSetAuditLog(self, "Project")

    def refresh_version_list(self):
        """Fetches the project version history and populates the list with custom widgets, respecting user roles and program modes."""
        self.middleList.clear()
        self.projectVersionData = getProjectVersionsByProjectID(self.project_data.id)
        version_icons = getItemIcons(self.projectVersionData, "ProjectVersion")
        currentUserRoleInRepo = client_api.getUserRole_Client(self.user.id, self.currentRepository.id)

        can_edit = (currentUserRoleInRepo in ["Admin", "Author"])
        can_approve = (currentUserRoleInRepo in ["Admin", "Reviewer"])

        for p, icon in zip(self.projectVersionData, version_icons):
            if currentUserRoleInRepo == "Guest" and p.status != "Approved": continue
            item = QListWidgetItem(self.middleList)
            item.setSizeHint(QSize(0, 40))

            if self.programType == "Studio":
                custom_widget = FileItemWidget(p, icon, self, context_type="ProjectVersion", can_edit=can_edit,
                                               can_approve=can_approve)
            else:
                custom_widget = FileItemWidget(p, icon, self, context_type="ProjectVersion", explicitNoFollow=True,
                                               can_edit=can_edit, can_approve=can_approve)

            self.middleList.addItem(item)
            self.middleList.setItemWidget(item, custom_widget)

    def handle_audit_toggle(self):
        """Expands or collapses the audit log panel for the Project view."""
        guiExpandAuditLog(self, "Project")