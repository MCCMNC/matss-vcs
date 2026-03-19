from ConsoleFunctions import *
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

User.objects.update(loginStatus=0)

mainFuncs = {"Log out":consoleUserLogout,
             "File Manager":consoleFileManager
             }
localUser = consoleUserLogin("dummyInput")
if localUser == 0 :
    exit(500)
while True:
    if localUser != "dummyInput" and localUser != 0 :
        uiParagraph("You are currently logged in as : " + localUser.username)
        localUser = mainFuncs[consoleMenu("basicUserMenu")](localUser)
    else : localUser = consoleUserLogin("dummyInput")