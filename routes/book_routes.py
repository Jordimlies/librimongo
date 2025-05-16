"""
Book routes for LibriMongo application.
Handles book listing, filtering, search, and book-specific actions.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, abort
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from services.book_service import (
    get_all_books, get_book_by_id, search_books, get_book_content,
    get_book_reviews, get_average_rating, add_review, lend_book,
    return_book, get_genres, get_languages, create_book, update_book,
    delete_book, update_book_content
)
from services.recommendation_service import get_recommendations_by_book, track_user_interaction
from services.user_service import track_book_view
from services.auth_service import require_role
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from models.mongodb_models import LoanHistory

# Create blueprint
book_bp = Blueprint('book_routes', __name__, url_prefix='/books')

# Form classes
class BookSearchForm(FlaskForm):
    """Form for searching books."""
    query = StringField('Search', validators=[Optional(), Length(min=2)])
    genre = SelectField('Genre', validators=[Optional()], choices=[])
    language = SelectField('Language', validators=[Optional()], choices=[])
    sort_by = SelectField('Sort by', choices=[
        ('title', 'Title'),
        ('author', 'Author'),
        ('year', 'Year')
    ])
    sort_order = SelectField('Order', choices=[
        ('asc', 'Ascending'),
        ('desc', 'Descending')
    ])
    submit = SubmitField('Search')

class ReviewForm(FlaskForm):
    """Form for adding a book review."""
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    text = TextAreaField('Review', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Review')

class BookForm(FlaskForm):
    """Form for adding or editing a book."""
    title = StringField('Title', validators=[DataRequired(), Length(max=256)])
    author = StringField('Author', validators=[DataRequired(), Length(max=128)])
    year = IntegerField('Year', validators=[Optional()])
    isbn = StringField('ISBN', validators=[Optional(), Length(max=20)])
    language = StringField('Language', validators=[Optional(), Length(max=20)])
    genre = StringField('Genre', validators=[Optional(), Length(max=64)])
    publisher = StringField('Publisher', validators=[Optional(), Length(max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    cover_image = FileField('Cover Image', validators=[Optional()])
    available_copies = IntegerField('Available Copies', validators=[DataRequired(), NumberRange(min=0)])
    total_copies = IntegerField('Total Copies', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Book')

class BookContentForm(FlaskForm):
    """Form for adding or editing book content."""
    content = TextAreaField('Book Content', validators=[DataRequired()])
    submit = SubmitField('Save Content')

# Routes
@book_bp.route('/')
def book_list():
    """Display a list of books with filtering and pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    # Initialize search form
    form = BookSearchForm()
    
    # Populate genre and language choices
    genres = get_genres()
    languages = get_languages()
    
    form.genre.choices = [('', 'All Genres')] + [(g, g) for g in genres]
    form.language.choices = [('', 'All Languages')] + [(l, l) for l in languages]
    
    # Get filter parameters from request
    filters = {}
    if 'title' in request.args and request.args['title']:
        filters['title'] = request.args['title']
    if 'author' in request.args and request.args['author']:
        filters['author'] = request.args['author']
    if 'genre' in request.args and request.args['genre']:
        filters['genre'] = request.args['genre']
        form.genre.data = request.args['genre']
    if 'language' in request.args and request.args['language']:
        filters['language'] = request.args['language']
        form.language.data = request.args['language']
    if 'year_from' in request.args and request.args['year_from']:
        filters['year_from'] = int(request.args['year_from'])
    if 'year_to' in request.args and request.args['year_to']:
        filters['year_to'] = int(request.args['year_to'])
    if 'available' in request.args:
        filters['available'] = True
    
    # Get sort parameters
    sort_by = request.args.get('sort_by', 'title')
    sort_order = request.args.get('sort_order', 'asc')
    
    form.sort_by.data = sort_by
    form.sort_order.data = sort_order
    
    # Get books
    if 'query' in request.args and request.args['query']:
        query = request.args['query']
        form.query.data = query
        books, total_pages, total_items = search_books(query, page=page, per_page=per_page)
    else:
        books, total_pages, total_items = get_all_books(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters
        )
    

    # Calculamos los valores de los elementos a mostrar
    start_item = (page - 1) * per_page + 1
    end_item = min(page * per_page, total_items)
    page_range = range(max(1, page-2), min(total_pages+1, page+3))

    # Pasamos esos valores calculados a la plantilla
    return render_template(
        'book_list.html',
        books=books,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total_items,
        start_item=start_item,  # Este es el valor calculado
        end_item=end_item,      # Este es el valor calculado
        form=form,
        page_range=page_range   # Calculado previamente
    )

