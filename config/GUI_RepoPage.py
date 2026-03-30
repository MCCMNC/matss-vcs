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
from GUI_FileItemWidget import FileItemWidget # Import the custom widget

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

class RepoPage(QWidget):
    def __init__(self, loginUser, repo_name, back_callback, logout_callback, project_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.repo_name = repo_name
        self.back_callback = back_callback
        self.logout_callback = logout_callback
        self.project_callback = project_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.original_logs = []
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"RepoPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

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

        guiSetTopLabel(self, getElementRelativePath(getRepoByName(self.repo_name), "Repository"), 18)

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

        guiSetAuditLog(self, "Repo")

        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setContentsMargins(0, 10, 0, 10)
        center_v_layout.setSpacing(10)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        project_box = QWidget()
        project_v = QVBoxLayout(project_box)
        project_v.setContentsMargins(0, 0, 0, 0)

        self.project_list = QListWidget()
        self.project_list.setMinimumSize(500, 400)
        # Enable mouse tracking for the hover buttons to work
        self.project_list.setMouseTracking(True)
        self.project_list.setStyleSheet(
            f"""
            QListWidget {{ 
                border: 1px solid #0d1115; 
                background: rgba(255,255,255,0.02); 
                color: #dce1e6; 
                outline: none; 
            }} 
            QListWidget::item:hover, QListWidget::item:selected {{ 
                background: transparent; 
            }}
            QListWidget::item {{ 
                padding: 0px; 
            }}
            {SCROLLBAR_STYLE}
            """
        )

        # Populate using the custom FileItemWidget
        self.projects_data = getRepoProjectsByRepoName(self.repo_name)
        project_icons = getItemIcons(self.projects_data, "Project")

        for p, icon in zip(self.projects_data, project_icons):
            item = QListWidgetItem(self.project_list)
            item.setSizeHint(QSize(0, 40))
            # Use context_type="Repository" to get the blue Follow button
            custom_widget = FileItemWidget(p, icon, self, context_type="Repository")
            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, custom_widget)

        project_v.addWidget(QLabel("List of Projects :"))
        project_v.addWidget(self.project_list)
        center_v_layout.addWidget(project_box)

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

    def showEvent(self, event):
        """Triggered every time the user navigates back to this Repo page."""
        super().showEvent(event)
        try:
            # 1. Refresh the Audit Log for the Repo
            guiSetAuditLog(self, "Repo")

            # 2. Refresh the Project List
            self.refresh_project_list()
        except Exception as e:
            print(f"RepoPage refresh failed: {e}")

    def refresh_project_list(self):
        """Clears and repopulates the project list from the database."""
        self.project_list.clear()

        # Fetch fresh data
        self.projects_data = getRepoProjectsByRepoName(self.repo_name)
        project_icons = getItemIcons(self.projects_data, "Project")

        for p, icon in zip(self.projects_data, project_icons):
            item = QListWidgetItem(self.project_list)
            item.setSizeHint(QSize(0, 40))

            # Re-create the custom widget with the new data
            custom_widget = FileItemWidget(p, icon, self, context_type="Repository")

            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, custom_widget)
    # -------------------- Handlers --------------------

    def handle_follow(self, project_obj):
        """Replacement for the old click functionality"""
        if project_obj:
            self.project_callback(project_obj)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Repo")