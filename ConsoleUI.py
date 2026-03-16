def uiParagraph(writtenText):
    print("\n" + "=" * 50)
    print(writtenText)
    print("=" * 50)
def uiFiles(files):
    for f in files:
        print(f"  {f.path}")
        print(f"    → {f.content}")
def uiLogs(logs):
    for entry in logs:
        print(f"  [{entry.timestamp}] {entry.user.username} → {entry.action} ({entry.details})")