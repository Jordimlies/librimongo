"""
Rutas de autenticación para la aplicación LibriMongo.
Gestiona el registro, inicio y cierre de sesión de usuarios.
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
    """Formulario para el inicio de sesión del usuario."""
    username = StringField('Usuario o Correo Electrónico', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    """Formulario para el registro de usuarios."""
    username = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Correo Electrónico', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('Nombre', validators=[Length(max=64)])
    last_name = StringField('Apellido', validators=[Length(max=64)])
    submit = SubmitField('Registrarse')
    
    def validate_username(self, username):
        """Valida que el nombre de usuario sea único."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('El nombre de usuario ya existe. Por favor, elige otro.')
    
    def validate_email(self, email):
        """Valida que el correo electrónico sea único."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Correo electrónico ya registrado. Por favor, utiliza otro.')

# Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login_route():
    """Gestiona el inicio de sesión del usuario."""
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
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(next_page)
        else:
            flash(user_or_error, 'danger')
    
    return render_template('login.html', form=form, title='Log In')

@auth_bp.route('/logout')
@login_required
def logout_route():
    """Gestiona el cierre de sesión del usuario."""
    logout()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_route():
    """Gestiona el registro de nuevos usuarios."""
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
            flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth_routes.login_route'))
        else:
            flash(user_or_error, 'danger')
    
    return render_template('register.html', form=form, title='Register')