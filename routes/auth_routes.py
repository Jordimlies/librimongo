"""
Authentication routes for LibriMongo application.
Handles user registration, login, and logout.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from services.auth_service import register_user, authenticate_user, login, logout
from models.mariadb_models import User

# Create blueprint
auth_bp = Blueprint('auth_routes', __name__)

# Form classes
class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[Length(max=64)])
    last_name = StringField('Last Name', validators=[Length(max=64)])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Validate that the username is unique."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Validate that the email is unique."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

# Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login_route():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        success, user_or_error = authenticate_user(form.username.data, form.password.data)
        if success:
            login(user_or_error, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            flash('Login successful!', 'success')
            return redirect(next_page)
        else:
            flash(user_or_error, 'danger')
    
    return render_template('login.html', form=form, title='Log In')

@auth_bp.route('/logout')
@login_required
def logout_route():
    """Handle user logout."""
    logout()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_route():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        success, user_or_error = register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        
        if success:
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth_routes.login_route'))
        else:
            flash(user_or_error, 'danger')
    
    return render_template('register.html', form=form, title='Register')