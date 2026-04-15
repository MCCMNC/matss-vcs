import os
import django
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *

# --- DJANGO SETUP ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    django.setup()
except Exception:
    pass

from GUIFunctions import SCROLLBAR_STYLE


class ManageUsersDialog(QDialog):
    def __init__(self, repo_obj, parent=None):
        super().__init__(parent)
        self.repo_obj = repo_obj
        self.setWindowTitle(f"Управление на потребители: {repo_obj.title}")
        self.setMinimumSize(500, 500)
        self.setStyleSheet("background-color: #151719; color: #b9c2c9;")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Членове на {repo_obj.title}:"))

        self.user_list = QListWidget()
        self.user_list.setStyleSheet(f"background: #0d1115; border: 1px solid #30363d; {SCROLLBAR_STYLE}")
        self.user_list.itemSelectionChanged.connect(self.update_button_states)
        layout.addWidget(self.user_list)

        btn_ctrl_layout = QHBoxLayout()

        self.change_role_btn = QPushButton("Смяна на роля")
        self.change_role_btn.setStyleSheet("background: #30363d; color: white; padding: 6px;")
        self.change_role_btn.clicked.connect(self.change_user_role)

        self.remove_user_btn = QPushButton("Премахни потребител")
        self.remove_user_btn.setStyleSheet("background: #da3633; color: white; padding: 6px; font-weight: bold;")
        self.remove_user_btn.clicked.connect(self.remove_user)

        btn_ctrl_layout.addWidget(self.change_role_btn)
        btn_ctrl_layout.addWidget(self.remove_user_btn)
        layout.addLayout(btn_ctrl_layout)

        self.refresh_list()

        close_btn = QPushButton("Затвори")
        close_btn.setStyleSheet("background: #393E42; color: white; padding: 8px; font-weight: bold; margin-top: 10px;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def refresh_list(self):
        self.user_list.clear()
        from vcs_core.models import RepositoryMembership
        # Използваме repository_id за стабилност при интегрирания сървър
        memberships = RepositoryMembership.objects.filter(repository_id=self.repo_obj.id).select_related('user')

        for m in memberships:
            item = QListWidgetItem(f"{m.user.username} — [{m.repo_role}]")
            item.setData(Qt.ItemDataRole.UserRole, m.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, m.repo_role)

            if m.repo_role == "Admin":
                item.setForeground(Qt.GlobalColor.yellow)

            item.setFont(QFont("Segoe UI", 10))
            self.user_list.addItem(item)

        self.update_button_states()

    def update_button_states(self):
        current_item = self.user_list.currentItem()
        if not current_item:
            self.change_role_btn.setEnabled(False)
            self.remove_user_btn.setEnabled(False)
            return

        role = current_item.data(Qt.ItemDataRole.UserRole + 1)
        is_admin = (role == "Admin")

        self.change_role_btn.setEnabled(not is_admin)
        self.remove_user_btn.setEnabled(not is_admin)

        if is_admin:
            self.remove_user_btn.setStyleSheet("background: #442726; color: #888; padding: 6px;")
        else:
            self.remove_user_btn.setStyleSheet("background: #da3633; color: white; padding: 6px; font-weight: bold;")

    def remove_user(self):
        current_item = self.user_list.currentItem()
        if not current_item: return

        membership_id = current_item.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(self, "Потвърждение", f"Премахване на {current_item.text()}?")

        if confirm == QMessageBox.StandardButton.Yes:
            from vcs_core.models import RepositoryMembership
            RepositoryMembership.objects.filter(id=membership_id).delete()
            self.refresh_list()

    def change_user_role(self):
        current_item = self.user_list.currentItem()
        if not current_item: return

        membership_id = current_item.data(Qt.ItemDataRole.UserRole)
        from vcs_core.models import RepositoryMembership
        membership = RepositoryMembership.objects.get(id=membership_id)

        roles = ["Admin", "Reviewer", "Author", "Guest"]
        new_role, ok = QInputDialog.getItem(self, "Промяна на роля",
                                            f"Нова роля за {membership.user.username}:",
                                            roles, roles.index(membership.repo_role), False)

        if ok and new_role:
            membership.repo_role = new_role
            membership.save()
            self.refresh_list()


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добави потребител")
        self.setFixedSize(320, 180)
        self.setStyleSheet("background-color: #151719; color: #b9c2c9;")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Потребителско име:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("background: #0d1115; border: 1px solid #30363d; padding: 5px; color: white;")
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Роля:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Reviewer", "Author", "Guest"])
        self.role_combo.setCurrentIndex(3)
        self.role_combo.setStyleSheet("background: #0d1115; border: 1px solid #30363d; color: white;")
        layout.addWidget(self.role_combo)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Добави")
        self.add_btn.setStyleSheet("background: #238636; color: white; font-weight: bold; padding: 6px;")
        self.add_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("Отказ")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.username_input.text().strip(), self.role_combo.currentText()