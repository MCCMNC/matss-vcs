# GUI.py
import sys
import os
import django
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QInputDialog, QMessageBox
)

# -------------------- Django Setup --------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

# -------------------- Helper Functions --------------------
def get_user_projects(user):
    return Project.objects.filter(owner=user)

def get_contributed_projects(user):
    return Project.objects.filter(projectversion__author=user).distinct()

def get_project_versions(project):
    return ProjectVersion.objects.filter(project=project)

def get_version_files(project_version):
    return VersionFile.objects.filter(version=project_version)

def get_audit_logs(project):
    return AuditLog.objects.filter(project=project).order_by("timestamp")

# -------------------- Dark-Themed MessageBox --------------------
def show_dark_message(parent, title, message, icon=QMessageBox.Information):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(icon)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.setStyleSheet("""
        QMessageBox {
            background-color: #0d1115;
            color: #c9d1d9;
            font-size: 14px;
        }
        QPushButton {
            background-color: #060709;
            color: #c9d1d9;
            border: none;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #21262d;
        }
    """)
    msg.exec_()

def show_dark_confirm(parent, title, message):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Question)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setStyleSheet("""
        QMessageBox {
            background-color: #0d1115;
            color: #c9d1d9;
            font-size: 14px;
        }
        QPushButton {
            background-color: #060709;
            color: #c9d1d9;
            border: none;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #21262d;
        }
    """)
    return msg.exec_() == QMessageBox.Yes

# -------------------- Login Widget --------------------
class LoginWidget(QWidget):
    def __init__(self, switch_to_main_menu):
        super().__init__()
        self.switch_to_main_menu = switch_to_main_menu
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.title = QLabel("MAT Version Control Login")
        self.title.setAlignment(Qt.AlignCenter)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)

        layout.addWidget(self.title)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        user = User.objects.filter(username=username).first()
        if not user or user.password_hash != password:
            show_dark_message(self, "Login Failed", "Incorrect username or password", QMessageBox.Warning)
            return
        user.loginStatus = True
        user.save()
        self.switch_to_main_menu(user)

# -------------------- Main Menu Widget --------------------
class MainMenuWidget(QWidget):
    def __init__(self, user, switch_to_login, switch_to_file_manager):
        super().__init__()
        self.user = user
        self.switch_to_login = switch_to_login
        self.switch_to_file_manager = switch_to_file_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        welcome = QLabel(f"Logged in as: {self.user.username}")
        welcome.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome)

        self.file_manager_btn = QPushButton("File Manager")
        self.file_manager_btn.clicked.connect(lambda: self.switch_to_file_manager(self.user))
        self.logout_btn = QPushButton("Log out")
        self.logout_btn.clicked.connect(self.logout)

        layout.addWidget(self.file_manager_btn)
        layout.addWidget(self.logout_btn)
        self.setLayout(layout)

    def logout(self):
        self.user.loginStatus = False
        self.user.save()
        self.switch_to_login()

