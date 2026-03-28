import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame
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
    def __init__(self, loginUser, repo_name, back_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.repo_name = repo_name
        self.back_callback = back_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.original_logs = []  # Restored for expansion logic
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"RepoPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

        # Main Layout - Locked alignment
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
        if self.pfp_pixmap and not self.pfp_pixmap.isNull():
            self.pfp.setIcon(QIcon(self.pfp_pixmap))
            self.pfp.setIconSize(self.pfp.size())

        self.user_label = QLabel(self.user.username)
        self.user_label.setFont(QFont("Arial", 12))
        left_layout.addWidget(self.pfp)
        left_layout.addWidget(self.user_label)

        # 2. Middle
        self.repo_label = QLabel(self.repo_name)
        self.repo_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.repo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Right
        self.right_section = QWidget()
        right_layout = QHBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.back_btn = QPushButton("Go Back")
        self.back_btn.setFixedSize(100, 35)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.back_btn.clicked.connect(self.back_callback)
        right_layout.addWidget(self.back_btn)

        top_bar_layout.addWidget(self.left_section, 1)
        top_bar_layout.addWidget(self.repo_label, 1)
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

        self.audit_label = QLabel(f"Audit Log for : {self.repo_name}")
        self.audit_list = QListWidget()
        self.audit_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.audit_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.audit_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.audit_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #b9c2c9; outline: none; }} {SCROLLBAR_STYLE}")

        repo_logs = getRepoAuditLogsByRepoName(self.repo_name)
        log_font = QFont("Arial", 8)
        for log in reversed(repo_logs):
            text = auditLogToText(log)
            self.original_logs.append(text)  # Store for shrinking back
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

        # Center (List)
        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        project_box = QWidget()
        project_box.setFixedSize(500, 500)
        project_v = QVBoxLayout(project_box)
        self.project_list = QListWidget()
        self.project_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #dce1e6; }} {SCROLLBAR_STYLE}")

        projects = getRepoProjectsByRepoName(self.repo_name)
        for p in projects:
            self.project_list.addItem(f"{p.title} - {p.path}")

        project_v.addWidget(QLabel("List of Projects :"))
        project_v.addWidget(self.project_list)
        center_v_layout.addWidget(project_box)

        # Right (Fixed 350)
        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)

    def handle_audit_toggle(self):
        if self._is_toggling: return
        self._is_toggling = True

        if not self.is_expanded:
            self.audit_container.setFixedWidth(self.width() - 40)
            self.center_container.hide()
            self.right_spacer.hide()

            # Switch to Expanded Text
            repo_logs = getRepoAuditLogsByRepoName(self.repo_name)
            for i, log in enumerate(reversed(repo_logs)):
                if i < self.audit_list.count():
                    text = auditLogToTextExpanded(log)
                    self.audit_list.item(i).setText(text)

            self.expand_btn.setText("Minimise Audit Log")
            self.is_expanded = True
        else:
            self.audit_container.setFixedWidth(350)
            self.center_container.show()
            self.right_spacer.show()

            # Switch back to Original Text
            for i in range(self.audit_list.count()):
                if i < len(self.original_logs):
                    self.audit_list.item(i).setText(self.original_logs[i])

            self.expand_btn.setText("Expand Audit Log")
            self.is_expanded = False

        self._is_toggling = False