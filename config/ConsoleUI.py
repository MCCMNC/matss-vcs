## BASIC UI -----------------------------------------------------
def clearConsole():
    print("\n" * 100)
def printCharLine(inputChar):
    print("\n" + inputChar * 50)
def uiError(inputErrorType):
    clearConsole()
    print("\n MAT VCS Ran into an " + inputErrorType + " Error")
## ADVANCED UI -----------------------------------------------------
def uiParagraph(inputWrittenText): ## Displays any line of text into the console window
    printCharLine("=")
    print(inputWrittenText)
    printCharLine("=")
def uiFiles(inputFiles): ## Displays data of any file array (or list) in the console window
    clearConsole()
    for f in inputFiles:
        print(f"  {f.path}")
        print(f"    → {f.content}")
def uiLogs(inputLogs): ## Displays data of any log array (or list) in the consol window
    clearConsole()
    for entry in inputLogs:
        print(f" [{entry.timestamp}] {entry.user.username} → {entry.action} ({entry.details})")
def uiProjectVersion(projectVersion):
    print(f" {projectVersion.created_at} ; {projectVersion.version_number} ; {projectVersion.status}")

def uiFileManagerMenu():
        print("\n--- File Manager Menu ---")
        print("1 : List projects")
        print("2 : List project versions of specific Project - Approved")
        print("3 : List ALL files associated with Project - Approved")
        print("4 : List Audit Log")
        print("5 : Add Project to DB")
        print("6 : Add Project Version to DB")
        print("7 : Add File to Project Version")
        print("8 : Remove File from DB")
        print("9 : Manage Project Version Approval")
        print("0 : WIPE DB (NOT INCLUDING USERS)")
        print("\n")
        print("99 : Log Out")

## USER INPUT -----------------------------------------------------
def uiUserInputPrompt(inputWrittenText):
    print(inputWrittenText)
    print("    -> ", end="")
    UserInput = input()
    clearConsole()
    return UserInput