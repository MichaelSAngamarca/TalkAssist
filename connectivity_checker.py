
import requests
import socket
import time

def check_internet_connectivity(timeout: int = 5) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        pass
    
    try:
        response = requests.get("https://www.google.com", timeout=timeout)
        return response.status_code == 200
    except (requests.RequestException, OSError):
        pass
    
    return False

def check_api_connectivity(api_url: str, timeout: int = 5) -> bool:
    try:
        response = requests.get(api_url, timeout=timeout)
        return response.status_code in [200, 401, 403]  
    except (requests.RequestException, OSError):
        return False

def safe_api_call(func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except requests.RequestException as e:
        return False, None, f"Network error: {str(e)}"
    except Exception as e:
        return False, None, f"API error: {str(e)}"
