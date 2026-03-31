import os
import shutil
from PyQt6.QtCore import Qt, QFileInfo, QSize, QObject
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QFileIconProvider, QInputDialog, QLineEdit
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

from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QComboBox, QPushButton, QVBoxLayout, QHBoxLayout

class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add User to Repository")
        self.setFixedSize(300, 180)
        self.setStyleSheet("background-color: #151719; color: #b9c2c9;")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("background: #0d1115; border: 1px solid #30363d; padding: 5px;")
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Reviewer", "Author", "Guest"])
        self.role_combo.setStyleSheet("background: #0d1115; border: 1px solid #30363d;")
        layout.addWidget(self.role_combo)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add User")
        self.add_btn.setStyleSheet("background: #238636; color: white; font-weight: bold; padding: 5px;")
        self.cancel_btn = QPushButton("Cancel")

        self.add_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.username_input.text().strip(), self.role_combo.currentText()

class RepoPage(QWidget):
    def __init__(self, loginUser, repo_obj, back_callback, logout_callback, project_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.currentRepository = repo_obj
        self.repo_name = repo_obj.title
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
        self.project_list.setMouseTracking(True)

        # --- DRAG AND DROP SETUP ---
        self.project_list.setAcceptDrops(True)
        self.project_list.installEventFilter(self)

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
        self.refresh_project_list()
        project_v.addWidget(QLabel("List of Projects :"))
        project_v.addWidget(self.project_list)
        center_v_layout.addWidget(project_box)

        # -------------------- Bottom Button Row --------------------
        # We create a horizontal container to hold both buttons side-by-side
        button_row_widget = QWidget()
        button_row_layout = QHBoxLayout(button_row_widget)
        button_row_layout.setContentsMargins(0, 0, 0, 0)
        button_row_layout.setSpacing(15)
        button_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.back_btn = QPushButton("Go Back")
        self.back_btn.setFixedSize(120, 30)
        self.back_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.back_btn.clicked.connect(self.back_callback)

        self.addUser_btn = QPushButton("Add Users")
        self.addUser_btn.setFixedSize(120, 30)
        self.addUser_btn.setStyleSheet(
            "background: #393E42; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.addUser_btn.clicked.connect(self.handleAddUser)

        button_row_layout.addWidget(self.back_btn)
        is_admin = RepositoryMembership.objects.filter(
            user=self.user,
            repository=repo_obj.pk,
            repo_role="Admin"
        ).exists()
        if is_admin : button_row_layout.addWidget(self.addUser_btn)

        # Add the horizontal row to the vertical center layout
        center_v_layout.addWidget(button_row_widget)

        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)

        formatWidget(self)

    # -------------------- Drag & Drop Event Filter --------------------
    def eventFilter(self, source, event):
        if source is self.project_list:
            if event.type() == event.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                    return True
            elif event.type() == event.Type.Drop:
                self.handle_dropped_file(event)
                return True
        return super().eventFilter(source, event)

    def handleAddUser(self):
        dialog = AddUserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username, role = dialog.get_data()

            if not username:
                QMessageBox.warning(self, "Input Error", "Please enter a username.")
                return

            try:
                # 1. Check if user exists
                from vcs_core.models import User, Repository, RepositoryMembership

                try:
                    target_user = User.objects.get(username=username)
                except User.DoesNotExist:
                    QMessageBox.critical(self, "Error", f"User '{username}' not found in database.")
                    return
                repo_obj = self.currentRepository

                # 3. Create or Update membership
                membership, created = RepositoryMembership.objects.update_or_create(
                    user=target_user,
                    repository=repo_obj,
                    defaults={'repo_role': role}
                )

                # 4. Log the action
                AuditLog.objects.create(
                    user=self.user,  # The person performing the addition
                    action="ADD_MEMBER",
                    repository=repo_obj,
                    details=f"Added {username} as {role} to {self.repo_name}"
                )

                status_msg = "Added" if created else "Updated"
                QMessageBox.information(self, "Success", f"Successfully {status_msg} {username} as {role}.")

                # Optional: Refresh your UI if you have a member list
                # self.refresh_member_list()

            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Could not add user: {e}")
    def handle_dropped_file(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return

        file_path = files[0]
        file_name = os.path.basename(file_path)
        title, ok1 = QInputDialog.getText(self, "New Project", "Project Title:", QLineEdit.EchoMode.Normal, file_name)
        if not ok1 or not title: return

        desc, ok2 = QInputDialog.getMultiLineText(self, "New Project", "Description:")
        if not ok2: return

        # Call logic to create project and first version
        if guiCreateProjectFromDrop(self.user, self.currentRepository, title, desc, file_path):
            self.refresh_project_list()
            guiSetAuditLog(self, "Repo")
        else:
            QMessageBox.warning(self, "Error", "Could not create project from file.")

    # -------------------- Handlers & Refresh --------------------
    def refresh_project_list(self):
        self.project_list.clear()
        self.projects_data = getRepoProjectsByRepo(self.currentRepository)
        project_icons = getItemIcons(self.projects_data, "Project")

        for p, icon in zip(self.projects_data, project_icons):
            item = QListWidgetItem(self.project_list)
            item.setSizeHint(QSize(0, 40))
            custom_widget = FileItemWidget(p, icon, self, context_type="Project")
            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, custom_widget)

    def handle_delete(self, project_obj):
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f"Are you sure you want to delete the project '{project_obj.title}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if removeProjectFromDB(self.user, project_obj):
                self.refresh_project_list()
                guiSetAuditLog(self, "Repo")
            else:
                QMessageBox.warning(self, "Error", "Could not delete project.")

    def handle_follow(self, project_obj):
        if project_obj:
            self.project_callback(project_obj)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Repo")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_project_list()