# -------------------- File Manager Widget --------------------
class FileManagerWidget(QWidget):
    def __init__(self, user, switch_to_main):
        super().__init__()
        self.user = user
        self.switch_to_main = switch_to_main
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.label = QLabel("File Manager Menu")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Buttons
        btn_texts = [
            ("List Projects", self.list_projects),
            ("List Project Versions", self.list_project_versions),
            ("List All Files", self.list_all_files),
            ("List Audit Log", self.list_audit_log),
            ("Add Project", self.add_project),
            ("Add Project Version", self.add_project_version),
            ("Add File", self.add_file),
            ("Remove File", self.remove_file),
            ("Approve Version", self.approve_version),
            ("Wipe DB (except users)", self.wipe_db),
            ("Back to Main Menu", self.back_to_main)
        ]

        for text, func in btn_texts:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            layout.addWidget(btn)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

        self.setLayout(layout)

    # -------------------- Button Functions --------------------
    def list_projects(self):
        self.output_area.clear()
        owned = get_user_projects(self.user)
        contributed = get_contributed_projects(self.user)
        self.output_area.append("Owned Projects:")
        for p in owned:
            self.output_area.append(f"  ID: {p.pk} | Title: {p.title}")
        self.output_area.append("\nContributed Projects:")
        for p in contributed:
            self.output_area.append(f"  ID: {p.pk} | Title: {p.title}")

    def list_project_versions(self):
        pid, ok = QInputDialog.getInt(self, "Project ID", "Enter Project ID:")
        if not ok:
            return
        project = Project.objects.get(pk=pid)
        versions = get_project_versions(project)
        self.output_area.clear()
        self.output_area.append(f"Versions for {project.title}:")
        for v in versions:
            self.output_area.append(f"  Version {v.version_number} | Status: {v.status} | Message: {v.message}")

    def list_all_files(self):
        pid, ok = QInputDialog.getInt(self, "Project ID", "Enter Project ID:")
        if not ok:
            return
        project = Project.objects.get(pk=pid)
        versions = get_project_versions(project)
        self.output_area.clear()
        self.output_area.append(f"Files for project {project.title}:")
        for v in versions:
            files = get_version_files(v)
            for f in files:
                self.output_area.append(f"  Version {v.version_number} | Path: {f.path} | Content: {f.content}")

    def list_audit_log(self):
        pid, ok = QInputDialog.getInt(self, "Project ID", "Enter Project ID:")
        if not ok:
            return
        project = Project.objects.get(pk=pid)
        logs = get_audit_logs(project)
        self.output_area.clear()
        self.output_area.append(f"Audit Logs for {project.title}:")
        for log in logs:
            self.output_area.append(f"[{log.timestamp}] {log.user.username} → {log.action} ({log.details})")

    def add_project(self):
        title, ok1 = QInputDialog.getText(self, "Project Title", "Enter Project Title:")
        if not ok1:
            return
        desc, ok2 = QInputDialog.getText(self, "Project Description", "Enter Project Description:")
        if not ok2:
            return
        project, _ = Project.objects.get_or_create(title=title, defaults={"description": desc, "owner": self.user})
        AuditLog.objects.get_or_create(user=self.user, project=project, action="CREATE_PROJECT",
                                       details=f"Added {project.title} to DB")
        self.output_area.setText(f"Project {title} added successfully.")

    def add_project_version(self):
        pid, ok = QInputDialog.getInt(self, "Project ID", "Enter Project ID:")
        if not ok:
            return
        project = Project.objects.get(pk=pid)
        msg, ok2 = QInputDialog.getText(self, "Version Message", "Enter Version Message:")
        if not ok2:
            return
        latest = ProjectVersion.objects.filter(project=project).order_by("-version_number").first()
        next_ver = 1 if not latest else latest.version_number + 1
        version, _ = ProjectVersion.objects.get_or_create(project=project, version_number=next_ver,
                                                          defaults={"author": self.user, "message": msg})
        AuditLog.objects.get_or_create(user=self.user, project=project, action="CREATE_VERSION",
                                       details=f"{project.title} v{next_ver} created")
        self.output_area.setText(f"Version {next_ver} added to project {project.title}.")

    def add_file(self):
        pid, ok = QInputDialog.getInt(self, "Project ID", "Enter Project ID:")
        if not ok:
            return
        project = Project.objects.get(pk=pid)
        vid, ok2 = QInputDialog.getInt(self, "Version Number", "Enter Version Number:")
        if not ok2:
            return
        version = ProjectVersion.objects.get(project=project, version_number=vid)
        path, ok3 = QInputDialog.getText(self, "File Path", "Enter File Path:")
        if not ok3:
            return
        content, ok4 = QInputDialog.getText(self, "File Content", "Enter File Content:")
        if not ok4:
            return
        vf, _ = VersionFile.objects.get_or_create(version=version, path=path, content=content)
        AuditLog.objects.get_or_create(user=self.user, project=project, action="CREATE_VERSION_FILE",
                                       details=f"Added {path} to {project.title} v{vid}")
        self.output_area.setText(f"File {path} added to version {vid}.")

    def remove_file(self):
        path, ok = QInputDialog.getText(self, "File Path", "Enter File Path to Remove:")
        if not ok:
            return
        vf = VersionFile.objects.filter(path=path).first()
        if not vf:
            show_dark_message(self, "Error", "File not found!", QMessageBox.Warning)
            return
        AuditLog.objects.get_or_create(user=self.user, project=vf.version.project, action="REMOVE_VERSION_FILE",
                                       details=f"Removed {path} from DB")
        vf.delete()
        self.output_area.setText(f"File {path} removed successfully.")

    def approve_version(self):
        pid, ok = QInputDialog.getInt(self, "Project ID", "Enter Project ID:")
        if not ok:
            return
        project = Project.objects.get(pk=pid)
        vid, ok2 = QInputDialog.getInt(self, "Version Number", "Enter Version Number:")
        if not ok2:
            return
        version = ProjectVersion.objects.get(project=project, version_number=vid)
        if self.user.role not in ["Author", "Admin"]:
            show_dark_message(self, "Error", "You are not allowed to approve versions", QMessageBox.Warning)
            return
        if version.status == "Approved":
            show_dark_message(self, "Info", "Version already approved", QMessageBox.Information)
            return
        version.status = "Approved"
        version.save()
        AuditLog.objects.get_or_create(user=self.user, project=project, action="APPROVE_VERSION",
                                       details=f"{project.title} v{vid} approved")
        self.output_area.setText(f"Version {vid} approved successfully.")

    def wipe_db(self):
        if show_dark_confirm(self, "Confirm", "Wipe entire DB (except users)?"):
            Project.objects.all().delete()
            ProjectVersion.objects.all().delete()
            VersionFile.objects.all().delete()
            AuditLog.objects.all().delete()
            self.output_area.setText("Database wiped (users preserved).")

    def back_to_main(self):
        self.parent().switch_widget(self.parent().main_menu)

