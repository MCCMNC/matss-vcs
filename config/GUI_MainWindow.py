import sys
import os
import django

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    django.setup()
except RuntimeWarning:
    pass

from GUI_LoginPage import LoginPage
from GUI_DashboardPage import DashboardPage
from GUI_RepoPage import RepoPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.setStyleSheet("""
            QMainWindow { background-color: #0d1115; }
            QLabel { color: #c9d1d9; }
            QPushButton { background-color: #060709; color: #c9d1d9; border: none; padding: 5px 10px; }
            QPushButton:hover { background-color: #21262d; }
        """)

        self.setFixedSize(480, 640)
        self.oldPos = self.pos()
        self.current_user = None

        self.titleBar = QWidget(self)
        self.titleBar.setFixedHeight(30)
        self.titleBar.setStyleSheet("background-color: #060709;")

        self.titleLabel = QLabel("    MAT Version Control Software", self.titleBar)
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
        titleLayout.setSpacing(0)
        titleLayout.addWidget(self.titleLabel)
        titleLayout.addStretch()
        titleLayout.addWidget(self.minBtn)
        titleLayout.addWidget(self.maxBtn)
        titleLayout.addWidget(self.closeBtn)
        self.titleBar.setLayout(titleLayout)

        self.main_container = QWidget()
        self.main_v_layout = QVBoxLayout(self.main_container)
        self.main_v_layout.setContentsMargins(0, 0, 0, 0)
        self.main_v_layout.setSpacing(0)
        self.main_v_layout.addWidget(self.titleBar)

        self.Stack = QStackedWidget()
        self.main_v_layout.addWidget(self.Stack)

        self.login_page = LoginPage(self.show_dashboard)
        self.dashboard_page = None
        self.repo_page = None

        self.Stack.addWidget(self.login_page)
        self.Stack.setCurrentWidget(self.login_page)

        self.setCentralWidget(self.main_container)

        self.titleBar.mousePressEvent = self.startMove
        self.titleBar.mouseMoveEvent = self.doMove

    def show_dashboard(self, user):
        self.hide()
        self.current_user = user
        self.setFixedSize(1440, 810)

        screen_geo = self.screen().availableGeometry().center()
        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(screen_geo)
        self.move(frame_geo.topLeft())

        if not self.dashboard_page:
            self.dashboard_page = DashboardPage(user, self.show_repos, self.logout)
            self.Stack.addWidget(self.dashboard_page)

        self.Stack.setCurrentWidget(self.dashboard_page)
        self.show()

    def show_repos(self, repo_name):
        pixmap = self.dashboard_page.get_pfp_pixmap() if self.dashboard_page else None

        if self.repo_page:
            self.Stack.removeWidget(self.repo_page)
            self.repo_page.deleteLater()

        self.repo_page = RepoPage(
            self.current_user,
            repo_name,
            self.back_to_dashboard,
            self.logout,
            pfp_pixmap=pixmap
        )

        self.Stack.addWidget(self.repo_page)
        self.Stack.setCurrentWidget(self.repo_page)

    def back_to_dashboard(self):
        self.Stack.setCurrentWidget(self.dashboard_page)
        if self.repo_page:
            self.Stack.removeWidget(self.repo_page)
            self.repo_page.deleteLater()
            self.repo_page = None

    def logout(self):
        self.hide()
        if self.current_user:
            self.current_user.loginStatus = False
            self.current_user = None

        if self.dashboard_page:
            self.Stack.removeWidget(self.dashboard_page)
            self.dashboard_page.deleteLater()
            self.dashboard_page = None

        if self.repo_page:
            self.Stack.removeWidget(self.repo_page)
            self.repo_page.deleteLater()
            self.repo_page = None

        self.setFixedSize(480, 640)
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        self.Stack.setCurrentWidget(self.login_page)
        self.show()

    def toggleMaximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def startMove(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def doMove(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()