from DBFunctions import *
import os
import django
import PyQt6
from PyQt6.QtWidgets import QMessageBox, QFileIconProvider
from PyQt6.QtCore import Qt, QFileInfo
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox
)
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QListWidget
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtWidgets import QPushButton, QMessageBox
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
def guiSetTopLabel(inputWidget,inputText,inputFontSize):
    inputWidget.page_title = QLabel(inputText)
    inputWidget.page_title.setFont(QFont("Arial", inputFontSize, QFont.Weight.Bold))
    inputWidget.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)


def guiSetAuditLog(inputWidget, inputInstruction):
    # --- PHASE 1: UI SETUP (Only runs once) ---
    if not hasattr(inputWidget, 'audit_list'):
        inputWidget.audit_container = QWidget()
        inputWidget.audit_container.setFixedWidth(350)
        audit_v_layout = QVBoxLayout(inputWidget.audit_container)
        audit_v_layout.setContentsMargins(0, 10, 10, 10)

        inputWidget.audit_label = QLabel()
        inputWidget.audit_list = QListWidget()
        inputWidget.audit_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        inputWidget.audit_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        inputWidget.audit_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inputWidget.audit_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid #0d1115; "
            f"background: rgba(255,255,255,0.02); "
            f"color: #b9c2c9; outline: none; }} "
            f"{SCROLLBAR_STYLE}")

        inputWidget.expand_btn = QPushButton("Expand Audit Log")
        inputWidget.expand_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; padding: 10px; font-weight: bold;")
        inputWidget.expand_btn.clicked.connect(inputWidget.handle_audit_toggle)

        audit_v_layout.addWidget(inputWidget.audit_label)
        audit_v_layout.addWidget(inputWidget.audit_list)
        audit_v_layout.addWidget(inputWidget.expand_btn)

    # --- PHASE 2: DATA POPULATION (Runs every time) ---
    inputWidget.audit_list.clear()
    inputWidget.original_logs = []
    log_font = QFont("Arial", 8)
    logs = []

    # Identify the correct data source based on instruction
    if inputInstruction == "Dashboard":
        inputWidget.audit_label.setText(f"Audit Log for : {inputWidget.user.username}")
        logs = getUserAuditLogs(inputWidget.user.id)

    elif inputInstruction == "Repo":
        inputWidget.audit_label.setText(f"Audit Log for : {inputWidget.repo_name}")
        logs = getRepoAuditLogsByRepoName(inputWidget.repo_name)

    elif inputInstruction == "Project":
        inputWidget.audit_label.setText(f"Audit Log for : {inputWidget.project_data.title}")
        logs = getProjectAuditLogs(inputWidget.project_data.id)

    elif inputInstruction == "ProjectVersion":
        inputWidget.audit_label.setText(
            f"Audit Log for : {inputWidget.project_version.project.title} v{inputWidget.project_version.version_number}")
        logs = getProjectVersionAuditLogsByID(inputWidget.project_version.id)

    # Populate the list with fresh data from DB
    # Note: Use list(logs) to ensure we can reverse a QuerySet safely
    for log in reversed(list(logs)):
        text = auditLogToText(log)
        inputWidget.original_logs.append(text)
        item = QListWidgetItem(text)
        item.setFont(log_font)
        inputWidget.audit_list.addItem(item)

