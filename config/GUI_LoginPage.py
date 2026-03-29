import sys
import os
import django

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget
)
from PyQt6.QtGui import QPixmap, QIcon

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from GUIFunctions import *
from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

class LoginPage(QWidget):
    def __init__(self, login_success_callback):
        super().__init__()
        self.login_success_callback = login_success_callback

        # Main layout handles the centering relative to the entire window
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container is now flexible instead of fixed
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(20)

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(BASE_DIR, "Assets", "MAT Software Solutions Logo.png")

        self.logo = QLabel()
        self.logo.setFixedSize(320, 320) # Slightly smaller for the 480 width
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(
                self.logo.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        # Reduced width to 350 to look better in the smaller window
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setFixedSize(350, 40)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedSize(350, 40)

        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedSize(200, 40)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- KEYBOARD NAVIGATION ---
        self.login_btn.clicked.connect(self.handleLogin)
        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self.handleLogin)

        # Add widgets with Center alignment to the internal layout
        container_layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addSpacing(20)
        container_layout.addWidget(self.username, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.password, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.login_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(container)

    def showEvent(self, event):
        super().showEvent(event)
        self.username.setFocus()

    def clearFields(self):
        self.username.clear()
        self.password.clear()
        self.username.setFocus()

    def handleLogin(self):
        user = guiUserLogin(self.username.text(),self.password.text())
        if user is not None:
            self.username.clear()
            self.password.clear()
            self.login_success_callback(user)
        else:
            guiErrorBox(self, "Invalid Credentials")
            self.clearFields()