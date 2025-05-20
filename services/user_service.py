"""
User service for LibriMongo application.
Handles user profile management, reading history, and preferences.
"""

from flask import current_app
from models.mariadb_models import User, Loan, Book, db
from models.mongodb_models import Review, LoanHistory, UserPreferences
from services.recommendation_service import get_recommendations_for_user, track_user_interaction
from utils.helpers import log_activity
from datetime import datetime, timezone
from dateutil.parser import parse

def get_user_by_id(user_id):
    """
    Get a user by their ID.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        User: The user object, or None if not found
    """
    return User.query.get(user_id)

def get_user_profile(user_id):
    """
    Get a user's profile information.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        dict: The user's profile information
    """
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # Get user's active loans
    active_loans = Loan.query.filter_by(user_id=user_id, is_returned=False).all()
    
    # Get user's reading history
    loan_history = list(LoanHistory.get_by_user(user_id))
    total_books_read = len({loan['book_id'] for loan in loan_history if loan.get('is_returned', False)})
    
    # Get user's reviews
    reviews = list(Review.find({'user_id': user_id}))
    
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_admin': user.is_admin,
        'created_at': user.created_at,
        'active_loans': active_loans,
        'total_books_read': total_books_read,
        'total_reviews': len(reviews)
    }

def get_user_reading_history(user_id, page=1, per_page=10, include_active=True):
    # Obtener historial de préstamos
    loan_history = list(LoanHistory.find(
        {'user_id': user_id},
        sort=[('loan_date', -1)]
    ))
    
    # Filtrar préstamos activos si es necesario
    if not include_active:
        loan_history = [loan for loan in loan_history if loan.get('is_returned', False)]
    
    clean_loan_history = []
    for loan in loan_history:
        loan_date = loan.get('loan_date')
        if not loan_date:
            continue  # Ignorar préstamos sin fecha
        
        # Convertir cadena a datetime si es necesario
        if isinstance(loan_date, str):
            try:
                loan['loan_date'] = parse(loan_date)
            except Exception:
                continue  # Ignorar si no se puede parsear
        
        clean_loan_history.append(loan)
    
    # Obtener detalles del libro para cada préstamo limpio
    history_items = []
    for loan in clean_loan_history:
        book = Book.query.get(loan['book_id'])
        if book:
            loan['id'] = str(loan['_id'])
            history_items.append({
                'loan': loan,
                'book': book
            })
    
    # Paginación manual
    total_items = len(history_items)
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    return history_items[start_idx:end_idx], total_pages, total_items

def get_user_reviews(user_id, page=1, per_page=10):
    """
    Get reviews written by a user.
    
    Args:
        user_id (int): The ID of the user
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        
    Returns:
        tuple: (reviews_with_books, total_pages, total_items)
    """
    # Get reviews from MongoDB
    skip = (page - 1) * per_page
    reviews = list(Review.find(
        {'user_id': user_id},
        sort=[('created_at', -1)],
        skip=skip,
        limit=per_page
    ))
    
    # Get total count for pagination
    total_items = Review.get_collection().count_documents({'user_id': user_id})
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    # Get book details for each review
    reviews_with_books = []
    for review in reviews:
        book = Book.query.get(review['book_id'])
        if book:
            reviews_with_books.append({
                'review': review,
                'book': book
            })
    
    return reviews_with_books, total_pages, total_items

def get_user_recommendations(user_id, limit=10):
    """
    Get personalized book recommendations for a user.
    
    Args:
        user_id (int): The ID of the user
        limit (int): Maximum number of recommendations to return
        
    Returns:
        list: Recommended books
    """
    return get_recommendations_for_user(user_id, limit=limit)

def track_book_view(user_id, book_id):
    """
    Track when a user views a book.
    
    Args:
        user_id (int): The ID of the user
        book_id (int): The ID of the book
        
    Returns:
        bool: Whether the tracking was successful
    """
    return track_user_interaction(user_id, book_id, 'view')

def get_user_active_loans(user_id):
    loans = Loan.query.filter_by(user_id=user_id, is_returned=False).all()
    active_loans = []
    for loan in loans:
        book = Book.query.get(loan.book_id)
        if book:
            active_loans.append({
                'loan': loan,
                'book': book,
                'is_overdue': loan.is_overdue
            })
    print(f"Active loans for user {user_id}: {active_loans} (type: {type(active_loans)})")  # Depuración
    return active_loans or []

def get_user_reading_preferences(user_id):
    """
    Get a user's reading preferences.

    Args:
        user_id (int): The ID of the user

    Returns:
        dict: Reading preferences
    """
    preferences = UserPreferences.get_preferences(user_id)
    return {
        'preferred_genres': preferences.get('preferred_genres', []),
        'preferred_authors': preferences.get('preferred_authors', []),
        'reading_frequency': preferences.get('reading_frequency', 'New reader')
    }

def update_user_preferences(user_id, preferred_genres=None, preferred_authors=None, reading_frequency=None):
    """
    Update a user's reading preferences.

    Args:
        user_id (int): The ID of the user
        preferred_genres (list, optional): Preferred genres
        preferred_authors (list, optional): Preferred authors
        reading_frequency (str, optional): Reading frequency

    Returns:
        bool: Whether the update was successful
    """
    try:
        UserPreferences.update_preferences(
            user_id=user_id,
            preferred_genres=preferred_genres,
            preferred_authors=preferred_authors,
            reading_frequency=reading_frequency
        )
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
        return False

def get_overdue_loans(user_id):
    """
    Get a user's overdue loans.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        list: Overdue loans with book details
    """
    now = datetime.now(timezone.utc)
    loans = Loan.query.filter(
        Loan.user_id == user_id,
        Loan.is_returned == False,
        Loan.due_date < now
    ).all()
    
    overdue_loans = []
    for loan in loans:
        book = Book.query.get(loan.book_id)
        if book:
            overdue_loans.append({
                'loan': loan,
                'book': book,
                'days_overdue': (now - loan.due_date).days
            })
    
    return overdue_loans

def get_user_statistics(user_id):
    """
    Get statistics about a user's reading habits.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        dict: User statistics
    """
    # Get loan history
    loan_history = list(LoanHistory.get_by_user(user_id))
    
    # Calculate statistics
    total_books_read = len({loan['book_id'] for loan in loan_history if loan.get('action') == 'read'})
    
    # Calculate average rating given
    reviews = list(Review.find({'user_id': user_id}))
    ratings = [review.get('rating', 0) for review in reviews if 'rating' in review]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Calculate books read per month (last 6 months)
    now = datetime.now(timezone.utc)
    months = {}
    for i in range(6):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        months[(year, month)] = 0
    
    for loan in loan_history:
        if 'loan_date' in loan:
            loan_date = loan['loan_date']
            if (loan_date.year, loan_date.month) in months:
                months[(loan_date.year, loan_date.month)] += 1
    
    monthly_reads = [{'year': year, 'month': month, 'count': count} 
                    for (year, month), count in months.items()]
    
    return {
        'total_books_read': total_books_read,
        'total_reviews': len(reviews),
        'average_rating': avg_rating,
        'monthly_reads': monthly_reads
    }