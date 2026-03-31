import os
from PyQt6.QtCore import Qt, QFileInfo, QSize
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem,
    QMessageBox, QFileIconProvider
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


class DashboardPage(QWidget):
    def __init__(self, loginUser, on_repo_selected, on_logout):
        super().__init__()
        self.user = loginUser
        self.on_repo_selected = on_repo_selected
        self.on_logout = on_logout
        self.is_expanded = False
        self.original_logs = []
        self.cached_pixmap = None
        self._is_toggling = False

        # --- Enable Drag and Drop ---
        self.setAcceptDrops(True)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"DashboardPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

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

        BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
        pfp_path = os.path.join(BASE_DIR, "Assets", "Poet Cover 3.png")
        raw_pixmap = QPixmap(pfp_path)
        if not raw_pixmap.isNull():
            self.cached_pixmap = raw_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.FastTransformation)
            self.pfp.setIcon(QIcon(self.cached_pixmap))
            self.pfp.setIconSize(self.pfp.size())

        self.user_label = QLabel(self.user.username)
        self.user_label.setFont(QFont("Arial", 12))
        left_layout.addWidget(self.pfp)
        left_layout.addWidget(self.user_label)

        guiSetTopLabel(self, "Dashboard", 24)

        self.right_section = QWidget()
        self.right_section.setFixedWidth(350)
        right_layout = QHBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        guiAddLogoutButton(self, right_layout, self.on_logout)

        top_bar_layout.addWidget(self.left_section)
        top_bar_layout.addWidget(self.page_title, 1)
        top_bar_layout.addWidget(self.right_section)
        self.main_layout.addWidget(top_bar_container)

        # -------------------- Middle Layout --------------------
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)

        guiSetAuditLog(self, "Dashboard")

        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        center_v_layout.setSpacing(10)
        center_v_layout.setContentsMargins(0, 10, 0, 10)

        repo_box = QWidget()
        repo_v = QVBoxLayout(repo_box)
        repo_v.setContentsMargins(0, 0, 0, 0)

        self.repo_list = QListWidget()
        self.repo_list.setMinimumSize(500, 400)
        self.repo_list.setMouseTracking(True)
        self.repo_list.setStyleSheet(
            f"""
                    QListWidget {{ 
                        border: none;  /* Changed from 2px dashed #30363d */
                        background: rgba(255,255,255,0.02); 
                        color: #dce1e6; 
                        outline: none; 
                        border-radius: 10px;
                    }} 
                    QListWidget::item:hover, QListWidget::item:selected {{ 
                        background: transparent; 
                    }}
                    {SCROLLBAR_STYLE}
                    """
        )
        repo_v.addWidget(QLabel("List of Repositories :"))
        repo_v.addWidget(self.repo_list)
        center_v_layout.addWidget(repo_box)

        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(350)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_spacer)
        self.main_layout.addLayout(self.middle_layout)

        formatWidget(self)

    # -------------------- Drag & Drop Logic --------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Visual feedback
            self.repo_list.setStyleSheet(self.repo_list.styleSheet().replace("#30363d", "#58a6ff"))
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.repo_list.setStyleSheet(self.repo_list.styleSheet().replace("#58a6ff", "#30363d"))

    def dropEvent(self, event):
        self.repo_list.setStyleSheet(self.repo_list.styleSheet().replace("#58a6ff", "#30363d"))

        for url in event.mimeData().urls():
            folder_path = url.toLocalFile()
            if os.path.isdir(folder_path):
                repo_name = os.path.basename(folder_path)

                confirm = QMessageBox.question(
                    self, "Initialize Repository",
                    f"Create new repository '{repo_name}' from this folder?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if confirm == QMessageBox.StandardButton.Yes:
                    if createRepositoryInDB(self.user, repo_name, folder_path):
                        self.refresh_repo_list()
                        guiSetAuditLog(self, "Dashboard")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to create repository record.")
            else:
                QMessageBox.warning(self, "Invalid Drop", "Only folders can be initialized as repositories.")

    # -------------------- UI Management --------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.repo_list.clearSelection()
        try:
            guiSetAuditLog(self, "Dashboard")
            self.refresh_repo_list()
        except Exception as e:
            print(f"Dashboard refresh failed: {e}")

    def refresh_repo_list(self):
        self.repo_list.clear()
        repos = getUserRepos(self.user)
        repo_icons = getItemIcons(repos, "Repository")

        for repo, icon in zip(repos, repo_icons):
            item = QListWidgetItem(self.repo_list)
            item.setSizeHint(QSize(0, 40))
            custom_widget = FileItemWidget(repo, icon, self, context_type="Repository")
            self.repo_list.addItem(item)
            self.repo_list.setItemWidget(item, custom_widget)

    def handle_delete(self, repo_obj):
        """Action triggered by the red Delete button in FileItemWidget"""
        if not repo_obj:
            return

        # 1. Double-check with the user
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the repository '{repo_obj.title}'?\n\n"
            "This will remove all associated projects, versions, and logs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # 2. Call DB logic
            success = removeRepositoryFromDB(self.user, repo_obj)

            if success:
                # 3. Refresh the UI
                self.refresh_repo_list()
                guiSetAuditLog(self, "Dashboard")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete repository from database.")
    def handle_follow(self, repo_obj):
        if repo_obj:
            self.on_repo_selected(repo_obj)

    def handle_audit_toggle(self):
        guiExpandAuditLog(self, "Dashboard")

    def get_pfp_pixmap(self):
        return self.cached_pixmap