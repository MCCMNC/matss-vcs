import sys
import os
import django

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap, QIcon

# -------------------- Django Setup --------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog


# -------------------- Login Page --------------------
class LoginPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        container = QWidget()
        container.setFixedSize(900, 600)

        container_layout = QVBoxLayout()
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setSpacing(25)

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(BASE_DIR, "Assets", "MAT Software Solutions Logo.png")

        self.logo = QLabel()
        self.logo.setFixedSize(180, 180)
        self.logo.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(
                self.logo.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setFixedSize(450, 40)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedSize(450, 40)

        container_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        container_layout.addSpacing(40)
        container_layout.addWidget(self.username, alignment=Qt.AlignCenter)
        container_layout.addWidget(self.password, alignment=Qt.AlignCenter)

        container.setLayout(container_layout)

        # 🔥 FIX: force container to center
        main_layout.addWidget(container, alignment=Qt.AlignCenter)

        self.setLayout(main_layout)


# -------------------- Dashboard Page --------------------
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        pfp_path = os.path.join(BASE_DIR, "Assets", "Poet Cover 3.png")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)

        # -------------------- Top Bar --------------------
        top_bar = QHBoxLayout()

        self.pfp = QPushButton()
        self.pfp.setFixedSize(60, 60)

        pixmap = QPixmap(pfp_path)
        if not pixmap.isNull():
            self.pfp.setIcon(QIcon(pixmap))
            self.pfp.setIconSize(self.pfp.size())

        self.username_label = QLabel("Username")

        top_bar.addWidget(self.pfp)
        top_bar.addWidget(self.username_label)
        top_bar.addStretch()

        main_layout.addLayout(top_bar)

        # -------------------- Middle Layout --------------------
        middle_layout = QHBoxLayout()

        # LEFT: Audit log
        audit_container = QWidget()
        audit_container.setFixedWidth(300)

        audit_layout = QVBoxLayout()
        audit_label = QLabel("User Audit Log:")
        self.audit_list = QListWidget()

        self.audit_list.setFocusPolicy(Qt.NoFocus)
        self.audit_list.setSelectionMode(QListWidget.NoSelection)

        for i in range(8):
            self.audit_list.addItem(f"Audit Entry {i+1}")

        audit_layout.addWidget(audit_label)
        audit_layout.addWidget(self.audit_list)
        audit_container.setLayout(audit_layout)

        # CENTER: Repo list
        center_container = QWidget()
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)

        repo_container = QWidget()
        repo_container.setFixedWidth(500)

        repo_layout = QVBoxLayout()
        repo_label = QLabel("Repository List:")
        repo_label.setAlignment(Qt.AlignCenter)

        self.repo_list = QListWidget()

        for i in range(6):
            self.repo_list.addItem(f"Repo {i+1} - /path/to/repo (Role)")

        repo_layout.addWidget(repo_label)
        repo_layout.addWidget(self.repo_list)
        repo_container.setLayout(repo_layout)

        center_layout.addWidget(repo_container)
        center_container.setLayout(center_layout)

        # RIGHT spacer (balances layout)
        right_spacer = QWidget()
        right_spacer.setFixedWidth(300)

        middle_layout.addWidget(audit_container)
        middle_layout.addWidget(center_container, 1)
        middle_layout.addWidget(right_spacer)

        main_layout.addLayout(middle_layout)
        self.setLayout(main_layout)


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
            QLineEdit {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                padding: 5px;
            }
            QListWidget {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
            }
        """)

        self.oldPos = self.pos()

        # -------------------- Title Bar --------------------
        self.titleBar = QWidget(self)
        self.titleBar.setFixedHeight(30)
        self.titleBar.setStyleSheet("background-color: #060709;")

        self.titleLabel = QLabel("MAT Version Control Software", self.titleBar)

        self.closeBtn = QPushButton("✕", self.titleBar)
        self.maxBtn = QPushButton("⬜", self.titleBar)
        self.minBtn = QPushButton("—", self.titleBar)

        for btn in (self.closeBtn, self.maxBtn, self.minBtn):
            btn.setFixedHeight(30)

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

        # -------------------- Main Layout --------------------
        self.container = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.titleBar)

        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content.setLayout(self.content_layout)

        self.layout.addWidget(self.content)

        self.current_widget = LoginPage()
        self.content_layout.addWidget(self.current_widget)

        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

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
        self.content_layout.replaceWidget(self.current_widget, new_widget)
        self.current_widget.setParent(None)
        self.current_widget = new_widget


# -------------------- Run App --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()

    window.switch_widget(DashboardPage())  # LoginPage()/DashboardPage()

    window.show()
    sys.exit(app.exec_())