# Simple auth stub for development
def get_current_user():
    """Mock current user - returns a simple dict for development"""
    return {"id": "dev-user", "name": "Development User", "roles": ["ADMIN"]}

def require_roles(*roles):
    """Mock role requirement - always passes for development"""
    def dependency():
        return True
    return dependency

def require_api_permission(permission_code: str):
    """Mock API permission check - always passes for development"""
    def dependency():
        return True
    return dependency