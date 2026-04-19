import os
import shutil
from datetime import timezone

import django
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog, Repository, RepositoryMembership

databaseStoragePath = "Dummy Host Storage Folder"

def getUserAuditLogs(inputUserID):
    return AuditLog.objects.filter(user_id=inputUserID).order_by("timestamp")
def getProjectAuditLogs(inputProjectID):
    print("got to project audit log view ",inputProjectID)
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
    try:
        with transaction.atomic():
            currentProject, _ = Project.objects.get_or_create(
                title=inputTitle,
                defaults={
                    "description": inputDescription,
                    "owner": inputOwner,
                    "repository" : inputRepo
                }
            )
            logCreateProject(inputOwner,currentProject)
    except Exception as e:
        print(f"Error during project creation: {e}")

def logCreateProjectVersion(inputUser, inputProject, inputVersion):
    returnedLog, _ = AuditLog.objects.get_or_create(
        user=inputUser,
        project=inputProject,
        action="CREATE_VERSION",
        details=f"{inputProject.title} v{inputVersion.version_number} created",
        project_version_id = inputVersion.pk
    )


def addNextProjectVersionToDB(inputProject, inputAuthor, inputMessage, inputPath):
    try:
        with transaction.atomic():
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
    except Exception as e:
        print(f"Error during project version creation: {e}")
        return None

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


# NEW
def addVersionFileToDB(inputUser, inputVersion, inputPath, inputContent):
    try:
        with transaction.atomic():
            version_file, created = VersionFile.objects.get_or_create(
                path=inputPath,
                content=inputContent
            )
            version_file.versions.add(inputVersion)
            logCreateVersionFile(inputUser, version_file, inputVersion)

            return version_file
    except Exception as e:
        print(f"Error during version file creation: {e}")
        return None
def logRemoveVersionFile(inputUser,inputProjectVersionFile):
    AuditLog.objects.get_or_create(
        user_id = inputUser.pk,
        project_id = getProjectByVersionFile(inputProjectVersionFile).pk,
        repository_id = inputProjectVersionFile.versions.first().project.repository_id,
        action = "REMOVE_VERSION_FILE",
        details = f"REMOVED {inputProjectVersionFile.path} FROM DB",
    )


# NEW
def removeVersionFileFromDB(inputUser, inputFileObj, inputVersion):
    try:
        with transaction.atomic():
            project = inputVersion.project
            AuditLog.objects.create(
                user=inputUser,
                project=project,
                project_version=inputVersion,
                repository_id=inputVersion.project.repository.id,
                action="DELETE_VERSION_FILE",
                details=f"Removed {inputFileObj.path} from {project.title} v{inputVersion.version_number}"
            )
            inputFileObj.versions.remove(inputVersion)
            if inputFileObj.versions.count() == 0:
                inputFileObj.delete()
    except Exception as e:
        print(f"Error during version file removal: {e}")
def logRemoveProject(inputUser, inputProject):
    studioOrCode = inputProject.repository.repoType
    AuditLog.objects.create(
        user = inputUser,
        repository_id = inputProject.repository.id,
        action = "REMOVE_PROJECT",
        details = f"{inputUser.username} REMOVED {studioOrCode} '{inputProject.title}' and all its versions"
    )
def deleteAllProjectAuditLogs(project_obj): #TODO : MIGHT BE UNUSED
    AuditLog.objects.filter(project_id=project_obj.pk).delete()
def removeCodeFileFromDB(user, project_obj, deletingRepo=False):
    try:
        with transaction.atomic():
            AuditLog.objects.filter(project_id=project_obj.pk).delete()
            if deletingRepo:
                print("deleting repo")
                AuditLog.objects.filter(repository_id=project_obj.repository_id, project__isnull=True).update(
                    repository=None)
                AuditLog.objects.filter(repository_id=project_obj.repository_id, project__isnull=True).delete()
            else:
                AuditLog.objects.create(
                    user=user,
                    repository_id=project_obj.repository_id,
                    action="REMOVE_CODEFILE",
                    details=f"REMOVED Code file '{project_obj.path}' and all associated versions from database"
                )
            versions = ProjectVersion.objects.filter(project=project_obj)
            for version in versions:
                removeProjectVersionFromDB(user, version, deletingProject=True)
            project_obj.delete()
            return True
    except Exception as e:
        print(f"Critical error during project deletion: {e}")
        return False
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
                print("version : ", version.version_number)
                removeProjectVersionFromDB(user, version, deletingProject=True)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            repo_path = os.path.normpath(project_obj.repository.path)
            file_rel_path = project_obj.path.lstrip('\\/')
            projectPath = ""
            if project_obj.repository.path.startswith("config"):
                projectPath = os.path.normpath(os.path.join(project_root, repo_path, file_rel_path))
            else:
                projectPath = os.path.normpath(os.path.join(repo_path, file_rel_path))
            if projectPath:
                print("Deleting ProjectVersion at : " + projectPath)
                if os.path.exists(projectPath):
                    try:
                        os.remove(projectPath)
                        print(f"Physical storage deleted: {projectPath}")
                    except OSError as file_error:
                        # We print but don't necessarily crash the DB transaction
                        # unless you want strict parity between DB and Disk
                        print(f"Warning: Could not delete physical path: {file_error}")
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

