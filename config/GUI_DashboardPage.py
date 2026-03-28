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
        self.original_logs = []  # Restored
        self.cached_pixmap = None
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"DashboardPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -------------------- Top Bar (LOCKED 70px) --------------------
        top_bar_container = QWidget()
        top_bar_container.setFixedHeight(70)
        top_bar_layout = QHBoxLayout(top_bar_container)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Left
        self.left_section = QWidget()
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
        self.page_title = QLabel("Dashboard")
        self.page_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Right
        self.right_section = QWidget()
        right_layout = QHBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.setFixedSize(100, 35)
        self.logout_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.logout_btn.clicked.connect(self.confirm_logout)
        right_layout.addWidget(self.logout_btn)

        top_bar_layout.addWidget(self.left_section, 1)
        top_bar_layout.addWidget(self.page_title, 1)
        top_bar_layout.addWidget(self.right_section, 1)
        self.main_layout.addWidget(top_bar_container)

        # -------------------- Middle Layout --------------------
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)

        # Audit (Fixed 350)
        self.audit_container = QWidget()
        self.audit_container.setFixedWidth(350)
        audit_v_layout = QVBoxLayout(self.audit_container)
        audit_v_layout.setContentsMargins(0, 10, 10, 10)

        self.audit_label = QLabel(f"Audit Log for : {self.user.username} ")
        self.audit_list = QListWidget()
        self.audit_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.audit_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.audit_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.audit_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #b9c2c9; outline: none; }} {SCROLLBAR_STYLE}")

        user_logs = getUserAuditLogs(self.user.id)
        log_font = QFont("Arial", 8)
        for log in reversed(user_logs):
            text = auditLogToText(log)
            self.original_logs.append(text)  # Saving original text
            item = QListWidgetItem(text)
            item.setFont(log_font)
            self.audit_list.addItem(item)

        self.expand_btn = QPushButton("Expand Audit Log")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; padding: 10px; font-weight: bold;")
        self.expand_btn.clicked.connect(self.handle_audit_toggle)

        audit_v_layout.addWidget(self.audit_label)
        audit_v_layout.addWidget(self.audit_list)
        audit_v_layout.addWidget(self.expand_btn)

        # Center
        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        repo_box = QWidget()
        repo_box.setFixedSize(500, 500)
        repo_v = QVBoxLayout(repo_box)
        self.repo_list = QListWidget()
        self.repo_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #dce1e6; }} {SCROLLBAR_STYLE}")
        self.repo_list.itemClicked.connect(self.handle_repo_selection)

        for repo in getUserRepos(self.user):
            self.repo_list.addItem(f"{repo.title} - {repo.path}")

        repo_v.addWidget(QLabel("List of Repositories :"))
        repo_v.addWidget(self.repo_list)
        center_v_layout.addWidget(repo_box)

        # Right
        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)
    def showEvent(self, event):
        """Resets the UI state when navigating back to the dashboard."""
        super().showEvent(event)

        # 1. Clear the visual 'glow' (selection)
        self.repo_list.clearSelection()

        # 2. Clear the dotted focus rectangle
        self.repo_list.clearFocus()

        # 3. Reset the current item to None so it doesn't remember the last click
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
        if self._is_toggling: return
        self._is_toggling = True

        if not self.is_expanded:
            self.audit_container.setFixedWidth(self.width() - 40)
            self.center_container.hide()
            self.right_spacer.hide()

            userAuditLogs = getUserAuditLogs(self.user.id)
            for i, log in enumerate(reversed(userAuditLogs)):
                if i < self.audit_list.count():
                    text = auditLogToTextExpanded(log)  # Restored
                    self.audit_list.item(i).setText(text)

            self.expand_btn.setText("Minimise Audit Log")
            self.is_expanded = True
        else:
            self.audit_container.setFixedWidth(350)
            self.center_container.show()
            self.right_spacer.show()

            for i in range(self.audit_list.count()):
                if i < len(self.original_logs):
                    self.audit_list.item(i).setText(self.original_logs[i])  # Restored

            self.expand_btn.setText("Expand Audit Log")
            self.is_expanded = False

        self._is_toggling = False