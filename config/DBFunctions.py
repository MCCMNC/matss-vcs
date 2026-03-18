import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog



def getProjectByID(inputProjectID):
    return Project.objects.get(pk=inputProjectID)

def getProjectByVersionFile(inputVersionFile):
    returnedProject = inputVersionFile.version.project
    # Potential issue: inputVersionFile may be None or not linked to a version/project

    return returnedProject

def getUserProjects(user):
    projects = Project.objects.filter(owner=user) #ISSUE : ONLY FILTERS FOR OWNER

    # Potential issue: if user is None or not a valid User instance, this will return an empty queryset
    return projects


def getProjectVersionsByProjectID(inputProjectId):
    return ProjectVersion.objects.filter(project_id=inputProjectId)

def getProjectVersionSpecificByVersionFile(inputVersionFile):
    return ProjectVersion.objects.get(pk = getProjectByVersionFile(inputVersionFile.version).pk)

def getALlProjectFiles(inputProjectId):
    return VersionFile.objects.filter(version__id__in=getProjectVersionsByProjectID(inputProjectId))



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
        details=f"ADDED {inputProject.title} to DB"
    )

def addProjectToDB(inputTitle, inputDescription, inputOwner):
    currentProject, _ = Project.objects.get_or_create(
        title=inputTitle,
        defaults={
            "description": inputDescription,
            "owner": inputOwner
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

def addNextProjectVersionToDB(inputProject, inputAuthor, inputMessage):
    latest = (
        ProjectVersion.objects
        .filter(project_id=inputProject.pk)
        .order_by("-version_number")
        .first()
    )
    # Potential issue: inputProject may be None → query will fail
    nextVersion = 1 if not latest else latest.version_number + 1
    currentVersion, _ = ProjectVersion.objects.get_or_create(
        project=inputProject,
        version_number=nextVersion,
        defaults={
            "author": inputAuthor,
            "message": inputMessage
        }
    )
    # Potential issue: race condition → duplicate version numbers possible
    logCreateProjectVersion(inputAuthor,inputProject,currentVersion)

def logCreateVersionFile(inputUser,inputProjectVersionFile):
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = getProjectByVersionFile(inputProjectVersionFile).pk,
        action="CREATE_VERSION_FILE",
        details=f"ADDED {inputProjectVersionFile.path} to "
                f"{getProjectByVersionFile(inputProjectVersionFile).title} "
                f"Version {inputProjectVersionFile.version.version_number}"
    )

def addFileToDB(inputUser,inputVersion, inputPath, inputContent): ##PATHS SHOULD NOT COLLIDE
    currentVersionFile , _= VersionFile.objects.get_or_create(
        version_id = inputVersion.id,
        path = inputPath,
        content = inputContent
    )
    logCreateVersionFile(inputUser,currentVersionFile)
    # Potential issue: UNIQUE constraint on (version, path)

def logRemoveVersionFile(inputUser,inputProjectVersionFile):
    AuditLog.objects.get_or_create(
        user_id = inputUser.pk,
        project_id = getProjectByVersionFile(inputProjectVersionFile).pk,
        action = "REMOVE_VERSION_FILE",
        details = f"REMOVED {inputProjectVersionFile.path} FROM DB"
    )
def removeFIleFromDB(inputUser,inputFilePath):
    toBeDeletedFile = VersionFile.objects.get(path=inputFilePath)
    logRemoveVersionFile(inputUser,toBeDeletedFile)

def approveProjectVersion(inputVersion, inputUser, inputProjectID):
    if inputVersion.status != "Approved":
        inputVersion.status = "Approved"
        inputVersion.save()
        # Potential issue: inputVersion may be None or unsaved
    returnedLog, _ = AuditLog.objects.get_or_create(
        user = inputUser,
        project_id = inputProjectID,
        action = "APPROVE_VERSION",
        details = f"{Project.objects.get(pk=inputProjectID).title} v{inputVersion.version_number} approved"
    )