@book_bp.route('/<int:book_id>')
def book_detail(book_id):
    """Display details for a specific book."""
    book = get_book_by_id(book_id)
    if not book:
        abort(404)
    
    # Track book view if user is logged in
    if current_user.is_authenticated:
        track_book_view(current_user.id, book_id)
    
    # Get reviews
    reviews = get_book_reviews(book_id)
    average_rating = get_average_rating(book_id) or 0
    
    # Get recommendations
    recommendations = []
    if current_user.is_authenticated:
        recommendations = get_recommendations_by_book(book_id)
    
    # Check if user has already reviewed this book
    user_review = None
    if current_user.is_authenticated:
        for review in reviews:
            if review.get('user_id') == current_user.id:
                user_review = review
                break
    
    # Initialize review form
    review_form = ReviewForm()
    if user_review:
        review_form.rating.data = user_review.get('rating', 0)
        review_form.text.data = user_review.get('text', '')
    
    return render_template(
        'book_detail.html',
        book=book,
        reviews=reviews,
        average_rating=average_rating,
        recommendations=recommendations,
        review_form=review_form,
        user_review=user_review
    )

@book_bp.route('/<int:book_id>/review', methods=['POST'])
@login_required
def add_book_review(book_id):
    """Add or update a review for a book."""
    form = ReviewForm()
    if form.validate_on_submit():
        try:
            # Check if user has already reviewed this book
            reviews = get_book_reviews(book_id)
            user_review = None
            for review in reviews:
                if review.get('user_id') == current_user.id:
                    user_review = review
                    break
            
            if user_review:
                # Update existing review
                from models.mongodb_models import Review
                Review.update_one(
                    {'_id': user_review['_id']},
                    {'$set': {'rating': form.rating.data, 'text': form.text.data}}
                )
                flash('Your review has been updated.', 'success')
            else:
                # Add new review
                add_review(book_id, current_user.id, form.rating.data, form.text.data)
                flash('Your review has been added.', 'success')
            
            # Track interaction
            track_user_interaction(current_user.id, book_id, 'review', {'rating': form.rating.data})
            
        except ValueError as e:
            flash(str(e), 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('book_routes.book_detail', book_id=book_id))

@book_bp.route('/<int:book_id>/lend', methods=['POST'])
@login_required
def lend_book_route(book_id):
    """Lend a book to the current user."""
    success, loan_or_error = lend_book(book_id, current_user.id)
    
    if success:
        flash('Book borrowed successfully.', 'success')
        # Track interaction
        track_user_interaction(current_user.id, book_id, 'loan')
    else:
        flash(loan_or_error, 'danger')
    
    return redirect(url_for('book_routes.book_detail', book_id=book_id))

