import os
import re
import shutil
from PyQt6.QtCore import Qt, QFileInfo, QSize, QObject
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QFileIconProvider, QInputDialog, QLineEdit
)
from PyQt6.QtGui import QFont, QPixmap, QIcon
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUIHelperWindows import *

from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QComboBox, QPushButton, QVBoxLayout, QHBoxLayout

class RepoPage(QWidget):
    def __init__(self, loginUser, repo_obj, back_callback, logout_callback, project_callback,
                 pfp_pixmap=None,programType = "Studio"):
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

        # Builds the UI Design and containers
        gui_buildDesign(self, "Repository",self.programType)
        # We create the button row and add buttons to it
        gui_buildBottomRow(self,"Repository")

    # -------------------- Drag & Drop Event Filter --------------------
    def eventFilter(self, source, event):
        if source is self.middleList:
            if event.type() == event.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                    return True
            elif event.type() == event.Type.Drop:
                self.handle_dropped_file(event)
                return True
        return super().eventFilter(source, event)
    
    def handleManageUsers(self):
        """Displays the list of all users associated with this repository."""
        dialog = ManageUsersDialog(self.currentRepository, self)
        dialog.exec()

    def handleAddUser(self):
        dialog = AddUserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username, role = dialog.get_data()

            if not username:
                QMessageBox.warning(self, "Input Error", "Please enter a username.")
                return

            try:
                # 1. Check if user exists
                from vcs_core.models import User, Repository, RepositoryMembership

                try:
                    target_user = User.objects.get(username=username)
                except User.DoesNotExist:
                    QMessageBox.critical(self, "Error", f"User '{username}' not found in database.")
                    return
                repo_obj = self.currentRepository

                # 3. Create or Update membership
                membership, created = RepositoryMembership.objects.update_or_create(
                    user=target_user,
                    repository=repo_obj,
                    defaults={'repo_role': role}
                )

                # 4. Log the action
                AuditLog.objects.create(
                    user=self.user,  # The person performing the addition
                    action="ADD_MEMBER",
                    repository=repo_obj,
                    details=f"Added {username} as {role} to {self.repo_name}"
                )

                status_msg = "Added" if created else "Updated"
                QMessageBox.information(self, "Success", f"Successfully {status_msg} {username} as {role}.")

            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Could not add user: {e}")
    def handle_dropped_file(self, event):
        auth = RepositoryMembership.objects.filter(
            user=self.user,
            repository=self.currentRepository,
            repo_role__in=["Admin", "Author"]
        ).exists()

        if not auth:
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

        # Call logic to create project and first version
        if guiCreateProjectFromDrop(self.user, self.currentRepository, title, desc, file_path):
            self.refresh_project_list()
            guiSetAuditLog(self, "Repo")
        else:
            QMessageBox.warning(self, "Error", "Could not create project from file.")

    # -------------------- Handlers & Refresh --------------------
    def refresh_project_list(self):
        self.middleList.clear()
        self.projects_data = getRepoProjectsByRepo(self.currentRepository)
        project_icons = getItemIcons(self.projects_data, "Project")

        for p, icon in zip(self.projects_data, project_icons):
            item = QListWidgetItem(self.middleList)
            item.setSizeHint(QSize(0, 40))
            custom_widget = FileItemWidget(p, icon, self, context_type="Project")
            self.middleList.addItem(item)
            self.middleList.setItemWidget(item, custom_widget)
    def handle_file_open(self,project_obj):
        version_obj = getLatestProjectVersion(project_obj)
        print("Attempting to Open" + version_obj.path)
        raw_root = str(project_obj.repository.path)
        raw_path = str(version_obj.path)
        clean_root = re.sub(r'^[\s\0]+|[\s\0]+$', '', raw_root)
        clean_path = re.sub(r'^[\s\0]+|[\s\0]+$', '', raw_path)
        if os.path.isabs(clean_path):
            full_path = clean_path
        else:
            full_path = os.path.join(clean_root, clean_path.lstrip('\\/'))
        full_path = os.path.normpath(os.path.abspath(full_path))
        project_dir = os.path.dirname(full_path)
        if not os.path.exists(full_path):
            QMessageBox.warning(self, "File Not Found", f"No file at:\n{full_path}")
            return

        try:
            if sys.platform == "win32":
                print("Opening" + full_path)
                os.startfile(full_path)
            else:
                subprocess.Popen(["xdg-open", full_path], cwd=project_dir)
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Error: {e}")
        return
    def handle_delete(self, project_obj):
        reply = QMessageBox.StandardButton.No
        if self.programType == "Studio":
            reply = QMessageBox.question(
                self, 'Confirm Deletion',
                f"Are you sure you want to delete the project '{project_obj.title}'?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        elif self.programType == "Code":
            reply = QMessageBox.question(
                self, 'Confirm Deletion',
                f"Are you sure you want to delete the code file '{project_obj.path}'?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        if reply == QMessageBox.StandardButton.Yes:
            if self.programType == "Studio":
                if removeProjectFromDB(self.user, project_obj):
                    self.refresh_project_list()
                    guiSetAuditLog(self, "Repository")
                else:
                    QMessageBox.warning(self, "Error", "Could not delete project.")
            elif self.programType == "Code":
                if removeCodeFileFromDB(self.user, project_obj):
                    self.refresh_project_list()
                    guiSetAuditLog(self, "Repository")
                else:
                    QMessageBox.warning(self, "Error", "Could not delete project.")

    def handle_follow(self, project_obj):
        if project_obj:
            self.project_callback(project_obj,self.programType)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Repo")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_project_list()