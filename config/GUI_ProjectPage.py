import os
import re

from PyQt6.QtCore import Qt, QFileInfo, QSize
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QFileIconProvider, QInputDialog
)
from PyQt6.QtGui import QFont, QPixmap, QIcon
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUIHelperWindows import *


class ProjectPage(QWidget):
    def __init__(self, loginUser, project_data, back_to_repo_callback, logout_callback, version_callback,
                 pfp_pixmap=None,programType="Studio"):
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

        # Builds the UI Design and containers
        gui_buildDesign(self, "Project",self.programType)
        # We create the button row and add buttons to it
        gui_buildBottomRow(self, "Project")

    # -------------------- Handlers --------------------

    def handle_version_open(self, version_obj):
        # 1. Get raw strings
        raw_root = str(self.project_data.repository.path)
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
                os.startfile(full_path)
            else:
                subprocess.Popen(["xdg-open", full_path], cwd=project_dir)
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Error: {e}")
    def handle_version_delete(self, version_obj):
        """
        Handles the deletion of a project version, showing which unique files will be removed.
        """
        # 1. Identify files that are only used by this version
        # Check 'version_files' or 'files' based on your model's attribute name
        m2m_attr = 'version_files' if hasattr(version_obj, 'version_files') else 'files'
        associated_files = getattr(version_obj, m2m_attr).all()

        orphaned_files_paths = []
        for f in associated_files:
            # Use your existing function to check usage
            usage_list = getVersionsByFileID(f.id)
            if len(usage_list) <= 1:
                orphaned_files_paths.append(f.path)

        # 2. Construct the confirmation message
        file_list_str = "\n".join([f" - {path}" for path in orphaned_files_paths])
        if not orphaned_files_paths:
            file_list_str = " (No unique files will be removed)"

        msg = (
            f"Are you sure you want to delete version {version_obj.version_number}?\n\n"
            f"The following unique files will be removed from the database:\n"
            f"{file_list_str}"
        )

        # 3. Prompt the user
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Pass the object to your safe DB function
            if removeProjectVersionFromDB(self.user, version_obj):
                self.refresh_version_list()
                guiSetAuditLog(self, "Project")
            else:
                QMessageBox.warning(self, "Delete Error", "Could not delete the project version.")
    def handleManageUsers(self):
        """Displays the list of all users associated with this repository."""
        dialog = ManageUsersDialog(self.currentRepository, self)
        dialog.exec()
    def handleAddUser(self): #TODO : GET RID OF DB LOGIC HERE
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
                    details=f"Added {username} as {role} to {self.currentRepository.title}"
                )

                status_msg = "Added" if created else "Updated"
                QMessageBox.information(self, "Success", f"Successfully {status_msg} {username} as {role}.")

            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Could not add user: {e}")

    def handle_follow(self, version_obj):
        if version_obj:
            self.version_callback(version_obj)
        else:
            print("Project ran into an error following version")
    def handle_approve(self,version_obj):
        try:
            print(version_obj.pk)
            print(version_obj.status)
            version_obj.status="Approved"
            version_obj.save(update_fields=['status'])
            print(version_obj.status)
            version_obj.save()
            self.refresh_version_list()
        except Exception as e:
            print(e)
    # -------------------- Drag & Drop Logic --------------------

    def dragEnterEvent(self, event):
        # Only accept if dragging over the middle list widget area
        if event.mimeData().hasUrls():
            pos = event.position().toPoint()
            if self.middleList.geometry().contains(self.center_container.mapFrom(self, pos)):
                event.acceptProposedAction()

    def dropEvent(self, event):
        pos = event.position().toPoint()
        # Ensure the drop landed inside the list's visual area
        if not self.middleList.geometry().contains(self.center_container.mapFrom(self, pos)):
            return

        urls = event.mimeData().urls()
        if not urls: return

        # Get Repo Root for relative pathing
        repo_path_raw = self.project_data.repository.path
        repo_root = os.path.normpath(os.path.abspath(repo_path_raw))

        for url in urls:
            abs_path = os.path.normpath(url.toLocalFile())
            if os.path.isfile(abs_path):
                if self.programType=="Studio":
                    # Calculate relative path past the repository
                    relative_path = os.path.relpath(abs_path, repo_root)
                    if relative_path.startswith(".."):
                        QMessageBox.warning(self, "Invalid Location", f"File must be inside repository:\n{repo_root}")
                        continue

                    # Prompt for version message
                    message, ok = QInputDialog.getMultiLineText(self, "New Version", "Enter version message:")
                    if ok and message:
                        status = "Pending"
                        # Admin Auto-Approve Check
                        if self.user.role == "Admin": #TODO : FIX THIS TO POINT TO REPOSITORYMEMBERSHIP
                            reply = QMessageBox.question(self, "Admin", "Auto-approve this version?",
                                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                            if reply == QMessageBox.StandardButton.Yes:
                                status = "Approved"

                        try:
                            # Create version (Inherits M2M files from previous version automatically)
                            new_ver = addNextProjectVersionToDB(self.project_data, self.user, message, relative_path)
                            new_ver.status = status
                            new_ver.save()
                            self.refresh_version_list()
                            guiSetAuditLog(self, "Project")
                        except Exception as e:
                            QMessageBox.warning(self, "DB Error", f"Failed: {e}")
                elif self.programType == "Code":
                    print(abs_path)
                    if checkAbsPathToCodeFile(self.project_data,abs_path):
                        message, ok = QInputDialog.getMultiLineText(self, "New Version", "Enter version message:")
                        if ok and message:
                            print("matching names")
                            status = "Pending"
                            if self.user.role == "Admin":  # TODO : FIX THIS TO POINT TO REPOSITORYMEMBERSHIP
                                reply = QMessageBox.question(self, "Admin", "Auto-approve this version?",
                                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                if reply == QMessageBox.StandardButton.Yes:
                                    status = "Approved"
                            new_codeFileVer = addNextCodeFileVersionToDB(self.project_data, self.user, message,abs_path)
                            new_codeFileVer.status = status
                            new_codeFileVer.save()
                            self.refresh_version_list()
                            guiSetAuditLog(self, "Project")
                    else :
                        print("mismatched names")
                    #check if the file's name is the exact same as project_data.title

        event.acceptProposedAction()

    # -------------------- UI Helpers --------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_version_list()
        guiSetAuditLog(self, "Project")

    def refresh_version_list(self):
        print("Project attempting to refresh middleList")
        self.middleList.clear()
        self.projectVersionData = getProjectVersionsByProjectID(self.project_data.id)
        version_icons = getItemIcons(self.projectVersionData, "ProjectVersion")

        for p, icon in zip(self.projectVersionData, version_icons):
            isGuest = RepositoryMembership.objects.filter(
                user=self.user,
                repository=self.currentRepository,
                repo_role__in=["Guest"]
            ).exists()
            if isGuest and p.status == "Draft" : continue
            item = QListWidgetItem(self.middleList)
            item.setSizeHint(QSize(0, 40))
            # context_type="Project" ensures the widget selects the correct delete callback
            if self.programType == "Studio" : custom_widget = FileItemWidget(p, icon, self, context_type="ProjectVersion")
            else : custom_widget = FileItemWidget(p, icon, self, context_type="ProjectVersion",explicitNoFollow=True)
            self.middleList.addItem(item)
            self.middleList.setItemWidget(item, custom_widget)
        print("Project successfully refreshed middleList")

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Project")