from GUI_interfaces.ProjectList import *
from GUIFunctions import *

from PyQt6.QtCore import QObject

from PyQt6.QtCore import QObject
from vcs_core.models import Project, AuditLog

class ProjectListController(QObject):
    def __init__(self, ui, user):
        super().__init__()

        self.ui = ui
        self.user = user

        self.load_projects()

    def load_projects(self):
        projects = Project.objects.filter(owner=self.user)

        for project in projects:
            button = self.ui.add_repository(project.name)

            button.clicked.connect(
                lambda checked=False, p=project: self.select_project(p)
            )

    def select_project(self, project):
        print(f"Selected: {project.name}")

        self.load_audit_log(project)

    def load_audit_log(self, project):
        logs = AuditLog.objects.filter(project=project).order_by("-timestamp")

        self.ui.audit_log.clear()

        for log in logs:
            text = f"{log.timestamp} - {log.action}"
            self.ui.audit_log.addItem(text)