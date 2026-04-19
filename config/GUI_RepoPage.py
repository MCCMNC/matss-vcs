import re
from PyQt6.QtCore import QSize
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUIHelperWindows import *

from PyQt6.QtWidgets import QLineEdit


class RepoPage(QWidget):
    def __init__(self, loginUser, repo_obj, back_callback, logout_callback, project_callback,
                 pfp_pixmap=None, programType="Studio"):
        """Initializes the Repository page, sets up the UI design, bottom action row, and internal state for project management."""
        super().__init__()
        self.programType = programType
        self.user = loginUser
        self.currentRepository = repo_obj
        self.repo_name = repo_obj.title
        self.back_callback = back_callback
        self.on_logout = logout_callback
        self.project_callback = project_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.original_logs = []
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"RepoPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")
        self.handleAddUser = "TO BE OVERWRITTEN"

        # Builds the UI Design and containers
        gui_buildDesign(self, "Repository", self.programType)
        # We create the button row and add buttons to it
        gui_buildBottomRow(self, "Repository")

    # -------------------- Drag & Drop Event Filter --------------------
    def eventFilter(self, source, event):
        """Intercepts events for the project list to handle drag-and-drop file inputs specifically."""
        if source is self.middleList:
            if event.type() == event.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                    return True
            elif event.type() == event.Type.Drop:
                self.handle_dropped_file(event)
                return True
        return super().eventFilter(source, event)

    def handle_dropped_file(self, event):
        """Processes files dropped onto the repository list, prompting the user for metadata to create a new project."""
        currentUserRoleInRepo = client_api.getUserRole_Client(self.user.id, self.currentRepository.id)
        can_edit = (currentUserRoleInRepo in ["Admin", "Author"])

        if not can_edit:
            QMessageBox.warning(self, "Error", "You cannot upload to this repository.")
            return

        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return

        file_path = files[0]
        file_name = os.path.basename(file_path)
        title, ok1 = QInputDialog.getText(self, "New Project", "Project Title:", QLineEdit.EchoMode.Normal, file_name)
        if not ok1 or not title: return

        desc, ok2 = QInputDialog.getMultiLineText(self, "New Project", "Description:")
        if not ok2: return

        try:
            guiCreateProjectFromDrop(self.user, self.currentRepository, title, desc, file_path)
            guiSetAuditLog(self, "Repository")
            self.refresh_project_list()
        except Exception as e:
            QMessageBox.warning(self, "Error", "Could not create project from file.")

    # -------------------- Handlers & Refresh --------------------
    def refresh_project_list(self):
        """Fetches all projects associated with the current repository and populates the UI list with custom widgets."""
        self.middleList.clear()
        self.projects_data = client_api.getRepoProjectsByRepo_Client(self.currentRepository.id)

        project_icons = getItemIcons(self.projects_data, "Project")
        currentUserRoleInRepo = client_api.getUserRole_Client(self.user.id, self.currentRepository.id)
        can_edit = (currentUserRoleInRepo in ["Admin", "Author"])

        for p, icon in zip(self.projects_data, project_icons):
            item = QListWidgetItem(self.middleList)
            item.setSizeHint(QSize(0, 40))
            custom_widget = FileItemWidget(p, icon, self, context_type="Project", can_edit=can_edit)
            self.middleList.addItem(item)
            self.middleList.setItemWidget(item, custom_widget)

    def handle_file_open(self, project_obj):
        """Locates the physical file of the latest version and launches it using the system's default application."""
        version_obj = client_api.getLatestProjectVersion_Client(project_obj.id)

        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)

        raw_root = str(project_obj.repository.path)
        raw_path = str(version_obj.path)

        clean_root = re.sub(r'^[\s\0]+|[\s\0]+$', '', raw_root)
        clean_path = re.sub(r'^[\s\0]+|[\s\0]+$', '', raw_path)

        if clean_root.startswith("config"):
            full_path = os.path.normpath(os.path.join(project_root, clean_root, clean_path.lstrip('\\/')))
        else:
            full_path = os.path.normpath(os.path.abspath(os.path.join(clean_root, clean_path.lstrip('\\/'))))

        project_dir = os.path.dirname(full_path)

        if not os.path.exists(full_path):
            QMessageBox.warning(self, "File Not Found", f"No file at:\n{full_path}")
            return

        try:
            if sys.platform == "win32":
                os.startfile(full_path)
            else:
                subprocess.Popen(["xdg-open", full_path], cwd=project_dir)
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Error: {e}")

    def handle_project_delete(self, project_obj):
        """Verifies intent and removes a project from the repository and database, updating the UI and logs upon success."""
        reply = QMessageBox.StandardButton.No
        msg = f"Are you sure you want to delete the project '{project_obj.title}'?\nThis cannot be undone."
        if self.programType == "Code":
            msg = f"Are you sure you want to delete the code file '{project_obj.path}'?\nThis cannot be undone."

        reply = QMessageBox.question(self, 'Confirm Deletion', msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if client_api.api_removeProjectFromDB(self.user, project_obj.id):
                guiSetAuditLog(self, "Repository")
                self.refresh_project_list()
            else:
                QMessageBox.warning(self, "Error", "Could not delete project.")

    def handle_follow(self, project_obj):
        """Triggers the project callback to navigate into the detailed view of a specific project."""
        if project_obj:
            self.project_callback(project_obj, self.programType)

    def handle_audit_toggle(self):
        """Expands or collapses the audit log panel for the current Repository view."""
        guiExpandAuditLog(self, "Repository")

    def showEvent(self, event):
        """Standard show event override that ensures the project list is updated whenever the page is displayed."""
        super().showEvent(event)
        self.refresh_project_list()