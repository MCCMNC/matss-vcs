import os
import wave
import numpy as np
import random
from PyQt6.QtCore import Qt, QFileInfo, QSize, QUrl, QTimer
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QFileIconProvider, QSlider, QInputDialog
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QBrush
from GUIFunctions import *
from DBFunctions import *
from GUI_FileItemWidget import FileItemWidget
from GUI_AudioSupport import AudioPlayerWidget, StaticWaveformWidget

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


class ProjectVersionPage(QWidget):
    def __init__(self, loginUser, inputProjectVersion, back_callback, logout_callback, pfp_pixmap=None):
        super().__init__()
        self.user = loginUser
        self.project_version = inputProjectVersion
        self.back_callback = back_callback
        self.logout_callback = logout_callback
        self.pfp_pixmap = pfp_pixmap
        self.is_expanded = False
        self.original_logs = []
        self._is_toggling = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"ProjectVersionPage {{ background-color: #0d0e0f; color: #b9c2c9; }} {SCROLLBAR_STYLE}")

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

        guiSetTopLabel(self, getElementRelativePath(self.project_version, "ProjectVersion"), 18)

        self.right_section = QWidget()
        self.right_section.setFixedWidth(350)
        right_layout = QHBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        guiAddLogoutButton(self, right_layout, self.handle_logout_click)

        top_bar_layout.addWidget(self.left_section)
        top_bar_layout.addWidget(self.page_title, 1)
        top_bar_layout.addWidget(self.right_section)
        self.main_layout.addWidget(top_bar_container)

        # -------------------- Middle Layout --------------------
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)

        guiSetAuditLog(self, "ProjectVersion")

        self.center_container = QWidget()
        center_v_layout = QVBoxLayout(self.center_container)
        center_v_layout.setContentsMargins(0, 10, 0, 10)
        center_v_layout.setSpacing(10)
        center_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        version_box = QWidget()
        version_v = QVBoxLayout(version_box)
        version_v.setContentsMargins(0, 0, 0, 0)

        self.versionFileList = QListWidget()
        self.versionFileList.setMinimumSize(500, 400)
        self.versionFileList.setMouseTracking(True)
        self.versionFileList.setAcceptDrops(True)
        self.versionFileList.installEventFilter(self)
        self.versionFileList.setStyleSheet(
            f"""
            QListWidget {{ 
                border: 1px solid #0d1115; 
                background: rgba(255,255,255,0.02); 
                color: #dce1e6; 
                outline: none; 
            }} 
            QListWidget::item:hover, QListWidget::item:selected {{ background: transparent; }}
            QListWidget::item {{ padding: 0px; }}
            {SCROLLBAR_STYLE}
            """
        )

        version_v.addWidget(QLabel(f"List of Files for Version {self.project_version.version_number} :"))
        version_v.addWidget(self.versionFileList)
        center_v_layout.addWidget(version_box)

        self.back_btn = QPushButton("Go Back")
        self.back_btn.setFixedSize(120, 30)
        self.back_btn.setStyleSheet(
            "background: #151719; color: #b9c2c9; border: 1px solid #0d1115; font-weight: bold;")
        self.back_btn.clicked.connect(self.handle_back_click)
        center_v_layout.addWidget(self.back_btn)

        self.right_side_container = QWidget()
        self.right_side_container.setFixedWidth(350)
        right_side_layout = QVBoxLayout(self.right_side_container)
        right_side_layout.setContentsMargins(10, 10, 10, 10)
        right_side_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.audio_player = AudioPlayerWidget()
        self.audio_player.hide()
        right_side_layout.addWidget(self.audio_player)

        self.right_spacer = QWidget(self)
        self.right_spacer.setFixedWidth(0)

        self.middle_layout.addWidget(self.audit_container)
        self.middle_layout.addWidget(self.center_container, 1)
        self.middle_layout.addWidget(self.right_side_container)
        self.middle_layout.addWidget(self.right_spacer)

        self.main_layout.addLayout(self.middle_layout)

        self.refresh_file_list()
        formatWidget(self)

    # -------------------- Handlers --------------------

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.refresh_file_list()
            guiSetAuditLog(self, "ProjectVersion")
        except Exception as e:
            print(f"ProjectVersionPage refresh failed: {e}")

    def handle_back_click(self):
        if hasattr(self, 'audio_player'):
            self.audio_player.player.stop()
        self.back_callback()

    def handle_logout_click(self):
        if hasattr(self, 'audio_player'):
            self.audio_player.player.stop()
        self.logout_callback()

    def handle_file_open(self, file_obj):
        if not file_obj or not file_obj.path:
            return

        repo_path_raw = self.project_version.project.repository.path
        repo_root = os.path.normpath(os.path.abspath(repo_path_raw))
        full_path = os.path.join(repo_root, file_obj.path)

        audio_exts = ['.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a']

        if os.path.splitext(full_path)[1].lower() in audio_exts:
            if os.path.exists(full_path):
                self.audio_player.show()
                self.audio_player.load_file(full_path, os.path.basename(full_path))
            else:
                QMessageBox.warning(self, "Missing File", f"File not found:\n{full_path}")
        else:
            try:
                os.startfile(full_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def eventFilter(self, source, event):
        if source is self.versionFileList and event.type() == event.Type.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        if source is self.versionFileList and event.type() == event.Type.Drop:
            self.handle_file_drop(event)
            return True
        return super().eventFilter(source, event)

    def handle_file_drop(self, event):
        urls = event.mimeData().urls()
        files_added = False

        try:
            self.project_version.refresh_from_db()

            repo_path_raw = self.project_version.project.repository.path
            repo_root = os.path.normpath(os.path.abspath(repo_path_raw))
        except Exception as e:
            return

        for url in urls:
            abs_dropped_path = os.path.normpath(url.toLocalFile())

            if os.path.isfile(abs_dropped_path):
                try:
                    relative_path = os.path.relpath(abs_dropped_path, repo_root)
                    if relative_path.startswith(".."):
                        continue
                except ValueError:
                    continue
                existing_file = getVersionFileByPath(relative_path)

                if existing_file:
                    try:
                        already_linked = isFileLinkedToVersion(existing_file, self.project_version)
                    except Exception as e:
                        print(f"M2M Evaluation Error: {e}")
                        already_linked = False

                    if already_linked:
                        QMessageBox.information(self, "Duplicate", f"File is already in this version.")
                        continue

                    reply = QMessageBox.question(
                        self, "Link Existing File",
                        f"This file already exists in the database.\nWould you like to link it to this version?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        linkExistingFileToVersion(existing_file, self.project_version)
                        files_added = True
                        continue
                content_input, ok = QInputDialog.getMultiLineText(
                    self, "File Content", f"Description for {os.path.basename(abs_dropped_path)}:"
                )
                if ok:
                    addVersionFileToDB(self.user, self.project_version, relative_path, content_input)
                    files_added = True

        if files_added:
            self.refresh_file_list()
            guiSetAuditLog(self, "ProjectVersion")

        event.acceptProposedAction()

    def refresh_file_list(self):
        self.versionFileList.clear()
        self.projectVersionData = getProjectVersionFilesByProjectVersionID(self.project_version.id)

        if self.projectVersionData:
            file_icons = getItemIcons(self.projectVersionData, "ProjectVersionFile")

            for f, icon in zip(self.projectVersionData, file_icons):
                item = QListWidgetItem(self.versionFileList)
                item.setSizeHint(QSize(0, 40))
                custom_widget = FileItemWidget(f, icon, self, "ProjectVersionFile", self.project_version)
                self.versionFileList.addItem(item)
                self.versionFileList.setItemWidget(item, custom_widget)

    def handle_file_delete(self, file_obj):
        associated_versions = getVersionsByFileID(file_obj.id)
        version_links = []

        for ver in associated_versions:
            p_title = ver.get('project__title') or "Untitled Project"
            v_num = ver.get('version_number') or "Unknown"
            tag = " (Current)" if ver['id'] == self.project_version.id else ""
            version_links.append(f"• {p_title} - v{v_num}{tag}")

        association_text = "\n".join(version_links) if version_links else "No other associations found."
        message = (
            f"Remove link to: {file_obj.path}?\n\n"
            f"Linked versions:\n{association_text}\n\n"
            "This only removes the link from THIS version."
        )

        reply = QMessageBox.question(self, 'Confirm Removal', message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                removeVersionFileFromDB(self.user, file_obj, self.project_version)
                self.refresh_file_list()
                guiSetAuditLog(self, "ProjectVersion")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Removal failed: {e}")

    def handle_audit_toggle(self):
        try:
            if hasattr(self, 'audit_container'):
                guiExpandAuditLog(self, "ProjectVersion")
                if self.is_expanded and hasattr(self, 'audio_player'):
                    self.audio_player.player.stop()
                    self.audio_player.hide()
        except Exception as e:
            print(f"Audit Toggle Error: {e}")