# NEW
def approveProjectVersion(inputVersion, inputUser, inputProjectID):
    try:
        with transaction.atomic():
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
    except Exception as e:
        print(f"Error during version approval: {e}")
        return 0
def getUserRepos(inputUser, repoType="Studio"):
    """
    Returns repositories of a specific type that the input user
    has a membership in.
    """
    from django.db.models import Q

    return Repository.objects.filter(
        Q(repositorymembership__user=inputUser) & ~Q(repositorymembership__repo_role="Removed"),
        repoType=repoType  # This keyword argument MUST be last
    ).distinct()
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


def getLatestProjectVersion(project):
    """
    Given a Project instance, returns the latest ProjectVersion
    based on the highest version number.
    """
    from vcs_core.models import ProjectVersion

    if not project:
        return None

    # Get the version with the highest version_number
    latest_version = ProjectVersion.objects.filter(
        project=project
    ).order_by('-version_number').first()

    return latest_version
def getLatestApprovedProjectVersion(projectID):
    """
    Given a Project instance, returns the latest ProjectVersion
    based on the highest version number.
    """
    from vcs_core.models import ProjectVersion

    if not projectID:
        return None

    # Get the version with the highest version_number
    latest_approved_version = ProjectVersion.objects.filter(
        project_id=projectID, status="Approved"
    ).order_by('-version_number').first()

    return latest_approved_version
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
        repository_id=inputProject.repository.id,
        action="REMOVE_VERSION",
        details=f"DELETED {inputProject.title} v{inputVersion.version_number} from database"
    )

from django.db import transaction
# Replace with this version (cleaned + consistent)
def removeProjectVersionFromDB(inputUser, inputVersionMap, deletingProject=False):
    try:
        with transaction.atomic():
            inputVersion = ProjectVersion.objects.get(id = inputVersionMap.id)
            m2m_attr = 'version_files' if hasattr(inputVersion, 'version_files') else 'files'
            associated_files = list(getattr(inputVersion, m2m_attr).all())
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            repo_path = os.path.normpath(inputVersion.project.repository.path)
            file_rel_path = inputVersion.path.lstrip('\\/')
            versionPath = ""
            if inputVersion.project.repository.path.startswith("config"):
                versionPath = os.path.normpath(os.path.join(project_root, repo_path, file_rel_path))
            else:
                versionPath = os.path.normpath(os.path.join(repo_path, file_rel_path))
            files_to_actually_delete = []

            for f in associated_files:
                usage_list = getVersionsByFileID(f.id)
                if len(usage_list) <= 1:
                    files_to_actually_delete.append(f)
            if not deletingProject :
                logRemoveProjectVersion(inputUser, inputVersion.project,inputVersion)

            if inputVersion.path:
                print("Deleting ProjectVersion at : " + versionPath)
                if os.path.exists(versionPath):
                    try:
                        os.remove(versionPath)
                        print(f"Physical storage deleted: {versionPath}")
                    except OSError as file_error:
                        # We print but don't necessarily crash the DB transaction
                        # unless you want strict parity between DB and Disk
                        print(f"Warning: Could not delete physical path: {file_error}")
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
        print(filePath)
        print("DB ADDED filePath " + filePath)
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


