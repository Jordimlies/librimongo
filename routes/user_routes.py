"""
User routes for LibriMongo application.
Handles user profile management, reading history, and book interactions.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from services.user_service import (
    get_user_profile, get_user_reading_history, get_user_reviews,
    get_user_recommendations, get_user_active_loans, get_user_reading_preferences,
    update_user_preferences, get_overdue_loans, get_user_statistics
)
from services.auth_service import change_password, update_user_profile
from services.book_service import get_genres
from services.auth_service import require_role
from models.mariadb_models import User, db

# Create blueprint
user_bp = Blueprint('user_routes', __name__, url_prefix='/user')

# Form classes
class ProfileForm(FlaskForm):
    """Form for updating user profile."""
    first_name = StringField('First Name', validators=[Optional(), Length(max=64)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Update Profile')

class PasswordChangeForm(FlaskForm):
    """Form for changing password."""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')

class PreferencesForm(FlaskForm):
    """Form for updating reading preferences."""
    preferred_genres = SelectMultipleField('Preferred Genres', choices=[])
    preferred_authors = StringField('Preferred Authors', validators=[Optional()])
    reading_frequency = StringField('Reading Frequency', validators=[Optional()])
    submit = SubmitField('Update Preferences')

# Routes
@user_bp.route('/profile')
@login_required
def profile():
    """Display user profile."""
    profile_data = get_user_profile(current_user.id)
    if not profile_data:
        abort(404)
    
    # Get user statistics
    statistics = get_user_statistics(current_user.id)
    
    # Get reading preferences
    preferences = get_user_reading_preferences(current_user.id)
    
    return render_template(
        'user_profile.html',
        profile=profile_data,
        statistics=statistics,
        preferences=preferences
    )

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        success, message = update_user_profile(
            current_user,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('user_routes.profile'))
        else:
            flash(message, 'danger')
    
    return render_template('user_edit_profile.html', form=form)

@user_bp.route('/password/change', methods=['GET', 'POST'])
@login_required
def change_password_route():
    """Change user password."""
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        success, message = change_password(
            current_user,
            form.current_password.data,
            form.new_password.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('user_routes.profile'))
        else:
            flash(message, 'danger')
    
    return render_template('user_change_password.html', form=form)

@user_bp.route('/history')
@login_required
def reading_history():
    """Muestra el historial de lectura del usuario."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    include_active = request.args.get('include_active', 'true') == 'true'
    
    history_items, total_pages, total_items = get_user_reading_history(
        current_user.id,
        page=page,
        per_page=per_page,
        include_active=include_active
    )
    
    return render_template(
        'user_reading_history.html',
        history_items=history_items,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total_items,
        include_active=include_active
    )

