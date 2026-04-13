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

#POST
def addProjectAndInitialVersion_Upload_Client(user_id, repo_id, title, description, local_file_path):
    url = f"{BASE_URL}/projects/create-with-initial/"
    try:
        with open(local_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'user_id': user_id,
                'repo_id': repo_id,
                'title': title,
                'description': description,
                'timestamp': datetime.now().isoformat()
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

def getVersionsByFileID_Client(inputVersionFileID):
    return _api_call('GET', f'/files/{inputVersionFileID}/versions-summary/')

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