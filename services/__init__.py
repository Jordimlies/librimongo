"""
Services package for LibriMongo application.
Contains all business logic services for the application.
"""

# Import services
from services.auth_service import (
    register_user, 
    authenticate_user, 
    login, 
    logout, 
    change_password, 
    update_user_profile, 
    require_role, 
    is_admin
)

# List of all services
__all__ = [
    'register_user',
    'authenticate_user',
    'login',
    'logout',
    'change_password',
    'update_user_profile',
    'require_role',
    'is_admin'
]