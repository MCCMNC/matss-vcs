import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog



def getProjectByID(inputProjectID):
    return Project.objects.get(pk=inputProjectID)


def getUserProjects(user):
    projects = Project.objects.filter(owner=user) #ISSUE : ONLY FILTERS FOR OWNER

    # Potential issue: if user is None or not a valid User instance, this will return an empty queryset
    return projects


def getProjectVersionsByProjectID(inputProjectId,approvalStatus):
    return ProjectVersion.objects.filter(project_id=inputProjectId,status=approvalStatus)


def getALlProjectFiles(inputProjectId):
    return VersionFile.objects.filter(version__id__in=getProjectVersionsByProjectID(inputProjectId,"Approved"))




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

def getOrCreateProject(inputTitle, inputDescription, inputOwner):
    returnedProject, _ = Project.objects.get_or_create(
        title=inputTitle,
        defaults={
            "description": inputDescription,
            "owner": inputOwner
        }
    )
    # Potential issue: title may not be unique → existing project may be reused

    return returnedProject


def getOrCreateNextVersion(inputProject, inputAuthor, inputMessage):
    latest = (
        ProjectVersion.objects
        .filter(project=inputProject)
        .order_by("-version_number")
        .first()
    )
    # Potential issue: inputProject may be None → query will fail

    nextVersion = 1 if not latest else latest.version_number + 1

    returnedVersion, _ = ProjectVersion.objects.get_or_create(
        project=inputProject,
        version_number=nextVersion,
        defaults={
            "author": inputAuthor,
            "message": inputMessage
        }
    )
    # Potential issue: race condition → duplicate version numbers possible

    return returnedVersion


def addFileToDB(inputVersion, inputPath, inputContent):
    VersionFile.objects.get_or_create(
        version_id=inputVersion.id,
        path=inputPath,
        content = inputContent
    )
    # Potential issue: UNIQUE constraint on (version, path)


def logCreateVersion(inputUser, inputProject, inputVersion):
    returnedLog, _ = AuditLog.objects.get_or_create(
        user=inputUser,
        project=inputProject,
        action="CREATE_VERSION",
        details=f"v{inputVersion.version_number} created"
    )
    # Potential issue: duplicate logs if uniqueness is not enforced

    return returnedLog


def approveVersion(inputVersion, inputUser, inputProject):
    if inputVersion.status != "Approved":
        inputVersion.status = "Approved"
        inputVersion.save()
        # Potential issue: inputVersion may be None or unsaved

    returnedLog, _ = AuditLog.objects.get_or_create(
        user=inputUser,
        project=inputProject,
        action="APPROVE_VERSION",
        details=f"v{inputVersion.version_number} approved"
    )

    return returnedLog