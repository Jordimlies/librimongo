"""
Test script for the authentication system.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager

# Create a test app with SQLite
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'test_secret_key'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Define User model for testing
class User(UserMixin, db.Model):
    """User model for authentication and user management."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    """Load a user from the database."""
    return User.query.get(int(user_id))

# Authentication functions for testing
def register_user(username, email, password, first_name=None, last_name=None, is_admin=False):
    """Register a new user."""
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
        return True, user
    except Exception as e:
        db.session.rollback()
        return False, f"Error registering user: {str(e)}"

def authenticate_user(username_or_email, password):
    """Authenticate a user with username/email and password."""
    # Check if input is email or username
    if '@' in username_or_email:
        user = User.query.filter_by(email=username_or_email).first()
    else:
        user = User.query.filter_by(username=username_or_email).first()
    
    if not user:
        return False, "Invalid username or email"
    
    if not user.check_password(password):
        return False, "Invalid password"
    
    return True, user

def test_auth_system():
    """Test the authentication system."""
    with app.app_context():
        # Create tables
        db.create_all()
        
        print("Testing user registration...")
        # Test user registration
        success, user_or_error = register_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User'
        )
        
        if success:
            print(f"User registration successful: {user_or_error}")
        else:
            print(f"User registration failed: {user_or_error}")
            return False
        
        print("\nTesting user authentication...")
        # Test user authentication with username
        success, user_or_error = authenticate_user('testuser', 'password123')
        if success:
            print(f"Authentication with username successful: {user_or_error}")
        else:
            print(f"Authentication with username failed: {user_or_error}")
            return False
        
        # Test user authentication with email
        success, user_or_error = authenticate_user('test@example.com', 'password123')
        if success:
            print(f"Authentication with email successful: {user_or_error}")
        else:
            print(f"Authentication with email failed: {user_or_error}")
            return False
        
        # Test user authentication with wrong password
        success, user_or_error = authenticate_user('testuser', 'wrongpassword')
        if not success:
            print(f"Authentication with wrong password correctly failed: {user_or_error}")
        else:
            print(f"Authentication with wrong password incorrectly succeeded")
            return False
        
        print("\nTesting role-based access control...")
        # Test admin role
        user = User.query.filter_by(username='testuser').first()
        user.is_admin = True
        db.session.commit()
        
        user = User.query.filter_by(username='testuser').first()
        if user.is_admin:
            print("Admin role assignment successful")
        else:
            print("Admin role assignment failed")
            return False
        
        print("\nAll authentication tests passed!")
        return True

if __name__ == '__main__':
    success = test_auth_system()
    sys.exit(0 if success else 1)