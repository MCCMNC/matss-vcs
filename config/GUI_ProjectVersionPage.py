from PyQt6.QtCore import QSize
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUIHelperWindows import ManageUsersDialog
from GUI_AudioSupport import AudioPlayerWidget


class ProjectVersionPage(QWidget):
    def __init__(self, loginUser, inputProjectVersion, back_callback, logout_callback, pfp_pixmap=None):
        """Initializes the version detail page, sets up UI layouts, and instantiates the audio player for media files."""
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
        self.handleAddUSer = "TO BE OVERWRITTEN"

        gui_buildDesign(self, "ProjectVersion")
        gui_buildBottomRow(self, "ProjectVersion")
        self.audio_player = AudioPlayerWidget()

    # -------------------- Handlers --------------------

    def showEvent(self, event):
        """Standard show event override that refreshes the file list and updates audit logs when the page appears."""
        super().showEvent(event)
        try:
            self.refresh_file_list()
            guiSetAuditLog(self, "ProjectVersion")
        except Exception as e:
            print(f"ProjectVersionPage refresh failed: {e}")

    def handleManageUsers(self):
        """Launches a dialog to view and manage user permissions associated with the current repository."""
        dialog = ManageUsersDialog(self.currentRepository, self)
        dialog.exec()

    def handle_back_click(self):
        """Stops any active audio playback and triggers the callback to return to the previous project view."""
        if hasattr(self, 'audio_player'):
            self.audio_player.player.stop()
        self.back_callback()

    def handle_logout_click(self):
        """Stops audio playback and triggers the global logout sequence."""
        if hasattr(self, 'audio_player'):
            self.audio_player.player.stop()
        self.logout_callback()

    def handle_file_open(self, file_obj):
        """Determines file type to either launch in the integrated audio player or open via the system's default application."""
        if not file_obj or not file_obj.path:
            return

        path_val = file_obj.get('path') if isinstance(file_obj, dict) else file_obj.path

        if isinstance(self.project_version, dict):
            repo_path_raw = self.project_version['project']['repository']['path']
        else:
            repo_path_raw = self.project_version.project.repository.path

        repo_root = os.path.normpath(os.path.abspath(repo_path_raw))
        full_path = os.path.join(repo_root, path_val)

        audio_exts = ['.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a']

        if os.path.splitext(full_path)[1].lower() in audio_exts:
            if os.path.exists(full_path):
                if hasattr(self, 'audio_player') and self.audio_player is not None:
                    self.audio_player.show()
                    self.audio_player.load_file(full_path, os.path.basename(full_path))
                else:
                    QMessageBox.critical(self, "Player Error", "Audio player was not initialized.")
            else:
                QMessageBox.warning(self, "Missing File", f"File not found:\n{full_path}")
        else:
            try:
                os.startfile(full_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def eventFilter(self, source, event):
        """Intercepts drag and drop events specifically for the file list area to facilitate file uploads."""
        if source is self.middleList and event.type() == event.Type.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        if source is self.middleList and event.type() == event.Type.Drop:
            self.handle_file_drop(event)
            return True
        return super().eventFilter(source, event)

    def handle_file_drop(self, event):
        """Processes files dropped into the version, checking for authorization, resolving paths, and handling duplicate file links."""
        print("\n--- [DEBUG] START handle_file_drop ---")
        project = getattr(self.project_version, 'project', None)
        target_repo = None
        if project:
            target_repo = getattr(project, 'repository', None)

        auth = False
        if target_repo:
            currentUserRoleInRepo = client_api.getUserRole_Client(self.user.id, target_repo.id)
            if currentUserRoleInRepo in ["Admin", "Author"]:
                auth = True

        if not auth:
            QMessageBox.warning(self, "Error", "You cannot upload to this repository.")
            return

        urls = event.mimeData().urls()
        files_added = False

        try:
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
                        relative_path = os.path.basename(abs_dropped_path)
                except ValueError:
                    relative_path = os.path.basename(abs_dropped_path)

                relative_path = relative_path.replace('\\', '/')
                existing_file = getVersionFileByPath(relative_path)

                if existing_file:
                    already_linked = isFileLinkedToVersion(existing_file, self.project_version)
                    if already_linked:
                        QMessageBox.information(self, "Duplicate", f"'{relative_path}' is already in this version.")
                        continue

                    reply = QMessageBox.question(
                        self, "Link Existing File",
                        f"The path '{relative_path}' already exists.\nLink it to this version?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        linkExistingFileToVersion(existing_file, self.project_version)
                        files_added = True
                        continue
                    else:
                        continue

                content_input, ok = QInputDialog.getMultiLineText(
                    self, "File Content", f"Description for {os.path.basename(abs_dropped_path)}:"
                )

                if ok:
                    success = client_api.addVersionFileToDB_Client(
                        self.user.id,
                        self.project_version.id,
                        relative_path,
                        content_input
                    )
                    files_added = True

        if files_added:
            guiSetAuditLog(self, "ProjectVersion")
            self.refresh_file_list()

        event.acceptProposedAction()

    def refresh_file_list(self):
        """Fetches the files associated with this specific project version and repopulates the list with custom FileItemWidgets."""
        self.middleList.clear()
        self.projectVersionData = client_api.getProjectVersionFilesByProjectVersionID_Client(self.project_version.id)

        if isinstance(self.projectVersionData, list) and len(self.projectVersionData) > 0:
            try:
                file_icons = getItemIcons(self.projectVersionData, "ProjectVersionFile")
                for f, icon in zip(self.projectVersionData, file_icons):
                    item = QListWidgetItem(self.middleList)
                    item.setSizeHint(QSize(0, 40))
                    custom_widget = FileItemWidget(f, icon, self, "ProjectVersionFile", self.project_version)
                    self.middleList.addItem(item)
                    self.middleList.setItemWidget(item, custom_widget)
            except Exception as e:
                print(f"[DEBUG] UI Render Error: {e}")

    def handle_file_delete(self, file_obj):
        """Prompts for removal of a file link from the current version, displaying other project associations for context."""
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
        """Expands or collapses the audit log panel and ensures media players are stopped when the layout changes."""
        try:
            if hasattr(self, 'audit_container'):
                guiExpandAuditLog(self, "ProjectVersion")
                if self.is_expanded and hasattr(self, 'audio_player'):
                    self.audio_player.player.stop()
                    self.audio_player.hide()
        except Exception as e:
            print(f"Audit Toggle Error: {e}")