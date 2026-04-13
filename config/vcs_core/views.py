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
    #get parameters from /api/utility/get-path/?id=5&type=Project
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
def addProjectAndInitialVersionToDB_View(request):
    data = request.data
    user = get_object_or_404(User, pk=data.get('user_id'))
    repo = get_object_or_404(Repository, pk=data.get('repo_id'))

    success = DBFunctions.addProjectAndInitialVersionToDB(
        user, 
        repo, 
        data.get('title'), 
        data.get('description'), 
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

@api_view(['POST'])
def createRepositoryInDB_View(request):
    data = request.data
    user = get_object_or_404(User, pk=data.get('user_id'))
    
    repo_type = data.get('repo_type', 'Studio')
    
    success = DBFunctions.createRepositoryInDB(
        user, 
        data.get('title'), 
        data.get('input_path'), 
        repo_type
    )
    
    if success:
        return Response({"message": f"Repository '{data.get('title')}' created and indexed"}, status=status.HTTP_201_CREATED)
    return Response({"error": "Failed to create repository"}, status=500)

@api_view(['DELETE'])
def removeRepositoryFromDB_View(request, repo_id):
    user = get_object_or_404(User, pk=request.data.get('user_id'))
    repo_obj = get_object_or_404(Repository, pk=repo_id)
    repo_type = request.data.get('repo_type', 'Studio')

    success = DBFunctions.removeRepositoryFromDB(user, repo_obj, repo_type)
    
    if success:
        return Response({"message": "Repository and all associated data permanently deleted"}, status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Failed to delete repository"}, status=500)