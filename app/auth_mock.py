# Temporary mock auth functions for development
from typing import List, Any, Callable
from fastapi import Depends, HTTPException, status


def get_current_user():
    """Mock current user - returns a simple dict for development"""
    return {"id": "dev-user", "name": "Development User", "roles": ["ADMIN"]}


def require_roles(roles: List[str]):
    """Mock role requirement - always passes for development"""
    def dependency():
        return True
    return dependency


def require_api_permission(permission_code: str):
    """Mock API permission check - always passes for development"""
    def dependency():
        return True
    return dependency