def guiExpandAuditLog(inputWidget, inputInstruction):
    # Added "Project" and "ProjectVersion" to the allowed instructions
    if inputInstruction not in ["Dashboard", "Repo", "Project", "ProjectVersion"] or getattr(inputWidget, '_is_toggling', False):
        return

    inputWidget._is_toggling = True
    expand = not inputWidget.is_expanded

    # Unified UI Toggle
    inputWidget.audit_container.setFixedWidth(inputWidget.width() - 40 if expand else 350)
    inputWidget.center_container.setVisible(not expand)
    inputWidget.right_spacer.setVisible(not expand)
    inputWidget.expand_btn.setText("Minimise Audit Log" if expand else "Expand Audit Log")

    if expand:
        # 1. Determine which logs to fetch based on the page type
        if inputInstruction == "Dashboard":
            logs = getUserAuditLogs(inputWidget.user.id)
        elif inputInstruction == "Repo":
            logs = getRepoAuditLogsByRepoName(inputWidget.repo_name)
        elif inputInstruction == "Project":
            logs = getProjectAuditLogs(inputWidget.project_data.id)
        elif inputInstruction == "ProjectVersion":
            logs = getProjectVersionAuditLogsByID(inputWidget.project_version.id)
        else:
            logs = []

        # 2. Update the list with expanded text
        for i, log in enumerate(reversed(logs)):
            if i < inputWidget.audit_list.count():
                inputWidget.audit_list.item(i).setText(auditLogToTextExpanded(log))
    else:
        # Restore original short-form logs
        for i in range(min(inputWidget.audit_list.count(), len(inputWidget.original_logs))):
            inputWidget.audit_list.item(i).setText(inputWidget.original_logs[i])

    inputWidget.is_expanded = expand
    inputWidget._is_toggling = False

def getItemIcons(inputDBElements, inputItemsType):
    returnedIcons = []
    icon_provider = QFileIconProvider()
    for item in inputDBElements:
        file_info = QFileInfo(getElementRelativePath(item, inputItemsType))
        native_icon = icon_provider.icon(file_info)
        returnedIcons.append(native_icon)
    return returnedIcons
def formatWidgetSlashes(inputWidget):
    """
    Recursively finds all text-bearing elements within a widget
    and adds spaces around any '/' characters.
    """
    # Define which widgets we want to target and how to get/set their text
    # This covers the most common types in your current project
    for child in inputWidget.findChildren(QWidget):

        # Handle Labels, Buttons, and LineEdits
        if isinstance(child, (QLabel, QPushButton, QLineEdit)):
            current_text = child.text()
            if "/" in current_text:
                # Replace "/" with " / " but prevent double-spacing if it's already there
                new_text = current_text.replace("/", " / ").replace("  /  ", " / ")
                child.setText(new_text.strip())

        # Handle List Widgets (like your Project or Audit lists)
        elif isinstance(child, QListWidget):
            for i in range(child.count()):
                item = child.item(i)
                current_text = item.text()
                if "/" in current_text:
                    new_text = current_text.replace("/", " / ").replace("  /  ", " / ")
                    item.setText(new_text.strip())

        # If the child is a container, the findChildren call already
        # handles the recursion, but you can manually recurse if needed.


def guiAddLogoutButton(parent_widget, layout, logout_callback):
    """
    Creates and adds the standardized logout button to a layout.

    Args:
        parent_widget: The QWidget (page) the button belongs to (for QMessageBox parenting).
        layout: The QHBoxLayout or QVBoxLayout where the button should be added.
        logout_callback: The function to execute if the user confirms logout.
    """
    logout_btn = QPushButton("Log Out")
    logout_btn.setFixedSize(100, 35)
    logout_btn.setStyleSheet(
        "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;"
    )

    def confirm_logout():
        msg_box = QMessageBox(parent_widget)
        msg_box.setWindowTitle("Confirm Log Out")
        msg_box.setText("Are you sure you want to log out?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(
            "QMessageBox { background-color: #0d0e0f; } "
            "QLabel { color: #b9c2c9; } "
            "QPushButton { background-color: #151719; color: #b9c2c9; border: 1px solid #30363d; "
            "padding: 5px; min-width: 80px; }"
        )

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            logout_callback()

    logout_btn.clicked.connect(confirm_logout)
    layout.addWidget(logout_btn)

    # Returning the button in case you need to store a reference to it
    return logout_btn

def formatWidget(inputWidget):
    formatWidgetSlashes(inputWidget)