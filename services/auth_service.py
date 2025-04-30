"""
Authentication service for LibriMongo application.
Handles user registration, login, logout, and role-based access control.
"""

from flask import current_app, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models.mariadb_models import User, db
from utils.helpers import log_activity

def register_user(username, email, password, first_name=None, last_name=None, is_admin=False):
    """
    Register a new user.
    
    Args:
        username (str): The username for the new user
        email (str): The email address for the new user
        password (str): The password for the new user
        first_name (str, optional): The first name of the user
        last_name (str, optional): The last name of the user
        is_admin (bool, optional): Whether the user is an admin
        
    Returns:
        tuple: (success, user_or_error_message)
    """
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return False, "Username already exists"
    
    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return False, "Email already exists"
    
    # Create new user
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_admin=is_admin
    )
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        log_activity('user_registration', user_id=user.id)
        return True, user
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error registering user: {str(e)}")
        return False, "Error registering user"

def authenticate_user(username_or_email, password):
    """
    Authenticate a user with username/email and password.
    
    Args:
        username_or_email (str): The username or email of the user
        password (str): The password of the user
        
    Returns:
        tuple: (success, user_or_error_message)
    """
    # Check if input is email or username
    if '@' in username_or_email:
        user = User.query.filter_by(email=username_or_email).first()
    else:
        user = User.query.filter_by(username=username_or_email).first()
    
    if not user:
        return False, "Invalid username or email"
    
    if not user.check_password(password):
        log_activity('failed_login_attempt', user_id=user.id)
        return False, "Invalid password"
    
    log_activity('user_login', user_id=user.id)
    return True, user

def login(user, remember=False):
    """
    Log in a user.
    
    Args:
        user (User): The user to log in
        remember (bool, optional): Whether to remember the user's session
        
    Returns:
        bool: Whether the login was successful
    """
    return login_user(user, remember=remember)

def logout():
    """
    Log out the current user.
    
    Returns:
        bool: Whether the logout was successful
    """
    if current_user.is_authenticated:
        log_activity('user_logout', user_id=current_user.id)
    return logout_user()

def change_password(user, current_password, new_password):
    """
    Change a user's password.
    
    Args:
        user (User): The user whose password to change
        current_password (str): The user's current password
        new_password (str): The new password
        
    Returns:
        tuple: (success, message)
    """
    if not user.check_password(current_password):
        return False, "Current password is incorrect"
    
    user.set_password(new_password)
    
    try:
        db.session.commit()
        log_activity('password_change', user_id=user.id)
        return True, "Password changed successfully"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password: {str(e)}")
        return False, "Error changing password"

def update_user_profile(user, first_name=None, last_name=None, email=None):
    """
    Update a user's profile information.
    
    Args:
        user (User): The user to update
        first_name (str, optional): The new first name
        last_name (str, optional): The new last name
        email (str, optional): The new email
        
    Returns:
        tuple: (success, message)
    """
    if email and email != user.email:
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return False, "Email already exists"
        user.email = email
    
    if first_name:
        user.first_name = first_name
    
    if last_name:
        user.last_name = last_name
    
    try:
        db.session.commit()
        log_activity('profile_update', user_id=user.id)
        return True, "Profile updated successfully"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        return False, "Error updating profile"

def require_role(role):
    """
    Decorator to require a specific role for a route.
    
    Args:
        role (str): The role required to access the route
        
    Returns:
        function: The decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            
            if role == 'admin' and not current_user.is_admin:
                return current_app.login_manager.unauthorized()
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_admin(user):
    """
    Check if a user is an admin.
    
    Args:
        user (User): The user to check
        
    Returns:
        bool: Whether the user is an admin
    """
    return user.is_admin