from django.utils import timezone

from django.shortcuts import get_object_or_404, render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from django.conf import settings
from .serializers import *
import DBFunctions

@api_view(['GET'])
def getUserAuditLogs_View(request, inputUserID):
    logs = DBFunctions.getUserAuditLogs(inputUserID)
    serializer = AuditLogSerializer(logs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProjectAuditLogs_View(request, inputProjectID):
    logs = DBFunctions.getProjectAuditLogs(inputProjectID)
    serializer = AuditLogSerializer(logs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProjectByID_View(request, inputProjectID):
    project = DBFunctions.getProjectByID(inputProjectID)
    serializer = ProjectSerializer(project)
    return Response(serializer.data)

@api_view(['GET'])
def getUserProjects_View(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id) # get user obj from user_id
    projects = DBFunctions.getUserProjects(user_obj)
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProjectVersionAuditLogsByID_View(request, inputProjectVersionID):
    logs = DBFunctions.getProjectVersionAuditLogsByID(inputProjectVersionID)
    serializer = AuditLogSerializer(logs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProjectVersionsByProjectID_View(request, inputProjectId):
    versions = DBFunctions.getProjectVersionsByProjectID(inputProjectId)
    serializer = ProjectVersionSerializer(versions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProjectVersionSpecificByVersionFile_View(request, version_file_id):
    file_obj = get_object_or_404(VersionFile, pk=version_file_id)
    version = DBFunctions.getProjectVersionSpecificByVersionFile(file_obj)
    serializer = ProjectVersionSerializer(version) 
    return Response(serializer.data)

@api_view(['GET'])
def getAllProjectFilesByProjectID_View(request, inputProjectId):
    files = DBFunctions.getALlProjectFilesByProjectID(inputProjectId)
    serializer = VersionFileSerializer(files, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProjectVersionFilesByProjectVersionID_View(request, inputVersionID):
    files = DBFunctions.getProjectVersionFilesByProjectVersionID(inputVersionID)
    serializer = VersionFileSerializer(files, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def getOrCreateUser_View(request):
    data = request.data
    user = DBFunctions.getOrCreateUser(
        data.get('username'),
        data.get('email'),
        data.get('password_hash'),
        data.get('role')
    )
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def logCreateProject_View(request):
    data = request.data
    user = get_object_or_404(User, pk=data.get('user_id'))
    project = get_object_or_404(Project, pk=data.get('project_id'))
    
    DBFunctions.logCreateProject(user, project)
    return Response({"message": "Logs created"}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def addProjectToDB_View(request):
    data = request.data
    owner = get_object_or_404(User, pk=data.get('owner_id'))
    repo = get_object_or_404(Repository, pk=data.get('repo_id'))
    
    DBFunctions.addProjectToDB(
        data.get('title'),
        data.get('description'),
        owner,
        repo
    )
    return Response({"message": "Project added successfully"}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def addNextProjectVersion_View(request):
    data = request.data
    
    project_obj = get_object_or_404(Project, pk=data.get('project_id'))
    author_obj = get_object_or_404(User, pk=data.get('author_id'))
    
    new_version = DBFunctions.addNextProjectVersionToDB(
        project_obj, 
        author_obj, 
        data.get('message'), 
        data.get('path')
    )
    
    serializer = ProjectVersionSerializer(new_version)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def addVersionFileToDB_View(request):
    data = request.data
    
    user_obj = get_object_or_404(User, pk=data.get('user_id'))
    version_obj = get_object_or_404(ProjectVersion, pk=data.get('version_id'))
    
    new_file = DBFunctions.addVersionFileToDB(
        user_obj, 
        version_obj, 
        data.get('path'), 
        data.get('content')
    )
    
    serializer = VersionFileSerializer(new_file)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
def removeVersionFileFromDB_View(request):
    data = request.data
    user = get_object_or_404(User, pk=data.get('user_id'))
    file_obj = get_object_or_404(VersionFile, pk=data.get('file_id'))
    version = get_object_or_404(ProjectVersion, pk=data.get('version_id'))

    DBFunctions.removeVersionFileFromDB(user, file_obj, version)
    return Response({"message": "File removed from version"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
def removeCodeFileFromDB_View(request, project_id):
    user = get_object_or_404(User, pk=request.data.get('user_id'))
    project_obj = get_object_or_404(Project, pk=project_id)
    deleting_repo = request.data.get('deleting_repo', False)

    success = DBFunctions.removeCodeFileFromDB(user, project_obj, deleting_repo)

    if success:
        return Response({"message": "Code file and versions removed"}, status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Failed to delete code file"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def removeProjectFromDB_View(request, project_id):
    user = get_object_or_404(User, pk=request.data.get('user_id'))
    project_obj = get_object_or_404(Project, pk=project_id)
    deleting_repo = request.data.get('deleting_repo', False)
    print("got here")
    success = DBFunctions.removeProjectFromDB(user, project_obj, deleting_repo)

    if success:
        return Response({"message": "Project fully removed from DB"}, status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Failed to delete project"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def getUserRepos_View(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)
    repo_type = request.query_params.get('repoType', 'Studio')
    
    repos = DBFunctions.getUserRepos(user_obj, repoType=repo_type)
    serializer = RepositorySerializer(repos, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getRepoProjectsByRepo_View(request, repo_id):
    print("got to view")
    #repo_id = request.query_params.get('repository_id')
    #print("view: ", repo_id)
    repo_obj = get_object_or_404(Repository, pk=repo_id)
    print(repo_obj.path)
    projects = DBFunctions.getRepoProjectsByRepo(repo_obj)
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getRepoAuditLogsByRepo_View(request, repo_id):
    print("got to repo audit logs view ",repo_id)
    repo_obj = get_object_or_404(Repository, pk=repo_id)
    logs = DBFunctions.getRepoAuditLogsByRepo(repo_obj)
    serializer = AuditLogSerializer(logs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getRepoAuditLogsByRepoName_View(request, repo_name):
    logs = DBFunctions.getRepoAuditLogsByRepoName(repo_name)
    serializer = AuditLogSerializer(logs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getRepoByName_View(request, inputRepoName):
    repo = DBFunctions.getRepoByName(inputRepoName)
    serializer = RepositorySerializer(repo)
    return Response(serializer.data)

@api_view(['GET'])
def getVersionsByFileID_View(request, inputVersionFileID):
    version_data = DBFunctions.getVersionsByFileID(inputVersionFileID)
    return Response(version_data)

@api_view(['GET'])
def getElementRelativePath_View(request):
    # get parameters from /api/utility/get-path/?id=5&type=Project
    element_id = request.query_params.get('id')
    element_type = request.query_params.get('type')
    context_id = request.query_params.get('context_id')

    if not element_id or not element_type:
        return Response({"error": "Missing 'id' or 'type' parameters"}, status=400)

    try:
        if element_type == "Repository":
            obj = get_object_or_404(Repository, pk=element_id)

        elif element_type == "Project":
            obj = get_object_or_404(Project, pk=element_id)

        elif element_type == "ProjectVersion":
            obj = get_object_or_404(ProjectVersion, pk=element_id)

        elif element_type == "ProjectVersionFile":
            obj = get_object_or_404(VersionFile, pk=element_id)

        else:
            return Response({"error": "Invalid element type"}, status=400)

        context_obj = None
        if element_type == "ProjectVersionFile" and context_id:
            context_obj = ProjectVersion.objects.filter(pk=context_id).first()

        path_string = DBFunctions.getElementRelativePath(obj, element_type, inputContext=context_obj)

        return Response({"relative_path": path_string})

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def getLatestProjectVersion_View(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    latest = DBFunctions.getLatestProjectVersion(project)
    
    if not latest:
        return Response({"message": "No versions found for this project"}, status=404)
        
    serializer = ProjectVersionSerializer(latest)
    return Response(serializer.data)


@api_view(['GET'])
def getLatestApprovedProjectVersion_View(request, project_id):
    latest = DBFunctions.getLatestApprovedProjectVersion(project_id)
    if not latest:
        return Response({"message": "No versions found for this project"}, status=404)
    serializer = ProjectVersionSerializer(latest)
    return Response(serializer.data)

@api_view(['GET'])
def getVersionFileByPath_View(request):
    # Using query params because paths can contain slashes that break URLs
    path_str = request.query_params.get('path')
    file_obj = DBFunctions.getVersionFileByPath(path_str)
    
    if not file_obj:
        return Response({"message": "File not found"}, status=404)
        
    serializer = VersionFileSerializer(file_obj)
    return Response(serializer.data)

@api_view(['GET'])
def isFileLinkedToVersion_View(request):
    file_id = request.query_params.get('file_id')
    version_id = request.query_params.get('version_id')
    
    file_obj = get_object_or_404(VersionFile, pk=file_id)
    version_obj = get_object_or_404(ProjectVersion, pk=version_id)
    
    is_linked = DBFunctions.isFileLinkedToVersion(file_obj, version_obj)
    return Response({"is_linked": is_linked})

@api_view(['POST'])
def linkExistingFileToVersion_View(request):
    # IDs come from the JSON body
    file_id = request.data.get('file_id')
    version_id = request.data.get('version_id')
    
    file_obj = get_object_or_404(VersionFile, pk=file_id)
    version_obj = get_object_or_404(ProjectVersion, pk=version_id)
    
    success = DBFunctions.linkExistingFileToVersion(file_obj, version_obj)
    
    if success:
        return Response({"message": "Link created successfully"})
    return Response({"error": "Failed to create link"}, status=500)

@api_view(['DELETE'])
def removeProjectVersionFromDB_View(request, version_id):
    user = get_object_or_404(User, pk=request.data.get('user_id'))
    version = get_object_or_404(ProjectVersion, pk=version_id)
    deleting_project = request.data.get('deleting_project', False)

    success = DBFunctions.removeProjectVersionFromDB(user, version, deleting_project)
    
    if success:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Failed to delete version"}, status=500)

@api_view(['POST'])
def addProjectAndInitialVersionDrop_View(request):
    data = request.data
    user = get_object_or_404(User, pk=data.get('user_id'))
    repo = get_object_or_404(Repository, pk=data.get('repo_id'))

    # Ensure we have a timestamp (if client doesn't send one, use server time)
    timestamp = data.get('timestamp') or timezone.now()

    # Path extraction
    full_source_path = data.get('filePath')  # e.g., "D:/MyFolder/script.py"

    # We want the file to live in the root of the repo by default,
    # or you can extract a relative path if the GUI sends one.
    relative_path = os.path.basename(full_source_path)

    if repo.repoType == "Studio":
        success = DBFunctions.addProjectAndInitialVersionToDB(
            user,
            repo,
            data.get('title'),
            data.get('description'),
            full_source_path,
            timestamp
        )
    else:
        # Now passing all required positional arguments:
        # actual_source_path=full_source_path
        # relative_repo_path=relative_path
        # timestamp=timestamp
        success = DBFunctions.addInitialCodeFileDrop(
            user,
            repo,
            data.get('title'),
            full_source_path,  # actual_source_path
            relative_path,  # relative_repo_path
            timestamp  # timestamp (The missing argument!)
        )

    if success:
        return Response({"message": "Project and Version 1 created"}, status=status.HTTP_201_CREATED)

    return Response({"error": "Database entry failed"}, status=500)
@api_view(['POST'])
def addProjectAndInitialVersionToDB_View(request):
    data = request.data
    user = get_object_or_404(User, pk=data.get('user_id'))
    repo = get_object_or_404(Repository, pk=data.get('repo_id'))
    if repo.repoType == "Studio":
        success = DBFunctions.addProjectAndInitialVersionToDB(
            user,
            repo,
            data.get('title'),
            data.get('description'),
            data.get('filePath'),
            data.get('timestamp')
        )
    else :
        success = DBFunctions.addInitialCodeFileToDB(
            user,
            repo,
            data.get('title'),
            data.get('filePath'),
            data.get('timestamp')
        )
    if success:
        return Response({"message": "Project and Version 1 created"}, status=status.HTTP_201_CREATED)
    return Response({"error": "Database entry failed"}, status=500)

@api_view(['POST'])
def checkAbsPathToCodeFile_View(request):
    project = get_object_or_404(Project, pk=request.data.get('project_id'))
    abs_path = request.data.get('abs_path')

    is_match = DBFunctions.checkAbsPathToCodeFile(project, abs_path)
    return Response({"match": is_match})

from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
import os

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def addNextCodeFileVersion_View(request):
    data = request.data
    
    project = get_object_or_404(Project, pk=data.get('project_id'))
    author = get_object_or_404(User, pk=data.get('author_id'))
    
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response({"error": "No file uploaded"}, status=400)

    # save the uploaded file somewhere 
    # so DB function can find it at a "localPath"
    temp_path = default_storage.save(f'tmp/{uploaded_file.name}', uploaded_file)
    full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_path)

    try:
        # pass the full_temp_path as the 'localPath'
        new_version = DBFunctions.addNextCodeFileVersionToDB(
            project, 
            author, 
            data.get('message'), 
            full_temp_path
        )

        if new_version:
            serializer = ProjectVersionSerializer(new_version)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({"error": "Failed to process version"}, status=500)

    finally:
        # delete the temp file after processing
        if os.path.exists(full_temp_path):
            os.remove(full_temp_path)

@api_view(['POST'])
def addInitialCodeFileToDB_View(request):
    data = request.data
    
    # 1. Resolve the IDs to actual Objects
    user = get_object_or_404(User, pk=data.get('user_id'))
    repo = get_object_or_404(Repository, pk=data.get('repo_id'))
    
    # 2. Call the logic
    # Note: filePath here is the relative path within the repo folder
    success = DBFunctions.addInitialCodeFileToDB(
        user, 
        repo, 
        data.get('title'), 
        data.get('filePath'), 
        data.get('timestamp')
    )
    
    if success:
        return Response({"message": "Initial file versioned and added to DB"}, status=status.HTTP_201_CREATED)
    
    return Response({"error": "Failed to initialize code file in DB"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def removeRepositoryFromDB_View(request, repo_id):
    user = get_object_or_404(User, pk=request.data.get('user_id'))
    repo_obj = get_object_or_404(Repository, pk=repo_id)
    repo_type = request.data.get('repo_type', 'Studio')

    success = DBFunctions.removeRepositoryFromDB(user, repo_obj, repo_type)
    
    if success:
        return Response({"message": "Repository and all associated data permanently deleted"}, status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Failed to delete repository"}, status=500)


@api_view(['POST'])
def createRepositoryInDB_View(request):
    """
    Directly bridges the API to DBFunctions.createRepositoryInDB
    """
    data = request.data

    # 1. Get the User object (required for the function)
    user_id = data.get('user_id')
    user = get_object_or_404(User, pk=user_id)

    # 2. Extract the raw string data
    title = data.get('title')
    input_path = data.get('inputPath')
    repo_type = data.get('repoType', 'Code')  # Default to Code if not specified

    if not title or not input_path:
        return Response(
            {"error": "Missing title or inputPath"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Call your function directly
    # This will trigger the shutil.copytree and the addInitialCodeFileToDB loop
    success = DBFunctions.createRepositoryInDB(
        user=user,
        title=title,
        inputPath=input_path,
        repoType=repo_type
    )

    # 4. Return response based on the boolean returned by your function
    if success:
        return Response(
            {"message": f"Repository '{title}' created and indexed successfully."},
            status=status.HTTP_201_CREATED
        )
    else:
        return Response(
            {"error": "Failed to create repository. Check server console for errors."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
def getUserRole_View(request):
    user_id = request.GET.get('user_id')
    repo_id = request.GET.get('repo_id')
    try:
        membership = RepositoryMembership.objects.get(
            user_id=user_id,
            repository_id=repo_id
        )
        return Response({'role': membership.repo_role}, status=200)
    except RepositoryMembership.DoesNotExist:
        return Response({'role': 'None'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
def updateProjectVersionStatus_View(request, version_id):
    try:
        # 1. Find the real DB object
        version = ProjectVersion.objects.get(id=version_id)

        # 2. Get the new status from request data
        new_status = request.data.get('status', 'Approved')

        # 3. Update and Save
        version.status = new_status
        version.save(update_fields=['status'])

        return Response({'message': f'Version status updated to {new_status}'}, status=status.HTTP_200_OK)

    except ProjectVersion.DoesNotExist:
        return Response({'error': 'Version not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def getRepoMembers_View(request, repo_id):
    try:
        # Optimized query using select_related to get user data in one go
        memberships = RepositoryMembership.objects.filter(
            repository_id=repo_id
        ).select_related('user')

        member_list = []
        for m in memberships:
            member_list.append({
                'id' : m.id,
                'user_id': m.user.id,
                'username': m.user.username,
                'role': m.repo_role,
                'joined_at': m.joined_at if hasattr(m, 'joined_at') else None
            })

        return Response(member_list, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
def updateMemberRole_View(request, m_id):
    try:
        membership = RepositoryMembership.objects.get(id=m_id)
        new_role = request.data.get('role')

        if new_role not in ["Admin", "Reviewer", "Author", "Guest", "Removed"]:
            return Response({'error': 'Invalid role'}, status=400)

        membership.repo_role = new_role
        membership.save(update_fields=['repo_role'])
        return Response({'message': 'Role updated'}, status=200)
    except RepositoryMembership.DoesNotExist:
        return Response({'error': 'Membership not found'}, status=404)


import hashlib


def hash_password(password):
    salt = os.urandom(16).hex()  # Creates a 32-character hex string
    hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
    return f"{salt}:{hash_obj.hexdigest()}"


def verify_password(stored_val, provided_password):
    try:
        # If the DB doesn't have a colon, it's an old plain-text password
        if ":" not in stored_val:
            return False

        salt, original_hash = stored_val.split(':')
        # Hash the attempt using the salt we found in the DB
        new_hash = hashlib.sha256((provided_password + salt).encode('utf-8')).hexdigest()

        return new_hash == original_hash
    except Exception:
        return False
@api_view(['POST'])
def login_view(request):
    print("got to login view")
    username = request.data.get('username')
    # Use .strip() to remove any accidental whitespace from the GUI input
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'error': 'Missing credentials'}, status=400)

    potential_user = User.objects.filter(username=username).first()

    # CHECK: Pass the DB string AND the user's input
    if potential_user is None or not verify_password(potential_user.password_hash, password):
        return Response({'error': 'Invalid credentials'}, status=401)

    # Success
    DBFunctions.userLogIn(potential_user)

    return Response({
        'id': potential_user.id,
        'username': potential_user.username,
        'role': potential_user.role
    }, status=200)


@api_view(['POST'])
def addRepoMember_View(request):
    username = request.data.get('username')
    role = request.data.get('role')
    repo_id = request.data.get('repository_id')
    admin_id = request.data.get('admin_id')  # The person performing the action

    try:
        # 1. Check if user exists
        target_user = User.objects.get(username=username)

        # 2. Update or Create membership
        membership, created = RepositoryMembership.objects.update_or_create(
            user=target_user,
            repository_id=repo_id,
            defaults={'repo_role': role}
        )

        # 3. Log the action to AuditLog
        AuditLog.objects.create(
            user_id=admin_id,
            action="ADD_MEMBER",
            repository_id=repo_id,
            details=f"Added {username} as {role}"
        )

        status = "Added" if created else "Updated"
        return Response({'message': f'Successfully {status} {username}', 'status': status}, status=200)

    except User.DoesNotExist:
        return Response({'error': f"User '{username}' not found."}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def logout_view(request):
    user_id = request.data.get('user_id')

    try:
        user = User.objects.get(id=user_id)
        user.loginStatus = 0
        user.save()
        return Response({'message': 'Logged out successfully'}, status=200)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@api_view(['POST'])
def register_user_view(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)

    try:
        # --- THE FIX: HASH THE PASSWORD HERE ---
        hashed_pw = hash_password(password)

        new_user = User.objects.create(
            username=username,
            email=email if email else "no email",
            password_hash=hashed_pw, # Store the salted hash
            role="UNUSED",
            loginStatus=0,
            created_at=timezone.now()
        )
        return Response({'message': 'Registration successful'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

import logging
logger = logging.getLogger(__name__)

@api_view(['POST'])
def create_project_version_view(request):
    try:
        # Debug print to see what the server is actually receiving
        print(f"[DEBUG] Received Data: {request.data}")

        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')
        message = request.data.get('message', '')
        path = request.data.get('path', '')
        status = request.data.get('status', 'Pending')

        if not project_id or not user_id:
            return Response({"success": False, "error": "project_id and user_id are required"}, status=400)

        # Fetch actual objects
        project = Project.objects.get(pk=project_id)
        user = User.objects.get(pk=user_id)

        # Execute logic
        new_version = DBFunctions.addNextProjectVersionToDB(project, user, message, path, status)

        return Response({
            "success": True,
            "version_id": new_version.id,
            "version_number": new_version.version_number
        }, status=201)

    except Project.DoesNotExist:
        return Response({"success": False, "error": "Project not found"}, status=404)
    except User.DoesNotExist:
        return Response({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        # This will print the actual error to your Django terminal
        import traceback
        traceback.print_exc()
        return Response({"success": False, "error": str(e)}, status=500)
@api_view(['GET'])
def get_versions_by_file_view(request):
    """
    Returns all ProjectVersions associated with a specific file ID.
    URL Pattern: /api/utility/file-versions/?file_id=123
    """
    try:
        file_id = request.query_params.get('file_id')
        if not file_id:
            return Response({"success": False, "error": "file_id is required"}, status=400)

        # We filter versions that contain this file.
        # Using 'files__id' or 'projectversionfile__id' depending on your schema.
        # Based on your last error, 'versions' was the M2M, so we query ProjectVersion directly:
        queryset = ProjectVersion.objects.filter(
            files__id=file_id
        ).values('id', 'version_number', 'project__title', 'message', 'created_at')

        return Response({
            "success": True,
            "versions": list(queryset)
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"success": False, "error": str(e)}, status=500)