import os
from PyQt6.QtCore import Qt, QFileInfo, QSize
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem,
    QMessageBox, QFileIconProvider
)
from PyQt6.QtGui import QFont, QPixmap, QIcon
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget

class DashboardPage(QWidget):
    def __init__(self, loginUser, on_repo_selected, on_logout, programType):
        super().__init__()
        print("init DashboardPage - "+programType)
        self.program_type = programType
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
        gui_buildDesign(self,"Dashboard",programType)
    # -------------------- Drag & Drop Logic --------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Visual feedback
            self.middleList.setStyleSheet(self.middleList.styleSheet().replace("#30363d", "#58a6ff"))
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.middleList.setStyleSheet(self.middleList.styleSheet().replace("#58a6ff", "#30363d"))

    def dropEvent(self, event):
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
                    if createRepositoryInDB(self.user, repo_name, folder_path,self.program_type):
                        self.refresh_repo_list()
                        guiSetAuditLog(self, "Dashboard")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to create repository record.")
            else:
                QMessageBox.warning(self, "Invalid Drop", "Only folders can be initialized as repositories.")

    # -------------------- UI Management --------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.middleList.clearSelection()
        try:
            guiSetAuditLog(self, "Dashboard")
            self.refresh_repo_list()
        except Exception as e:
            print(f"Dashboard refresh failed: {e}")

    def refresh_repo_list(self): #TODO : UNIFY MIDDLE LIST REFRESH
        self.middleList.clear()
        repos = getUserRepos(self.user,self.program_type)
        repo_icons = getItemIcons(repos, "Repository")

        for repo, icon in zip(repos, repo_icons):
            item = QListWidgetItem(self.middleList)
            item.setSizeHint(QSize(0, 40))
            custom_widget = FileItemWidget(repo, icon, self, context_type="Repository")
            self.middleList.addItem(item)
            self.middleList.setItemWidget(item, custom_widget)

    def handle_delete(self, repo_obj):
        """Action triggered by the red Delete button in FileItemWidget"""
        if not repo_obj:
            return

        # 1. Double-check with the user
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the repository '{repo_obj.title}'?\n\n"
            "This will remove all associated projects, versions, and logs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # 2. Call DB logic
            success = removeRepositoryFromDB(self.user, repo_obj,self.program_type)

            if success:
                # 3. Refresh the UI
                self.refresh_repo_list()
                guiSetAuditLog(self, "Dashboard")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete repository from database.")
    def handle_follow(self, repo_obj):
        if repo_obj:
            self.on_repo_selected(repo_obj,self.program_type)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Dashboard")

    def get_pfp_pixmap(self):
        return self.cached_pixmap