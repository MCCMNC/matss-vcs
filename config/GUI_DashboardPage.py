from PyQt6.QtCore import QSize
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
import client_api


class DashboardPage(QWidget):
    def __init__(self, loginUser, on_repo_selected, on_logout, programType):
        """Initializes the Dashboard, sets up user session data, styles, and triggers the UI design build."""
        super().__init__()
        print("init DashboardPage - " + programType)
        self.programType = programType
        self.user = loginUser
        self.on_repo_selected = on_repo_selected
        self.on_logout = on_logout
        self.is_expanded = False
        self.original_logs = []
        self.cached_pixmap = None
        self._is_toggling = False
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"DashboardPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

        # Builds the UI Design and containers
        gui_buildDesign(self, "Dashboard", programType)

    # -------------------- Drag & Drop Logic --------------------

    def dragEnterEvent(self, event):
        """Validates that dragged content contains URLs (files/folders) and provides visual highlighting for the drop zone."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Visual feedback
            self.middleList.setStyleSheet(self.middleList.styleSheet().replace("#30363d", "#58a6ff"))
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Removes the visual highlighting from the drop zone when the dragged object leaves the widget area."""
        self.middleList.setStyleSheet(self.middleList.styleSheet().replace("#58a6ff", "#30363d"))

    def dropEvent(self, event):
        """Processes dropped folders to initialize them as new repositories after user confirmation."""
        self.middleList.setStyleSheet(self.middleList.styleSheet().replace("#58a6ff", "#30363d"))

        for url in event.mimeData().urls():
            folder_path = url.toLocalFile()
            if os.path.isdir(folder_path):
                repo_name = os.path.basename(folder_path)

                confirm = QMessageBox.question(
                    self, "Initialize Repository",
                    f"Create new repository '{repo_name}' from this folder?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if confirm == QMessageBox.StandardButton.Yes:
                    if client_api.api_create_repository(self.user, repo_name, folder_path, self.programType):
                        self.refresh_repo_list()
                        guiSetAuditLog(self, "Dashboard")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to create repository record via Server.")
            else:
                QMessageBox.warning(self, "Invalid Drop", "Only folders can be initialized as repositories.")

    # -------------------- UI Management --------------------

    def showEvent(self, event):
        """Refreshes the repository list and audit logs whenever the dashboard page becomes visible."""
        super().showEvent(event)
        self.middleList.clearSelection()
        try:
            guiSetAuditLog(self, "Dashboard")
            self.refresh_repo_list()
        except Exception as e:
            print(f"Dashboard refresh failed: {e}")

    def refresh_repo_list(self):
        """Fetches the latest repositories from the server and repopulates the UI list with custom FileItemWidgets."""
        self.middleList.clear()
        print("program type ", self.programType)
        repos = client_api.getUserRepos_Client(self.user.id, self.programType)
        print(repos)
        repo_icons = getItemIcons(repos, "Repository")
        for repo, icon in zip(repos, repo_icons):
            currentUserRoleInRepo = client_api.getUserRole_Client(self.user.id, repo.id)
            is_admin = (currentUserRoleInRepo == "Admin")

            item = QListWidgetItem(self.middleList)
            item.setSizeHint(QSize(0, 40))
            custom_widget = FileItemWidget(repo, icon, self, context_type="Repository", is_admin=is_admin)
            self.middleList.addItem(item)
            self.middleList.setItemWidget(item, custom_widget)

    def handle_delete(self, repo_map):
        """Prompts for confirmation and deletes a repository, its associated data, and logs via the server API."""
        if not repo_map:
            return

        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the repository '{repo_map.title}'?\n\n"
            "This will remove all associated projects, versions, and logs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            success = client_api.removeRepository_Client(self.user.id, repo_map.id, self.programType)
            if success:
                self.refresh_repo_list()
                guiSetAuditLog(self, "Dashboard")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete repository from database.")

    def handle_follow(self, repo_obj):
        """Navigates into a specific repository to view its projects."""
        if repo_obj:
            self.on_repo_selected(repo_obj, self.programType)

    def perform_repo_pull(self, repo_obj, local_dest):
        """Logic for downloading the latest approved versions of all projects in a repository to a local directory."""
        base_storage = os.path.normpath(databaseStoragePath)
        repo_relative_path = os.path.normpath(repo_obj.path)
        project_root = os.path.dirname(base_storage)

        if repo_relative_path.startswith("config"):
            server_repo_path = os.path.join(project_root, repo_relative_path)
        else:
            server_repo_path = os.path.join(base_storage, repo_relative_path)

        server_repo_path = os.path.normpath(server_repo_path)
        final_local_path = os.path.join(local_dest, repo_obj.title)

        if not os.path.exists(final_local_path):
            os.makedirs(final_local_path)

        try:
            projects = client_api.getRepoProjectsByRepo_Client(repo_obj.id)

            for project in projects:
                latest_approved = client_api.getLatestApprovedProjectVersion_Client(project.id)

                if latest_approved:
                    server_file_path = os.path.normpath(os.path.join(server_repo_path, latest_approved.path))
                    target_file_path = os.path.normpath(os.path.join(final_local_path, project.path))

                    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                    if server_file_path.startswith('config'):
                        server_file_path = server_file_path[7:]

                    if os.path.exists(server_file_path):
                        shutil.copy2(server_file_path, target_file_path)
                    else:
                        print(f"Warning: Physical file not found for {project.title}: {server_file_path}")
                else:
                    print(f"Skipping {project.title}: No approved versions found.")

            return True
        except Exception as e:
            raise Exception(f"Pull failed: {str(e)}")

    def handle_pull(self, repo_obj):
        """Opens a folder selection dialog and initiates the repository pull process to the chosen local path."""
        if not repo_obj:
            return

        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder to Pull Repository",
            ""
        )

        if dest_dir:
            try:
                success = self.perform_repo_pull(repo_obj, dest_dir)
                if success:
                    QMessageBox.information(self, "Success", f"Repository pulled to:\n{dest_dir}")
            except Exception as e:
                QMessageBox.critical(self, "Pull Error", f"Failed to pull repository: {e}")

    def handle_audit_toggle(self):
        """Expands or collapses the audit log panel for the Dashboard view."""
        guiExpandAuditLog(self, "Dashboard")

    def get_pfp_pixmap(self):
        """Returns the cached profile picture pixmap for consistent use across different pages."""
        return self.cached_pixmap