@book_bp.route('/loans/<string:loan_id>/return', methods=['POST'])
@login_required
def return_book_route(loan_id):
    """Return a book."""
    success, message = return_book(loan_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    # Redirect to user loans page or referrer
    next_page = request.args.get('next') or request.referrer or url_for('user_routes.user_loans')
    return redirect(next_page)

@book_bp.route('/<int:book_id>/read')
@login_required
def read_book(book_id):
    """Read a book's content."""
    book = get_book_by_id(book_id)
    if not book:
        abort(404)
    
    # Get book content
    book_content = get_book_content(book_id)
    print(f"Book ID: {book_id}, Content: {book_content}")
    
    if not book_content:
        flash('Book content not available.', 'warning')
        return redirect(url_for('book_routes.book_detail', book_id=book_id))
    
    return render_template(
        'book_read.html',
        book=book,
        content=book_content
    )

@book_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def new_book():
    """Create a new book."""
    form = BookForm()
    
    if form.validate_on_submit():
        # Handle cover image upload
        cover_image_path = None
        if form.cover_image.data:
            filename = secure_filename(form.cover_image.data.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.cover_image.data.save(filepath)
            cover_image_path = f"covers/{filename}"
        
        # Create book
        success, book_or_error = create_book(
            title=form.title.data,
            author=form.author.data,
            year=form.year.data,
            isbn=form.isbn.data,
            language=form.language.data,
            genre=form.genre.data,
            publisher=form.publisher.data,
            description=form.description.data,
            cover_image_path=cover_image_path,
            available_copies=form.available_copies.data,
            total_copies=form.total_copies.data
        )
        
        if success:
            flash('Book created successfully.', 'success')
            return redirect(url_for('book_routes.book_detail', book_id=book_or_error.id))
        else:
            flash(book_or_error, 'danger')
    
    return render_template('book_form.html', form=form, title='New Book')

@book_bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def edit_book(book_id):
    """Edit a book."""
    book = get_book_by_id(book_id)
    if not book:
        abort(404)
    
    form = BookForm(obj=book)
    
    if form.validate_on_submit():
        # Handle cover image upload
        cover_image_path = book.cover_image_path
        if form.cover_image.data:
            filename = secure_filename(form.cover_image.data.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.cover_image.data.save(filepath)
            cover_image_path = f"covers/{filename}"
        
        # Update book
        success, book_or_error = update_book(
            book_id=book_id,
            title=form.title.data,
            author=form.author.data,
            year=form.year.data,
            isbn=form.isbn.data,
            language=form.language.data,
            genre=form.genre.data,
            publisher=form.publisher.data,
            description=form.description.data,
            cover_image_path=cover_image_path,
            available_copies=form.available_copies.data,
            total_copies=form.total_copies.data
        )
        
        if success:
            flash('Book updated successfully.', 'success')
            return redirect(url_for('book_routes.book_detail', book_id=book_id))
        else:
            flash(book_or_error, 'danger')
    
    return render_template('book_form.html', form=form, book=book, title='Edit Book')

@book_bp.route('/<int:book_id>/content', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def edit_book_content(book_id):
    """Edit a book's content."""
    book = get_book_by_id(book_id)
    if not book:
        abort(404)
    
    # Get existing content
    book_content = get_book_content(book_id)
    
    form = BookContentForm()
    
    if request.method == 'GET' and book_content:
        form.content.data = book_content.get('content', '')
    
    if form.validate_on_submit():
        # Update book content
        success = update_book_content(book_id, form.content.data)
        
        if success:
            flash('Book content updated successfully.', 'success')
            return redirect(url_for('book_routes.book_detail', book_id=book_id))
        else:
            flash('Error updating book content.', 'danger')
    
    return render_template('book_content_form.html', form=form, book=book, title='Edit Book Content')

@book_bp.route('/<int:book_id>/delete', methods=['POST'])
@login_required
@require_role('admin')
def delete_book_route(book_id):
    """Delete a book."""
    success, message = delete_book(book_id)
    
    if success:
        flash(message, 'success')
        return redirect(url_for('book_routes.book_list'))
    else:
        flash(message, 'danger')
        return redirect(url_for('book_routes.book_detail', book_id=book_id))

@book_bp.route('/search')
def search():
    """Search for books."""
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    if not query:
        return redirect(url_for('book_routes.book_list'))
    
    books, total_pages, total_items = search_books(query, page=page, per_page=per_page)
    
    return render_template(
        'book_search_results.html',
        books=books,
        query=query,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total_items
    )

@book_bp.route('/api/search')
def api_search():
    """API endpoint for searching books."""
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    books, total_pages, total_items = search_books(query, page=page, per_page=per_page)
    
    # Convert books to JSON-serializable format
    books_json = []
    for book in books:
        books_json.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'year': book.year,
            'isbn': book.isbn,
            'cover_image_path': book.cover_image_path,
            'is_available': book.is_available
        })
    
    return jsonify({
        'books': books_json,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_items': total_items
    })

@book_bp.route('/<int:book_id>/mark_as_read', methods=['POST'])
@login_required
def mark_as_read(book_id):
    """Marca un libro como leído por el usuario actual."""
    try:
        # Registrar la acción en LoanHistory o en otra estructura
        LoanHistory.insert_one({
            'user_id': current_user.id,
            'book_id': book_id,
            'action': 'read',
            'timestamp': datetime.utcnow()
        })
        flash('Libro marcado como leído.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error marcando libro como leído: {str(e)}")
        flash('Error al marcar el libro como leído.', 'danger')
    
    return redirect(url_for('book_routes.book_detail', book_id=book_id))