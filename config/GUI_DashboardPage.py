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


class DashboardPage(QWidget):
    def __init__(self, loginUser, on_repo_selected, on_logout):
        super().__init__()
        self.user = loginUser
        self.on_repo_selected = on_repo_selected
        self.on_logout = on_logout
        self.is_expanded = False
        self.original_logs = []
        self.cached_pixmap = None
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"DashboardPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

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

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        pfp_path = os.path.join(BASE_DIR, "Assets", "Poet Cover 3.png")
        raw_pixmap = QPixmap(pfp_path)
        if not raw_pixmap.isNull():
            self.cached_pixmap = raw_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.FastTransformation)
            self.pfp.setIcon(QIcon(self.cached_pixmap))
            self.pfp.setIconSize(self.pfp.size())

        self.user_label = QLabel(self.user.username)
        self.user_label.setFont(QFont("Arial", 12))
        left_layout.addWidget(self.pfp)
        left_layout.addWidget(self.user_label)

        # 2. Middle

        guiSetTopLabel(self,"Dashboard")

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

        # Audit (Fixed 350)
        guiSetAuditLog(self,"Dashboard")
        # Center Column
        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        # CHANGED: Alignment to Top so the list shifts up
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        # CHANGED: Added top margin (10) to match the vertical start of the audit log
        center_v_layout.setContentsMargins(0, 10, 0, 0)

        repo_box = QWidget()
        repo_box.setFixedSize(500, 500)
        repo_v = QVBoxLayout(repo_box)
        repo_v.setContentsMargins(0, 0, 0, 0)  # Tighten internal list margins

        self.repo_list = QListWidget()
        self.repo_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #dce1e6; }} {SCROLLBAR_STYLE}")
        self.repo_list.itemClicked.connect(self.handle_repo_selection)

        for repo in getUserRepos(self.user):
            self.repo_list.addItem(f"{repo.title} - {repo.path}")

        repo_v.addWidget(QLabel("List of Repositories :"))
        repo_v.addWidget(self.repo_list)
        center_v_layout.addWidget(repo_box)

        # Right (350px)
        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.repo_list.clearSelection()
        self.repo_list.clearFocus()
        self.repo_list.setCurrentItem(None)

    def get_pfp_pixmap(self):
        return self.cached_pixmap

    def confirm_logout(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Log Out")
        msg_box.setText("Are you sure you want to log out?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(
            "QMessageBox { background-color: #0d0e0f; } QLabel { color: #b9c2c9; } QPushButton { background-color: #151719; color: #b9c2c9; border: 1px solid #30363d; padding: 5px; min-width: 80px; }")
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            self.on_logout()

    def handle_repo_selection(self, item):
        name = item.text().split(" - ")[0].strip()
        self.on_repo_selected(name)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self,"Dashboard")