from ConsoleUI import *
from DBFunctions import *
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

def consoleUserLogin():
    printCharLine("*")
    localUserName = uiUserInputPrompt("Please enter your username:")
    localPassword = uiUserInputPrompt("Please enter your password:")

    potentialUser = User.objects.filter(
        username = localUserName).first()  # Potential issue: if the username does not exist, potentialUser will be None

    if potentialUser is None or potentialUser.password_hash != localPassword:
        uiError("Incorrect Login")
        printCharLine("*")
        return 0
    printCharLine("*")
    return potentialUser

def consoleUserLogout(inputUser):
    uiParagraph("Successfully logged out from " + inputUser.username)

def consoleUserProjectList(inputUser):
    printCharLine("*")
    # Projects owned by the user
    owned_projects = Project.objects.filter(owner=inputUser)

    # Projects where the user created versions
    worked_projects = Project.objects.filter(
        projectversion__author=inputUser
    ).distinct()
    # Potential issue: if relations are misnamed in the model, this query will fail

    print("\nProjects owned by user:")
    for project in owned_projects:
        print("->"+project.title + "   ID : " + str(project.pk))

    print("\nProjects contributed to:")
    for project in worked_projects:
        print("->"+project.title + "   ID : " + str(project.pk))
    printCharLine("*")

def consoleUserAuditLog(inputUser):
    inputUserProjects = getUserProjects(inputUser)

    for currentProject in inputUserProjects:
        print(currentProject.title)

        logs = AuditLog.objects.filter(project=currentProject).order_by("timestamp")
        # Potential issue: no logs for a project → empty queryset

        uiLogs(logs)
## MENUS -----------------------------------------------------
basicUserMenu = ["Log out", "Project List", "Audit Log","File Manager"]
menuMap = {"basicUserMenu":basicUserMenu}
def consoleMenu(inputMenuType):
    currentMenu = menuMap[inputMenuType]
    for i in range(len(currentMenu)):
        print(currentMenu[i] + " : "+ str(i))
    return currentMenu[int(uiUserInputPrompt("Pick an Action"))]

def consoleFileManager(inputUser): ##NEXT STEP HERE
    while True:
        print("\n--- File Manager Menu ---")
        print("1 : List projects")
        print("2 : List project versions of specific Project - Approved")
        print("3 : List ALL files associated with Project - Approved")
        print("4 : List Audit Log")
        print("5 : Add Project to DB")
        print("6 : Add Project Version to DB")
        print("7 : Add File to Project Version")
        print("8 : Remove File from DB")
        print("0 : WIPE DB (NOT INCLUDING USERS)")
        userChoice = input("Select an option: ")

        if userChoice == "1": #List Projects
            clearConsole()
            consoleUserProjectList(inputUser)
        elif userChoice == "2": # List Project Versions of specific project - Approved
            clearConsole()
            currentProjectVersions = getProjectVersionsByProjectID((input("Enter Project ID :")),"Approved")
            for cpv in currentProjectVersions:
                print(f"  Project Version Number: {cpv.version_number} | {cpv.created_at} | {cpv.message}")
        elif userChoice == "3": # List all Version Files associated with Project - Approved
            clearConsole()
            currentFiles = getALlProjectFiles(input("Enter Project ID :"))
            for cpf in currentFiles:
                print(f"  Project Version Number: {cpf.version_id} | {cpf.created_at} | {cpf.content}")
        elif userChoice == "4": # List Audit Log
            consoleUserAuditLog(inputUser)
        elif userChoice == "5": # Add Project to DB
            clearConsole()
            addProjectToDB(input("Enter Project Title : "),input("Enter Project Description : "),inputUser)
            print("ADDED PROJECT TO DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "6":
            clearConsole()
            addNextProjectVersionToDB(getProjectByID(input("Enter Project Id : ")), inputUser, input("Enter Version Message : "))
            print("ADDED PROJECT VERSION TO DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "7":
            clearConsole()
            currentFilePath = input("Enter File Path: ")
            currentFileContent = input("Enter File Content: ")
            printedUserProjects = getUserProjects(inputUser)
            print("Projects:")
            for printedProject in printedUserProjects:
                print(f"  Project ID: {printedProject.pk} | Title: {printedProject.title}")
            printedProjectVersions = getProjectVersionsByProjectID((input("Enter Project ID :")),"Approved")
            for printedProjectVersion in printedProjectVersions:
                print(f"Version Number: {printedProjectVersion.version_number}")
            currentProjectVersionSpecific = ProjectVersion.objects.get(version_number=input("Enter Project Version Number :"))
            addFileToDB(inputUser,currentProjectVersionSpecific, currentFilePath, currentFileContent)
            print("ADDED FILE TO DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "8":
            clearConsole()
            removeFIleFromDB(inputUser,input("Enter File Path: "))
            print("REMOVED FILE FROM DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "0": #WIPES THE ENTIRE DB
            clearConsole()
            Project.objects.all().delete()
            ProjectVersion.objects.all().delete()
            VersionFile.objects.all().delete()
            AuditLog.objects.all().delete()
            print("WIPED DATABASE")
            quit(1000)
        else:
            print("Invalid choice")