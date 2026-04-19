from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
import client_api

class ManageUsersDialog(QDialog):
    def __init__(self, repo_obj, parent=None):
        super().__init__(parent)
        self.repo_obj = repo_obj
        self.setWindowTitle(f"Manage Users: {repo_obj.title}")
        self.setMinimumSize(500, 500)
        self.setStyleSheet("background-color: #151719; color: #b9c2c9;")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Members of {repo_obj.title}:"))

        self.user_list = QListWidget()
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
        self.user_list.setStyleSheet(f"background: #0d1115; border: 1px solid #30363d; {SCROLLBAR_STYLE}")
        self.user_list.itemSelectionChanged.connect(self.update_button_states)
        layout.addWidget(self.user_list)

        btn_ctrl_layout = QHBoxLayout()

        self.change_role_btn = QPushButton("Change Role")
        self.change_role_btn.setStyleSheet("background: #30363d; color: white; padding: 6px;")
        self.change_role_btn.clicked.connect(self.change_user_role)

        self.remove_user_btn = QPushButton("Remove User")
        self.remove_user_btn.setStyleSheet("background: #da3633; color: white; padding: 6px; font-weight: bold;")
        self.remove_user_btn.clicked.connect(self.remove_user)

        btn_ctrl_layout.addWidget(self.change_role_btn)
        btn_ctrl_layout.addWidget(self.remove_user_btn)
        layout.addLayout(btn_ctrl_layout)

        self.refresh_list()
        """
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background: #393E42; color: white; padding: 8px; font-weight: bold; margin-top: 10px;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        """

    def refresh_list(self):
        self.user_list.clear()
        memberships = client_api.getRepoMembers_Client(self.repo_obj.id)

        if not memberships:
            print("No members found or error occurred.")
            return

        for m in memberships:
            # Create the label
            item = QListWidgetItem(f"{m.username} — [{m.role}]")

            # KEY CHANGE: Store the entire Map object 'm' into UserRole
            # This contains id, username, and role
            item.setData(Qt.ItemDataRole.UserRole, m)

            if m.role == "Admin":
                item.setForeground(Qt.GlobalColor.yellow)
            if m.role == "Removed":
                item.setForeground(Qt.GlobalColor.gray)
                item.setBackground(Qt.GlobalColor.black)
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
        if not current_item:
            return

        member_data = current_item.data(Qt.ItemDataRole.UserRole)
        m_id = member_data.get('id')
        username = member_data.get('username')

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to remove {username}?"
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # We reuse the exact same API call, just passing "Removed" as the role
            success = client_api.updateMemberRole_Client(m_id, "Removed")

            if success:
                self.refresh_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to remove user.")

    def change_user_role(self):
        current_item = self.user_list.currentItem()
        if not current_item:
            return
        member_data = current_item.data(Qt.ItemDataRole.UserRole)

        # Now member_data is a Map, so .get() works
        m_id = member_data.get('id')
        username = member_data.get('username')
        current_role = member_data.get('role')

        print(f"DEBUG: m_id={m_id}, user={username}, role={current_role}")

        if not m_id:
            print("CRITICAL: m_id is missing from member_data!")
            return

        # 2. Show the Input Dialog
        roles = ["Admin", "Reviewer", "Author", "Guest"]

        try:
            # Handle case where current_role might be a Map() if missing
            start_role = str(current_role) if current_role else "Guest"
            start_index = roles.index(start_role)
        except (ValueError, KeyError):
            start_index = 0

        new_role, ok = QInputDialog.getItem(
            self, "Change Role",
            f"New Role for {username}:",
            roles, start_index, False
        )

        # 3. Call the Server
        if ok and new_role and new_role != current_role:
            success = client_api.updateMemberRole_Client(m_id, new_role)
            if success:
                # Check if this method exists on 'self'
                if hasattr(self, 'refresh_list'):
                    self.refresh_list()
                elif hasattr(self, 'load_members'):  # Common alternative name
                    self.load_members()
            else:
                QMessageBox.critical(self, "Error", "Failed to update role on server.")


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add User")
        self.setFixedSize(320, 180)
        self.setStyleSheet("background-color: #151719; color: #b9c2c9;")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("background: #0d1115; border: 1px solid #30363d; padding: 5px; color: white;")
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Reviewer", "Author", "Guest"])
        self.role_combo.setCurrentIndex(3)
        self.role_combo.setStyleSheet("background: #0d1115; border: 1px solid #30363d; color: white;")
        layout.addWidget(self.role_combo)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet("background: #238636; color: white; font-weight: bold; padding: 6px;")
        self.add_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)
    def get_data(self):
        return self.username_input.text().strip(), self.role_combo.currentText()