import os
import wave
import numpy as np
import random
from PyQt6.QtCore import Qt, QFileInfo, QSize, QUrl, QTimer
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QFileIconProvider, QSlider, QInputDialog, QDialog
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QBrush
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUI_AudioSupport import AudioPlayerWidget, StaticWaveformWidget
from GUIHelperWindows import ManageUsersDialog, AddUserDialog


def getItemIcons(inputDBElements, inputItemsType):
    returnedIcons = []
    icon_provider = QFileIconProvider()
    for item in inputDBElements:
        file_info = QFileInfo(getElementRelativePath(item, inputItemsType))
        native_icon = icon_provider.icon(file_info)
        returnedIcons.append(native_icon)
    return returnedIcons


class ProjectVersionPage(QWidget):
    def __init__(self, loginUser, inputProjectVersion, back_callback, logout_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.project_version = inputProjectVersion
        self.currentRepository = inputProjectVersion.project.repository
        self.back_callback = back_callback
        self.on_logout = logout_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.original_logs = []
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"ProjectVersionPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

        gui_buildDesign(self, "ProjectVersion")
        gui_buildBottomRow(self,"ProjectVersion")

    # -------------------- Handlers --------------------

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.refresh_file_list()
            guiSetAuditLog(self, "ProjectVersion")
        except Exception as e:
            print(f"ProjectVersionPage refresh failed: {e}")
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
    def handle_back_click(self):
        if hasattr(self, 'audio_player'):
            self.audio_player.player.stop()
        self.back_callback()

    def handle_logout_click(self):
        if hasattr(self, 'audio_player'):
            self.audio_player.player.stop()
        self.logout_callback()

    def handle_file_open(self, file_obj):
        if not file_obj or not file_obj.path:
            return

        repo_path_raw = self.project_version.project.repository.path
        repo_root = os.path.normpath(os.path.abspath(repo_path_raw))
        full_path = os.path.join(repo_root, file_obj.path)

        audio_exts = ['.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a']

        if os.path.splitext(full_path)[1].lower() in audio_exts:
            if os.path.exists(full_path):
                self.audio_player.show()
                self.audio_player.load_file(full_path, os.path.basename(full_path))
            else:
                QMessageBox.warning(self, "Missing File", f"File not found:\n{full_path}")
        else:
            try:
                os.startfile(full_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def eventFilter(self, source, event):
        if source is self.middleList and event.type() == event.Type.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        if source is self.middleList and event.type() == event.Type.Drop:
            self.handle_file_drop(event)
            return True
        return super().eventFilter(source, event)

    def handle_file_drop(self, event):
        project = getattr(self.project_version, 'project', None)
    
        target_repo = None
        if project:
            target_repo = getattr(project, 'repository', None)

        auth = False
        if target_repo:
            auth = RepositoryMembership.objects.filter(
                user=self.user,
                repository=target_repo,
                repo_role__in=["Admin", "Author"]
            ).exists()

        if not auth:
            QMessageBox.warning(self, "Error", "You cannot upload to this repository.")
            return
        
        urls = event.mimeData().urls()
        files_added = False

        try:
            self.project_version.refresh_from_db()

            repo_path_raw = self.project_version.project.repository.path
            repo_root = os.path.normpath(os.path.abspath(repo_path_raw))
        except Exception as e:
            return

        for url in urls:
            abs_dropped_path = os.path.normpath(url.toLocalFile())

            if os.path.isfile(abs_dropped_path):
                try:
                    relative_path = os.path.relpath(abs_dropped_path, repo_root)
                    if relative_path.startswith(".."):
                        continue
                except ValueError:
                    continue
                existing_file = getVersionFileByPath(relative_path)

                if existing_file:
                    try:
                        already_linked = isFileLinkedToVersion(existing_file, self.project_version)
                    except Exception as e:
                        print(f"M2M Evaluation Error: {e}")
                        already_linked = False

                    if already_linked:
                        QMessageBox.information(self, "Duplicate", f"File is already in this version.")
                        continue

                    reply = QMessageBox.question(
                        self, "Link Existing File",
                        f"This file already exists in the database.\nWould you like to link it to this version?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        linkExistingFileToVersion(existing_file, self.project_version)
                        files_added = True
                        continue
                content_input, ok = QInputDialog.getMultiLineText(
                    self, "File Content", f"Description for {os.path.basename(abs_dropped_path)}:"
                )
                if ok:
                    client_api.addVersionFileToDB_Client(self.user.id, self.project_version,relative_path,content_input)
                    files_added = True

        if files_added:
            self.refresh_file_list()
            guiSetAuditLog(self, "ProjectVersion")

        event.acceptProposedAction()

    def refresh_file_list(self):
        self.middleList.clear()
        self.projectVersionData = client_api.getProjectVersionFilesByProjectVersionID_Client(self.project_version.id)

        if self.projectVersionData:
            file_icons = getItemIcons(self.projectVersionData, "ProjectVersionFile")

            for f, icon in zip(self.projectVersionData, file_icons):
                item = QListWidgetItem(self.middleList)
                item.setSizeHint(QSize(0, 40))
                custom_widget = FileItemWidget(f, icon, self, "ProjectVersionFile", self.project_version)
                self.middleList.addItem(item)
                self.middleList.setItemWidget(item, custom_widget)

    def handle_file_delete(self, file_obj):
        associated_versions = client_api.getVersionsByFileID_Client(file_obj.id)
        version_links = []

        for ver in associated_versions:
            p_title = ver.get('project__title') or "Untitled Project"
            v_num = ver.get('version_number') or "Unknown"
            tag = " (Current)" if ver['id'] == self.project_version.id else ""
            version_links.append(f"• {p_title} - v{v_num}{tag}")

        association_text = "\n".join(version_links) if version_links else "No other associations found."
        message = (
            f"Remove link to: {file_obj.path}?\n\n"
            f"Linked versions:\n{association_text}\n\n"
            "This only removes the link from THIS version."
        )

        reply = QMessageBox.question(self, 'Confirm Removal', message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                client_api.removeVersionFileFromDB_Client(self.user.id, file_obj.id, self.project_version.id)
                self.refresh_file_list()
                guiSetAuditLog(self, "ProjectVersion")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Removal failed: {e}")

    def handle_audit_toggle(self):
        try:
            if hasattr(self, 'audit_container'):
                guiExpandAuditLog(self, "ProjectVersion")
                if self.is_expanded and hasattr(self, 'audio_player'):
                    self.audio_player.player.stop()
                    self.audio_player.hide()
        except Exception as e:
            print(f"Audit Toggle Error: {e}")