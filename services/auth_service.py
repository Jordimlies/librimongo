"""
Servicio de autenticación para la aplicación LibriMongo.
Gestiona el registro de usuarios, el inicio y cierre de sesión, y el control de acceso basado en roles.
"""

from flask import current_app, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models.mariadb_models import User, db
from utils.helpers import log_activity

def register_user(username, email, password, first_name=None, last_name=None, is_admin=False):
    """
    Registra un nuevo usuario.
    
    Args:
        username (str): El nombre de usuario del nuevo usuario
        email (str): La dirección de correo electrónico del nuevo usuario
        password (str): La contraseña del nuevo usuario
        first_name (str, opcional): El nombre del usuario
        last_name (str, opcional): El apellido del usuario
        is_admin (bool, opcional): Si el usuario es administrador
    
    Retorna:
        tuple: (éxito, usuario_o_mensaje_de_error)
    """
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return False, "El nombre de usuario ya existe"
    
    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return False, "El correo electrónico ya existe"
    
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
        return False, "Error al registrar al usuario"

def authenticate_user(username_or_email, password):
    """
    Autentica a un usuario con nombre de usuario/correo electrónico y contraseña.
    
    Args:
        username_or_email (str): El nombre de usuario o correo electrónico
        password (str): La contraseña del usuario
    
    Retorna:
        tuple: (éxito, usuario_o_mensaje_de_error)
    """
    # Check if input is email or username
    if '@' in username_or_email:
        user = User.query.filter_by(email=username_or_email).first()
    else:
        user = User.query.filter_by(username=username_or_email).first()
    
    if not user:
        return False, "Nombre de usuario o correo electrónico no válido"
    
    if not user.check_password(password):
        log_activity('failed_login_attempt', user_id=user.id)
        return False, "Contraseña incorrecta"
    
    log_activity('user_login', user_id=user.id)
    return True, user

def login(user, remember=False):
    """
    Inicia sesión de un usuario.
    
    Args:
        user (User): El usuario que inicia sesión
        remember (bool, opcional): Si se debe recordar la sesión del usuario
    
    Retorna:
        bool: Si el inicio de sesión fue exitoso
    """
    return login_user(user, remember=remember)

def logout():
    """
    Cierra la sesión del usuario actual.
    
    Retorna:
        bool: Si el cierre de sesión fue exitoso
    """
    if current_user.is_authenticated:
        log_activity('user_logout', user_id=current_user.id)
    return logout_user()

def change_password(user, current_password, new_password):
    """
    Cambia la contraseña de un usuario.
    
    Args:
        user (User): El usuario cuya contraseña se cambiará
        current_password (str): La contraseña actual
        new_password (str): La nueva contraseña
    
    Retorna:
        tuple: (éxito, mensaje)
    """
    if not user.check_password(current_password):
        return False, "La contraseña actual es incorrecta"
    
    user.set_password(new_password)
    
    try:
        db.session.commit()
        log_activity('password_change', user_id=user.id)
        return True, "Contraseña cambiada correctamente"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password: {str(e)}")
        return False, "Error al cambiar la contraseña"

def update_user_profile(user, first_name=None, last_name=None, email=None):
    """
    Actualiza la información del perfil del usuario.
    
    Args:
        user (User): El usuario a actualizar
        first_name (str, opcional): El nuevo nombre
        last_name (str, opcional): El nuevo apellido
        email (str, opcional): El nuevo correo electrónico
    
    Retorna:
        tuple: (éxito, mensaje)
    """
    if email and email != user.email:
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return False, "El correo electrónico ya existe"
        user.email = email
    
    if first_name:
        user.first_name = first_name
    
    if last_name:
        user.last_name = last_name
    
    try:
        db.session.commit()
        log_activity('profile_update', user_id=user.id)
        return True, "Perfil actualizado correctamente"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        return False, "Error al actualizar el perfil"

def require_role(role):
    """
    Decorador para exigir un rol específico en una ruta.
    
    Args:
        role (str): El rol requerido para acceder a la ruta
    
    Retorna:
        function: La función decorada
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
    Verifica si un usuario es administrador.
    
    Args:
        user (User): El usuario a verificar
    
    Retorna:
        bool: Si el usuario es administrador
    """
    return user.is_admin