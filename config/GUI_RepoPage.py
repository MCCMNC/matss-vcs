import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox
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


class RepoPage(QWidget):
    def __init__(self, loginUser, repo_name, back_callback, logout_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.repo_name = repo_name
        self.back_callback = back_callback
        self.logout_callback = logout_callback
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

        # -------------------- Top Bar (LOCKED 70px) --------------------
        top_bar_container = QWidget()
        top_bar_container.setFixedHeight(70)
        top_bar_layout = QHBoxLayout(top_bar_container)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Left (350px)
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

        # 2. Middle
        guiSetTopLabel(self,self.repo_name)

        # 3. Right (350px)
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

        # Audit (Left - Fixed 350)
        guiSetAuditLog(self,"Repo")
        # Center Column
        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setContentsMargins(0, 10, 0, 10)
        center_v_layout.setSpacing(10) # Space between List and Button
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        # 1. Project List
        project_box = QWidget()
        project_box.setFixedSize(500, 500)
        project_v = QVBoxLayout(project_box)
        project_v.setContentsMargins(0, 0, 0, 0)

        self.project_list = QListWidget()
        self.project_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #dce1e6; }} {SCROLLBAR_STYLE}")

        projects = getRepoProjectsByRepoName(self.repo_name)
        for p in projects:
            self.project_list.addItem(f"{p.title} - {p.path}")

        project_v.addWidget(QLabel("List of Projects :"))
        project_v.addWidget(self.project_list)

        center_v_layout.addWidget(project_box)

        # 2. Go Back Button (Now safely underneath)
        self.back_btn = QPushButton("Go Back")
        self.back_btn.setFixedSize(120, 30)
        self.back_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.back_btn.clicked.connect(self.back_callback)
        center_v_layout.addWidget(self.back_btn)

        # Right Spacer
        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)

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
        guiExpandAuditLog(self,"Repo")