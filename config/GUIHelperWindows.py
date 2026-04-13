from PyQt6 import *
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
from GUIFunctions import SCROLLBAR_STYLE
class ManageUsersDialog(QDialog):
    def __init__(self, repo_obj, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manage Users: {repo_obj.title}")
        self.setMinimumSize(400, 500)
        self.setStyleSheet("background-color: #151719; color: #b9c2c9;")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Members of {repo_obj.title}:"))

        self.user_list = QListWidget()
        self.user_list.setStyleSheet(f"background: #0d1115; border: 1px solid #30363d; {SCROLLBAR_STYLE}")
        layout.addWidget(self.user_list)

        self.refresh_list(repo_obj)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background: #393E42; color: white; padding: 8px; font-weight: bold;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def refresh_list(self, repo_obj):
        self.user_list.clear()
        from vcs_core.models import RepositoryMembership
        memberships = RepositoryMembership.objects.filter(repository_id=repo_obj.id)

        for m in memberships:
            # Format: "Username (Role)"
            item_text = f"{m.user.username} — [{m.repo_role}]"
            item = QListWidgetItem(item_text)
            item.setFont(QFont("Arial", 10))
            self.user_list.addItem(item)

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