def checkAbsPathToCodeFile(project_obj, abs_path):
    """
    Returns True if the filename (including extension) of abs_path
    matches the filename of project_obj.path.
    """
    # 1. Get the final filename from the absolute path
    # Example: "C:/Users/Docs/file.txt" -> "file.txt"
    filename_from_abs = os.path.basename(abs_path)

    # 2. Get the final filename from the project object path
    # Example: "repo_1/src/file.txt" -> "file.txt"
    filename_from_project = os.path.basename(project_obj.path)

    # 3. Compare them (Case-sensitive by default)
    if filename_from_abs == filename_from_project:##TODO:CURRENTLY HERE
        return True
    else:
        print(f"Path mismatch: {filename_from_abs} != {filename_from_project}")
        return False

def addNextCodeFileVersionToDB(inputProjectMap, inputAuthorMap, inputMessage, localPath):
    """
    Handles the physical file versioning and database registration.
    Prevents overwriting by calculating the next version number first.
    """
    try:
        # --- 1. RESOLVE ABSOLUTE PROJECT ROOT ---
        # Get the path to 'matss-vcs' (Project Root)
        # Assuming this file/server is running from the 'config' folder
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)

        inputProject = Project.objects.get(id = inputProjectMap.id)
        repo_obj = inputProject.repository
        # repo_obj.path should be 'config/Dummy Host Storage Folder/RepoName_ID'
        repo_path_str = os.path.normpath(repo_obj.path)

        # This creates the absolute path: C:/.../matss-vcs/config/Dummy Host Storage Folder/Repo_ID
        repo_base_disk_path = os.path.normpath(os.path.join(project_root, repo_path_str))

        # --- 2. CALCULATE NEXT VERSION ---

        last_version = ProjectVersion.objects.filter(project_id=inputProject.id).order_by('-version_number').first()
        next_v = (last_version.version_number + 1) if last_version else 1

        # --- 3. DEFINE FILENAMES ---
        # filePath in DB is 'src/main.py' or just 'main.py'
        # We need the relative folder structure inside the repo
        relative_file_dir = os.path.dirname(inputProject.path)
        filename_only = os.path.basename(inputProject.path)
        name, ext = os.path.splitext(filename_only)

        # The physical file names
        versioned_filename = f"{name}_{next_v}{ext}"

        # Absolute paths for the OS to use
        # The 'Master' file (the one that always represents the latest state)
        full_master_path = os.path.normpath(os.path.join(repo_base_disk_path, inputProject.path))
        # The 'Versioned' file (the historical snapshot)
        full_versioned_path = os.path.normpath(os.path.join(repo_base_disk_path, relative_file_dir, versioned_filename))

        # Relative path for the DB (portable)
        relative_versioned_db_path = os.path.join(relative_file_dir, versioned_filename).replace('\\', '/')

        print(f"DEBUG: Versioning {filename_only} to version {next_v}")
        print(f"DEBUG: Target Backup Path -> {full_versioned_path}")

        # --- 4. PHYSICAL FILE OPERATIONS ---
        # Ensure the subdirectories inside the repo exist (e.g., Repo_ID/src/)
        os.makedirs(os.path.dirname(full_versioned_path), exist_ok=True)

        # A. Copy the local file into the Repo as the 'Master' (the latest live version)
        shutil.copy2(localPath, full_master_path)

        # B. Copy that master to the versioned backup (the historical record)
        shutil.copy2(full_master_path, full_versioned_path)

        # --- 5. DATABASE TRANSACTION ---
        with transaction.atomic():
            # Update the main project timestamp
            inputProject.created_at = timezone.now()
            inputProject.save()

            # Create the specific version entry
            new_version = ProjectVersion.objects.create(
                project=inputProject,
                version_number=next_v,
                author_id=inputAuthorMap.id,
                path=relative_versioned_db_path,
                message=inputMessage,
                created_at=timezone.now(),
                status="Approved"  # Or logic based on roles
            )
            AuditLog.objects.get_or_create(
                user_id=inputAuthorMap.id,
                project=inputProject,
                action="CREATE_CODEFILE_VERSION",
                details=f"{inputAuthorMap.username} created {inputProject.title} v{new_version.version_number}",
                project_version_id=new_version.pk,
                repository_id = new_version.project.repository.id
            )
        print(f"SUCCESS: Created version {next_v} for {inputProject.title}")
        return new_version

    except Exception as e:
        print(f"CRITICAL ERROR in addNextCodeFileVersionToDB: {e}")
        import traceback
        traceback.print_exc()
        return None
