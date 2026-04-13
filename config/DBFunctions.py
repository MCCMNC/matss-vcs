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
def getUserRepos(inputUser, repoType="Studio"):
    """
    Returns repositories of a specific type that the input user
    has a membership in.
    """
    return Repository.objects.filter(
        repositorymembership__user=inputUser,
        repoType=repoType
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


def addNextCodeFileVersionToDB(inputProject, inputAuthor, inputMessage, localPath):
    """
    Takes a file from localPath, copies it into the repository storage
    as the new 'current' file, and creates a versioned backup (_N).
    """

    try:
        # --- 1. Path Normalization for the Repository ---
        base_storage = os.path.normpath(databaseStoragePath)
        print(1)
        repo_obj = inputProject.repository
        
        repo_rel_path = os.path.normpath(repo_obj.path)

        if repo_rel_path.startswith(base_storage):
            repo_base_disk_path = repo_rel_path
        else:
            repo_base_disk_path = os.path.join(base_storage, repo_rel_path)
        print(2)
        # --- 2. Determine Version Number ---
        latestCodeFileVer = (
            ProjectVersion.objects
            .filter(project_id=inputProject.id)
            .order_by("-version_number")
            .first()
        )
        next_version_num = 1 if not latestCodeFileVer else latestCodeFileVer.version_number + 1
        print(3)
        # --- 3. Define Internal Repository Paths ---
        # inputProject.path is the relative path within the repo (e.g., 'src/main.py')
        internal_rel_path = inputProject.path

        # This is where the file lives inside your Managed Storage
        full_repo_destination = os.path.normpath(os.path.join(repo_base_disk_path, internal_rel_path))

        # Create the versioned filename for history (e.g., 'src/main_2.py')
        file_dir = os.path.dirname(internal_rel_path)
        file_name = os.path.basename(internal_rel_path)
        name, ext = os.path.splitext(file_name)

        relative_versioned_path = os.path.join(file_dir, f"{name}_{next_version_num}{ext}").replace('\\', '/')
        full_versioned_backup_path = os.path.normpath(os.path.join(repo_base_disk_path, relative_versioned_path))
        print(4)
        # --- 4. Physical File Operations ---
        if not os.path.exists(localPath):
            print(f"Error: User's local file not found at {localPath}")
            return None
        print(5)
        # A. Copy from User's Computer to the Main Repo Location (Updates 'main.py')
        shutil.copy2(localPath, full_repo_destination)

        # B. Copy from the Main Repo Location to the Versioned File (Creates 'main_2.py')
        shutil.copy2(full_repo_destination, full_versioned_backup_path)

        print(f"Imported {localPath} to {full_repo_destination}")
        print(f"Created version backup at {full_versioned_backup_path}")

        # --- 5. Database Transaction ---
        with transaction.atomic():
            # Determine Approval Status
            final_status = "Draft"
            is_admin = RepositoryMembership.objects.filter(
                user=inputAuthor,
                repository_id=repo_obj.id,
                repo_role="Admin"
            ).exists()

            if is_admin:
                final_status = "Approved"

            # Create the next ProjectVersion pointing to the _N file
            currentVersion = ProjectVersion.objects.create(
                project_id=inputProject.id,
                version_number=next_version_num,
                author=inputAuthor,
                path=relative_versioned_path,  # Path to the _N file
                message=inputMessage,
                status=final_status,
                created_at=timezone.now()
            )

        return currentVersion

    except Exception as e:
        print(f"Failed to import and version file: {e}")
        return None
def logAddCodeFileToDB(inputUser,inputCodeFile):
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = inputCodeFile.pk,
        repository_id=inputCodeFile.repository_id,
        action="CREATE_CODEFILE",
        details=f"ADDED {inputCodeFile.title} to {inputCodeFile.repository.title}"
    )
    AuditLog.objects.get_or_create(
        user_id=inputUser.pk,
        project_id = inputCodeFile.pk,
        repository_id=inputCodeFile.repository_id,
        project_version_id = ProjectVersion.objects.filter(project_id=inputCodeFile.pk).first().pk,
        action="CREATE_CODEFILE_VERSION",
        details=f"ADDED INITIAL VERSION to {inputCodeFile.title}"
    )


