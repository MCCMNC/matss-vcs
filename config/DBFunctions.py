import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog, Repository

def getUserAuditLogs(inputUserID):
        # Potential issue: no logs for a user → empty queryset
    return AuditLog.objects.filter(user_id=inputUserID).order_by("timestamp")
def getProjectAuditLogs(inputProjectID):
        # Potential issue: no logs for a project → empty queryset
    return AuditLog.objects.filter(project_id=inputProjectID).order_by("timestamp")

def getProjectByID(inputProjectID):
    return Project.objects.get(pk=inputProjectID)

def getProjectByVersionFile(inputVersion):
    return inputVersion.project

def getUserProjects(user):
    projects = Project.objects.filter(owner=user) #ISSUE : ONLY FILTERS FOR OWNER

    # Potential issue: if user is None or not a valid User instance, this will return an empty queryset
    return projects

def getProjectVersionAuditLogsByID(inputProjectVersionID):
    try:
        # Force integer conversion to prevent type mismatch
        version_id = int(inputProjectVersionID)
        # Use the FK field name (usually fieldname_id in Django)
        return AuditLog.objects.filter(project_version_id=version_id).order_by("timestamp")
    except (ValueError, TypeError):
        return []
def getProjectVersionsByProjectID(inputProjectId):
    return ProjectVersion.objects.filter(project_id=inputProjectId)

def getProjectVersionSpecificByVersionFile(inputVersionFile):
    return ProjectVersion.objects.get(pk = getProjectByVersionFile(inputVersionFile.version).pk)

def getALlProjectFilesByProjectID(inputProjectId):
    return VersionFile.objects.filter(version__id__in=getProjectVersionsByProjectID(inputProjectId))


def getProjectVersionFilesByProjectVersionID(inputVersionID):
    try:
        # 1. Get the specific version
        version = ProjectVersion.objects.get(id=inputVersionID)

        # 2. Return all linked files via the ManyToMany relationship
        # 'version_files' is the related_name you defined in the model.
        # Use .all() to get the QuerySet
        return version.version_files.all()

    except ProjectVersion.DoesNotExist:
        print(f"Error: ProjectVersion {inputVersionID} not found.")
        return []
    except Exception as e:
        print(f"Database Error during fetch: {e}")
        return []

def getOrCreateUser(inputUsername, inputEmail, inputPasswordHash, inputRole):
    returnedUser, _ = User.objects.get_or_create(
        username=inputUsername,
        defaults={
            "email": inputEmail,
            "password_hash": inputPasswordHash,
            "role": inputRole,
        }
    )
    return returnedUser

def logCreateProject(inputUser,inputProject):
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = inputProject.pk,
        action="CREATE_PROJECT",
        details=f"ADDED {inputProject.title} to {inputProject.repository.title}"
    )

def addProjectToDB(inputTitle, inputDescription, inputOwner,inputRepo):
    currentProject, _ = Project.objects.get_or_create(
        title=inputTitle,
        defaults={
            "description": inputDescription,
            "owner": inputOwner,
            "repository" : inputRepo
        }
    )
    # Potential issue: title may not be unique → existing project may be reused
    logCreateProject(inputOwner,currentProject)

def logCreateProjectVersion(inputUser, inputProject, inputVersion):
    returnedLog, _ = AuditLog.objects.get_or_create(
        user=inputUser,
        project=inputProject,
        action="CREATE_VERSION",
        details=f"{inputProject.title} v{inputVersion.version_number} created"
    )
    # Potential issue: duplicate logs if uniqueness is not enforced


def addNextProjectVersionToDB(inputProject, inputAuthor, inputMessage, inputPath):
    # 1. Get the most recent version
    latest = (
        ProjectVersion.objects
        .filter(project_id=inputProject.pk)
        .order_by("-version_number")
        .first()
    )

    nextVersion = 1 if not latest else latest.version_number + 1

    # 2. Create the new version
    currentVersion, created = ProjectVersion.objects.get_or_create(
        project=inputProject,
        version_number=nextVersion,
        defaults={
            "path": inputPath,
            "author": inputAuthor,
            "message": inputMessage
        }
    )

    # 3. Inherit Many-to-Many relationships
    if latest:
        # We try 'files' first; if that fails, we check for 'version_files'
        # or the default Django 'projectversionfile_set'
        for attr in ['files', 'version_files', 'projectversionfile_set']:
            if hasattr(latest, attr):
                old_files = getattr(latest, attr).all()
                getattr(currentVersion, attr).add(*old_files)
                break
        else:
            print("Warning: No Many-to-Many relationship found on ProjectVersion.")

    logCreateProjectVersion(inputAuthor, inputProject, currentVersion)
    return currentVersion


def logCreateVersionFile(inputUser, inputProjectVersionFile, inputProjectVersion):
    # Get the project directly from the version provided
    project = inputProjectVersion.project

    AuditLog.objects.create(
        user_id=inputUser.pk,
        project_id=project.pk,
        project_version_id=inputProjectVersion.pk,
        action="CREATE_VERSION_FILE",
        details=(
            f"ADDED {inputProjectVersionFile.path} to "
            f"{project.title} Version {inputProjectVersion.version_number}"
        )
    )


def addVersionFileToDB(inputUser, inputVersion, inputPath, inputContent):
    # 1. get_or_create finds or makes the file entry (ID 18 in your screenshot)
    # Note: We don't pass the version here yet!
    version_file, created = VersionFile.objects.get_or_create(
        path=inputPath,
        content=inputContent
    )

    # 2. Add the relationship to the join table
    # This is what populates the 'versionfile_id' and 'projectversion_id' columns
    version_file.versions.add(inputVersion)

    # 3. Log the action using the explicit version context
    logCreateVersionFile(inputUser, version_file, inputVersion)

    return version_file

