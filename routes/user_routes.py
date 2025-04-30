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
    """Display user reading history."""
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
    active_loans = get_user_active_loans(current_user.id)  # ✅ esto debe ser una LISTA
    overdue_loans = get_overdue_loans(current_user.id)

    return render_template(
        'user_dashboard.html',
        active_loans=list(active_loans),  # 👈 Esto fuerza la conversión a lista
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
    """Update user reading preferences."""
    # Get all available genres
    all_genres = get_genres()
    
    # Get user's current preferences
    user_preferences = get_user_reading_preferences(current_user.id)
    
    # Create form
    form = PreferencesForm()
    form.preferred_genres.choices = [(genre, genre) for genre in all_genres]
    
    if request.method == 'GET':
        form.preferred_genres.data = user_preferences.get('favorite_genres', [])
    
    if form.validate_on_submit():
        success = update_user_preferences(
            current_user.id,
            preferred_genres=form.preferred_genres.data
        )
        
        if success:
            flash('Preferences updated successfully.', 'success')
            return redirect(url_for('user_routes.profile'))
        else:
            flash('Error updating preferences.', 'danger')
    
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

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with overview of loans, recommendations, and activity."""
    # Get active loans
    active_loans = get_user_active_loans(current_user.id)
    
    # Get overdue loans
    overdue_loans = get_overdue_loans(current_user.id)
    
    # Get recommendations
    recommendations = get_user_recommendations(current_user.id, limit=5)
    
    # Get reading statistics
    statistics = get_user_statistics(current_user.id)
    
    return render_template(
        'user_dashboard.html',
        active_loans=active_loans,
        overdue_loans=overdue_loans,
        recommendations=recommendations,
        statistics=statistics
    )