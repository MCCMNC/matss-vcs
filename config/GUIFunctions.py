from ConsoleUI import *
from DBFunctions import *
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

def UserLogin(inputUser, localUserName, localPassword):
    potentialUser = User.objects.filter(username = localUserName).first()  # Potential issue: if the username does not exist, potentialUser will be None
    if potentialUser is None or potentialUser.password_hash != localPassword:
        #return to gui incorrect login credentials
        print("Incorrect login credentials")
        return 0
    if inputUser != "dummyInput" : userLogOut(inputUser)
    userLogIn(potentialUser)
    print("Logged in as" , potentialUser)
    return potentialUser

def UserLogout(inputUser):
    inputUser.refresh_from_db()
    if inputUser.loginStatus:
        userLogOut(inputUser)
        # return to gui Successfully logged out from " + inputUser.username
    elif not inputUser.loginStatus :
        # return to gui Already logged out
        print()
    return "dummyInput"

def UserAuditLog(inputUser):
    inputUserProjects = getUserProjects(inputUser)
    for currentProject in inputUserProjects:
        print(currentProject.title)
        uiLogs(getProjectAuditLogs(currentProject))
        AuditLog.objects.filter(project_id=currentProject).order_by("timestamp")