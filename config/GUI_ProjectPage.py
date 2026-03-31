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

SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        border: none;
        background: #0d1115;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #30363d;
        min-height: 20px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover { background: #484f58; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


def getItemIcons(inputDBElements, inputItemsType):
    returnedIcons = []
    icon_provider = QFileIconProvider()
    for item in inputDBElements:
        file_info = QFileInfo(getElementRelativePath(item, inputItemsType))
        native_icon = icon_provider.icon(file_info)
        returnedIcons.append(native_icon)
    return returnedIcons


class ProjectPage(QWidget):
    def __init__(self, loginUser, project_data, back_to_repo_callback, logout_callback, version_callback,
                 pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.project_data = project_data
        self.back_callback = back_to_repo_callback
        self.logout_callback = logout_callback
        self.version_callback = version_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False

        self.setAcceptDrops(True)  # Enable at page level but filter in the drop event
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"ProjectPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -------------------- Top Bar --------------------
        top_bar_container = QWidget()
        top_bar_container.setFixedHeight(70)
        top_bar_layout = QHBoxLayout(top_bar_container)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        self.left_section = QWidget()
        self.left_section.setFixedWidth(350)
        left_layout = QHBoxLayout(self.left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.pfp = QPushButton()
        self.pfp.setFixedSize(60, 60)
        self.pfp.setStyleSheet("border: none; background: transparent;")
        if self.pfp_pixmap and not self.pfp_pixmap.isNull():
            self.pfp.setIcon(QIcon(self.pfp_pixmap))
            self.pfp.setIconSize(self.pfp.size())

        self.user_label = QLabel(self.user.username)
        self.user_label.setFont(QFont("Arial", 12))
        left_layout.addWidget(self.pfp)
        left_layout.addWidget(self.user_label)

        guiSetTopLabel(self, getElementRelativePath(self.project_data, "Project"), 18)

        self.right_section = QWidget()
        self.right_section.setFixedWidth(350)
        right_layout = QHBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        guiAddLogoutButton(self, right_layout, self.logout_callback)

        top_bar_layout.addWidget(self.left_section)
        top_bar_layout.addWidget(self.page_title, 1)
        top_bar_layout.addWidget(self.right_section)
        self.main_layout.addWidget(top_bar_container)

        # -------------------- Middle Layout --------------------
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)

        guiSetAuditLog(self, "Project")

        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setContentsMargins(0, 10, 0, 10)
        center_v_layout.setSpacing(10)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        projectVersionBox = QWidget()
        detail_v = QVBoxLayout(projectVersionBox)
        detail_v.setContentsMargins(0, 0, 0, 0)

        detail_v.addWidget(QLabel(f"Viewing versions of : {self.project_data.title}"))

        self.projectVersionList = QListWidget()
        self.projectVersionList.setMinimumSize(500, 400)
        self.projectVersionList.setMouseTracking(True)
        self.projectVersionList.setStyleSheet(
            f"""
            QListWidget {{ 
                border: 1px solid #0d1115; 
                background: rgba(255,255,255,0.02); 
                color: #dce1e6; 
                outline: none; 
            }} 
            QListWidget::item:hover, QListWidget::item:selected {{ background: transparent; }}
            QListWidget::item {{ padding: 0px; }}
            {SCROLLBAR_STYLE}
            """
        )

        self.refresh_version_list()

        detail_v.addWidget(self.projectVersionList)
        center_v_layout.addWidget(projectVersionBox)

        self.back_btn = QPushButton("Go Back")
        self.back_btn.setFixedSize(120, 30)
        self.back_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.back_btn.clicked.connect(self.back_callback)
        center_v_layout.addWidget(self.back_btn)

        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)

        formatWidget(self)

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

    def handle_follow(self, version_obj):
        if version_obj: self.version_callback(version_obj)

    # -------------------- Drag & Drop Logic --------------------

    def dragEnterEvent(self, event):
        # Only accept if dragging over the middle list widget area
        if event.mimeData().hasUrls():
            pos = event.position().toPoint()
            if self.projectVersionList.geometry().contains(self.center_container.mapFrom(self, pos)):
                event.acceptProposedAction()

    def dropEvent(self, event):
        pos = event.position().toPoint()
        # Ensure the drop landed inside the list's visual area
        if not self.projectVersionList.geometry().contains(self.center_container.mapFrom(self, pos)):
            return

        urls = event.mimeData().urls()
        if not urls: return

        # Get Repo Root for relative pathing
        repo_path_raw = self.project_data.repository.path
        repo_root = os.path.normpath(os.path.abspath(repo_path_raw))

        for url in urls:
            abs_path = os.path.normpath(url.toLocalFile())
            if os.path.isfile(abs_path):
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
                    if self.user.role == "Admin":
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

        event.acceptProposedAction()

    # -------------------- UI Helpers --------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_version_list()
        guiSetAuditLog(self, "Project")

    def refresh_version_list(self):
        self.projectVersionList.clear()
        self.projectVersionData = getProjectVersionsByProjectID(self.project_data.id)
        version_icons = getItemIcons(self.projectVersionData, "ProjectVersion")

        for p, icon in zip(self.projectVersionData, version_icons):
            item = QListWidgetItem(self.projectVersionList)
            item.setSizeHint(QSize(0, 40))
            # context_type="Project" ensures the widget selects the correct delete callback
            custom_widget = FileItemWidget(p, icon, self, context_type="Project")
            self.projectVersionList.addItem(item)
            self.projectVersionList.setItemWidget(item, custom_widget)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Project")