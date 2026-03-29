import os
from PyQt6.QtCore import Qt, QFileInfo, QSize
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QFileIconProvider
)
from PyQt6.QtGui import QFont, QPixmap, QIcon
from GUIFunctions import *
from DBFunctions import *

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
        file_info = QFileInfo(getElementFullPath(item, inputItemsType))
        native_icon = icon_provider.icon(file_info)
        returnedIcons.append(native_icon)
    return returnedIcons

class ProjectPage(QWidget):
    def __init__(self, loginUser, project_data, back_to_repo_callback, logout_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.project_data = project_data
        self.back_callback = back_to_repo_callback
        self.logout_callback = logout_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.original_logs = []
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Style matched to RepoPage baseline
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

        guiSetTopLabel(self, getElementFullPath(self.project_data, "Project"))

        self.right_section = QWidget()
        self.right_section.setFixedWidth(350)
        right_layout = QHBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.setFixedSize(100, 35)
        self.logout_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.logout_btn.clicked.connect(self.confirm_logout)
        right_layout.addWidget(self.logout_btn)

        top_bar_layout.addWidget(self.left_section)
        top_bar_layout.addWidget(self.page_title, 1)
        top_bar_layout.addWidget(self.right_section)
        self.main_layout.addWidget(top_bar_container)

        # -------------------- Middle Layout --------------------
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)

        guiSetAuditLog(self, "Dashboard")

        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setContentsMargins(0, 10, 0, 10)
        center_v_layout.setSpacing(10)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        # Project Detail Box (Sizes matched to RepoPage)
        projectVersionBox = QWidget()
        projectVersionBox.setFixedSize(500, 500)
        detail_v = QVBoxLayout(projectVersionBox)
        detail_v.setContentsMargins(0, 0, 0, 0)

        detail_v.addWidget(QLabel(f"Viewing Details for: {self.project_data.title}"))

        self.projectVersionList = QListWidget()
        # Stylesheet logic synced with RepoPage baseline
        self.projectVersionList.setStyleSheet(
            f"""QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #dce1e6; }} 
               QListWidget::item {{ padding: 5px; }}
               {SCROLLBAR_STYLE}""")
        self.projectVersionList.setIconSize(QSize(20, 20))

        # --- Populate Versions ---
        self.projectVersionData = getProjectVersionsByProjectID(self.project_data.id)
        version_icons = getItemIcons(self.projectVersionData, "ProjectVersion")

        for p, icon in zip(self.projectVersionData, version_icons):
            item = QListWidgetItem(f"{p.version_number} - {p.path}")
            item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.projectVersionList.addItem(item)

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

    def confirm_logout(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Log Out")
        msg_box.setText("Are you sure you want to log out?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(
            "QMessageBox { background-color: #0d0e0f; } "
            "QLabel { color: #b9c2c9; } "
            "QPushButton { background-color: #151719; color: #b9c2c9; border: 1px solid #30363d; padding: 5px; min-width: 80px; }")
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            self.logout_callback()

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Dashboard")