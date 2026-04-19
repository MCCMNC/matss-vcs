from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
import client_api


class ManageUsersDialog(QDialog):
    def __init__(self, repo_obj, parent=None):
        """
        Initializes the user management dialog, setting up the repository context and custom dark-themed styling.
        Configures the list widget and control buttons for modifying user roles or removing members.
        """
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

    def refresh_list(self):
        """
        Queries the server for the latest list of repository memberships and repopulates the list widget.
        Applies visual formatting such as yellow text for Admins and gray/black styling for removed users.
        """
        self.user_list.clear()
        # Fetch membership data from the client API
        memberships = client_api.getRepoMembers_Client(self.repo_obj.id)

        if not memberships:
            print("No members found or error occurred.")
            return

        for m in memberships:
            item = QListWidgetItem(f"{m.username} — [{m.role}]")

            # Store the full data object directly in the item for easy retrieval during callbacks
            item.setData(Qt.ItemDataRole.UserRole, m)

            # Apply role-specific color coding
            if m.role == "Admin":
                item.setForeground(Qt.GlobalColor.yellow)
            elif m.role == "Removed":
                item.setForeground(Qt.GlobalColor.gray)
                item.setBackground(Qt.GlobalColor.black)

            item.setFont(QFont("Segoe UI", 10))
            self.user_list.addItem(item)

        # Ensure UI controls reflect the newly loaded selection state
        self.update_button_states()

    def update_button_states(self):
        """
        Evaluates the currently selected user and toggles the availability of management buttons.
        Prevents modification or removal of Admin users to preserve repository ownership stability.
        """
        current_item = self.user_list.currentItem()
        if not current_item:
            self.change_role_btn.setEnabled(False)
            self.remove_user_btn.setEnabled(False)
            return

        # Check the role stored in the hidden data of the list item
        role = current_item.data(Qt.ItemDataRole.UserRole + 1)
        is_admin = (role == "Admin")

        # Disable interaction if the target is an administrator
        self.change_role_btn.setEnabled(not is_admin)
        self.remove_user_btn.setEnabled(not is_admin)

        # Update button aesthetics to reflect disabled state
        if is_admin:
            self.remove_user_btn.setStyleSheet("background: #442726; color: #888; padding: 6px;")
        else:
            self.remove_user_btn.setStyleSheet("background: #da3633; color: white; padding: 6px; font-weight: bold;")

    def remove_user(self):
        """
        Triggers a confirmation prompt before initiating the user removal process via the API.
        Effectively "removes" a user by setting their repository role to the 'Removed' status.
        """
        current_item = self.user_list.currentItem()
        if not current_item:
            return

        member_data = current_item.data(Qt.ItemDataRole.UserRole)
        m_id = member_data.get('id')
        username = member_data.get('username')

        # Safety prompt to avoid accidental deletions
        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to remove {username}?"
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # Update the user to 'Removed' status on the backend
            success = client_api.updateMemberRole_Client(m_id, "Removed")
            if success:
                self.refresh_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to remove user.")

    def change_user_role(self):
        """
        Displays a selection dialog allowing an administrator to promote or demote a selected user.
        Communicates the new role to the server and refreshes the display upon a successful update.
        """
        current_item = self.user_list.currentItem()
        if not current_item:
            return

        member_data = current_item.data(Qt.ItemDataRole.UserRole)
        m_id = member_data.get('id')
        username = member_data.get('username')
        current_role = member_data.get('role')

        if not m_id:
            print("CRITICAL: m_id is missing from member_data!")
            return

        # Prepare the selection dialog with available role options
        roles = ["Admin", "Reviewer", "Author", "Guest"]
        try:
            start_role = str(current_role) if current_role else "Guest"
            start_index = roles.index(start_role)
        except (ValueError, KeyError):
            start_index = 0

        new_role, ok = QInputDialog.getItem(
            self, "Change Role",
            f"New Role for {username}:",
            roles, start_index, False
        )

        # If a new role is selected, update the server database
        if ok and new_role and new_role != current_role:
            success = client_api.updateMemberRole_Client(m_id, new_role)
            if success:
                self.refresh_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to update role on server.")


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        """
        Initializes the dialog for adding new members, providing inputs for both the username and the assigned role.
        Applies styling to match the main application's dark theme and provides standard Add/Cancel controls.
        """
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
        """
        Retrieves and sanitizes the user-provided username and the selected role from the dialog inputs.
        Returns the data as a tuple for use by the parent calling widget.
        """
        return self.username_input.text().strip(), self.role_combo.currentText()