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

from GUI_DiffPanel import DiffPanel

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
matvcs_MIDDLE_LIST_STYLE = f"""
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
def gui_buildMIDDLE_LIST(inputWidget): #TODO: Possibly unused
    inputWidget.middleList = QListWidget()
    inputWidget.middleList.setMinimumSize(500, 400)
    inputWidget.middleList.setMouseTracking(True)
    inputWidget.middleList.setAcceptDrops(True)
    inputWidget.middleList.installEventFilter(inputWidget)
    inputWidget.middleList.setStyleSheet(matvcs_MIDDLE_LIST_STYLE)
def gui_buildBottomRow(inputWidget,inputWidgetType):
    print(inputWidgetType + " Began Building Bottom Row")
    inputWidget.button_row_widget = QWidget()
    inputWidget.button_row_layout = QHBoxLayout(inputWidget.button_row_widget)
    inputWidget.button_row_layout.setContentsMargins(0, 0, 0, 0)
    inputWidget.button_row_layout.setSpacing(15)
    inputWidget.button_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    inputWidget.back_btn = QPushButton("Go Back")
    inputWidget.back_btn.setFixedSize(120, 30)
    inputWidget.back_btn.setStyleSheet(
        "background: #212226; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
    inputWidget.back_btn.clicked.connect(inputWidget.back_callback)
    inputWidget.button_row_layout.addWidget(inputWidget.back_btn)
    if inputWidgetType == "Repository" or inputWidgetType == "Project"or inputWidgetType == "ProjectVersion":
        print(inputWidgetType + " Attempting to Build 'Manage Users' Button")
        is_admin = RepositoryMembership.objects.filter(
            user=inputWidget.user,
            repository=inputWidget.currentRepository.pk,
            repo_role="Admin"
        ).exists()
        # TODO : ADD USER REMOVAL FUNCTIONALITY TO MANAGE USERS WIDGET AND FILTER HERE
        inputWidget.manageUsers_btn = QPushButton("Manage Users")
        inputWidget.manageUsers_btn.setFixedSize(120, 30)
        inputWidget.manageUsers_btn.setStyleSheet(
            "background: #133347; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        inputWidget.manageUsers_btn.clicked.connect(inputWidget.handleManageUsers)
        inputWidget.button_row_layout.addWidget(inputWidget.manageUsers_btn)
        print(inputWidgetType + " Successfully Built 'Manage Users' Button")

        if is_admin:
            print(inputWidgetType + " Attempting to Build 'Add Users' Button")
            inputWidget.addUser_btn = QPushButton("Add Users")
            inputWidget.addUser_btn.setFixedSize(120, 30)
            inputWidget.addUser_btn.setStyleSheet(
                "background: #393E42; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
            inputWidget.addUser_btn.clicked.connect(inputWidget.handleAddUser)
            inputWidget.button_row_layout.addWidget(inputWidget.addUser_btn)
            print(inputWidgetType + " Successfully Built 'Add Users' Button")

    # Add the horizontal row to the vertical center layout
    inputWidget.center_v_layout.addWidget(inputWidget.button_row_widget)
    print(inputWidgetType + " Passed Bottom Row Build")

def gui_buildDesign(inputWidget,inputWidgetType,inputProgramType = "Studio"):
    print("Began Building "+inputWidgetType)
    inputWidget.main_layout = QVBoxLayout(inputWidget)
    inputWidget.main_layout.setContentsMargins(20, 20, 20, 20)
    inputWidget.main_layout.setSpacing(0)
    inputWidget.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    inputWidget.top_bar_container = QWidget()
    inputWidget.top_bar_container.setFixedHeight(70)
    inputWidget.top_bar_layout = QHBoxLayout(inputWidget.top_bar_container)
    inputWidget.top_bar_layout.setContentsMargins(0, 0, 0, 0)

    inputWidget.left_section = QWidget()
    inputWidget.left_section.setFixedWidth(350)
    inputWidget.left_layout = QHBoxLayout(inputWidget.left_section)
    inputWidget.left_layout.setContentsMargins(0, 0, 0, 0)
    inputWidget.left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    #Gets local profile picture
    if not hasattr(inputWidget,'pfp_pixmap'):
        print("no pfp loaded in " + inputWidgetType)
        inputWidget.pfp = QPushButton()
        inputWidget.pfp.setFixedSize(60, 60)
        inputWidget.pfp.setStyleSheet("border: none; background: transparent;")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
        pfp_path = os.path.join(BASE_DIR, "Assets", "Poet Cover 3.png")
        raw_pixmap = QPixmap(pfp_path)
        if not raw_pixmap.isNull():
            inputWidget.cached_pixmap = raw_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.FastTransformation)
            inputWidget.pfp.setIcon(QIcon(inputWidget.cached_pixmap))
            inputWidget.pfp.setIconSize(inputWidget.pfp.size())
            print(inputWidgetType + " Passed pfp Build")
    else:
        print(inputWidgetType + " Has Attribute pfp_pixmap")
        inputWidget.pfp = QPushButton()
        inputWidget.pfp.setFixedSize(60, 60)
        inputWidget.pfp.setStyleSheet("border: none; background: transparent;")
        inputWidget.pfp.setIcon(QIcon(inputWidget.pfp_pixmap))
        inputWidget.pfp.setIconSize(inputWidget.pfp.size())
        print(inputWidgetType + " Passed pfp Build")
    inputWidget.user_label = QLabel(inputWidget.user.username)
    inputWidget.user_label.setFont(QFont("Arial", 12))
    inputWidget.left_layout.addWidget(inputWidget.pfp)
    inputWidget.left_layout.addWidget(inputWidget.user_label)

    if inputProgramType == "Code" and inputWidgetType == "Project":
        guiSetTopLabel(inputWidget, "Code File", 24)
    else : guiSetTopLabel(inputWidget, inputProgramType + " " + inputWidgetType, 24)
    inputWidget.right_section = QWidget()
    inputWidget.right_section.setFixedWidth(350)
    inputWidget.right_layout = QHBoxLayout(inputWidget.right_section)
    inputWidget.right_layout.setContentsMargins(0, 0, 0, 0)
    inputWidget.right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    guiAddLogoutButton(inputWidget, inputWidget.right_layout, inputWidget.on_logout)
    inputWidget.top_bar_layout.addWidget(inputWidget.left_section)
    inputWidget.top_bar_layout.addWidget(inputWidget.page_title, 1)
    inputWidget.top_bar_layout.addWidget(inputWidget.right_section)
    inputWidget.main_layout.addWidget(inputWidget.top_bar_container)

    inputWidget.middle_layout = QHBoxLayout()
    inputWidget.middle_layout.setContentsMargins(0, 0, 0, 0)
    inputWidget.middle_layout.setSpacing(0)
    inputWidget.center_container = QWidget()
    inputWidget.center_v_layout = QVBoxLayout(inputWidget.center_container)
    inputWidget.center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
    inputWidget.center_v_layout.setSpacing(10)
    inputWidget.center_v_layout.setContentsMargins(0, 10, 0, 10)


    inputWidget.middleList = QListWidget()
    inputWidget.middleList.setMinimumSize(500, 400)
    inputWidget.middleList.setMouseTracking(True)
    inputWidget.middleList.setAcceptDrops(True)
    inputWidget.middleList.installEventFilter(inputWidget)
    inputWidget.middleList.setStyleSheet(matvcs_MIDDLE_LIST_STYLE)
    print(inputWidgetType + " Built Middle List")
    inputWidget.middle_box = QWidget()
    inputWidget.middle_v = QVBoxLayout(inputWidget.middle_box)
    inputWidget.middle_v.setContentsMargins(0, 0, 0, 0)


    inputWidget.middle_v.addWidget(QLabel("Relevant List :"))
    inputWidget.middle_v.addWidget(inputWidget.middleList)
    inputWidget.center_v_layout.addWidget(inputWidget.middle_box)



    guiSetAuditLog(inputWidget, inputWidgetType)

    inputWidget.middle_layout.addWidget(inputWidget.audit_container)
    inputWidget.middle_layout.addWidget(inputWidget.center_container, 1)
    if inputProgramType == "Code" and inputWidgetType == "Project":
        # Initialize the new Diff Panel using projectVersionData
        inputWidget.diff_panel = DiffPanel(inputWidget.projectVersionData)
        inputWidget.middle_layout.addWidget(inputWidget.diff_panel)
    else:
        # Default empty spacer for non-code projects
        inputWidget.right_spacer = QWidget()
        inputWidget.right_spacer.setFixedWidth(350)
        inputWidget.middle_layout.addWidget(inputWidget.right_spacer)
    inputWidget.main_layout.addLayout(inputWidget.middle_layout)
    print(inputWidgetType + " Passed GUI Build")

def guiUserLogin(inputUsername,inputPassword):
    potentialUser = User.objects.filter(username = inputUsername).first() # Potential issue: if the username does not exist, potentialUser will be None
    if potentialUser is None or potentialUser.password_hash != inputPassword:
        return None
    userLogIn(potentialUser)
    return potentialUser

def auditLogToText(entry):
    if entry.project is None:
        return f" {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {entry.action} ({entry.details})"
    return f" {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {entry.action} ({entry.project.title})"
def auditLogToTextExtended(entry):
    if entry.project is None:
        return f" {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {entry.action} ({entry.details})"
    return f" {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {entry.user.username} {entry.action} ({entry.project.title})"
def auditLogToTextExpanded(entry):
    if entry.project is None:
        return f" {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {entry.action} ({entry.details})"
    return f" {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {entry.user.username} {entry.action} ({entry.project.title} {entry.details})"
def guiErrorBox(parent,inputErrorStr):
    msg = QMessageBox(parent)
    msg.setWindowTitle("Error")
    msg.setText("MAT VCS ran into an "+inputErrorStr+" Error")
    msg.exec()
def guiSetTopLabel(inputWidget,inputText,inputFontSize):
    inputWidget.page_title = QLabel(inputText)
    inputWidget.page_title.setFont(QFont("Arial", inputFontSize, QFont.Weight.Bold))
    inputWidget.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)


def guiSetAuditLog(inputWidget, inputWidgetType):
    print(inputWidgetType + " Started setting Audit Log")
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
    if inputWidgetType == "Dashboard":
        inputWidget.audit_label.setText(f"Audit Log for : {inputWidget.user.username}")
        logs = getUserAuditLogs(inputWidget.user.id)

    elif inputWidgetType == "Repository":
        inputWidget.audit_label.setText(f"Audit Log for : {inputWidget.repo_name}")
        logs = getRepoAuditLogsByRepo(inputWidget.currentRepository)

    elif inputWidgetType == "Project":
        inputWidget.audit_label.setText(f"Audit Log for : {inputWidget.project_data.title}")
        logs = getProjectAuditLogs(inputWidget.project_data.id)

    elif inputWidgetType == "ProjectVersion":
        inputWidget.audit_label.setText(
            f"Audit Log for : {inputWidget.project_version.project.title} v{inputWidget.project_version.version_number}")
        logs = getProjectVersionAuditLogsByID(inputWidget.project_version.id)

    for log in reversed(list(logs)):
        text = auditLogToText(log)
        inputWidget.original_logs.append(text)
        item = QListWidgetItem(text)
        item.setFont(log_font)
        inputWidget.audit_list.addItem(item)
    print(inputWidgetType + " Successfully set Audit Log")

def guiExpandAuditLog(inputWidget, inputInstruction):
    if inputInstruction not in ["Dashboard", "Repo", "Project", "ProjectVersion"] or getattr(inputWidget, '_is_toggling', False):
        return

    inputWidget._is_toggling = True
    expand = not inputWidget.is_expanded
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


def guiAddLogoutButton(parent_widget,layout, logout_callback):
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

import sys
import shutil
import subprocess
import winreg

def guiLocalDeviceHasDefaultProgram(ext):
    """
    Dynamically determines if the current OS has a registered
    application for the given extension (e.g., '.rpp').
    """
    if not ext or ext == ".":
        return False
    if not ext.startswith('.'):
        ext = "." + ext

    # --- Windows Logic ---
    if sys.platform == "win32":
        try:
            # Check for the Progid pointer
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ext) as key:
                prog_id, _ = winreg.QueryValueEx(key, "")
            # Check if that Progid has a shell open command
            shell_path = rf"{prog_id}\shell\open\command"
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, shell_path) as _:
                return True
        except (WindowsError, FileNotFoundError):
            return False

    # --- macOS Logic ---
    elif sys.platform == "darwin":
        # On Mac, if 'open' can find an app for the extension, it's valid.
        # We check if 'open' would succeed without actually launching.
        try:
            # 'test -f' isn't enough; we check the handler via 'lsappinfo' or 'open'
            result = subprocess.run(['open', '-Ra', ext], capture_output=True)
            return result.returncode == 0
        except:
            return True # MacOS 'open' is very robust, fallback to True

    # --- Linux Logic ---
    elif sys.platform.startswith("linux"):
        # Linux uses xdg-mime to manage file associations
        if shutil.which("xdg-mime"):
            try:
                # Query the default handler for the mimetype
                # We construct a generic mimetype guess
                mimetype = f"application/{ext[1:]}"
                result = subprocess.run(
                    ["xdg-mime", "query", "default", mimetype],
                    capture_output=True, text=True
                )
                return len(result.stdout.strip()) > 0
            except:
                return False
        return shutil.which("xdg-open") is not None

    return False

import os
from datetime import datetime

def guiCreateProjectFromDrop(user, inputRepo_obj, title, desc, source_path):
    try:
        repo = inputRepo_obj
        with open(source_path, 'rb') as fsrc:
            with open(source_path, 'wb') as fdst:
                fdst.write(fsrc.read())
        current_ts = datetime.now()
        return addProjectAndInitialVersionToDB(user, repo, title, desc, source_path, current_ts)

    except Exception as e:
        print(f"GUI Drop operation failed: {e}")
        return False
def formatWidget(inputWidget):
    formatWidgetSlashes(inputWidget)