def addInitialCodeFileToDB(user, repo_obj, title, filePath, timestamp):
    """
    Copies the original file to a versioned name (filename_1.ext)
    and creates the Project and ProjectVersion entries in the DB.
    """
    try:
        # --- 1. Path Normalization & Correction ---
        # Normalize to prevent "Folder\Folder" duplication
        base_storage = os.path.normpath(databaseStoragePath)
        repo_rel_path = os.path.normpath(repo_obj.path)

        # If the repo path already starts with the base storage path, don't join them
        if repo_rel_path.startswith(base_storage):
            repo_base_disk_path = repo_rel_path
        else:
            repo_base_disk_path = os.path.join(base_storage, repo_rel_path)

        # --- 2. Define Physical Source and Destination ---
        # full_source_path is the actual file currently sitting on disk
        full_source_path = os.path.normpath(os.path.join(repo_base_disk_path, filePath))

        # Create the versioned filename (e.g., main.py -> main_1.py)
        file_dir = os.path.dirname(filePath)
        file_name = os.path.basename(filePath)
        name, ext = os.path.splitext(file_name)

        relative_versioned_path = os.path.join(file_dir, f"{name}_1{ext}").replace('\\', '/')
        full_versioned_path = os.path.normpath(os.path.join(repo_base_disk_path, relative_versioned_path))

        # --- 3. Physical File Operations ---
        if not os.path.exists(full_source_path):
            print(f"Error: Physical file not found at {full_source_path}")
            return False

        # Copy the file to the new versioned name
        shutil.copy2(full_source_path, full_versioned_path)
        print(f"File Versioned: {full_source_path} -> {full_versioned_path}")

        # --- 4. Database Transaction ---
        with transaction.atomic():
            # Create the Project (The main tracking entry)
            # title is the relative path (e.g., 'src/main.py')
            new_codeFile = Project.objects.create(
                title=title,
                description="Initial Import",
                owner=user,
                repository=repo_obj,
                path=filePath,
                created_at=timestamp
            )

            # Create Version 1 (Pointing to the _1 file)
            finalStatus = "Draft"
            can_approve = RepositoryMembership.objects.filter(
                user= user,
                repository=repo_obj,
                repo_role__in=["Admin"]
            ).exists()
            if can_approve:finalStatus = "Approved"
            ProjectVersion.objects.create(
                project=new_codeFile,
                version_number=1,
                author=user,
                path=relative_versioned_path,
                message="Initial Import",
                created_at=timestamp,
                status = finalStatus
            )

        # Use your existing logging function
        logAddCodeFileToDB(user, new_codeFile)
        return True

    except Exception as e:
        print(f"DB Entry or File Copy failed for {title}: {e}")
        return False
def createRepositoryInDB(user, title, inputPath, repoType = "Studio"):
    try:
        with transaction.atomic():
            db_creationPath = "Unknown Repo Type"
            if repoType == "Studio" : db_creationPath = inputPath
            elif repoType == "Code": db_creationPath = "To Be Determined"
            new_repo = Repository.objects.create(
                title=title,
                path=db_creationPath,
                description=f"CURRENTLY UNIMPLEMENTED",
                repoType = repoType
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
                details=f"Created Repository '{title}' at {inputPath}"
            )
            if repoType == "Code":
                # 1. Define the new path using the primary key to ensure uniqueness
                new_repo.path = os.path.join(databaseStoragePath, f"{title}_{new_repo.pk}")
                new_repo.save()

                print(f"Attempting to copy all files from: {inputPath} to: {new_repo.path}")

                try:
                    # 2. Check if the source path actually exists
                    if not os.path.exists(inputPath):
                        print(f"Source path error: {inputPath} does not exist.")
                        # Handle error (e.g., delete the DB entry or raise exception)
                    else:
                        # 3. Copy the entire tree
                        # symlinks=True preserves symbolic links instead of copying the target file
                        # dirs_exist_ok=True allows the copy even if the folder was somehow pre-created
                        shutil.copytree(inputPath, new_repo.path, symlinks=True, dirs_exist_ok=True)
                        print("Repository structure successfully recreated at new path.")

                except Exception as e:
                    print(f"Failed to copy repository files: {e}")
                    # Logic for rollback if needed (e.g., new_repo.delete())

                print(f"Attempting to add all files from: {new_repo.path} to: DB Tracking")

                databaseStorageFilePaths = []

                try:
                    # os.walk yields a 3-tuple: (current_folder_path, subfolders, files_in_folder)
                    for root, dirs, files in os.walk(new_repo.path):
                        for filename in files:
                            # 1. Get the absolute path of the file
                            absolute_file_path = os.path.join(root, filename)
                            # 2. Calculate the path relative to the new_repo.path
                            relative_path = os.path.relpath(absolute_file_path, new_repo.path)
                            # 3. Store or process the relative path
                            databaseStorageFilePaths.append(relative_path)

                    print(f"Successfully indexed {len(databaseStorageFilePaths)} files for DB tracking.")
                except Exception as e:
                    print(f"Error while indexing files: {e}")
                current_time = timezone.now()
                print("Attempting to add all CODE FILES to DB")
                for codeFilePath in databaseStorageFilePaths:
                    """(user, repo_obj, title, filePath, timestamp)"""
                    addInitialCodeFileToDB(user, new_repo, codeFilePath, codeFilePath,current_time)
                print("SUCCESSFULLY ADDED all CODE FILES to DB")
            print(f"Successfully created repository: {title}")
            return True
    except Exception as e:
        print(f"Database Error during repository creation: {e}")
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
                details=f"Permanently deleted Repository '{repo_title}'"
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