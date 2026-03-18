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
## USER INPUT -----------------------------------------------------
def uiUserInputPrompt(inputWrittenText):
    print(inputWrittenText)
    print("    -> ", end="")
    UserInput = input()
    clearConsole()
    return UserInput