import os
from datetime import timezone

import django
from django.db import transaction
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog, Repository, RepositoryMembership


def getUserAuditLogs(inputUserID):
    return AuditLog.objects.filter(user_id=inputUserID).order_by("timestamp")
def getProjectAuditLogs(inputProjectID):
    return AuditLog.objects.filter(project_id=inputProjectID).order_by("timestamp")

def getProjectByID(inputProjectID):
    return Project.objects.get(pk=inputProjectID)

def getProjectByVersionFile(inputVersion):
    return inputVersion.project

def getUserProjects(user):
    projects = Project.objects.filter(owner=user)
    return projects

def getProjectVersionAuditLogsByID(inputProjectVersionID):
    try:
        version_id = int(inputProjectVersionID)
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
        version = ProjectVersion.objects.get(id=inputVersionID)
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
        repository_id=inputProject.repository_id,
        action="CREATE_PROJECT",
        details=f"ADDED {inputProject.title} to {inputProject.repository.title}"
    )
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = inputProject.pk,
        repository_id=inputProject.repository_id,
        project_version_id = ProjectVersion.objects.filter(project_id=inputProject.pk).first().pk,
        action="CREATE_VERSION",
        details=f"ADDED INITIAL VERSION to {inputProject.title}"
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
    logCreateProject(inputOwner,currentProject)

def logCreateProjectVersion(inputUser, inputProject, inputVersion):
    returnedLog, _ = AuditLog.objects.get_or_create(
        user=inputUser,
        project=inputProject,
        action="CREATE_VERSION",
        details=f"{inputProject.title} v{inputVersion.version_number} created",
        project_version_id = inputVersion.pk
    )


def addNextProjectVersionToDB(inputProject, inputAuthor, inputMessage, inputPath):
    latest = (
        ProjectVersion.objects
        .filter(project_id=inputProject.pk)
        .order_by("-version_number")
        .first()
    )

    nextVersion = 1 if not latest else latest.version_number + 1
    currentVersion, created = ProjectVersion.objects.get_or_create(
        project=inputProject,
        version_number=nextVersion,
        defaults={
            "path": inputPath,
            "author": inputAuthor,
            "message": inputMessage
        }
    )
    if latest:
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
    project = inputProjectVersion.project

    AuditLog.objects.create(
        user_id=inputUser.pk,
        project_id=project.pk,
        project_version_id=inputProjectVersion.pk,
        repository_id=inputProjectVersion.project.repository_id,
        action="CREATE_VERSION_FILE",
        details=(
            f"ADDED {inputProjectVersionFile.path} to "
            f"{project.title} Version {inputProjectVersion.version_number}"
        )
    )


def addVersionFileToDB(inputUser, inputVersion, inputPath, inputContent):
    version_file, created = VersionFile.objects.get_or_create(
        path=inputPath,
        content=inputContent
    )
    version_file.versions.add(inputVersion)
    logCreateVersionFile(inputUser, version_file, inputVersion)

    return version_file

def logRemoveVersionFile(inputUser,inputProjectVersionFile):
    AuditLog.objects.get_or_create(
        user_id = inputUser.pk,
        project_id = getProjectByVersionFile(inputProjectVersionFile).pk,
        repository_id = inputProjectVersionFile.versions.first().project.repository_id,
        action = "REMOVE_VERSION_FILE",
        details = f"REMOVED {inputProjectVersionFile.path} FROM DB",
    )


def removeVersionFileFromDB(inputUser, inputFileObj, inputVersion):
    project = inputVersion.project
    AuditLog.objects.create(
        user=inputUser,
        project=project,
        project_version=inputVersion,
        repository_id=inputVersion.project.repository_id,
        action="DELETE_VERSION_FILE",
        details=f"Removed {inputFileObj.path} from {project.title} v{inputVersion.version_number}"
    )
    inputFileObj.versions.remove(inputVersion)
    if inputFileObj.versions.count() == 0:
        inputFileObj.delete()
def logRemoveProject(inputUser, inputProject):
    AuditLog.objects.create(
        user = inputUser,
        repository_id = inputProject.repository_id,
        action = "REMOVE_PROJECT",
        details = f"REMOVED Project '{inputProject.title}' and all associated versions from database"
    )
def deleteAllProjectAuditLogs(project_obj):
    AuditLog.objects.filter(project_id=project_obj.pk).delete()
def removeProjectFromDB(user, project_obj, deletingRepo=False):
    try:
        with transaction.atomic():
            AuditLog.objects.filter(project_id=project_obj.pk).delete()
            if deletingRepo :
                print("deleting repo")
                AuditLog.objects.filter(repository_id=project_obj.repository_id, project__isnull=True).update(repository=None)
                AuditLog.objects.filter(repository_id=project_obj.repository_id,project__isnull=True).delete()
            else : logRemoveProject(user, project_obj)
            versions = ProjectVersion.objects.filter(project=project_obj)
            for version in versions:
                removeProjectVersionFromDB(user, version, deletingProject=True)
            project_obj.delete()
            return True
    except Exception as e:
        print(f"Critical error during project deletion: {e}")
        return False

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
def getUserRepos(inputUser):
    return Repository.objects.filter(repositorymembership__user=inputUser)
