from DBFunctions import *
import os
import django
import PyQt6
from PyQt6.QtWidgets import QMessageBox
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

def guiUserLogin(inputUsername,inputPassword):
    potentialUser = User.objects.filter(username = inputUsername).first() # Potential issue: if the username does not exist, potentialUser will be None
    if potentialUser is None or potentialUser.password_hash != inputPassword:
        return None
    userLogIn(potentialUser)
    return potentialUser

def auditLogToText(entry):
    return f" {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} → {entry.action} ({entry.project.title})"
def auditLogToTextExtended(entry):
    return f" {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} → {entry.user.username} {entry.action} ({entry.project.title})"
def auditLogToTextExpanded(entry):
    return f" {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} → {entry.user.username} {entry.action} ({entry.project.title} {entry.details})"
def guiErrorBox(parent,inputErrorStr):
    msg = QMessageBox(parent)
    msg.setWindowTitle("Error")
    msg.setText("MAT VCS ran into an "+inputErrorStr+" Error")
    msg.exec()