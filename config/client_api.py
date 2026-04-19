import requests

BASE_URL = "http://127.0.0.1:8000/api"

from datetime import datetime

class Map(dict):
    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for key, value in self.items():
            # 1. Handle Nested Dicts
            if isinstance(value, dict):
                self[key] = Map(value)
            # 2. Handle Lists
            elif isinstance(value, list):
                self[key] = [Map(i) if isinstance(i, dict) else i for i in value]
            # 3. Handle Date Strings (The strftime fix)
            elif isinstance(value, str) and key in ['timestamp', 'created_at', 'updated_at']:
                try:
                    # ISO format is what Django Serializers usually send
                    self[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass 

    def __getattr__(self, name):
        if name in self:
            return self[name]
        return Map()

def to_map(data):
    """Converts a dict or a list of dicts into Map objects."""
    if isinstance(data, list):
        return [Map(item) for item in data]
    if isinstance(data, dict):
        return Map(data)
    return data

def _api_call(method, endpoint, data=None, files=None):
    url = f"{BASE_URL}{endpoint}"
    print("accesing url: ", url)
    try:
        if method == 'GET':
            response = requests.get(url, params=data, timeout=10)
        elif method == 'POST':
            response = requests.post(url, data=data, files=files, timeout=15)
        elif method == 'DELETE':
            response = requests.delete(url, json=data, timeout=10)
        
        print("response code: ", response.status_code)
        if response.status_code in [200, 201, 204]:
            if response.status_code == 204: 
                return True
            return to_map(response.json())
        
        return False
    except Exception as e:
        print(f"API Error: {e}")
        return False


# API CALL FUNCTIONS BELOW

def getUserAuditLogs_Client(user_id):
    return _api_call('GET', f'/logs/user/{user_id}/')

def getProjectAuditLogs_Client(project_id):
    return _api_call('GET', f'/logs/project/{project_id}/')

def getRepoAuditLogsByRepo_Client(repo_id):
    return _api_call('GET', f'/repos/{repo_id}/logs/')

def getProjectVersionAuditLogsByID_Client(inputProjectVersionID):
    return _api_call('GET', f'/logs/version/{inputProjectVersionID}/')

def getRepoAuditLogsByRepoName_Client(repo_name):
    return _api_call('GET', f'repos/name/{repo_name}/logs/')
def getUserRole_Client(user_id,repository_id):
    """
        Fetches the role of a specific user within a specific repository.
        """
    payload = {
        'user_id': user_id,
        'repo_id': repository_id
    }
    # result will be a Map object like {'role': 'Admin'}
    result = _api_call('GET', '/repos/membership/role/', data=payload)

    return result.role if result else "Guest"
#POST
def addProjectAndInitialVersion_Upload_Client(user_id, repo_id, title, description, local_file_path):
    url = f"{BASE_URL}/projects/create-with-initial-drop/"
    try:
        with open(local_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'user_id': user_id,
                'repo_id': repo_id,
                'title': title,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'filePath':local_file_path
            }

            response = requests.post(url, data=data, files=files)
            return response.status_code == 201
    except Exception as e:
        print(f"File Upload Error: {e}")
        return False


def getElementRelativePath_Client(element_id, element_type, context_id=None):
    """
    Fetches the relative path for a specific DB element.
    URL format: /utility/get-path/?id=5&type=Project&context_id=10
    """
    params = {
        'id': element_id,
        'type': element_type
    }
    if context_id:
        params['context_id'] = context_id

    result = _api_call('GET', '/utility/get-path/', data=params)

    # Since the view returns {"relative_path": "..."},
    # and our helper returns a Map, we can access it with .relative_path
    return result.relative_path if result else ""

def removeRepository_Client(user_id, repo_id, repo_type='Studio'):
    """
    Calls the DELETE view to wipe a repository.
    """
    payload = {
        'user_id': user_id,
        'repo_type': repo_type
    }
    
    return _api_call('DELETE', f'/repositories/{repo_id}/delete/', data=payload)

def getUserRepos_Client(user_id, repo_type="Studio"):
    params={'repoType':repo_type}
    return _api_call('GET', f'/users/{user_id}/repos/', data=params)

def addVersionFileToDB_Client(user_id, version_id, file_path, content):
    """
    Adds a file record to a specific project version.
    """
    payload = {
        'user_id': user_id,
        'version_id': version_id,
        'path': file_path,
        'content': content
    }
    
    return _api_call('POST', '/files/add-to-version/', data=payload)

def getProjectVersionFilesByProjectVersionID_Client(inputVersionID):
    return _api_call('GET', f'/versions/{inputVersionID}/files/')

#path('files/remove-from-version/', views.removeVersionFileFromDB_View),
def removeVersionFileFromDB_Client(user_id, file_id, version_id):
    payload = {
        'user_id': user_id,
        'file_id': file_id,
        'version_id': version_id
    }
    
    return _api_call('DELETE', '/files/remove-from-version/', data=payload)

def getRepoProjectsByRepo_Client(repo_id):
    return _api_call('GET', f'/repos/{repo_id}/projects/')


def getLatestProjectVersion_Client(project_id):
    return _api_call('GET', f'/projects/{project_id}/latest-version/')

def getLatestApprovedProjectVersion_Client(project_id):
    return _api_call('GET', f'/projects/{project_id}/latest-approved-version/')

import requests


def api_create_repository(user,repo_name, folder_path,program_type):
    """
    Sends a request to the server view to execute DBFunctions.createRepositoryInDB
    """
    url = f"{BASE_URL}/repositories/create/"  # Match the URL in your urls.py

    payload = {
        "user_id": user.id,
        "title": repo_name,
        "inputPath": folder_path,
        "repoType": program_type
    }

    try:
        response = requests.post(url, json=payload)

        if response.status_code == 201:
            print(f"Server Success: {response.json().get('message')}")
            return True
        else:
            print(f"Server Error ({response.status_code}): {response.text}")
            return False

    except Exception as e:
        print(f"Connection Error: {e}")
        return False
def api_removeProjectVersionFromDB(user, version_obj):
    """
        Calls the DELETE view to remove a specific project version.
        URL: /api/versions/<version_id>/delete/
        """
    payload = {
        'user_id': user.id
    }

    # Matching the URL pattern: path('versions/<int:version_id>/delete/', ...)
    return _api_call('DELETE', f'/versions/{version_obj.id}/delete/', data=payload)
def api_removeProjectFromDB(user, projectID):
    """
    Calls the DELETE view to wipe a specific project (Code File) from the DB.
    URL: /api/projects/<project_id>/delete/
    """
    payload = {
        'user_id': user.id
    }

    # Matching your route: path('projects/<int:project_id>/delete/', views.removeProjectFromDB_View)
    return _api_call('DELETE', f'/projects/{projectID}/delete/', data=payload)
def updateProjectVersionStatus_Client(version_id, new_status="Approved"):
    """
    Sends a POST request to update the status of a specific version.
    """
    payload = {
        'status': new_status
    }
    # Matches the URL: /api/versions/<id>/update-status/
    return _api_call('POST', f'/versions/{version_id}/update-status/', data=payload)
def getRepoMembers_Client(repo_id):
    """
    Fetches all members and their roles for a specific repository.
    """
    # URL: /api/repos/<repo_id>/members/
    return _api_call('GET', f'/repos/{repo_id}/members/')
def updateMemberRole_Client(membership_id, new_role):
    """
    Updates the role of a specific membership record.
    """
    payload = {'role': new_role}
    return _api_call('POST', f'/repos/membership/{membership_id}/update-role/', data=payload)


def login_request(credentials):
    """
    Sends a login request to the server.
    'credentials' should be a dict: {'username': '...', 'password': '...'}
    """
    try:
        # Update the URL path to match your server's routing
        endpoint = "/api/login/"

        # Making the POST call to the server
        response = _api_call('POST', endpoint, data=credentials)

        if response:
            # The server should return the user object (id, username, role, etc.)
            print(f"Login successful for: {response.get('username')}")
            return response
        else:
            print("Login failed: Invalid credentials or server error.")
            return None

    except Exception as e:
        print(f"Connection Error during login: {e}")
        return None
def addRepoMember_Client(username, role, repo_id, admin_id):
    payload = {
        'username': username,
        'role': role,
        'repository_id': repo_id,
        'admin_id': admin_id
    }
    return _api_call('POST', '/repos/add-member/', data=payload)
def logout_request(user_id):
    """
    Tells the server to set the user's loginStatus to 0.
    """
    payload = {'user_id': user_id}
    return _api_call('POST', '/api/logout/', data=payload)

def register_request(username, email, password):
    """
    Sends a registration request to the server.
    """
    payload = {
        'username': username,
        'email': email,
        'password': password
    }
    return _api_call('POST', '/api/register/', data=payload)


def addNextProjectVersion_Client(project_id, user_id, message, path, status):
    try:
        # Ensure we are sending integers, not objects or keys
        p_id = int(project_id)
        u_id = int(user_id)
    except (ValueError, TypeError):
        print(f"[ERROR] API Call failed: project_id({project_id}) or user_id({user_id}) is not a number!")
        return {"success": False, "error": "Invalid ID format sent to server"}

    payload = {
        "project_id": p_id,
        "user_id": u_id,
        "message": str(message),
        "path": str(path),
        "status": str(status)
    }

    return _api_call('POST', '/projects/add-version/', data=payload)


def getVersionsByFileID_Client(file_id):
    """
    Calls the server to get all versions associated with a file.
    """
    endpoint = f'/utility/file-versions/{file_id}'
    response = _api_call('GET', endpoint)

    if isinstance(response, dict) and response.get('success'):
        return response.get('versions', [])

    print(f"[ERROR] Failed to fetch versions for file {file_id}: {response}")
    return []