def getRepoProjectsByRepo(repo_obj):
    return Project.objects.filter(repository_id=repo_obj.id)
def getRepoAuditLogsByRepo(repo_obj):
    return AuditLog.objects.filter(repository_id=repo_obj.id)
def getRepoAuditLogsByRepoName(repo_name):
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
        v = inputContext if inputContext else inputElement.versions.first()

        if v:
            returnedString = f"{v.project.repository.path}/{inputElement.path}"
        else:
            returnedString = f"ORPHANED/{inputElement.path}"

    return returnedString


def getVersionFileByPath(inputPath):
    try:
        return VersionFile.objects.filter(path=inputPath).first()
    except Exception as e:
        print(f"Error fetching version file by path: {e}")
        return None


def isFileLinkedToVersion(file_obj, version_obj):
    possible_attrs = ['files', 'version_files', 'projectversionfile_set']

    for attr in possible_attrs:
        if hasattr(version_obj, attr):
            relationship = getattr(version_obj, attr)
            return relationship.filter(id=file_obj.id).exists()

    print(f"Error: No M2M relationship found on ProjectVersion using {possible_attrs}")
    return False


def linkExistingFileToVersion(file_obj, version_obj):
    possible_attrs = ['files', 'version_files', 'projectversionfile_set']

    for attr in possible_attrs:
        if hasattr(version_obj, attr):
            relationship = getattr(version_obj, attr)
            relationship.add(file_obj)
            version_obj.save()
            return True

    print(f"Error: Could not link file. No M2M relationship found.")
    return False
def logRemoveProjectVersion(inputUser, inputProject, inputVersion):
    AuditLog.objects.create(
        user=inputUser,
        project=inputProject,
        repository_id=inputProject.repository.pk,
        action="REMOVE_VERSION",
        details=f"DELETED {inputProject.title} v{inputVersion.version_number} from database"
    )

from django.db import transaction
def removeProjectVersionFromDB(inputUser, inputVersion,deletingProject=False):
    try:
        with transaction.atomic():
            m2m_attr = 'version_files' if hasattr(inputVersion, 'version_files') else 'files'
            associated_files = list(getattr(inputVersion, m2m_attr).all())

            files_to_actually_delete = []

            for f in associated_files:
                usage_list = getVersionsByFileID(f.id)
                if len(usage_list) <= 1:
                    files_to_actually_delete.append(f)
            if not deletingProject :
                logRemoveProjectVersion(inputUser, inputVersion.project,inputVersion)
            inputVersion.delete()
            for orphaned_file in files_to_actually_delete:
                orphaned_file.delete()
            return True
    except Exception as e:
        print(f"Error during safe deletion: {e}")
        return False


def addProjectAndInitialVersionToDB(user, repo_obj, title, desc, filePath, timestamp):
    try:
        # 1. Create the Project
        print("DB ADDED filePath "+filePath)
        new_proj = Project.objects.create(
            title=title,
            description=desc,
            owner=user,
            repository=repo_obj,
            path=filePath,
            created_at=timestamp
        )

        # 2. Create Ver 1
        ProjectVersion.objects.create(
            project=new_proj,
            version_number=1,
            author_id=user.id,
            path=filePath,
            message="Initial Import",
            created_at=timestamp
        )

        logCreateProject(user, new_proj)
        return True
    except Exception as e:
        print(f"DB Entry failed: {e}")
        return False

def createRepositoryInDB(user, title, path):
    try:
        with transaction.atomic():
            new_repo = Repository.objects.create(
                title=title,
                path=path,
                description=f"Local repository initialized from: {path}"
            )
            RepositoryMembership.objects.create(
                user=user,
                repository=new_repo,
                repo_role="Admin"
            )
            AuditLog.objects.create(
                user=user,
                action="CREATE_REPOSITORY",
                repository_id=new_repo.id,
                details=f"Created Repository '{title}' at {path}"
            )
            print(f"Successfully created repository: {title}")
            return True
    except Exception as e:
        print(f"Database Error during repository creation: {e}")
        return False


def removeRepositoryFromDB(user, repo_obj):
    try:
        repo_title = repo_obj.title
        with transaction.atomic():
            projects = Project.objects.filter(repository=repo_obj)
            for project in projects:
                removeProjectFromDB(user, project,deletingRepo = True)
            RepositoryMembership.objects.filter(repository=repo_obj).delete()
            AuditLog.objects.filter(repository_id=repo_obj.pk,action="REMOVE_PROJECT").delete()
            AuditLog.objects.create(
                user=user,
                action="DELETE_REPO",
                details=f"Permanently deleted Repository '{repo_title}'"
            )
            repo_obj.delete()
            return True
    except Exception as e:
        print(f"Error during repository deletion: {e}")
        return False