def logRemoveVersionFile(inputUser,inputProjectVersionFile):
    AuditLog.objects.get_or_create(
        user_id = inputUser.pk,
        project_id = getProjectByVersionFile(inputProjectVersionFile).pk,
        action = "REMOVE_VERSION_FILE",
        details = f"REMOVED {inputProjectVersionFile.path} FROM DB",
    )


def removeVersionFileFromDB(inputUser, inputFileObj, inputVersion):
    # 1. Get the project context from the version, not the file
    project = inputVersion.project

    # 2. Log the deletion BEFORE unlinking (so we still have the data for the log string)
    AuditLog.objects.create(
        user=inputUser,
        project=project,
        project_version=inputVersion,
        action="DELETE_VERSION_FILE",
        details=f"Removed {inputFileObj.path} from {project.title} v{inputVersion.version_number}"
    )

    # 3. Remove the Many-to-Many relationship (Unlink)
    # This removes the row from the join table but keeps the file in the VersionFile table
    inputFileObj.versions.remove(inputVersion)

    # 4. Optional: Clean up "orphaned" files that aren't linked to ANY version anymore
    if inputFileObj.versions.count() == 0:
        inputFileObj.delete()
def removeProjectFromDB():
    return "CURRENTLY UNIMPLEMENTED"
def removeProjectVersionFromDB():
    return "CURRENTLY UNIMPLEMENTED"

def userLogOut(inputUser):
    inputUser.loginStatus = False
    inputUser.save()

def userLogIn(inputUser):
    inputUser.loginStatus = True
    inputUser.save()

def approveProjectVersion(inputVersion, inputUser, inputProjectID):
    if inputVersion.status != "Approved":
        inputVersion.status = "Approved"
        inputVersion.save()
        # Potential issue: inputVersion may be None
    else : return 0
    createdLog, _ = AuditLog.objects.get_or_create(
        user = inputUser,
        project_id = inputProjectID,
        action = "APPROVE_VERSION",
        details = f"{Project.objects.get(pk=inputProjectID).title} v{inputVersion.version_number} approved"
    )
    return 1

def editVersionFileToVersion():
    return "CURRENTLY UNIMPLEMENTED"
def getAllRepos():
    return Repository.objects.all()
def getUserRepos(inputUser):
    # Potential issue: if user is None or not a valid User instance, this will return an empty queryset
    return Repository.objects.filter(project__owner=inputUser).distinct()
def getRepoProjectsByRepoName(repo_name):
    # This looks at the 'title' field of the related Repository model
    return Project.objects.filter(repository__title=repo_name)
def getRepoAuditLogsByRepoName(repo_name):
    # This reaches: AuditLog -> Project -> Repository -> title
    return AuditLog.objects.filter(
        project__repository__title__iexact=repo_name
    ).order_by('timestamp')
def getRepoByName(inputRepoName):
    return Repository.objects.get(title=inputRepoName)


def getVersionsByFileID(inputVersionFileID):
    try:
        # Use 'project__title' based on your error log
        queryset = ProjectVersion.objects.filter(
            version_files__id=inputVersionFileID
        ).values('id', 'version_number', 'project__title')

        return list(queryset)

    except Exception as e:
        print(f"Error fetching associations: {e}")
        return []

def getElementRelativePath(inputElement, inputType, inputContext=None):
    returnedString = "UNKNOWN ELEMENT"

    if inputType == "Repository":
        returnedString = inputElement.path

    elif inputType == "Project":
        returnedString = f"{inputElement.repository.path}/{inputElement.path}"

    elif inputType == "ProjectVersion":
        # Repo / Project
        returnedString = f"{inputElement.project.repository.path}/{inputElement.path}"

    elif inputType == "ProjectVersionFile":
        # Use the provided context (inputContext) if available,
        # otherwise fallback to the first linked version.
        v = inputContext if inputContext else inputElement.versions.first()

        if v:
            # Path logic: RepositoryPath / ProjectPath / FilePath
            # Note: We usually don't put the 'Version' folder name in the path
            # unless your OS file structure actually has version folders.
            returnedString = f"{v.project.repository.path}/{inputElement.path}"
        else:
            returnedString = f"ORPHANED/{inputElement.path}"

    return returnedString


def getVersionFileByPath(inputPath):
    """
    Returns a ProjectVersionFile object if the path exists in the DB,
    otherwise returns None.
    """
    try:
        # We search by the relative path since that is the unique identifier for the file entry
        return VersionFile.objects.filter(path=inputPath).first()
    except Exception as e:
        print(f"Error fetching version file by path: {e}")
        return None


def isFileLinkedToVersion(file_obj, version_obj):
    """
    Checks if a file is linked, trying all possible relationship names.
    """
    # List of possible attribute names for the Many-to-Many field
    possible_attrs = ['files', 'version_files', 'projectversionfile_set']

    for attr in possible_attrs:
        if hasattr(version_obj, attr):
            relationship = getattr(version_obj, attr)
            return relationship.filter(id=file_obj.id).exists()

    print(f"Error: No M2M relationship found on ProjectVersion using {possible_attrs}")
    return False


def linkExistingFileToVersion(file_obj, version_obj):
    """
    Links an existing file, trying all possible relationship names.
    """
    possible_attrs = ['files', 'version_files', 'projectversionfile_set']

    for attr in possible_attrs:
        if hasattr(version_obj, attr):
            relationship = getattr(version_obj, attr)
            relationship.add(file_obj)
            version_obj.save()
            return True

    print(f"Error: Could not link file. No M2M relationship found.")
    return False