# -------------------- Main Window --------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1440, 810)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1115; }
            QLabel { color: #c9d1d9; }
            QPushButton {
                background-color: #060709;
                color: #c9d1d9;
                border: none;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #21262d; }
            QTextEdit { background-color: #161b22; color: #c9d1d9; }
            QLineEdit { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; padding: 3px; }
        """)

        self.oldPos = self.pos()

        # Title bar
        self.titleBar = QWidget(self)
        self.titleBar.setFixedHeight(30)
        self.titleBar.setStyleSheet("background-color: #060709;")
        self.titleLabel = QLabel("MAT Version Control Software", self.titleBar)
        self.titleLabel.setStyleSheet("color: #c9d1d9; padding-left: 10px;")
        self.closeBtn = QPushButton("✕", self.titleBar)
        self.maxBtn = QPushButton("⬜", self.titleBar)
        self.minBtn = QPushButton("—", self.titleBar)
        for btn in (self.closeBtn, self.maxBtn, self.minBtn):
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton { background-color: #060709; color: #c9d1d9; border: none; padding: 0 10px; }
                QPushButton:hover { background-color: #21262d; }
            """)
        self.closeBtn.clicked.connect(self.close)
        self.minBtn.clicked.connect(self.showMinimized)
        self.maxBtn.clicked.connect(self.toggleMaximize)
        titleLayout = QHBoxLayout()
        titleLayout.setContentsMargins(0, 0, 0, 0)
        titleLayout.addWidget(self.titleLabel)
        titleLayout.addStretch()
        titleLayout.addWidget(self.minBtn)
        titleLayout.addWidget(self.maxBtn)
        titleLayout.addWidget(self.closeBtn)
        self.titleBar.setLayout(titleLayout)

        # Central container
        self.container = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.titleBar)
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        # Initialize widgets
        self.login_widget = LoginWidget(self.switch_to_main_menu)
        self.main_menu = None
        self.current_widget = self.login_widget
        self.layout.addWidget(self.current_widget)

        # Enable dragging
        self.titleBar.mousePressEvent = self.startMove
        self.titleBar.mouseMoveEvent = self.doMove

    def toggleMaximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def startMove(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def doMove(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def switch_widget(self, new_widget):
        self.layout.replaceWidget(self.current_widget, new_widget)
        self.current_widget.setParent(None)
        self.current_widget = new_widget

    def switch_to_main_menu(self, user):
        self.main_menu = MainMenuWidget(user, self.switch_to_login, self.open_file_manager)
        self.switch_widget(self.main_menu)

    def switch_to_login(self):
        self.switch_widget(self.login_widget)

    def open_file_manager(self, user):
        fm = FileManagerWidget(user, self.main_menu)
        self.switch_widget(fm)

# -------------------- Run App --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())