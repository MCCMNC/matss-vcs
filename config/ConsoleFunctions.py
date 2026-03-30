from ConsoleUI import *
from DBFunctions import *
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

def consoleUserLogin(inputUser):
    printCharLine("*")
    localUserName = uiUserInputPrompt("Please enter your username:")
    localPassword = uiUserInputPrompt("Please enter your password:")
    potentialUser = User.objects.filter(username = localUserName).first()  # Potential issue: if the username does not exist, potentialUser will be None
    if potentialUser is None or potentialUser.password_hash != localPassword:
        uiError("Incorrect Login")
        printCharLine("*")
        return 0
    printCharLine("*")
    if inputUser != "dummyInput" : userLogOut(inputUser)
    userLogIn(potentialUser)
    return potentialUser

def consoleUserLogout(inputUser):
    inputUser.refresh_from_db()
    if inputUser.loginStatus:
        userLogOut(inputUser)
        uiParagraph("Successfully logged out from " + inputUser.username)
    elif not inputUser.loginStatus :
        uiParagraph("You are already logged out!")
    return "dummyInput"
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
        uiLogs(getProjectAuditLogs(currentProject))
## MENUS -----------------------------------------------------
basicUserMenu = ["Log out","File Manager"]
menuMap = {"basicUserMenu":basicUserMenu}
def consoleMenu(inputMenuType):
    print(inputMenuType)
    printCharLine("*")
    currentMenu = menuMap[inputMenuType]
    currentMenuLen = len(currentMenu)
    for i in range(currentMenuLen):
        print(currentMenu[i] + " : "+ str(i))
    currentUserInputInteger = 0
    while 1 :
        currentUserInput = uiUserInputPromptNoCLS("Pick an Action")
        if currentUserInput.isdigit():
            currentUserInputInteger = int(currentUserInput)
        else:
            uiError("Unexpected Input Type")
            continue
        if currentUserInputInteger < 0 or currentUserInputInteger >= currentMenuLen :
            uiError("Unexpected Input Value")
            continue
        return currentMenu[currentUserInputInteger]

def consoleFileManager(inputUser):
    while True:
        inputUser.refresh_from_db()
        if not inputUser.loginStatus:
            return "dummyInput"
        uiFileManagerMenu()
        userChoice = input("Select an option: ")
        if userChoice == "1": #List Projects
            clearConsole()
            consoleUserProjectList(inputUser)
        elif userChoice == "2": # List Project Versions of specific project - Approved
            clearConsole()
            currentProjectVersions = getProjectVersionsByProjectID((input("Enter Project ID :")))
            for cpv in currentProjectVersions:
                print(f"  Project Version Number: {cpv.version_number} | {cpv.created_at} | {cpv.message}")
        elif userChoice == "3": # List all Version Files associated with Project - Approved
            clearConsole()
            currentFiles = getALlProjectFilesByProjectID(input("Enter Project ID :"))
            for cpf in currentFiles:
                print(f"  Project Version Number: {cpf.version_id} | {cpf.created_at} | {cpf.content}")
        elif userChoice == "4": # List Audit Log
            consoleUserAuditLog(inputUser)
        elif userChoice == "5": # Add Project to DB
            clearConsole()
            addProjectToDB(input("Enter Project Title : "),input("Enter Project Description : "),inputUser)
            print("ADDED PROJECT TO DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "6": #Add Project Version DB
            clearConsole()
            addNextProjectVersionToDB(getProjectByID(input("Enter Project Id : ")), inputUser, input("Enter Version Message : "))
            print("ADDED PROJECT VERSION TO DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "7": # Add File to Project Version
            clearConsole()
            currentFilePath = input("Enter File Path: ")
            currentFileContent = input("Enter File Content: ")
            printedUserProjects = getUserProjects(inputUser)
            print("Projects:")
            for printedProject in printedUserProjects:
                print(f"  Project ID: {printedProject.pk} | Title: {printedProject.title}")
            printedProjectVersions = getProjectVersionsByProjectID((input("Enter Project ID :")))
            for printedProjectVersion in printedProjectVersions:
                print(f"Version Number: {printedProjectVersion.version_number}")
            currentProjectVersionSpecific = ProjectVersion.objects.get(version_number=input("Enter Project Version Number :"))
            addVersionFileToDB(inputUser, currentProjectVersionSpecific, currentFilePath, currentFileContent)
            print("ADDED FILE TO DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "8": # Remove File from DB
            clearConsole()
            removeVersionFileFromDB(inputUser, input("Enter File Path: "))
            print("REMOVED FILE FROM DB AND CREATED AUDIT LOG SUCCESSFULLY")
        elif userChoice == "9": # manage version approval
            clearConsole()
            if inputUser.role != "Author" and inputUser.role != "Admin":
                print("INVALID ROLE")
                continue
            consoleUserProjectList(inputUser)
            currentProjectID = input("Enter Project ID :")
            currentProjectVersions = getProjectVersionsByProjectID(currentProjectID)
            for currentProjectVersion in currentProjectVersions:
                uiProjectVersion(currentProjectVersion)
            currentInput = input("Please pick a version to approve ->")
            if approveProjectVersion(currentProjectVersions.get(version_number = currentInput),inputUser,currentProjectID) :
                print("APPROVED PROJECT VERSION AND CREATED AUDIT LOG SUCCESSFULLY")
            else : print("PROJECT VERSION ALREADY APPROVED")
        elif userChoice == "0": #WIPES THE ENTIRE DB EXCEPT FOR USER DATA
            clearConsole()
            if input("Are you sure you want to wipe the entire DB excluding user data? Y/N")=="Y":
                Project.objects.all().delete()
                ProjectVersion.objects.all().delete()
                VersionFile.objects.all().delete()
                AuditLog.objects.all().delete()
                print("WIPED DATABASE")
                quit(1000)
            else:
                print("Canceled database wipe")
                continue
        elif userChoice == "99": #Log User Out
            clearConsole()
            userLogOut(inputUser)
        else:
            print("Invalid choice")