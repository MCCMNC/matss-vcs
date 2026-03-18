from ConsoleFunctions import *
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog
mainFuncs = {"Log out":consoleUserLogout,
             "Project List":consoleUserProjectList,
             "Audit Log":consoleUserAuditLog,
             "File Manager":consoleFileManager
             }
localUser = consoleUserLogin()
if localUser == 0 :
    exit(500)
while True:
    mainFuncs[consoleMenu("basicUserMenu")](localUser)