def logAddCodeFileToDB(inputUser,inputCodeFile):
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = inputCodeFile.pk,
        repository_id=inputCodeFile.repository.id,
        action="CREATE_CODEFILE",
        details=f"ADDED {inputCodeFile.title} to {inputCodeFile.repository.title}"
    )
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = inputCodeFile.pk,
        repository_id=inputCodeFile.repository.id,
        project_version_id = ProjectVersion.objects.filter(project_id=inputCodeFile.pk).first().pk,
        action="CREATE_CODEFILE_VERSION",
        details=f"ADDED INITIAL VERSION to {inputCodeFile.title}"
    )


def addInitialCodeFileDrop(user, repo_obj, title, actual_source_path, relative_repo_path, timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()

    try:
        # 1. Resolve Storage Paths
        base_storage = os.path.normpath(databaseStoragePath)
        repo_path_str = os.path.normpath(repo_obj.path)
        project_root = os.path.dirname(base_storage)

        if repo_path_str.startswith("config"):
            repo_base_disk_path = os.path.join(project_root, repo_path_str)
        else:
            repo_base_disk_path = os.path.join(base_storage, repo_path_str)

        # 2. Setup Versioned Paths (e.g., test.txt -> test_1.txt)
        file_dir = os.path.dirname(relative_repo_path)
        file_name = os.path.basename(relative_repo_path)
        name, ext = os.path.splitext(file_name)
        relative_project_path = os.path.join(file_dir, f"{name}{ext}").replace('\\', '/')
        full_project_path = os.path.normpath(os.path.join(repo_base_disk_path,relative_project_path))
        relative_versioned_path = os.path.join(file_dir, f"{name}_1{ext}").replace('\\', '/')
        full_versioned_path = os.path.normpath(os.path.join(repo_base_disk_path, relative_versioned_path))

        # 3. PHYSICAL FILE OPERATION
        if not os.path.exists(actual_source_path):
            print(f"ERROR: Source file not found on D: drive: {actual_source_path}")
            return False

        # Create the folder structure in your Dummy Host storage first
        dest_dir = os.path.dirname(full_versioned_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        # Copy and Rename: From D:/.../test.txt to Storage/.../test_1.txt
        shutil.copy2(actual_source_path, full_project_path)
        shutil.copy2(actual_source_path, full_versioned_path)
        # Verify the copy worked
        if not os.path.exists(full_versioned_path):
            print(f"FAILED: File was not written to {full_versioned_path}")
            return False

        # 4. DATABASE ENTRIES
        with transaction.atomic():
            new_codeFile = Project.objects.create(
                title=title,
                description="Initial Import",
                owner=user,
                repository=repo_obj,
                path=relative_repo_path,  # e.g. "test.txt"
                created_at=timestamp
            )

            is_admin = RepositoryMembership.objects.filter(
                user=user,
                repository=repo_obj,
                repo_role="Admin"
            ).exists()

            ProjectVersion.objects.create(
                project=new_codeFile,
                version_number=1,
                author=user,
                path=relative_versioned_path,  # e.g. "test_1.txt"
                message="Initial Import",
                created_at=timestamp,
                status="Approved" if is_admin else "Draft"
            )
        return True

    except Exception as e:
        print(f"FAILED addInitialCodeFileDrop: {e}")
        return False
def addInitialCodeFileToDB(user, repo_obj, title, filePath, timestamp):
    try:
        base_storage = os.path.normpath(databaseStoragePath)
        repo_path_str = os.path.normpath(repo_obj.path)
        project_root = os.path.dirname(base_storage)
        if repo_path_str.startswith("config"):
            repo_base_disk_path = os.path.join(project_root, repo_path_str)
        else:
            repo_base_disk_path = os.path.join(base_storage, repo_path_str)

        repo_base_disk_path = os.path.normpath(repo_base_disk_path)
        full_source_path = os.path.normpath(os.path.join(repo_base_disk_path, filePath))
        file_dir = os.path.dirname(filePath)
        file_name = os.path.basename(filePath)
        name, ext = os.path.splitext(file_name)
        relative_versioned_path = os.path.join(file_dir, f"{name}_1{ext}").replace('\\', '/')
        full_versioned_path = os.path.normpath(os.path.join(repo_base_disk_path, relative_versioned_path))
        if not os.path.exists(full_source_path):
            print(f"ERROR: File not found for indexing: {full_source_path}")
            return False
        shutil.copy2(full_source_path, full_versioned_path)
        with transaction.atomic():
            new_codeFile = Project.objects.create(
                title=title,
                description="Initial Import",
                owner=user,
                repository=repo_obj,
                path=filePath,
                created_at=timestamp
            )
            is_admin = RepositoryMembership.objects.filter(
                user=user,
                repository=repo_obj,
                repo_role="Admin"
            ).exists()
            ProjectVersion.objects.create(
                project=new_codeFile,
                version_number=1,
                author=user,
                path=relative_versioned_path,
                message="Initial Import",
                created_at=timestamp,
                status="Approved" if is_admin else "Draft"
            )
        return True

    except Exception as e:
        print(f"FAILED addInitialCodeFileToDB: {e}")
        return False


def createRepositoryInDB(user, title, inputPath, repoType="Studio"):
    print(f"\n>>> STARTING REPO CREATION: {title} ({repoType})")
    try:
        with transaction.atomic():
            # 1. DB Entry
            repoTitle = title
            new_repo = Repository.objects.create(
                title=repoTitle,
                path="To Be Determined",
                description="Initial Import",
                repoType=repoType
            )
            print(f"STEP 1: DB Object created with PK: {new_repo.pk}")

            # 2. Permissions
            RepositoryMembership.objects.create(user=user, repository=new_repo, repo_role="Admin")
            print("STEP 2: Admin membership created.")

            if repoType == "Code":
                print("STEP 3: Detected 'Code' type. Starting path logic...")

                # Derive the project root
                # Assumes databaseStoragePath is: .../matss-vcs/Dummy Host Storage Folder
                project_root = os.path.dirname(os.path.abspath(databaseStoragePath))
                folder_name = f"{title}_{new_repo.pk}"

                # This puts it in matss-vcs/config/Dummy Host Storage Folder/...
                repo_disk_path = os.path.normpath(
                    os.path.join(project_root, "config", "Dummy Host Storage Folder", folder_name))
                repo_db_path = os.path.join("config", "Dummy Host Storage Folder", folder_name).replace("\\", "/")

                new_repo.path = repo_db_path
                new_repo.save()
                print(f"STEP 4: Path calculated: {repo_disk_path}")

                # 3. Physical Copy
                if not os.path.exists(inputPath):
                    print(f"!!! FAILURE: Source path does not exist: {inputPath}")
                    return False

                os.makedirs(os.path.dirname(repo_disk_path), exist_ok=True)
                print(f"STEP 5: Directory structure ready. Copying files...")

                shutil.copytree(inputPath, repo_disk_path, symlinks=True, dirs_exist_ok=True)
                print("STEP 6: shutil.copytree finished.")

                # Inside createRepositoryInDB
                print(f"Indexing started for: {repo_disk_path}")
                databaseStorageFilePaths = []
                for root, dirs, files in os.walk(repo_disk_path):
                    for filename in files:
                        # SKIP the versioned files we create so we don't index them twice
                        if filename.endswith("_1") or "_1." in filename:
                            continue

                        abs_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(abs_path, repo_disk_path).replace("\\", "/")
                        databaseStorageFilePaths.append(rel_path)

                print(f"Files found: {len(databaseStorageFilePaths)}")

                current_time = timezone.now()
                for codeFilePath in databaseStorageFilePaths:
                    # Use the filename as the title
                    title = os.path.basename(codeFilePath)
                    success = addInitialCodeFileToDB(user, new_repo, title, codeFilePath, current_time)
            AuditLog.objects.create(
                user=user,
                action="CREATE_REPO",
                repository_id = new_repo.pk,
                details=f"{user.username} Created Repository '{repoTitle}'"
            )
            print(">>> SUCCESS: Repository creation sequence finished.")
            return True

    except Exception as e:
        print(f"!!! CRITICAL EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


def removeRepositoryFromDB(user, repo_obj,repoType = "Studio"):
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
                details=f"{user.username} Permanently deleted Repository '{repo_title}'"
            )
            repo_storage_path = repo_obj.path
            if repoType == "Code" and repo_storage_path and repo_storage_path != "unknown":
                print("Deleting CodeRepo at + "+repo_storage_path)
                if os.path.exists(repo_storage_path):
                    try:
                        shutil.rmtree(repo_storage_path)
                        print(f"Physical storage deleted: {repo_storage_path}")
                    except OSError as file_error:
                        # We print but don't necessarily crash the DB transaction
                        # unless you want strict parity between DB and Disk
                        print(f"Warning: Could not delete physical path: {file_error}")
            repo_obj.delete()
            return True
    except Exception as e:
        print(f"Error during repository deletion: {e}")
        return False