@user_bp.route('/reviews')
@login_required
def reviews():
    """Display user reviews."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    reviews_with_books, total_pages, total_items = get_user_reviews(
        current_user.id,
        page=page,
        per_page=per_page
    )
    
    return render_template(
        'user_reviews.html',
        reviews=reviews_with_books,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total_items
    )

@user_bp.route('/loans')
@login_required
def loans():
    # Obtener préstamos activos y asegurarse de que sea una lista
    active_loans = get_user_active_loans(current_user.id)
    overdue_loans = get_overdue_loans(current_user.id)
    
    # Obtener recomendaciones para el usuario
    from services.recommendation_service import get_recommendations_for_user
    recommendations = get_recommendations_for_user(current_user.id, limit=5)
    
    # Obtener estadísticas del usuario
    from services.user_service import get_user_statistics
    statistics = get_user_statistics(current_user.id)

    return render_template(
        'user_dashboard.html',
        active_loans=active_loans,  # Ya es una lista desde get_user_active_loans
        overdue_loans=overdue_loans,
        recommendations=recommendations,
        statistics=statistics
    )

@user_bp.route('/recommendations')
@login_required
def recommendations():
    """Display personalized book recommendations."""
    limit = request.args.get('limit', 10, type=int)
    
    recommended_books = get_user_recommendations(current_user.id, limit=limit)
    
    return render_template(
        'user_recommendations.html',
        recommendations=recommended_books,
        limit=limit
    )

@user_bp.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """Actualizar las preferencias de lectura del usuario."""
    # Obtener todos los géneros disponibles
    all_genres = get_genres()

    # Obtener las preferencias actuales del usuario desde MongoDB
    user_preferences = get_user_reading_preferences(current_user.id)

    # Crear el formulario
    form = PreferencesForm()
    form.preferred_genres.choices = [(genre, genre) for genre in all_genres]

    # Prellenar el formulario con las preferencias actuales
    if request.method == 'GET':
        form.preferred_genres.data = user_preferences.get('preferred_genres', [])
        form.preferred_authors.data = ', '.join(user_preferences.get('preferred_authors', [])).split(', ')
        form.reading_frequency.data = user_preferences.get('reading_frequency', 'new_reader')

    if form.validate_on_submit():
        # Guardar las preferencias en MongoDB
        success = update_user_preferences(
            user_id=current_user.id,
            preferred_genres=form.preferred_genres.data,
            preferred_authors=request.form.get('preferred_authors', '').split(','),
            reading_frequency=request.form.get('reading_frequency')
        )

        if success:
            flash('Preferencias actualizadas correctamente.', 'success')
            return redirect(url_for('user_routes.profile'))
        else:
            flash('Error al actualizar las preferencias.', 'danger')

    return render_template(
        'user_preferences.html',
        form=form,
        current_preferences=user_preferences
    )

@user_bp.route('/statistics')
@login_required
def statistics():
    """Display detailed user statistics."""
    stats = get_user_statistics(current_user.id)
    
    return render_template(
        'user_statistics.html',
        statistics=stats
    )

@user_bp.route('/<int:user_id>')
@login_required
@require_role('admin')
def view_user(user_id):
    """Admin view of a user profile."""
    profile_data = get_user_profile(user_id)
    if not profile_data:
        abort(404)
    
    # Get user statistics
    statistics = get_user_statistics(user_id)
    
    # Get reading preferences
    preferences = get_user_reading_preferences(user_id)
    
    # Get active loans
    active_loans = get_user_active_loans(user_id)
    
    return render_template(
        'admin_user_view.html',
        profile=profile_data,
        statistics=statistics,
        preferences=preferences,
        active_loans=active_loans
    )

@user_bp.route('/admin/users')
@login_required
@require_role('admin')
def manage_users():
    if not current_user.is_admin:
        abort(403)
    
    users = User.query.order_by(User.id).all()
    return render_template("manage_users.html", users=users)

# Edit user route
@user_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = ProfileForm(obj=user)

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        try:
            db.session.commit()
            flash('Usuario actualizado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el usuario: {e}', 'danger')
        return redirect(url_for('user_routes.manage_users'))

    return render_template('edit_user.html', form=form, user=user)

# Delete user route
@user_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@require_role('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("No puedes eliminar tu propia cuenta mientras estás conectado.", 'danger')
        return redirect(url_for('user_routes.manage_users'))
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash("Usuario eliminado correctamente.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {e}', 'danger')
    
    return redirect(url_for('user_routes.manage_users'))

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with overview of loans, recommendations, and activity."""
    # Get active loans
    active_loans = get_user_active_loans(current_user.id)
    
        # Depuración: Verifica el valor de active_loans
    print(f"active_loans: {active_loans} (type: {type(active_loans)})")
    
    # Get overdue loans
    overdue_loans = get_overdue_loans(current_user.id)
    
    # Get recommendations
    recommendations = get_user_recommendations(current_user.id, limit=5)
    
    # Get reading statistics
    statistics = get_user_statistics(current_user.id)

    return render_template(
        'user_dashboard.html',
        active_loans=len(active_loans),
        overdue_loans=overdue_loans,
        recommendations=recommendations,
        statistics=statistics
    )