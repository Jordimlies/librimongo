"""
Routes package for LibriMongo application.
Contains all route blueprints for the application.
"""

# Import blueprints
from routes.auth_routes import auth_bp

# List of all blueprints
__all__ = ['auth_bp']