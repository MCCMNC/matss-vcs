from DBFunctions import *
import os
import django
import PyQt6
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox
)
from PyQt6.QtGui import QFont, QPixmap, QIcon
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

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

def guiUserLogin(inputUsername,inputPassword):
    potentialUser = User.objects.filter(username = inputUsername).first() # Potential issue: if the username does not exist, potentialUser will be None
    if potentialUser is None or potentialUser.password_hash != inputPassword:
        return None
    userLogIn(potentialUser)
    return potentialUser

def auditLogToText(entry):
    return f" {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} → {entry.action} ({entry.project.title})"
def auditLogToTextExtended(entry):
    return f" {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} → {entry.user.username} {entry.action} ({entry.project.title})"
def auditLogToTextExpanded(entry):
    return f" {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} → {entry.user.username} {entry.action} ({entry.project.title} {entry.details})"
def guiErrorBox(parent,inputErrorStr):
    msg = QMessageBox(parent)
    msg.setWindowTitle("Error")
    msg.setText("MAT VCS ran into an "+inputErrorStr+" Error")
    msg.exec()
def guiSetTopLabel(inputWidget,inputText):
    inputWidget.page_title = QLabel(inputText)
    inputWidget.page_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
    inputWidget.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

def guiSetAuditLog(inputWidget,inputInstruction):
    if inputInstruction == "Dashboard":
        inputWidget.audit_container = QWidget()
        inputWidget.audit_container.setFixedWidth(350)
        audit_v_layout = QVBoxLayout(inputWidget.audit_container)
        audit_v_layout.setContentsMargins(0, 10, 10, 10)

        inputWidget.audit_label = QLabel(f"Audit Log for : {inputWidget.user.username} ")
        inputWidget.audit_list = QListWidget()
        inputWidget.audit_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        inputWidget.audit_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        inputWidget.audit_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inputWidget.audit_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; "
            f"background: rgba(255,255,255,0.02); "
            f"color: #b9c2c9; outline: none; }} "
            f"{SCROLLBAR_STYLE}")

        user_logs = getUserAuditLogs(inputWidget.user.id)
        log_font = QFont("Arial", 8)
        for log in reversed(user_logs):
            text = auditLogToText(log)
            inputWidget.original_logs.append(text)
            item = QListWidgetItem(text)
            item.setFont(log_font)
            inputWidget.audit_list.addItem(item)

        inputWidget.expand_btn = QPushButton("Expand Audit Log")
        # REMOVED: setCursor(Qt.CursorShape.PointingHandCursor)
        inputWidget.expand_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; padding: 10px; font-weight: bold;")
        inputWidget.expand_btn.clicked.connect(inputWidget.handle_audit_toggle)

        audit_v_layout.addWidget(inputWidget.audit_label)
        audit_v_layout.addWidget(inputWidget.audit_list)
        audit_v_layout.addWidget(inputWidget.expand_btn)

    elif inputInstruction == "Repo":
        inputWidget.audit_container = QWidget()
        inputWidget.audit_container.setFixedWidth(350)
        audit_v_layout = QVBoxLayout(inputWidget.audit_container)
        audit_v_layout.setContentsMargins(0, 10, 10, 10)

        inputWidget.audit_label = QLabel(f"Audit Log for : {inputWidget.repo_name}")
        inputWidget.audit_list = QListWidget()
        inputWidget.audit_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        inputWidget.audit_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        inputWidget.audit_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inputWidget.audit_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; background: rgba(255,255,255,0.02); color: #b9c2c9; outline: none; }} {SCROLLBAR_STYLE}")

        repo_logs = getRepoAuditLogsByRepoName(inputWidget.repo_name)
        log_font = QFont("Arial", 8)
        for log in reversed(repo_logs):
            text = auditLogToText(log)
            inputWidget.original_logs.append(text)
            item = QListWidgetItem(text)
            item.setFont(log_font)
            inputWidget.audit_list.addItem(item)

        inputWidget.expand_btn = QPushButton("Expand Audit Log")
        inputWidget.expand_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; padding: 10px; font-weight: bold;")
        inputWidget.expand_btn.clicked.connect(inputWidget.handle_audit_toggle)

        audit_v_layout.addWidget(inputWidget.audit_label)
        audit_v_layout.addWidget(inputWidget.audit_list)
        audit_v_layout.addWidget(inputWidget.expand_btn)

def guiExpandAuditLog(inputWidget, inputInstruction):
    if inputInstruction not in ["Dashboard", "Repo"] or getattr(inputWidget, '_is_toggling', False):
        return

    inputWidget._is_toggling = True
    expand = not inputWidget.is_expanded

    # Unified UI Toggle
    inputWidget.audit_container.setFixedWidth(inputWidget.width() - 40 if expand else 350)
    inputWidget.center_container.setVisible(not expand)
    inputWidget.right_spacer.setVisible(not expand)
    inputWidget.expand_btn.setText("Minimise Audit Log" if expand else "Expand Audit Log")

    if expand:
        # Fetch based on instruction, then update list
        logs = getUserAuditLogs(inputWidget.user.id) if inputInstruction == "Dashboard" else getRepoAuditLogsByRepoName(inputWidget.repo_name)
        for i, log in enumerate(reversed(logs)):
            if i < inputWidget.audit_list.count():
                inputWidget.audit_list.item(i).setText(auditLogToTextExpanded(log))
    else:
        # Restore original logs
        for i in range(min(inputWidget.audit_list.count(), len(inputWidget.original_logs))):
            inputWidget.audit_list.item(i).setText(inputWidget.original_logs[i])

    inputWidget.is_expanded = expand
    inputWidget._is_toggling = False